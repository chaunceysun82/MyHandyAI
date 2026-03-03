import hashlib
import re
import time
from datetime import datetime, timezone
from urllib.parse import urldefrag, urlparse

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def normalize_url(u: str) -> str:
    u, _ = urldefrag(u)
    u = u.strip()
    if "?" in u:
        u = u.split("?", 1)[0]
    return u.rstrip("/")

def domain_of(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")

def sha256_normalized(text: str) -> str:
    norm = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

def sleep_rps(rps: float):
    delay = 1.0 / max(rps, 0.01)
    time.sleep(delay)