import re
import requests
from bs4 import BeautifulSoup
from utils import normalize_url

def extract_signals_requests(url: str, timeout_s: int = 20) -> dict:
    url = normalize_url(url)
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    })
    r = sess.get(url, timeout=timeout_s)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    title = (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else None) \
            or (soup.title.get_text(" ", strip=True) if soup.title else None)

    meta_desc = None
    md = soup.find("meta", attrs={"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    headings = []
    for h in soup.select("h2, h3")[:20]:
        t = h.get_text(" ", strip=True)
        if t:
            headings.append(t)

    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\s+", " ", text)
    snippet = text[:2000]

    return {"title": title, "meta_description": meta_desc, "headings": headings, "snippet_text": snippet}