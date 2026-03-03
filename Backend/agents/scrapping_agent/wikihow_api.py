from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional

import requests

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
    r = s.get(API, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
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

        r = s.get(API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

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