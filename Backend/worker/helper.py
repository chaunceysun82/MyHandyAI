
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import base64
import uuid
from pymongo import DESCENDING
import pickle
from db import conversations_collection, project_collection, tools_collection
from datetime import datetime
from .project import update_project
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from bson import ObjectId
from openai import OpenAI
from qdrant_client.http.exceptions import UnexpectedResponse
from dotenv import load_dotenv

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