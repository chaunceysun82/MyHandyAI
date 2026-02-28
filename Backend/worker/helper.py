from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import logging
import requests

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

logger = logging.getLogger(__name__)


def _qdrant_base_and_headers() -> Tuple[str, Dict[str, str]]:
    """
    Return base URL and headers for Qdrant REST calls using settings.
    Expects settings.QDRANT_URL and optionally settings.QDRANT_API_KEY.
    """
    base = getattr(settings, "QDRANT_URL", None)
    if not base:
        raise RuntimeError("QDRANT_URL not configured in settings")
    base = base.rstrip("/")
    headers: Dict[str, str] = {}
    api_key = getattr(settings, "QDRANT_API_KEY", None)
    if api_key:
        # qdrant expects 'api-key' header for API key auth
        headers["api-key"] = api_key
    return base, headers


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
        logger.exception(f"Error searching tools in Qdrant: {e}")
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


def _qdrant_search_fallback(collection_name: str, query_vector: List[float], limit: int = 10) -> List[Any]:
    """
    Try to use centralized qdrant client first. If client's search method is missing or fails,
    fallback to REST API request. Returns a list of 'hit' items; each item can be either:
      - a dict (REST response) with keys: id, payload, score
      - or an object from qdrant-client with attributes .id, .payload, .score
    """
    qclient = None
    try:
        qclient = get_qdrant_client()
    except Exception:
        qclient = None

    # Try to use client-based search if available
    if qclient:
        # Check collection exists (mirror original behavior)
        try:
            qclient.get_collection(collection_name=collection_name)
        except UnexpectedResponse as ex:
            if getattr(ex, "status_code", None) == 404:
                return []
            else:
                # If client is present but returns some other error, log and fallback to REST
                logger.warning(f"Qdrant client get_collection error: {ex}; falling back to REST")
        # Try various client search method names for compatibility
        try:
            if hasattr(qclient, "search"):
                return qclient.search(collection_name=collection_name, query_vector=query_vector, limit=limit, with_payload=True)
            if hasattr(qclient, "search_points"):
                # some versions name the method differently
                return qclient.search_points(collection_name=collection_name, query_vector=query_vector, limit=limit, with_payload=True)
            if hasattr(qclient, "query_points"):
                return qclient.query_points(collection_name=collection_name, query=query_vector, limit=limit, with_payload=True)
        except Exception as e:
            logger.warning(f"Qdrant client search failed: {e}; falling back to REST")

    # REST fallback
    try:
        base, headers = _qdrant_base_and_headers()
    except Exception as e:
        raise RuntimeError(f"QDRANT config missing: {e}")

    search_url = f"{base}/collections/{collection_name}/points/search"
    body = {
        "vector": query_vector,
        "limit": limit,
        "with_payload": True,
        "with_vector": False,
    }
    try:
        r = requests.post(search_url, headers=headers, json=body, timeout=20)
        r.raise_for_status()
        resp = r.json()
    except requests.HTTPError as e:
        text = getattr(e.response, "text", "")
        logger.error(f"Qdrant search HTTP error (REST): {e} - resp: {text}")
        raise RuntimeError(f"Qdrant search failed: {e} - resp: {text}") from e
    except requests.RequestException as e:
        logger.error(f"Qdrant search request failed (REST): {e}")
        raise RuntimeError(f"Qdrant search request failed: {e}") from e

    if isinstance(resp, dict):
        raw = resp.get("result") or resp.get("hits") or resp.get("data") or []
    else:
        raw = resp

    return raw


def similar_by_project(project_id: str, top_k: int = 2, collection_name: str = "project_summaries") -> Optional[Dict[str, Any]]:
    """
    REST/client-compatible Qdrant search + return the same output as your original function:
      - on match: {"project_id": matched_mongo_id, "best_score": best_score}
      - otherwise: None

    This function:
    - validates the project id,
    - creates an embedding for the project's summary,
    - queries Qdrant via client or REST fallback,
    - deduplicates by project_id (keeps best chunk per project),
    - returns the matched Mongo ID (if resolvable) and the best similarity score.
    """
    # validate project_id and load project
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

    # create embedding
    model_name = getattr(settings, "OPENAI_EMBEDDING_MODEL", None) or None
    try:
        embs = create_embeddings_for_texts([summary], model=model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding creation failed: {str(e)}")
    if not embs:
        raise HTTPException(status_code=500, detail="Embedding API returned no embedding")
    query_vec = embs[0]

    logger.info(f"🔍 Querying Qdrant for similar projects to {project_id} in collection {collection_name}")

    # search: request a few extra to allow skipping self-matches
    limit = top_k + 5
    try:
        raw_hits = _qdrant_search_fallback(collection_name=collection_name, query_vector=query_vec, limit=limit)
    except RuntimeError as e:
        logger.error(f"Qdrant search error: {e}")
        raise HTTPException(status_code=500, detail=f"Qdrant search failed: {str(e)}")

    results = []
    best_hit = None
    best_score = -1.0

    logger.info(f"🔍 Found {len(raw_hits or [])} raw hits in Qdrant for project {project_id}")

    # Normalize and process hits (support both dict items from REST and object items from client)
    for hit in raw_hits:
        try:
            if isinstance(hit, dict):
                payload = hit.get("payload") or {}
                point_id = hit.get("id")
                score = hit.get("score", None)
            else:
                # qdrant-client object (attribute access)
                payload = getattr(hit, "payload", {}) or {}
                point_id = getattr(hit, "id", None)
                score = getattr(hit, "score", None)

            # payload may include project_id, or projectId, or similar
            mongo_id_str = payload.get("project_id") or payload.get("projectId") or payload.get("project")
            text_preview = payload.get("text") or payload.get("chunk_text") or payload.get("content")
            chunk_index = payload.get("chunk_index") or payload.get("chunkIndex") or payload.get("index")

            # skip exact self-match
            if mongo_id_str and mongo_id_str == str(project.get("_id")):
                continue

            try:
                s = float(score) if score is not None else -1.0
            except Exception:
                s = -1.0

            logger.debug(f"🔍 Hit: mongo_id_payload={mongo_id_str} score={s} text_preview={text_preview}")

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
                best_hit = {"point_id": point_id, "payload": payload, "score": s, "mongo_id_payload": mongo_id_str}

            proj_summary = None
            if matched_obj:
                proj_summary = matched_obj.get("summary") or matched_obj.get("user_description")
            if not proj_summary:
                proj_summary = text_preview

            results.append({
                "point_id": str(point_id),
                "project_id": matched_project_id,
                "mongo_id_payload": mongo_id_str,
                "chunk_index": chunk_index,
                "text_preview": text_preview,
                "summary": proj_summary,
                "score": s
            })

            if len(results) >= top_k:
                break

        except Exception as e:
            logger.warning(f"Skipping malformed hit: {e} - hit: {hit}")
            continue

    logger.info(f"🔍 Best score for project {project_id} is {best_score}")
    if not best_hit:
        return None

    matched_mongo_id_payload = best_hit.get("mongo_id_payload")
    if matched_mongo_id_payload:
        try:
            matched_doc = project_collection.find_one({"_id": ObjectId(matched_mongo_id_payload)})
            if matched_doc:
                # keep same return shape as original
                return {"project_id": matched_mongo_id_payload, "best_score": best_score}
            else:
                return None
        except Exception:
            return None
    else:
        return None
