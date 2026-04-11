from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional

import requests
import time

API = "https://www.wikihow.com/api.php"
BASE = "https://www.wikihow.com/"

CmType = Literal["page", "subcat"]

@dataclass
class CategoryMember:
    title: str
    ns: int
    pageid: int

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def _get_json(
    session: requests.Session,
    params: dict,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> Optional[dict]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(API, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            print(
                f"[wikihow_api] request failed attempt={attempt}/{retries} "
                f"status={status} params={params} error={exc}"
            )
            if attempt < retries:
                time.sleep(backoff_seconds * attempt)
    print(f"[wikihow_api] giving up after {retries} attempts: {last_error}")
    return None

def resolve_category_title(desired: str) -> Optional[str]:
    """
    Try to find the best matching category page title (namespace 14).
    This avoids hardcoding seeds that 404 (like Category:Electrical).
    """
    s = _session()
    # namespace 14 = Category
    params = {
        "action": "query",
        "list": "search",
        "srnamespace": 14,
        "srsearch": desired,   # simple; you can refine later
        "srlimit": 5,
        "format": "json",
    }
    data = _get_json(s, params=params, timeout=30)
    if not data:
        return None
    hits = data.get("query", {}).get("search", []) or []
    if not hits:
        return None

    # Return the top hit (title includes "Category:...")
    return hits[0].get("title")

def iter_category_members(
    category_title: str,
    cmtype: Iterable[CmType] = ("page", "subcat"),
    limit_per_call: int = 500,
) -> Iterable[CategoryMember]:
    """
    Enumerate members of a category using MediaWiki API 'categorymembers'.
    Supports continuation.
    """
    s = _session()
    cmcontinue = None

    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_title,        # must include "Category:" prefix :contentReference[oaicite:1]{index=1}
            "cmtype": "|".join(cmtype),       # "page|subcat"
            "cmlimit": min(limit_per_call, 500),
            "format": "json",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        data = _get_json(s, params=params, timeout=30)
        if not data:
            print(f"[wikihow_api] stopping category expansion for {category_title} due to repeated API failures")
            break

        members = data.get("query", {}).get("categorymembers", []) or []
        for m in members:
            yield CategoryMember(title=m["title"], ns=m["ns"], pageid=m["pageid"])

        cont = data.get("continue", {})
        cmcontinue = cont.get("cmcontinue")
        if not cmcontinue:
            break

def title_to_url(title: str) -> str:
    # MediaWiki titles use spaces; WikiHow uses underscores or encoded spaces
    return BASE + title.replace(" ", "-")
