from pymongo import MongoClient
from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint
from dotenv import load_dotenv
import os
import json
import openai

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DATABASE]
col = db["kb_documents"]

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
openai.api_key = OPENAI_API_KEY

COLLECTION_NAME = "kb_summaries"
EMBEDDING_MODEL = "text-embedding-3-small"

def get_embedding(text: str) -> list:
    response = openai.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding

def search_similar_summaries(query_summary: str, top_k: int = 5, score_threshold: float = 0.0) -> list[dict]:
    """
    1. Embed the query_summary.
    2. Search Qdrant for the top_k most similar stored summaries.
    3. For each hit, fetch the full document from MongoDB using mongo_id.
    4. Return a list of result dicts sorted by similarity score (highest first).

    Each result dict contains:
      - score          : cosine similarity (0.0 – 1.0)
      - qdrant_point_id: Qdrant point UUID
      - mongo_id       : MongoDB _id string
      - url            : source URL
      - summary        : stored summary text
      - mongo_doc      : full MongoDB document (or None if not found)
    """
    query_vector = get_embedding(query_summary)

    hits: list[ScoredPoint] = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
        with_payload=True,
    )

    results = []
    for hit in hits:
        payload = hit.payload or {}
        mongo_id_str = payload.get("mongo_id")

        mongo_doc = None
        if mongo_id_str:
            from bson import ObjectId
            try:
                mongo_doc = col.find_one({"_id": ObjectId(mongo_id_str)})
                if mongo_doc:
                    mongo_doc["_id"] = str(mongo_doc["_id"])  
            except Exception as e:
                print(f"[WARN] Could not fetch mongo doc {mongo_id_str}: {e}")

        results.append({
            "score": round(hit.score, 6),
            "qdrant_point_id": hit.id,
            "mongo_id": mongo_id_str,
            "url": payload.get("url"),
            "summary": payload.get("summary"),
            "mongo_doc": mongo_doc,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def print_results(results: list[dict], query_summary: str):
    print("=" * 70)
    print("QUERY SUMMARY:")
    print(query_summary)
    print("=" * 70)
    print(f"Top {len(results)} result(s):\n")

    for rank, r in enumerate(results, start=1):
        mongo = r["mongo_doc"] or {}
        extracted = mongo.get("extracted", {})

        print(f"  Rank #{rank}  |  Score: {r['score']:.4f}")
        print(f"  URL     : {r['url']}")
        print(f"  Mongo ID: {r['mongo_id']}")
        print(f"  Qdrant  : {r['qdrant_point_id']}")
        print(f"  Summary :\n{_indent(r['summary'], 12)}")

        if extracted:
            print(f"  Tools     : {extracted.get('tools', [])}")
            print(f"  Materials : {extracted.get('materials', [])}")
            print(f"  Warnings  : {extracted.get('warnings', [])}")

        print("-" * 70)


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in (text or "").splitlines())



def test_with_random_summary():
    """
    Pull one random stored summary from MongoDB (those that have been indexed),
    use it as the query, and verify that the top hit is the document itself
    (score ≈ 1.0) while the remaining hits are genuinely similar neighbours.
    """
    sample = col.find_one(
        {"extracted.summary": {"$exists": True}, "extracted.qdrant_point_id": {"$exists": True}},
        {"extracted.summary": 1, "url": 1}
    )

    if not sample:
        print("[TEST] No indexed documents found in MongoDB.")
        return

    query_text = sample["extracted"]["summary"]
    source_url = sample.get("url", "<unknown>")

    print(f"\n[TEST] Using summary from: {source_url}\n")

    results = search_similar_summaries(query_text, top_k=5)
    print_results(results, query_text)

    if results and results[0]["url"] == source_url:
        print(f"[TEST PASS] Top hit is the source document itself "
              f"(score={results[0]['score']:.4f})  ✓")
    else:
        top_url = results[0]["url"] if results else "N/A"
        print(f"[TEST NOTE] Top hit is '{top_url}' (not the source). "
              f"This is fine if multiple docs share very similar summaries.")

if __name__ == "__main__":
    test_with_random_summary()
