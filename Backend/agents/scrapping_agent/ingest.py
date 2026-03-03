import asyncio
from typing import Optional, Dict

from config import FETCH_TIMEOUT_MS
from db import Stores, get_doc_meta, mark_url_status, upsert_kb_doc
from extract import extract_revision_id, extract_sections
from fetch import fetch_html
from utils import domain_of, utc_now

def should_skip(existing: Optional[dict], new_rev: Optional[int], new_hash: str) -> bool:
    if not existing:
        return False
    old_rev = existing.get("revision_id")
    old_hash = existing.get("text_hash")
    if old_rev is not None and new_rev is not None:
        return old_rev == new_rev
    return bool(old_hash) and old_hash == new_hash

async def ingest_one(stores: Stores, url: str, classification: dict, base_tags: list[str]) -> Dict[str, str]:
    html, status, final_url = await fetch_html(url, timeout_ms=FETCH_TIMEOUT_MS)

    rev_id = extract_revision_id(html)
    extracted = extract_sections(html)  # title, sections, text_hash

    existing = get_doc_meta(stores, url)
    if should_skip(existing, rev_id, extracted["text_hash"]):
        mark_url_status(stores, url, "fetched", {"skipped": True, "http_status": status, "final_url": final_url})
        return {"url": url, "result": "skipped_unchanged"}

    llm_cat = (classification or {}).get("category")
    manual_type = (classification or {}).get("manual_type") or "how_to"

    category_tags = list(dict.fromkeys(base_tags + ([llm_cat] if llm_cat else [])))

    doc = {
        "domain": domain_of(url),
        "url": url,
        "title": extracted["title"],
        "category_tags": category_tags,
        "authority_level": "medium",
        "reliability_weight": 0.7,
        "content_type": manual_type,
        "published_date": None,
        "revision_id": rev_id,
        "text_hash": extracted["text_hash"],
        "updated_at": utc_now(),
        "extracted": {
            "sections": extracted["sections"],
            "tools": [],
            "materials": [],
            "warnings": [],
        },
    }

    upsert_kb_doc(stores, doc)
    mark_url_status(stores, url, "fetched", {"skipped": False, "http_status": status, "final_url": final_url})
    return {"url": url, "result": "ingested"}

async def ingest_batch(stores: Stores, rows: list[dict], concurrency: int = 2):
    sem = asyncio.Semaphore(concurrency)

    async def _run(r: dict):
        url = r["url"]
        classification = r.get("classification") or {}
        base_tags = r.get("category_tags") or []
        async with sem:
            try:
                mark_url_status(stores, url, "fetching")
                return await ingest_one(stores, url, classification, base_tags)
            except Exception as e:
                mark_url_status(stores, url, "error", {"error": str(e)})
                return {"url": url, "result": "error", "error": str(e)}

    return await asyncio.gather(*[_run(r) for r in rows])