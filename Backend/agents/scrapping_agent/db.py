from dataclasses import dataclass
from typing import Any, Optional
from typing import Dict
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
    docs.create_index("url", unique=True)
    discovered.create_index("url", unique=True)
    discovered.create_index("status")
    discovered.create_index([("classification.is_diy_manual", 1), ("status", 1)])
    docs.create_index("updated_at")

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

def mark_url_status(stores: Stores, url: str, status: str, meta: Optional[dict] = None):
    now = utc_now()
    update: Dict[str, Any] = {
        "$set": {
            "status": status,
            "last_status_meta": meta or {},
            "last_status_at": now,
            "url": url,
        },
        "$push": {
            "status_history": {"status": status, "meta": meta or {}, "at": now}
        },
    }
    stores.discovered.update_one({"url": url}, update, upsert=True)

def get_next_approved_urls(stores: Stores, limit: int) -> list[dict]:
    return list(
        stores.discovered.find(
            {"status": "queued", "classification.is_diy_manual": True},
            {"_id": 0, "url": 1, "source": 1, "classification": 1, "category_tags": 1},
        ).limit(limit)
    )

def bulk_upsert_discovered(stores: Stores, rows: list[dict]):
    ops = []
    for r in rows:
        url = r["url"]
        doc = {k: v for k, v in r.items() if k != "url"}
        ops.append(UpdateOne({"url": url}, {"$setOnInsert": {"url": url}, "$set": doc}, upsert=True))
    if ops:
        stores.discovered.bulk_write(ops, ordered=False)


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
    doc_with_time = dict(doc)
    if "updated_at" not in doc_with_time:
        doc_with_time["updated_at"] = utc_now()
    stores.docs.update_one({"url": doc_with_time["url"]}, {"$set": doc_with_time}, upsert=True)


def get_state(stores: Stores, name: str) -> Optional[dict]:
    return stores.state.find_one({"name": name}, {"_id": 0})


def set_state(stores: Stores, name: str, value: dict):
    stores.state.update_one({"name": name}, {"$set": {"value": value, "updated_at": utc_now()}}, upsert=True)
