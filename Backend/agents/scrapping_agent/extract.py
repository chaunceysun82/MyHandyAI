import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from utils import sha256_normalized

REV_RE = re.compile(r'"wgCurRevisionId"\s*:\s*(\d+)', re.I)
PART_RE = re.compile(r"^\s*Part\s*\d+\s*(.*)$", re.I)
CITE_BRACKET_RE = re.compile(r"\[\d+\]")
NOISE_RE = re.compile(r"(Advertisement|X\s+Research\s+source|Expert\s+Interview|Expert\s+Source)", re.I)

def extract_revision_id(html: str) -> Optional[int]:
    m = REV_RE.search(html)
    return int(m.group(1)) if m else None

def _clean_step(s: str) -> str:
    s = CITE_BRACKET_RE.sub("", s)
    s = NOISE_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_sections(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("h1")
    title = title_el.get_text(" ", strip=True) if title_el else None

    sections: List[Dict[str, Any]] = []

    part_containers = soup.select("div.part, section.part")
    if part_containers:
        for part in part_containers:
            heading = None
            for c in part.select("h2, h3, .part_title, .mf-section-title, .stephead"):
                txt = c.get_text(" ", strip=True)
                if not txt:
                    continue
                m = PART_RE.match(txt)
                if m:
                    heading = (m.group(1) or "").strip() or txt
                    break
                if len(txt) > 5 and "part" not in txt.lower():
                    heading = txt
                    break

            steps = []
            for step_el in part.select("div.step, li.step, .step"):
                t = _clean_step(step_el.get_text(" ", strip=True))
                if t:
                    steps.append(t)

            if steps:
                sections.append({"heading": heading or "Steps", "steps": steps})

    if not sections:
        # fallback: all steps
        steps = []
        for step_el in soup.select("div.step, li.step, .step"):
            t = _clean_step(step_el.get_text(" ", strip=True))
            if t:
                steps.append(t)
        if steps:
            sections = [{"heading": "Steps", "steps": steps}]

    text_for_hash = soup.get_text("\n", strip=True)
    text_hash = sha256_normalized(text_for_hash)

    return {"title": title, "sections": sections, "text_hash": text_hash}