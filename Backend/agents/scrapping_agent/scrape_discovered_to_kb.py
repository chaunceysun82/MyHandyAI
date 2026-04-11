import os
import sys
import asyncio
import argparse
from datetime import timedelta

PROJECT_ROOT = os.path.dirname(__file__)
SCRAP_DIR = os.path.join(PROJECT_ROOT, "scrapping_agent")
if SCRAP_DIR not in sys.path:
    sys.path.insert(0, SCRAP_DIR)

from db import init_db  
from db import mark_url_status  
from ingest import ingest_one
from utils import utc_now

DEFAULT_BATCH_SIZE = 20
DEFAULT_CONCURRENCY = 3
MAX_ATTEMPTS = 5  

async def process_one(stores, doc, semaphore, timeout=None):
    url = doc["url"]
    classification = doc.get("classification", {}) or {}
    base_tags = doc.get("category_tags", []) or []

    async with semaphore:
        try:
            stores.discovered.update_one({"url": url},
                                        {"$inc": {"fetch_attempts": 1}, "$set": {"last_attempt_at": utc_now()}},
                                        upsert=True)

            mark_url_status(stores, url, "fetching", {"note": "processing from discovered_urls"})

            result = await ingest_one(stores, url, classification, base_tags)
            return result

        except Exception as e:
           
            err = {"error": str(e)}
            mark_url_status(stores, url, "error", err)
            return {"url": url, "result": "error", "error": str(e)}

async def run_batch(limit: int, concurrency: int, filter_q: dict):
    stores = init_db()
    cursor = stores.discovered.find(filter_q, {"_id": 0, "url": 1, "classification": 1, "category_tags": 1, "fetch_attempts": 1}).limit(limit)
    docs = list(cursor)
    if not docs:
        print("No documents found matching filter:", filter_q)
        return

    sem = asyncio.Semaphore(concurrency)
    tasks = [process_one(stores, d, sem) for d in docs]
    results = await asyncio.gather(*tasks)
    ingested = [r for r in results if r.get("result") == "ingested"]
    skipped = [r for r in results if r.get("result") and r.get("result").startswith("skipped")]
    errors = [r for r in results if r.get("result") == "error"]
    print(f"Processed {len(results)} docs — ingested: {len(ingested)}, skipped: {len(skipped)}, errors: {len(errors)}")
    if errors:
        print("Sample errors:", errors[:5])

def make_filter(max_attempts: int, only_statuses=("queued", "error")):
    return {
        "classification.is_diy_manual": True,
        "status": {"$in": list(only_statuses)},
        "$or": [
            {"fetch_attempts": {"$exists": False}},
            {"fetch_attempts": {"$lt": max_attempts}}
        ]
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE, help="how many discovered docs to process in this run")
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="concurrent fetches")
    ap.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS, help="max retry attempts before skipping")
    ap.add_argument("--status", type=str, default="queued,error", help="comma-separated discovered.status values to process")
    args = ap.parse_args()

    statuses = [s.strip() for s in args.status.split(",") if s.strip()]
    filter_query = make_filter(args.max_attempts, only_statuses=statuses)

    asyncio.run(run_batch(args.limit, args.concurrency, filter_query))
