import base64
import json
import os
import re
from typing import List, Dict, Any

from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI

load_dotenv()

router = APIRouter(tags=["chatbot"])


def _extract_json(text: str) -> str:
    """Strip code fences and grab the first JSON object/array if mixed with prose."""
    t = text.strip()
    # remove ```json ... ``` or ``` ... ```
    t = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", t, flags=re.IGNORECASE | re.DOTALL)
    # find first {...} or [...]
    m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", t)
    return m.group(1) if m else t


def _parse_tools(text: str) -> List[Dict[str, Any]]:
    """
    Parse the model output into [{name, confidence?, notes?}].
    Falls back to line-splitting if strict JSON parse fails.
    """
    try:
        t = _extract_json(text)
        data = json.loads(t)
        if isinstance(data, dict) and "tools" in data:
            data = data["tools"]
        if isinstance(data, list):
            out: List[Dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    conf = item.get("confidence", 0.0)
                    try:
                        conf = float(conf)
                    except Exception:
                        conf = 0.0
                    out.append({
                        "name": str(item["name"]).strip(),
                        "confidence": conf,
                        "notes": item.get("notes"),
                    })
                elif isinstance(item, str):
                    out.append({"name": item.strip(), "confidence": 0.0})
            # drop any leftover fence artifacts
            return [t for t in out if t["name"] and not str(t["name"]).startswith("```")]
    except Exception:
        pass

    # Fallback: split lines sensibly
    names = [ln.strip("-• ").strip() for ln in text.splitlines() if ln.strip()]
    names = [n for n in names if len(n) <= 60 and not n.startswith("```")]
    return [{"name": n, "confidence": 0.0} for n in names]


@router.post("/detect", summary="Detect tools in an uploaded image")
async def detect_tools(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server missing OPENAI_API_KEY")

    client = OpenAI(api_key=api_key)

    try:
        img_bytes = await file.read()
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        system_prompt = (
            "You are a precise tool-recognition assistant. "
            "Return ONLY a JSON array. Each item must be: "
            '{"name": string, "confidence": number between 0 and 1, "notes"?: string}. '
            "No prose. No explanations. No code fences."
        )

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identify any physical tools visible in this image."},
                        {"type": "image_url", "image_url": {"url": f"data:{file.content_type};base64,{b64}"}},
                    ],
                },
            ],
            max_tokens=300,
            temperature=0.2,
        )

        raw = resp.choices[0].message.content or "[]"
        tools = _parse_tools(raw)
        return JSONResponse(content={"tools": tools})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {e}")
