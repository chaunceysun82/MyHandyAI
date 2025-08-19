from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
from openai import OpenAI
import os, base64, json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


router = APIRouter(prefix="/api/tools", tags=["tools"])

def _parse_tools(text: str) -> List[Dict[str, Any]]:
    """
    Try to parse the model output as JSON list of {name, confidence?, notes?}.
    If parsing fails, fall back to a best-effort list of names.
    """
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "tools" in data:
            data = data["tools"]
        if isinstance(data, list):
            out = []
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    out.append({
                        "name": str(item["name"]).strip(),
                        "confidence": float(item.get("confidence", 0.0)),
                        "notes": item.get("notes")
                    })
                elif isinstance(item, str):
                    out.append({"name": item.strip(), "confidence": 0.0})
            return out
    except Exception:
        pass
    # Fallback: split lines
    names = [ln.strip("-• ").strip() for ln in text.splitlines() if ln.strip()]
    names = [n for n in names if len(n) <= 60]
    return [{"name": n, "confidence": 0.0} for n in names]

@router.post("/detect")
async def detect_tools(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    try:
        img_bytes = await file.read()
        base64_image = base64.b64encode(img_bytes).decode("utf-8")

        # Prompt for strict JSON
        system_prompt = (
            "You are a precise tool-recognition assistant. "
            "Extract the physical tools visible in the image and return STRICT JSON ONLY.\n"
            "JSON schema: [{\"name\": string, \"confidence\": number (0..1), \"notes\"?: string}]\n"
            "No prose, no backticks."
        )

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identify the tools visible."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{file.content_type};base64,{base64_image}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=300,
            temperature=0.2,
        )

        text = resp.choices[0].message.content or "[]"
        tools = _parse_tools(text)
        return JSONResponse(content={"tools": tools})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {e}")
