"""
Utility functions for tool management and Qdrant operations.
Extracted from routes/chatbot.py to avoid dependencies on deprecated code.
"""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from bson import ObjectId
from fastapi import HTTPException
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import PointStruct, VectorParams, Distance

from database.mongodb import mongodb

# Initialize OpenAI client for embeddings
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize database connections
database = mongodb.get_database()
tools_collection = database.get_collection("Tools")
project_collection = database.get_collection("Project")


def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    """
    Simple character-based chunker. Produces chunks of <= max_chars.
    """
    if not text:
        return []
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks


def create_embeddings_for_texts(texts, model: str = "text-embedding-3-small"):
    """
    Creates embeddings via OpenAI for a list of strings (batched).
    Returns list of embedding vectors in same order as texts.
    """
    if not texts:
        return []

    resp = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in resp.data]


def upsert_embeddings_to_qdrant(
        mongo_hex_id: str,
        embeddings: List[List[float]],
        texts: List[str],
        extra_payload: Optional[dict] = None,
        collection_name: Optional[str] = None
) -> dict:
    """
    Upsert embeddings to Qdrant vector database.
    """
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
        if extra_payload:
            payload.update(extra_payload)

        points.append(PointStruct(id=point_id, vector=vec, payload=payload))

    qclient.upsert(collection_name=collection_name, points=points)
    return {"status": "ok", "num_points": len(points), "collection": collection_name}


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


def create_and_store_tool_embeddings(tool_data: Dict[str, Any], tool_id: str):
    """
    Create embeddings for a tool and store them in Qdrant tools collection.
    """
    # Create text representation for embedding
    tool_text = f"{tool_data['name']} {tool_data['description']} {tool_data.get('category', '')} {' '.join(tool_data.get('tags', []))}"

    # Generate embedding
    embedding = create_embeddings_for_texts([tool_text],
                                            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))

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


def update_project(project_id: str, update_data: dict):
    """
    Update a project document in MongoDB.
    Extracted from routes/project.py to avoid route dependencies.
    """
    result = project_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated", "modified": bool(result.modified_count)}


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
    query_embedding = create_embeddings_for_texts([query],
                                                  model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))

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


async def extract_and_save_tools_from_project(project_id: str):
    """
    Extract tools from project.tool_generation and save them to tools_collection + Qdrant.
    This is triggered after tool generation is done.
    """
    
    # 1. Get the project and check if it has tool_generation data
    project = project_collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    if "tool_generation" not in project:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Project has no tool_generation data")

    tool_generation = project["tool_generation"]

    # Extract tools from tool_generation.tools
    if "tools" not in tool_generation:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No tools found in tool_generation")

    tools_list = tool_generation["tools"]
    print(f"🔧 Found {len(tools_list)} tools in project {project_id}")

    saved_tools = []
    failed_tools = []

    # 2. Save each tool to tools_collection and Qdrant
    for tool in tools_list:
        try:
            # Ensure required fields exist
            if not all(key in tool for key in ["name", "description", "price", "risk_factors", "safety_measures"]):
                print(f"⚠️ Skipping tool with missing required fields: {tool.get('name', 'unknown')}")
                failed_tools.append({"tool": tool, "error": "missing_required_fields"})
                continue

            # Check if tool already exists in tools_collection (avoid duplicates)
            existing_tool = tools_collection.find_one({"name": tool["name"]})
            if existing_tool:
                print(f"✅ Tool '{tool['name']}' already exists, skipping")
                saved_tools.append({"tool_id": str(existing_tool["_id"]), "status": "already_exists"})
                continue

            # Save new tool
            tool_id = store_tool_in_database(tool)
            embedding_result = create_and_store_tool_embeddings(tool, tool_id)

            saved_tools.append({
                "tool_id": tool_id,
                "name": tool["name"],
                "status": "saved",
                "qdrant_result": embedding_result
            })

            print(f"✅ Saved tool: {tool['name']} (ID: {tool_id})")

        except Exception as e:
            print(f"❌ Failed to save tool {tool.get('name', 'unknown')}: {e}")
            failed_tools.append({"tool": tool.get('name', 'unknown'), "error": str(e)})

    # 3. Update project to mark tools as processed
    update_project(project_id, {"tools_extracted_to_collection": True, "tools_extraction_date": datetime.utcnow()})

    return {
        "message": f"Processed {len(tools_list)} tools from project",
        "project_id": project_id,
        "saved_tools": len(saved_tools),
        "failed_tools": len(failed_tools),
        "tools": saved_tools,
        "failures": failed_tools
    }
