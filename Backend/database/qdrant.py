"""
Qdrant vector database operations.
Centralized Qdrant client and operations for embeddings and vector search.
"""
import uuid
from typing import List, Any, Optional

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import PointStruct, VectorParams, Distance

from config.settings import get_settings

settings = get_settings()

# Initialize OpenAI client for embeddings
_client: Optional[OpenAI] = None
_qdrant_client: Optional[QdrantClient] = None


def _get_openai_client() -> OpenAI:
    """Get or create OpenAI client for embeddings."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client instance."""
    global _qdrant_client
    if _qdrant_client is None:
        qdrant_url = settings.QDRANT_URL
        qdrant_api_key = settings.QDRANT_API_KEY

        if not qdrant_url or not qdrant_api_key:
            raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in env")

        _qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)
    return _qdrant_client


def create_embeddings_for_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """
    Creates embeddings via OpenAI for a list of strings (batched).
    Returns list of embedding vectors in same order as texts.
    """
    if not texts:
        return []

    client = _get_openai_client()
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

    Args:
        mongo_hex_id: MongoDB document ID (hex string)
        embeddings: List of embedding vectors
        texts: List of text strings corresponding to embeddings
        extra_payload: Additional metadata to include in payload
        collection_name: Qdrant collection name (default: "projects")

    Returns:
        dict with status, num_points, and collection name
    """
    collection_name = collection_name or "projects"

    if not embeddings:
        return {"status": "no_embeddings"}

    qclient = get_qdrant_client()
    vector_size = len(embeddings[0])

    # Ensure collection exists
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

    # Create points for upsert
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


def search_similar_vectors(
        query_vector: List[float],
        collection_name: str,
        limit: int = 5,
        score_threshold: Optional[float] = None
) -> List[Any]:
    """
    Search for similar vectors in a Qdrant collection.

    Uses query_points() (qdrant-client >= 1.10) instead of the removed search().
    Falls back to returning [] and logging on any error.

    Args:
        query_vector: Query embedding vector
        collection_name: Qdrant collection name
        limit: Maximum number of results
        score_threshold: Minimum similarity score (optional)

    Returns:
        List of ScoredPoint results with .score and .payload
    """
    qclient = get_qdrant_client()

    try:
        kwargs = dict(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
        # score_threshold is only passed when explicitly set to avoid filtering everything
        if score_threshold is not None:
            kwargs["score_threshold"] = score_threshold

        response = qclient.query_points(**kwargs)
        return list(response.points)

    except Exception as e:
        print(f"Error searching Qdrant collection {collection_name}: {e}")
        return []
