import re
from typing import Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from utils import normalize_url, sleep_rps
from config import ALLOWED_HOSTS

CAT_PATH_RE = re.compile(r"^/Category:[^?#]+$", re.I)
ARTICLE_PATH_RE = re.compile(r"^/(?!Category:|Special:|User:|Help:|Talk:)[^?#]+$", re.I)

NLP_CAT_RE = re.compile(r'"wgNlpCategory"\s*:\s*"([^"]+)"', re.I)

def is_allowed_host(url: str) -> bool:
    return urlparse(url).netloc in ALLOWED_HOSTS

def get_wg_nlp_category(html: str) -> str | None:
    m = NLP_CAT_RE.search(html)
    return m.group(1) if m else None

def in_scope(html: str, expected_keyword: str) -> bool:
    nlp = get_wg_nlp_category(html)
    if not nlp:
        return False
    return f"/{expected_keyword}" in nlp

def discover_category_graph(
    seed_url: str,
    expected_keyword: str,
    max_pages: int,
    rps: float,
) -> Tuple[Set[str], Set[str]]:
    """
    Crawl a single top-level category graph, scoped using wgNlpCategory.
    Returns: (categories, articles)
    """
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })

    q = [normalize_url(seed_url)]
    seen = set()
    cats: Set[str] = set()
    articles: Set[str] = set()

    while q and len(seen) < max_pages:
        url = normalize_url(q.pop(0))
        if url in seen:
            continue
        if not is_allowed_host(url):
            continue

        sleep_rps(rps)

        try:
            resp = sess.get(url, timeout=30)
        except Exception:
            continue

        seen.add(url)
        if resp.status_code != 200:
            continue

        html = resp.text

        # scope guard: only expand if still under the intended DIY domain
        if not in_scope(html, expected_keyword):
            continue

        soup = BeautifulSoup(html, "html.parser")

        # harvest only from main-ish content (reduces footer/nav drift)
        roots = soup.select("main") or [soup]

        for root in roots:
            for a in root.select("a[href]"):
                href = a.get("href")
                if not href:
                    continue
                abs_url = normalize_url(urljoin("https://www.wikihow.com", href))
                if not is_allowed_host(abs_url):
                    continue

                path = urlparse(abs_url).path

                if CAT_PATH_RE.match(path):
                    cats.add(abs_url)
                    if abs_url not in seen:
                        q.append(abs_url)
                elif ARTICLE_PATH_RE.match(path):
                    articles.add(abs_url)

        # pagination best-effort
        for a in soup.select("a[href]"):
            txt = (a.get_text(" ", strip=True) or "").lower()
            if txt in ("next", "next page", "more"):
                q.append(normalize_url(urljoin("https://www.wikihow.com", a["href"])))

    return cats, articles