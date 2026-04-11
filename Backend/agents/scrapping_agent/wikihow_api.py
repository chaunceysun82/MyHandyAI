from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional

import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote, urlparse

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


def category_title_to_url(category_title: str) -> str:
    if category_title.startswith("Category:"):
        slug = category_title[len("Category:"):].strip().replace(" ", "-")
        return f"{BASE}Category:{slug}"
    return urljoin(BASE, category_title.replace(" ", "-"))


def _is_article_path(path: str) -> bool:
    if not path or not path.startswith("/"):
        return False
    if path.startswith("/Category:"):
        return False
    blocked_prefixes = (
        "/Special:",
        "/User:",
        "/Help:",
        "/About-wikiHow",
        "/Main-Page",
        "/Log-in",
        "/Terms-of-Use",
        "/wikiHow:",
    )
    return not path.startswith(blocked_prefixes)


def extract_category_links_from_html(category_title: str) -> tuple[set[str], set[str]]:
    session = _session()
    url = category_title_to_url(category_title)
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[wikihow_api] html fallback failed for {category_title}: {exc}")
        return set(), set()

    soup = BeautifulSoup(response.text, "html.parser")
    category_urls: set[str] = set()
    article_urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        full_url = urljoin(BASE, href)
        parsed = urlparse(full_url)
        if parsed.netloc not in ("www.wikihow.com", "wikihow.com"):
            continue

        clean_path = unquote(parsed.path)
        if clean_path.startswith("/Category:"):
            category_urls.add(f"{BASE.rstrip('/')}{clean_path}")
        elif _is_article_path(clean_path):
            article_urls.add(f"{BASE.rstrip('/')}{clean_path}")

    return category_urls, article_urls


def title_to_url(title: str) -> str:
    # MediaWiki titles use spaces; WikiHow uses underscores or encoded spaces
    return BASE + title.replace(" ", "-")
