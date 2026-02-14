from datetime import datetime
from typing import List, Dict, Any

from bson import ObjectId
from fastapi import HTTPException
from pymongo.collection import Collection
from pymongo.database import Database
from qdrant_client.http.exceptions import UnexpectedResponse

from config.settings import get_settings
from database.mongodb import mongodb
from database.qdrant import create_embeddings_for_texts, upsert_embeddings_to_qdrant, search_similar_vectors, \
    get_qdrant_client

settings = get_settings()

database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")
tools_collection: Collection = database.get_collection("Tools")


def store_tool_in_database(tool_data: Dict[str, Any]) -> str:
    """
    Store a tool in the MongoDB tools collection.
    Returns the tool ID.
    """
    tool_doc = {
        "name": tool_data["name"],
        "description": tool_data["description"],
        "price": tool_data["price"],
        "risk_factors": tool_data["risk_factors"],
        "safety_measures": tool_data["safety_measures"],
        "image_link": tool_data.get("image_link"),
        "amazon_link": tool_data.get("amazon_link"),
        "category": tool_data.get("category", "general"),
        "tags": tool_data.get("tags", []),
        "created_at": datetime.utcnow(),
        "usage_count": 1,
        "last_used": datetime.utcnow()
    }

    result = tools_collection.insert_one(tool_doc)
    return str(result.inserted_id)


def create_and_store_tool_embeddings(tool_data: Dict[str, Any], tool_id: str):
    """
    Create embeddings for a tool and store them in Qdrant tools collection.
    """
    # Create text representation for embedding
    tool_text = f"{tool_data['name']} {tool_data['description']} {tool_data.get('category', '')} {' '.join(tool_data.get('tags', []))}"

    # Generate embedding
    embedding = create_embeddings_for_texts([tool_text],
                                            model=settings.OPENAI_EMBEDDING_MODEL)

    if not embedding:
        return {"status": "embedding_failed"}

    # Store in Qdrant tools collection
    qresult = upsert_embeddings_to_qdrant(
        mongo_hex_id=tool_id,
        embeddings=embedding,
        texts=[tool_text],
        extra_payload={
            "tool_id": tool_id,
            "tool_name": tool_data["name"],
            "category": tool_data.get("category", "general"),
            "collection": "tools"
        },
        collection_name="tools"
    )
    return qresult


# Qdrant operations are now centralized in database/qdrant.py


def find_similar_tools(query: str, limit: int = 5, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find similar tools in Qdrant based on semantic similarity.
    Uses centralized Qdrant operations from database/qdrant.py
    """
    # Generate embedding for the query
    query_embedding = create_embeddings_for_texts([query],
                                                  model=settings.OPENAI_EMBEDDING_MODEL)

    if not query_embedding:
        return []

    try:
        # Search in tools collection using centralized function
        search_result = search_similar_vectors(
            query_vector=query_embedding[0],
            collection_name="tools",
            limit=limit,
            score_threshold=similarity_threshold
        )

        similar_tools = []
        for result in search_result:
            # Note: search_similar_vectors already filters by score_threshold, but we check again for safety
            score = getattr(result, "score", 0.0)
            if score >= similarity_threshold:
                # Get tool details from MongoDB
                tool_id = result.payload.get("tool_id")
                if tool_id:
                    tool_doc = tools_collection.find_one({"_id": ObjectId(tool_id)})
                    if tool_doc:
                        tool_info = {
                            "tool_id": str(tool_doc["_id"]),
                            "name": tool_doc["name"],
                            "description": tool_doc["description"],
                            "price": tool_doc["price"],
                            "risk_factors": tool_doc["risk_factors"],
                            "safety_measures": tool_doc["safety_measures"],
                            "image_link": tool_doc.get("image_link"),
                            "amazon_link": tool_doc.get("amazon_link"),
                            "category": tool_doc.get("category"),
                            "similarity_score": score,
                            "usage_count": tool_doc.get("usage_count", 0)
                        }
                        similar_tools.append(tool_info)

        return similar_tools

    except Exception as e:
        print(f"Error searching tools in Qdrant: {e}")
        return []


def update_tool_usage(tool_id: str):
    """
    Update the usage count and last used timestamp for a tool.
    """
    tools_collection.update_one(
        {"_id": ObjectId(tool_id)},
        {
            "$inc": {"usage_count": 1},
            "$set": {"last_used": datetime.utcnow()}
        }
    )


# Qdrant operations are now centralized in database/qdrant.py


def similar_by_project(project_id: str, top_k: int = 2, collection_name: str = "projects"):
    """
    RAG decision logic (strictly implements the 3 cases you specified):
      1) best similarity >= 0.90 -> copy tools & steps from matched project into new project
      2) 0.60 <= similarity < 0.90 -> call ToolsAgent & StepJSONAgent (or fallback LLM) to *modify*
           tools & steps and store modified versions for the new project
      3) similarity < 0.60 -> do nothing (leave project as-is)
    The function assumes the project's summary has already been saved in Mongo (that's why
    save_information must be called before this function).
    """
    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    project = project_collection.find_one({"_id": obj_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

 
    summary = project.get("summary")
    if not summary or not str(summary).strip():
        raise HTTPException(status_code=400, detail="Project has no summary or user_description to embed")

    
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    try:
        embeddings = create_embeddings_for_texts([summary], model=model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {str(e)}")

    print(f"🔍 Created embedding for project {project_id} using model {model_name}")
    if not embeddings:
        raise HTTPException(status_code=500, detail="Embedding API returned no embedding")
    query_vec = embeddings[0]

    print(f"🔍 Querying Qdrant for similar projects to {project_id} in collection {collection_name}")
    # qdrant client
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if not qdrant_url or not qdrant_api_key:
        print(f"❌ QDRANT config missing in environment")
        raise HTTPException(status_code=500, detail="QDRANT config missing in environment")
    qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)

    print(f"🔍 Ensuring Qdrant collection {collection_name} exists")
    # ensure collection exists
    try:
        qclient.get_collection(collection_name=collection_name)
    except UnexpectedResponse as ex:
        if getattr(ex, "status_code", None) == 404:
            return {"query_project_id": project_id, "collection": collection_name, "matches": []}
        else:
            print(f"❌ Qdrant error: {str(ex)}")
            raise Exception(status_code=500, detail=f"Qdrant error: {str(ex)}")

    # search (request a few extra to allow skipping self-matches)
    limit = top_k + 5
    try:
        hits = qclient.search(collection_name=collection_name, query_vector=query_vec, limit=limit, with_payload=True)
    except Exception as e:
        print(f"❌ Qdrant search error: {str(e)}")
        raise Exception(status_code=500, detail=f"Qdrant search failed: {str(e)}")

    results = []
    best_hit = None
    best_score = -1.0

    print(f"🔍 Found {len(hits)} hits in Qdrant for project {project_id}")
   
    for hit in hits:
        payload = hit.payload or {}
        mongo_id_str = payload.get("mongo_id")
        text_preview = payload.get("text_preview")
        chunk_index = payload.get("chunk_index")
        score = getattr(hit, "score", None)

        # skip exact self-match
        if mongo_id_str and mongo_id_str == str(project.get("_id")):
            continue

        try:
            s = float(score) if score is not None else -1.0
        except Exception:
            s = -1.0

        print(f"🔍 Hit: mongo_id={mongo_id_str} score={s} text_preview={text_preview}")
        
        matched_obj = None
        matched_project_id = None
        if mongo_id_str:
            try:
                matched_obj = project_collection.find_one({"_id": ObjectId(mongo_id_str)})
                if matched_obj:
                    matched_project_id = str(matched_obj["_id"])
            except Exception:
                matched_obj = None

        
        if s > best_score:
            best_score = s
            best_hit = {"hit": hit, "payload": payload, "score": s, "mongo_id": mongo_id_str}

        proj_summary = None
        if matched_obj:
            proj_summary = matched_obj.get("summary") or matched_obj.get("user_description")

        if not proj_summary:
            proj_summary = text_preview

        results.append({
            "point_id": str(hit.id),
            "project_id": matched_project_id,
            "mongo_id_payload": mongo_id_str,
            "chunk_index": chunk_index,
            "text_preview": text_preview,
            "summary": proj_summary,
            "score": s
        })

        if len(results) >= top_k:
            break

    print(f"🔍 Best score for project {project_id} is {best_score}")
    if not best_hit:
        return None

   
    matched_mongo_id = best_hit.get("mongo_id")
    matched_doc = None
    if matched_mongo_id:
        try:
            matched_doc = project_collection.find_one({"_id": ObjectId(matched_mongo_id)})
            return {"project_id": matched_mongo_id, "best_score": best_score}
        except Exception:
            matched_doc = None
            return None
    else:
        return None
