
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
import os
import uuid
from db import project_collection, tools_collection
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from bson import ObjectId
from openai import OpenAI
from qdrant_client.http.exceptions import UnexpectedResponse
from planner import ToolsAgent, StepsAgentJSON

client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    embedding = create_embeddings_for_texts([tool_text], model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    
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

def upsert_embeddings_to_qdrant(
        mongo_hex_id: str,
        embeddings: List[List[float]],
        texts: List[str],
        extra_payload: Optional[dict] = None,
        collection_name: Optional[str] = None
    ) -> dict:

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection_name = collection_name or "projects"

    if not qdrant_url or not qdrant_api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in env")

    qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)

    if not embeddings:
        return {"status": "no_embeddings"}

    vector_size = len(embeddings[0])

    
    try:
        qclient.get_collection(collection_name=collection_name)
    except UnexpectedResponse as ex:
        if ex.status_code == 404:
            
            qclient.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        else:
            raise

    
    points = []
    for idx, (vec, txt) in enumerate(zip(embeddings, texts)):
        unique_str = f"{mongo_hex_id}-{idx}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_str))

        payload = {
            "mongo_id": mongo_hex_id,
            "chunk_index": idx,
            "text_preview": txt,
        }
        print(payload)
        if extra_payload:
            payload.update(extra_payload)

        points.append(PointStruct(id=point_id, vector=vec, payload=payload))

    qclient.upsert(collection_name=collection_name, points=points)
    return {"status": "ok", "num_points": len(points), "collection": collection_name}

def find_similar_tools(query: str, limit: int = 5, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find similar tools in Qdrant based on semantic similarity.
    """
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url or not qdrant_api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in env")
    
    qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)
    
    # Generate embedding for the query
    query_embedding = create_embeddings_for_texts([query], model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    
    if not query_embedding:
        return []
    
    try:
        # Search in tools collection
        search_result = qclient.search(
            collection_name="tools",
            query_vector=query_embedding[0],
            limit=limit,
            score_threshold=similarity_threshold
        )
        
        similar_tools = []
        for result in search_result:
            if result.score >= similarity_threshold:
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
                            "similarity_score": result.score,
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

def create_embeddings_for_texts(texts, model: str = "text-embedding-3-small"):
    """
    Creates embeddings via OpenAI for a list of strings (batched).
    Returns list of embedding vectors in same order as texts.
    """
    if not texts:
        return []
    
    resp = client.embeddings.create(model=model, input=texts)
    
    return [item.embedding for item in resp.data]

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

 
    summary = project.get("summary") or project.get("user_description")
    if not summary or not str(summary).strip():
        raise HTTPException(status_code=400, detail="Project has no summary or user_description to embed")

    
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    try:
        embeddings = create_embeddings_for_texts([summary], model=model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {str(e)}")

    if not embeddings:
        raise HTTPException(status_code=500, detail="Embedding API returned no embedding")
    query_vec = embeddings[0]

    # qdrant client
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if not qdrant_url or not qdrant_api_key:
        raise HTTPException(status_code=500, detail="QDRANT config missing in environment")
    qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)

    # ensure collection exists
    try:
        qclient.get_collection(collection_name=collection_name)
    except UnexpectedResponse as ex:
        if getattr(ex, "status_code", None) == 404:
            return {"query_project_id": project_id, "collection": collection_name, "matches": []}
        else:
            raise HTTPException(status_code=500, detail=f"Qdrant error: {str(ex)}")

    # search (request a few extra to allow skipping self-matches)
    limit = top_k + 5
    try:
        hits = qclient.search(collection_name=collection_name, query_vector=query_vec, limit=limit, with_payload=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant search failed: {str(e)}")

    results = []
    best_hit = None
    best_score = -1.0

   
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

   
    if best_score >= 0.90:
        if matched_doc:
            matched_tools = matched_doc.get("tools") or matched_doc.get("project_tools") or []
            matched_steps = matched_doc.get("steps") or matched_doc.get("project_steps") or matched_doc.get("step_list") or []
            
            project_collection.find_one_and_update(
                {"_id": obj_id},
                {"$set": {"tools": matched_tools, "steps": matched_steps}},
                upsert=True
            )
            return {
                "query_project_id": project_id,
                "collection": collection_name,
                "best_match": {"mongo_id": matched_mongo_id, "score": best_score},
                "action": "copied_tools_and_steps_from_matched_project",
                "matches": results
            }
        else:
            
            return {
                "query_project_id": project_id,
                "collection": collection_name,
                "best_match": {"mongo_id": matched_mongo_id, "score": best_score},
                "action": "matched_point_no_mongo_doc",
                "matches": results
            }

    
    if 0.60 <= best_score < 0.90:
        if not matched_doc:
            return {
                "query_project_id": project_id,
                "collection": collection_name,
                "best_match": {"mongo_id": matched_mongo_id, "score": best_score},
                "action": "no_mongo_doc_to_adapt",
                "matches": results
            }
        base_steps = matched_doc.get("steps") or matched_doc.get("project_steps") or matched_doc.get("step_list") or []
        tools_list=matched_doc['tool_generation']['tools']
        matched_tools=[]
        
        for i in tools_list:
            tool_dict={}
            tool_dict['name']=i['name']
            tool_dict['description']=i['description']
            tool_dict['price']=i['price']
            tool_dict['risk_factors']=i['risk_factors']
            tool_dict['safety_measures']=i['safety_measures']
            matched_tools.append(tool_dict)

        matched_summary = matched_doc.get("summary") or matched_doc.get("user_description") or ""

        def compute_step_changes(base: List[Dict], new: List[Dict]):
            
            def title_key(s):
                return (s.get("title") or s.get("step_title") or "").strip().lower()

            base_map = { title_key(s): s for s in base if title_key(s) }
            new_map = { title_key(s): s for s in new if title_key(s) }


            added = []
            removed = []
            updated = []

           
            for k, s in new_map.items():
                if k not in base_map:
                    added.append(s)
                else:
                    b = base_map[k]
                    diffs = {}
                    
                    for fld in ("instructions", "tools_needed", "est_time_min", "time_text", "safety_warnings", "tips"):
                        bv = b.get(fld)
                        nv = s.get(fld)
                        if bv != nv:
                            diffs[fld] = {"old": bv, "new": nv}
                    if diffs:
                        updated.append({"title": s.get("title") or s.get("step_title"), "diffs": diffs, "old": b, "new": s})

            for k, s in base_map.items():
                if k not in new_map:
                    removed.append(s)

            
            if not base_map or not new_map:
                
                min_len = min(len(base), len(new))
                for i in range(min_len):
                    b = base[i]
                    n = new[i]
                    diffs = {}
                   
                    if b.get("title") != n.get("title"):
                        diffs["title"] = {"old": b.get("title"), "new": n.get("title")}
                    if b.get("instructions") != n.get("instructions"):
                        diffs["instructions"] = {"old": b.get("instructions"), "new": n.get("instructions")}
                    if diffs:
                        updated.append({"index": i, "diffs": diffs, "old": b, "new": n})
                if len(new) > len(base):
                    added.extend(new[len(base):])
                if len(base) > len(new):
                    removed.extend(base[len(new):])

            return {"added": added, "removed": removed, "updated": updated}

        try:
            tools_agent_instance = ToolsAgent(new_summary=summary, matched_summary=matched_summary, matched_tools=tools_list)
            tools_res = tools_agent_instance.recommend_tools(summary=summary, include_json=True)
            
        except Exception as e:
           
            tools_res = {"error": str(e)}

   

        
        try:
            steps_agent_instance = StepsAgentJSON(new_summary=summary, matched_summary=matched_summary, matched_tools=tools_res, matched_steps=base_steps)
            steps_res = steps_agent_instance.generate(tools={"tools": tools_res, "raw": None}, summary=summary)
            print(steps_res)
            modified_steps = steps_res.get("steps", []) if isinstance(steps_res, dict) else []
        except Exception as e:
            modified_steps = base_steps
            steps_res = {"error": str(e)}

        steps_changes = compute_step_changes(base_steps, modified_steps)

        project_collection.find_one_and_update(
            {"_id": obj_id},
            {"$set": {
                "tools": tools_res,
                "steps": modified_steps,
                "rag_debug": {
                    "matched_project_id": matched_mongo_id,
                    "similarity": best_score,
                    "tools_agent_raw": tools_res,
                    "steps_agent_raw": steps_res,
                    "matched_summary": matched_summary,
                    "new_summary": summary
                }
            }},
            upsert=True
        )

        return {
            "query_project_id": project_id,
            "collection": collection_name,
            "best_match": {"mongo_id": matched_mongo_id, "score": best_score},
            "action": "adapted_tools_and_steps",
            "tools_changes": tools_res,
            "steps_changes": steps_changes,
            "raw_tools_agent_output": tools_res,
            "raw_steps_agent_output": steps_res,
            "matches": results
        }

    return {
        "query_project_id": project_id,
        "collection": collection_name,
        "best_match": {"mongo_id": matched_mongo_id, "score": best_score},
        "action": "no_action_low_similarity",
        "matches": results
    }