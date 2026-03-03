import asyncio

from config import (
    CATEGORY_SEEDS,
    SOURCE_DOMAIN,
    DISCOVERY_MAX_PAGES_PER_CATEGORY,
    DISCOVERY_RPS,
    CLASSIFY_BATCH_LIMIT,
    INGEST_MAX_ARTICLES_PER_RUN,
    INGEST_CONCURRENCY,
)
from db import init_db, upsert_discovered_urls, get_next_approved_urls
from discovery import discover_category_graph
from classify_stage import classify_queued_urls
from ingest import ingest_batch

def run_discovery_all(stores):
    total_articles = 0
    for cat_name, seed_url in CATEGORY_SEEDS.items():
        cats, articles = discover_category_graph(
            seed_url=seed_url,
            expected_keyword=cat_name,
            max_pages=DISCOVERY_MAX_PAGES_PER_CATEGORY,
            rps=DISCOVERY_RPS,
        )
        print(f"[discovery:{cat_name}] categories={len(cats)} articles={len(articles)}")
        total_articles += len(articles)

        upsert_discovered_urls(
            stores,
            urls=articles,
            source=f"wikihow_{cat_name.lower()}",
            domain=SOURCE_DOMAIN,
            tags=[cat_name],
        )

    print(f"[discovery] total articles found across categories: {total_articles}")

def run_classify(stores):
    classify_queued_urls(stores, limit=CLASSIFY_BATCH_LIMIT)

def run_ingest(stores):
    rows = get_next_approved_urls(stores, limit=INGEST_MAX_ARTICLES_PER_RUN)
    print(f"[ingest] approved queued urls: {len(rows)}")
    if not rows:
        return
    results = asyncio.run(ingest_batch(stores, rows, concurrency=INGEST_CONCURRENCY))
    ok = sum(1 for r in results if r["result"] in ("ingested", "skipped_unchanged"))
    err = sum(1 for r in results if r["result"] == "error")
    print(f"[ingest] done ok={ok} err={err}")

if __name__ == "__main__":
    stores = init_db()
    run_discovery_all(stores)
    run_classify(stores)
    run_ingest(stores)