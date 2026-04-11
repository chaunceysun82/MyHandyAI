import json
import os
from typing import Any, Dict

from openai import OpenAI
from config import ALLOWED_CATEGORIES, OPENAI_MODEL_CLASSIFIER

def normalize_category(cat: Any) -> Any:
    if not isinstance(cat, str):
        return None
    cat = cat.strip()
    return cat if cat in ALLOWED_CATEGORIES else None

def build_prompt(url: str, signals: Dict[str, Any]) -> str:
    return f"""
Return STRICT JSON ONLY (no markdown, no extra text):

{{
  "is_diy_manual": boolean,
  "manual_type": "how_to" | "installation_manual" | "spec_sheet" | "parts_diagram" | "troubleshooting" | "other",
  "category": "Plumbing" | "Electrical" | "Appliance" | "Walls" | "Doors" | "Toilet" | "Paint" | "Exterior" | "Flooring" | "HVAC" | null,
  "confidence": number,
  "notes": string
}}

Rules:
- category MUST be one of: {ALLOWED_CATEGORIES} or null.
- is_diy_manual=true only if it is a real DIY guide/manual/spec/parts/troubleshooting page.
- Category/list pages, marketing pages, unrelated content => is_diy_manual=false.
- notes <= 120 chars.

URL: {url}

Signals:
{json.dumps(signals, ensure_ascii=False)[:12000]}
""".strip()

def classify_url(url: str, signals: Dict[str, Any]) -> Dict[str, Any]:
    # Key comes from OPENAI_API_KEY env var or .env loaded in config
    client = OpenAI()
    prompt = build_prompt(url, signals)

    resp = client.responses.create(
        model=OPENAI_MODEL_CLASSIFIER,
        input=prompt,
    )

    text = resp.output_text.strip()
    try:
        data = json.loads(text)
    except Exception:
        # try extracting json substring
        s = text.find("{")
        e = text.rfind("}")
        if s != -1 and e != -1 and e > s:
            data = json.loads(text[s:e+1])
        else:
            raise

    data.setdefault("is_diy_manual", False)
    data.setdefault("manual_type", "other")
    data["category"] = normalize_category(data.get("category"))
    data.setdefault("confidence", 0.0)
    data.setdefault("notes", "")

    return data