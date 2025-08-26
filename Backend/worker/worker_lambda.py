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


SQS_URL = os.getenv("IMAGES_SQS_URL")  
api_key = os.getenv("GOOGLE_API_KEY")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY")
S3_BUCKET = "handyimages"
AWS_REGION="us-east-2"
s3 = boto3.client("s3", region_name=AWS_REGION) 
sqs = boto3.client("sqs", region_name=AWS_REGION)
PUBLIC_BASE    = "https://handyimages.s3.us-east-2.amazonaws.com"

def enqueue_image_tasks(project_id: str, steps: list[dict], size: str = "1536x1024",summary:str="") -> None:
    """Send one SQS message per step (no batch API)."""
    if not SQS_URL:
        print("⚠️ IMAGES_SQS_URL not set; skipping enqueue")
        return
    for i, step in enumerate(steps, start=1):
        step_text = "Overall summary: " +summary+"\n"
        step_text +="CURRENT STEP: "+ ", ".join(s for s in step.get("instructions", []) if s and s.strip())
        body = {
            "task": "image_step",
            "project": project_id,
            "step_id": str(i),
            "step_text": step_text,
            "size": size
        }
        project_collection.update_one({"_id": ObjectId(project_id)}, {"$set": {f"step_generation.steps.{int(i)-1}.image.status": "in-progress"}})
        
        sqs.send_message(QueueUrl=SQS_URL, MessageBody=json.dumps(body))
        
def handle_image_step(msg: dict) -> None:
    """Generate+upload image for a single step and persist result."""
    project_id = msg["project"]
    step_id    = msg["step_id"]
    step_text  = msg["step_text"]
    size       = msg.get("size", "1536x1024")

    # Call your existing generator (OpenAI/Gemini under the hood)
    res = generate_step_image(step_id, {"step_text": step_text, "project_id": project_id, "size": size})
    
    res['status']="complete"

    project_collection.update_one({"_id": ObjectId(project_id)}, {"$set": {f"step_generation.steps.{int(step_id)-1}.image": res}})

def lambda_handler(event, context):
    for record in event.get("Records", []):
        try:
            payload = json.loads(record["body"])
            task = payload.get("task", "full")

            if task == "image_step":
                # Image-only job (runs in parallel for each step)
                handle_image_step(payload)
                continue
            
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
            
            # FLOW 2: Compare and enhance tools with existing ones
            if "tools" in tools_result and tools_result["tools"]:
                print(f"🔄 FLOW 2: Comparing {len(tools_result['tools'])} generated tools with existing tools")
                
                try:
                    # Import comparison functions
                    from routes.chatbot import find_similar_tools, update_tool_usage
                    
                    enhanced_tools = []
                    reuse_stats = {"reused": 0, "new": 0, "errors": 0}
                    
                    for tool in tools_result["tools"]:
                        try:
                            # Search for similar existing tools
                            similar_tools = find_similar_tools(
                                query=tool.get("name", ""),
                                limit=3,
                                similarity_threshold=0.75
                            )
                            
                            if similar_tools and similar_tools[0]["similarity_score"] >= 0.8:
                                # High similarity - reuse image and amazon link
                                best_match = similar_tools[0]
                                tool["image_link"] = best_match["image_link"]
                                tool["amazon_link"] = best_match["amazon_link"]
                                tool["reused_from"] = best_match["tool_id"]
                                tool["similarity_score"] = best_match["similarity_score"]
                                
                                # Update usage count
                                update_tool_usage(best_match["tool_id"])
                                
                                reuse_stats["reused"] += 1
                                print(f"   ✅ Reused image/links for: {tool['name']}")
                                
                            else:
                                # No good match - keep as new tool
                                reuse_stats["new"] += 1
                                print(f"   🆕 New tool: {tool['name']}")
                            
                            enhanced_tools.append(tool)
                            
                        except Exception as e:
                            print(f"❌ Error processing tool {tool.get('name', 'unknown')}: {e}")
                            enhanced_tools.append(tool)
                            reuse_stats["errors"] += 1
                    
                    # Update tools_result with enhanced tools
                    tools_result["tools"] = enhanced_tools
                    tools_result["reuse_metadata"] = reuse_stats
                    
                    print(f"✅ FLOW 2 completed: {reuse_stats['reused']} reused, {reuse_stats['new']} new")
                    
                except Exception as e:
                    print(f"⚠️ FLOW 2 comparison error: {e}")
                    tools_result["reuse_metadata"] = {"error": str(e)}
            
            tools_result["status"]="complete"

            update_project(str(cursor["_id"]), {"tool_generation":tools_result})
            
            # FLOW 1: Extract and save tools to tools_collection
            try:
                print(f"🔄 FLOW 1: Extracting generated tools to tools_collection")
                
                # Import extraction functions
                from routes.chatbot import store_tool_in_database, create_and_store_tool_embeddings
                from db import tools_collection
                
                saved_tools = []
                failed_tools = []
                
                if "tools" in tools_result and tools_result["tools"]:
                    for tool in tools_result["tools"]:
                        try:
                            # Check if tool already exists (avoid duplicates)
                            existing_tool = tools_collection.find_one({"name": tool["name"]})
                            if existing_tool:
                                print(f"✅ Tool '{tool['name']}' already exists, skipping")
                                continue
                            
                            # Save new tool
                            tool_id = store_tool_in_database(tool)
                            embedding_result = create_and_store_tool_embeddings(tool, tool_id)
                            
                            saved_tools.append({
                                "tool_id": tool_id,
                                "name": tool["name"],
                                "status": "saved"
                            })
                            
                            print(f"✅ FLOW 1: Saved tool '{tool['name']}' to tools_collection")
                            
                        except Exception as e:
                            print(f"❌ FLOW 1: Failed to save tool {tool.get('name', 'unknown')}: {e}")
                            failed_tools.append({"tool": tool.get('name', 'unknown'), "error": str(e)})
                    
                    print(f"✅ FLOW 1: Completed - {len(saved_tools)} tools saved to collection")
                
            except Exception as e:
                print(f"⚠️ FLOW 1: Failed to extract tools: {e}")
            
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
            
            enqueue_image_tasks(project, steps_result["steps"], size="1536x1024",summary=cursor["summary"])
            # i = 1
            # for step in steps_result["steps"]:
            #     # if it's always a list of strings:
            #     step_text = ", ".join(s for s in step["instructions"] if s and s.strip())
            #     step["image"] = generate_step_image(str(i), {"step_text": step_text, "project_id": project})
            #     i += 1
            
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
                "Provide just a sentence max 12 words for youtube search, dont over extend even if you dont cover all details and avoid putting sords inside parenthesis"
            )},
            {"role": "user", "content": json.dumps({
                "description": summary
            })}
        ],
        "max_completion_tokens": 500,
        "reasoning_effort": "low",
        "verbosity": "low",
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
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    items = r.json().get("items", [])
    videos=[{
        "videoId": it["id"]["videoId"],
        "title": it["snippet"]["title"],
        "description": it["snippet"].get("description", ""),
        "channelTitle": it["snippet"].get("channelTitle", ""),
    } for it in items]
    print(r.json())
    
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
    print(r.json())
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
    
def _build_prompt(step_text: str, guidance="neutral") -> str:
        lines = [
            "Create an instructional image that faithfully depicts the CURRENT STEP.",
            "No text overlays, no logos, no watermarks.",
            "DONT GENERATE ANY WORD OR WRITTEN INSTRUCTION,DONT WRITE ANYTHING",
            f"Context: \n{step_text}",
            "DONT GENERATE ANY WORD OR WRITTEN INSTRUCTION,DONT WRITE ANYTHING"
        ]
        # ... keep your optional lines ...
        if guidance == "neutral":
            lines.append("If any attributes are unspecified, choose the most informative composition.")
        else:
            lines.append("Prioritize clarity of tool-to-surface contact; choose view and distance to avoid occlusion.")
        
        lines.append("DONT GENERATE ANY WORD OR WRITTEN INSTRUCTION,DONT WRITE ANYTHING")
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
        prompt = _build_prompt(payload.step_text)
        raw_png = _generate_png(prompt=prompt, size=payload.size)
        png_bytes = _png_to_bytes_ensure_rgba(raw_png)
    except Exception as e:
        print(f"Image generation failed: {e}")
        raise

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
                "model": "imagen-4.0-generate-001"
            },
        )
    except Exception as e:
        print(f"S3 upload failed: {e}")
        raise

    url = _public_url_or_presigned(key)
    return {
        "message": "ok",
        "step_id": step_id,
        "project_id": payload.project_id,
        "s3_key": key,
        "url": url,
        "size": payload.size,
        "model": "imagen-4.0-generate-001",
        "prompt_preview": prompt[:180],
    }
    
    