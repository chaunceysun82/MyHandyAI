import os, io, time
import json
import re, hashlib
import traceback
import boto3
from openai import OpenAI
from pydantic import BaseModel, Field
from datetime import datetime
from bson.objectid import ObjectId
from db import project_collection, steps_collection
from datetime import datetime
from planner import ToolsAgent, StepsAgentJSON, EstimationAgent
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
import requests
from google import genai
from google.genai import types
from PIL import Image


api_key = os.getenv("GOOGLE_API_KEY")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY")
S3_BUCKET = "handyimages"
AWS_REGION="us-east-2"
s3 = boto3.client("s3", region_name=AWS_REGION) 
PUBLIC_BASE    = "https://handyimages.s3.us-east-2.amazonaws.com"

def lambda_handler(event, context):
    for record in event.get("Records", []):
        try:
            payload = json.loads(record["body"])
            project = payload.get("project")

            if not project:
                print("⚠️ Incomplete message")
                continue

            print(f"📦 Received job for {project}")

            # Validate project exists
            cursor = project_collection.find_one({"_id": ObjectId(project)})
            if not cursor:
                print("Project not found")
                return {"message": "Project not found"}
            
            update_project(str(cursor["_id"]), {"tool_generation":{"status": "in progress"}})
            
            # Generate tools using the independent agent
            tools_agent = ToolsAgent()
            tools_result = tools_agent.recommend_tools(
                summary=cursor["summary"],
                include_json=True
            )
            if tools_result is None:
                print("LLM Generation tools failed")
                return {"message": "LLM Generation tools failed"}
            
            tools_result["status"]="complete"

            update_project(str(cursor["_id"]), {"tool_generation":tools_result})
            
            cursor = project_collection.find_one({"_id": ObjectId(project)})
            
            update_project(str(cursor["_id"]), {"step_generation":{"status": "in progress"}})
            
            steps_agent = StepsAgentJSON()
            steps_result = steps_agent.generate(
                tools= cursor["tool_generation"],
                summary=cursor["summary"],
                user_answers=cursor.get("user_answers") or cursor.get("answers"),
                questions=cursor["questions"]
            )
            
            if steps_result is None:
                print("LLM Generation steps failed")
                return {"message": "LLM Generation steps failed"}
            
            
            steps_result["youtube"]= get_youtube_link(cursor["summary"])
            
            i = 1
            for step in steps_result["steps"]:
                # if it's always a list of strings:
                step_text = ", ".join(s for s in step["instructions"] if s and s.strip())
                step["image"] = generate_step_image(str(i), {"step_text": step_text, "project_id": project})
                i += 1
            
            steps_result["status"]="complete"

            update_project(str(cursor["_id"]), {"step_generation":steps_result})

            for idx, step in enumerate(steps_result.get("steps", []), start=1):
                step_doc = {
                    "projectId": ObjectId(str(cursor["_id"])),
                    "stepNumber": step.get("order", idx),
                    "title": step.get("title", f"Step {idx}"),
                    "description": " ".join(step.get("instructions", [])),
                    "tools": [],
                    "materials": [],
                    "images": [],
                    "videoTutorialLink": None,
                    "referenceLinks": [],
                    "completed": False,
                    "createdAt": datetime.utcnow(),
                }
                steps_collection.insert_one(step_doc)
            
            print("Steps Generated")
            
            cursor = project_collection.find_one({"_id": ObjectId(project)})
            
            update_project(str(cursor["_id"]), {"estimation_generation":{"status": "in progress"}})
            
            estimation_agent = EstimationAgent()
            estimation_result = estimation_agent.generate_estimation(
                tools_data=cursor["tool_generation"],
                steps_data=cursor["step_generation"]
            )
            
            if estimation_result is None:
                print("LLM Generation steps failed")
                return {"message": "LLM Generation steps failed"}
            
            estimation_result["status"]="complete"

            update_project(str(cursor["_id"]), {"estimation_generation": estimation_result})
            
            update_project(str(cursor["_id"]), {"generation_status":"complete"})
            
            print("✅ project generation complete")


        except Exception as e:
            traceback.print_exc()
            
def update_project(project_id: str, update_data: dict):
    result = project_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        print("Project not found")
    return {"message": "Project updated", "modified": bool(result.modified_count)}

def clean_and_parse_json(raw_str: str):
    """
    Cleans code fences (```json ... ```) from a string and parses it as JSON.
    """
    if raw_str is None:
        raise ValueError("No input string")
    s = raw_str.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)           # strip fences
    m = re.search(r"\{.*\}\s*$", s, flags=re.S)               # grab last JSON object
    if m: s = m.group(0)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")

def get_youtube_link(summary):
    YOUTUBE_KEY = os.getenv("YOUTUBE_API_KEY")
    OPENAI_KEY   = os.getenv("OPENAI_API_KEY")
    
    payload = {
        "model": "gpt-5-nano",  # or the model you prefer
        "messages": [
            {"role": "system", "content": (
                "You are a summarization agent for youtube searches"
                "Return one line in based of the text provided to search the most helpfull video"
            )},
            {"role": "user", "content": json.dumps({
                "description": summary
            })}
        ],
        "max_completion_tokens": 500,
        "reasoning_effort": "low",
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json=payload, timeout=30
    )
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print (content)
    
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": YOUTUBE_KEY,
        "part": "snippet",
        "q": content,
        "type": "video",
        "maxResults": 8,
        "videoEmbeddable": "true",
        "safeSearch": "strict",
        "relevanceLanguage": "en",
        "order": "relevance",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    items = r.json().get("items", [])
    videos=[{
        "videoId": it["id"]["videoId"],
        "title": it["snippet"]["title"],
        "description": it["snippet"].get("description", ""),
        "channelTitle": it["snippet"].get("channelTitle", ""),
    } for it in items]
    
    payload = {
        "model": "gpt-5-mini",  # or the model you prefer
        "messages": [
            {"role": "system", "content": (
                "You are a strict evaluator for DIY/repair steps. "
                "Pick ONE video that best teaches the given step. "
                "Prefer safety, clarity, step-by-step, and recency. "
                "Return pure JSON with keys: best_videoId, reason."
            )},
            {"role": "user", "content": json.dumps({
                "step": summary,
                "candidates": [
                    {k: c[k] for k in ["videoId", "title", "description", "channelTitle"]}
                    for c in videos
                ]
            })}
        ],
        "max_completion_tokens": 2500,
        "reasoning_effort": "low",
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json=payload, timeout=30
    )
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    verdict=clean_and_parse_json(content)
    best_id = verdict.get("best_videoId")
    best = next((c for c in videos if c["videoId"] == best_id), None)
    if not best:
        # fallback to top candidate
        best = videos[0]
    return f"https://www.youtube.com/embed/{best['videoId']}"

class SceneSpec(BaseModel):
    action: Optional[str] = None
    tool: Optional[str] = None
    target: Optional[str] = None
    measures: Optional[str] = None
    angle: Optional[str] = None
    view: Optional[str] = None
    distance: Optional[str] = None
    style: Optional[str] = None
    hands_visible: Optional[str] = None
    safety: Optional[str] = None
    background: Optional[str] = None
    
class ImageRequest(BaseModel):
    step_text: str
    scene: Optional[SceneSpec] = None
    size: str = "1024x1024" 
    n: int = 1             
    project_id: str
    
def _build_prompt(step_text: str, scene: SceneSpec | None, guidance="neutral") -> str:
        s = scene or SceneSpec()

        lines = [
            "Create an instructional image that faithfully depicts the step.",
            "No text overlays, no logos, no watermarks. Aspect ratio 16:9.",
            f"STEP: {step_text}"
        ]
        if s.style:
            lines.append(f"Style: {s.style}.")
        if s.action:
            lines.append(f"Action: {s.action}.")
        if s.tool:
            lines.append(f"Tool: {s.tool}.")
        if s.target:
            lines.append(f"Target: {s.target}.")
        if s.measures:
            lines.append(f"Measurement cues: {s.measures}.")
        if s.angle:
            lines.append(f"Placement angle: {s.angle}.")
        if s.view:
            lines.append(f"Camera view: {s.view}.")
        if s.distance:
            lines.append(f"Camera distance: {s.distance}.")
        if s.hands_visible:
            lines.append(f"Hands visible: {s.hands_visible}.")
        if s.background:
            lines.append(f"Background: {s.background}.")
        if s.safety:
            lines.append(f"Safety: {s.safety}.")

        if guidance == "neutral":
            # Ask the model to choose composition when unspecified
            lines.append(
                "If any attributes are unspecified, choose the most informative composition "
                "(select view/distance/hands/background yourself for clarity)."
            )
        else:
            # optional slightly more prescriptive nudge you can toggle if needed
            lines.append(
                "Prioritize clarity of tool-to-surface contact; choose view and distance to avoid occlusion."
            )

        return "\n".join(lines)
# def _generate_png(prompt: str, size: str, seed: Optional[int] = None) -> bytes:
#     client = OpenAI(api_key=OPENAI_KEY)
#     kwargs: Dict[str, Any] = {"model": "gpt-image-1", "prompt": prompt, "size": size, "n": 1}
#     # If your account supports seed; if not, you can remove this key
#     if seed is not None:
#         kwargs["seed"] = seed
#     resp = client.images.generate(**kwargs)
#     b64png = resp.data[0].b64_json
#     return base64.b64decode(b64png)

def _generate_png(prompt: str, size: str, seed: int | None = None) -> bytes:
    """
    Generate PNG bytes via Gemini API (Imagen 4).
    Uses dict 'config' to avoid SDK type validation issues.
    """
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    aspect = _map_size_to_aspect(size)

    resp = client.models.generate_images(
        model=os.getenv("GEMINI_IMAGE_MODEL", "imagen-4.0-generate-001"),
        prompt=prompt,
        config={
            "numberOfImages": 1,
            "aspectRatio": aspect,         # "1:1","3:4","4:3","9:16","16:9"
            "outputMimeType": "image/png", # ask for PNG bytes
            # "sampleImageSize": "2K",     # optional; omit if your SDK rejects it
        },
    )
    return resp.generated_images[0].image.image_bytes

def _png_to_bytes_ensure_rgba(png_bytes: bytes) -> bytes:
    # Defensive: normalize to PNG/RGBA
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()

def _s3_key(step_id: str, project_id: Optional[str]) -> str:
    ts = int(time.time())
    base = f"project_{project_id or 'na'}/steps/{step_id}"
    return f"{base}/image_{ts}.png"

def _public_url_or_presigned(key: str) -> str:
    # If you use CloudFront or a public bucket, construct a public URL
    if PUBLIC_BASE:
        return f"{PUBLIC_BASE.rstrip('/')}/{key}"
    # Otherwise return a presigned URL
    
def _map_size_to_aspect(size_str: str) -> str:
    # map "WxH" to Imagen aspectRatio; keep it simple and robust
    try:
        w, h = [int(x) for x in size_str.lower().split("x")]
        ar = w / h
        if 1.66 <= ar <= 1.90:  # ~16:9
            return "16:9"
        if 1.25 <= ar < 1.66:   # ~4:3
            return "4:3"
        if 0.90 <= ar < 1.25:   # ~1:1
            return "1:1"
        if 0.75 <= ar < 0.90:   # ~3:4
            return "3:4"
        return "9:16"
    except Exception:
        return "16:9"

def generate_step_image(step_id: str, payload: ImageRequest | dict):
    try:
        if isinstance(payload, dict):
            payload = ImageRequest(**payload)
        prompt = _build_prompt(payload.step_text, payload.scene)
        raw_png = _generate_png(prompt=prompt, size=payload.size)
        png_bytes = _png_to_bytes_ensure_rgba(raw_png)
    except Exception as e:
        print(f"Image generation failed: {e}")
        raise HTTPException(HTTPException(status_code=500, detail=f"image generation failed {e}"))

    key = _s3_key(step_id, payload.project_id)
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=png_bytes,
            ContentType="image/png",
            Metadata={
                "step_id": step_id,
                "project_id": payload.project_id or "",
                "size": payload.size,
                "model": "gpt-image-1"
            },
        )
    except Exception as e:
        print(f"S3 upload failed: {e}")
        raise HTTPException(HTTPException(status_code=500, detail=f"S3 upload failed: {e}"))

    url = _public_url_or_presigned(key)
    return {
        "message": "ok",
        "step_id": step_id,
        "project_id": payload.project_id,
        "s3_key": key,
        "url": url,
        "size": payload.size,
        "model": "gpt-image-1",
        "prompt_preview": prompt[:180],
    }
    
    