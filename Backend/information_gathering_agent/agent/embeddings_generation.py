import uuid
from loguru import logger
import os
import time
import re
from typing import List, Dict, Any
import requests

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "project_summaries")

DEFAULT_EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?]\s)', text)
    chunks: List[str] = []
    current = ""
    for s in sentences:
        if len(current) + len(s) <= max_chars:
            current += s
        else:
            if current:
                chunks.append(current.strip())
            if len(s) > max_chars:
                for i in range(0, len(s), max_chars):
                    chunks.append(s[i:i + max_chars].strip())
                current = ""
            else:
                current = s
    if current:
        chunks.append(current.strip())

    if overlap and len(chunks) > 1:
        new_chunks: List[str] = []
        for i, c in enumerate(chunks):
            if i == 0:
                new_chunks.append(c)
            else:
                prev = new_chunks[-1]
                prefix = prev[-overlap:] if len(prev) > overlap else prev
                new_chunks.append((prefix + " " + c).strip())
        chunks = new_chunks

    return chunks

def get_embeddings(texts: List[str], model: str = DEFAULT_EMBEDDING_MODEL) -> List[List[float]]:

    if not texts:
        return []

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set in environment")

    base_url = OPENAI_BASE_URL.rstrip("/")
    url = f"{base_url}/v1/embeddings"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "input": texts,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        logger.error(f"OpenAI embeddings HTTP error: {e} - body: {resp.text}")
        raise

    data = resp.json()
    embeddings = [item["embedding"] for item in data.get("data", [])]
    return embeddings


def _normalize_base(url: str | None) -> str:
    if not url:
        return "http://localhost:6333"
    base = url.strip()
    if not base.startswith("http://") and not base.startswith("https://"):
        base = "http://" + base
    return base.rstrip("/")


def _qdrant_base_and_headers():
    base = _normalize_base(QDRANT_URL)
    headers = {"Content-Type": "application/json"}
    if QDRANT_API_KEY:
        headers["api-key"] = QDRANT_API_KEY
    return base, headers


def qdrant_collection_exists(collection_name: str) -> bool:
    base, headers = _qdrant_base_and_headers()

    exists_url = f"{base}/collections/{collection_name}/exists"
    try:
        r = requests.get(exists_url, headers=headers, timeout=10)
        if r.status_code == 200:
            j = r.json()
            if isinstance(j, dict) and (j.get("result") is True or j.get("status") is None):
                return True
            return True
        if r.status_code == 404:
            return False
    except requests.RequestException:
        pass

    info_url = f"{base}/collections/{collection_name}"
    try:
        r = requests.get(info_url, headers=headers, timeout=10)
        return r.status_code == 200
    except requests.RequestException:
        raise


def qdrant_create_collection(collection_name: str, vector_size: int, distance: str = "Cosine") -> Dict[str, Any]:

    base, headers = _qdrant_base_and_headers()
    url = f"{base}/collections/{collection_name}"
    payload = {
        "vectors": {"size": vector_size, "distance": distance}
    }
    r = requests.put(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def ensure_qdrant_collection(collection_name: str, vector_size: int, distance: str = "Cosine",) -> None:
    try:
        if not qdrant_collection_exists(collection_name):
            logger.info(
                f"Qdrant: creating collection {collection_name} "
                f"(size={vector_size}, distance={distance})"
            )
            qdrant_create_collection(collection_name, vector_size=vector_size, distance=distance)
        else:
            logger.info(f"Qdrant: collection {collection_name} already exists")
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection {collection_name}: {e}")
        raise


def upsert_qdrant_points(collection_name: str, points: List[dict]) -> Dict[str, Any]:
    if not points:
        return {"status": "no_points"}

    base, headers = _qdrant_base_and_headers()
    url = f"{base}/collections/{collection_name}/points"
    body = {"points": points}
    try:
        r = requests.put(url, headers=headers, json=body, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        text = getattr(e.response, "text", "")
        logger.error(f"Qdrant upsert failed: {e} - resp: {text}")
        raise RuntimeError(f"Qdrant upsert failed: {e} - resp: {text}") from e


def embed_and_store_project_summary(project_doc: Dict[str, Any], model: str = DEFAULT_EMBEDDING_MODEL, chunk_chars: int = 500000, overlap: int = 100,) -> Dict[str, Any]:
    if not project_doc:
        raise ValueError("project_doc is required")

    project_id = str(project_doc.get("_id"))
    summary_text = project_doc.get("summary", "")
    hypotheses_text = project_doc.get("hypotheses", "")

    text_to_embed = summary_text
    if hypotheses_text:
        text_to_embed = summary_text.strip() + "\n\nHypotheses:\n" + hypotheses_text.strip()

    if not text_to_embed.strip():
        return {"status": "no_text", "inserted": 0}

    chunks = chunk_text(text_to_embed, max_chars=chunk_chars, overlap=overlap)
    if not chunks:
        return {"status": "no_chunks", "inserted": 0}

    batch_size = 16
    embeddings: List[List[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embs = get_embeddings(batch, model=model)
        embeddings.extend(embs)
        time.sleep(0.05)

    logger.info(f"Embeddings created: {len(embeddings)} vectors")

    vector_size = len(embeddings[0])
    ensure_qdrant_collection(QDRANT_COLLECTION, vector_size=vector_size, distance="Cosine")

    points = []
    for idx, (chunk, vec) in enumerate(zip(chunks, embeddings)):
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{project_id}_{idx}"))
        payload = {
            "project_id": project_id,
            "chunk_index": idx,
            "text": chunk,
        }
        points.append({"id": pid, "vector": vec, "payload": payload})

    result = upsert_qdrant_points(QDRANT_COLLECTION, points)
    logger.info(f"Upsert result: {result}")

    return {
        "status": "ok",
        "project_id": project_id,
        "chunks": len(chunks),
        "inserted": len(points),
    }
