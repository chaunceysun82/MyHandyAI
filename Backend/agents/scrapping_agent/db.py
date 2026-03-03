from dataclasses import dataclass
from typing import Any, Optional

from pymongo import MongoClient, UpdateOne

from config import MONGO_URI, DB_NAME, COL_DISCOVERED, COL_DOCS, COL_STATE
from utils import utc_now

@dataclass
class Stores:
    discovered: Any
    docs: Any
    state: Any

def init_db() -> Stores:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    discovered = db[COL_DISCOVERED]
    docs = db[COL_DOCS]
    state = db[COL_STATE]

    return Stores(discovered=discovered, docs=docs, state=state)

def upsert_discovered_urls(
    stores: Stores,
    urls: set[str],
    source: str,
    domain: str,
    tags: list[str],
):
    now = utc_now()
    ops = []
    for url in urls:
        ops.append(
            UpdateOne(
                {"url": url},
                {
                    "$setOnInsert": {
                        "url": url,
                        "domain": domain,
                        "source": source,
                        "category_tags": tags,
                        "status": "queued",
                        "first_seen_at": now,
                    },
                    "$set": {"last_seen_at": now},
                },
                upsert=True,
            )
        )
    if ops:
        stores.discovered.bulk_write(ops, ordered=False)

def get_unclassified_queued(stores: Stores, limit: int) -> list[dict]:
    return list(
        stores.discovered.find(
            {"status": "queued", "classification": {"$exists": False}},
            {"_id": 0, "url": 1, "source": 1, "category_tags": 1},
        ).limit(limit)
    )

def save_url_classification(stores: Stores, url: str, cls: dict):
    stores.discovered.update_one(
        {"url": url},
        {"$set": {"classification": cls, "classified_at": utc_now()}},
        upsert=False,
    )

def mark_url_status(stores: Stores, url: str, status: str, extra: Optional[dict] = None):
    update = {"$set": {"status": status, "last_fetched_at": utc_now()}}
    if extra:
        update["$set"].update(extra)
    stores.discovered.update_one({"url": url}, update)

def get_next_approved_urls(stores: Stores, limit: int) -> list[dict]:
    return list(
        stores.discovered.find(
            {"status": "queued", "classification.is_diy_manual": True},
            {"_id": 0, "url": 1, "source": 1, "classification": 1, "category_tags": 1},
        ).limit(limit)
    )

def get_doc_meta(stores: Stores, url: str) -> Optional[dict]:
    return stores.docs.find_one({"url": url}, {"_id": 0, "revision_id": 1, "text_hash": 1})

def upsert_kb_doc(stores: Stores, doc: dict):
    stores.docs.update_one({"url": doc["url"]}, {"$set": doc}, upsert=True)