from db import Stores, get_unclassified_queued, save_url_classification, mark_url_status
from signals import extract_signals_requests
from agent_tools import classify_url

def classify_queued_urls(stores: Stores, limit: int):
    rows = get_unclassified_queued(stores, limit)
    print(f"[classify] unclassified queued: {len(rows)}")

    for r in rows:
        url = r["url"]
        try:
            signals = extract_signals_requests(url)
            cls = classify_url(url, signals)
            save_url_classification(stores, url, cls)

            if not cls.get("is_diy_manual", False):
                mark_url_status(stores, url, "rejected", {"rejected_reason": cls.get("notes", "")})
        except Exception as e:
            mark_url_status(stores, url, "error", {"error": f"classify_failed: {e}"})