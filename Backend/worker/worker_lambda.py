import json
import json
import re
import traceback
from datetime import datetime

import boto3
import requests
from bson.objectid import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database

from agents.solution_generation_multi_agent.image_generation_agent.image_generation_agent import ImageGenerationAgent
from agents.solution_generation_multi_agent.planner import ToolsAgent, EstimationAgent
from agents.solution_generation_multi_agent.services.image_generation_agent_service import ImageGenerationAgentService
from agents.solution_generation_multi_agent.services.steps_generation_agent_service import StepsGenerationAgentService
from agents.solution_generation_multi_agent.steps_generation_agent.steps_generation_agent import StepsGenerationAgent
from config.settings import get_settings
from database.mongodb import mongodb
from helper import similar_by_project, store_tool_in_database, create_and_store_tool_embeddings, find_similar_tools, \
    update_tool_usage

settings = get_settings()
s3 = boto3.client("s3", region_name=settings.AWS_REGION)
sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")
steps_collection: Collection = database.get_collection("ProjectSteps")
tools_collection: Collection = database.get_collection("Tools")


def enqueue_image_tasks(project_id: str, steps: list[dict], size: str = "1536x1024", summary: str = "") -> None:
    """Send one SQS message per step (no batch API)."""

    # LOCAL TESTING: Process images synchronously instead of sending to SQS
    # Uncomment the block below for local testing
    # for i, step in enumerate(steps, start=1):
    #     sum_text = "Overall summary: " + summary + "\n"
    #     step_text = "CURRENT STEP: " + ", ".join(s for s in step.get("instructions", []) if s and s.strip())
    #     body = {
    #         "task": "image_step",
    #         "project": project_id,
    #         "step_id": str(i),
    #         "step_text": step_text,
    #         "summary_text": sum_text,
    #         "size": size
    #     }
    #     project_collection.update_one({"_id": ObjectId(project_id)},
    #                                   {"$set": {f"step_generation.steps.{int(i) - 1}.image.status": "in-progress"}})
    #     handle_image_step(body)
    # return

    # PRODUCTION: Use SQS
    images_sqs_url = settings.AWS_SQS_URL
    if not images_sqs_url:
        print("⚠️ AWS_SQS_URL not set; skipping enqueue")
        return
    for i, step in enumerate(steps, start=1):
        sum_text = "Overall summary: " + summary + "\n"
        step_text = "CURRENT STEP: " + ", ".join(s for s in step.get("instructions", []) if s and s.strip())
        body = {
            "task": "image_step",
            "project": project_id,
            "step_id": str(i),
            "step_text": step_text,
            "summary_text": sum_text,
            "size": size
        }
        project_collection.update_one({"_id": ObjectId(project_id)},
                                      {"$set": {f"step_generation.steps.{int(i) - 1}.image.status": "in-progress"}})

        sqs.send_message(QueueUrl=images_sqs_url, MessageBody=json.dumps(body))


def handle_image_step(msg: dict) -> None:
    """Generate+upload image for a single step and persist result."""
    project_id = msg["project"]
    step_id = msg["step_id"]
    step_text = msg["step_text"]
    summary_text = msg.get("summary_text")
    size = msg.get("size", "1536x1024")

    image_generation_agent = ImageGenerationAgent()
    image_generation_service = ImageGenerationAgentService(
        image_generation_agent=image_generation_agent,
        s3_client=s3
    )
    # Use Image Generation Service
    result = image_generation_service.generate_step_image(
        step_id=step_id,
        step_text=step_text,
        summary_text=summary_text,
        size=size,
        project_id=project_id
    )

    # Convert Pydantic model to dict for MongoDB
    res = result.model_dump()

    project_collection.update_one({"_id": ObjectId(project_id)},
                                  {"$set": {f"step_generation.steps.{int(step_id) - 1}.image": res}})


def reset_all_steps(project_id):
    cursor = project_collection.find_one({
        "_id": ObjectId(project_id)
    })
    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        print("there is steps")
        print(cursor)
        project_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"step_generation.steps.$[].completed": False, "completed": False}}
        )

        return {"message": "Project/Steps updated"}

    return {"message": "No steps found"}


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

            print("🔍 Searching for similar projects")
            similar_result = similar_by_project(str(cursor["_id"]))
            print(f"similar_result: {similar_result}")

            # Check if similar_result has the expected structure
            if similar_result and "project_id" in similar_result and "best_score" in similar_result:
                print(
                    f"🔍 Found similar project: {similar_result['project_id']} with score: {similar_result['best_score']}")
            elif similar_result and "matches" in similar_result:
                # This is the "collection doesn't exist" case
                print("🔍 No Qdrant collection found, proceeding with generation from scratch")
                similar_result = None  # Treat as no matches
            else:
                print("🔍 No similar project found, proceeding with generation from scratch")
                similar_result = None

            if similar_result and similar_result["best_score"] >= 0.95:
                # If we found a highly similar project, we can use it as a reference
                print(f"🔗 Using similar project {similar_result['project_id']} as reference"
                      f" (score: {similar_result['best_score']})")

                matched_project = project_collection.find_one({"_id": ObjectId(similar_result["project_id"])})

                tools_result = matched_project.get("tool_generation", {})

                steps_result = matched_project.get("step_generation", {})

                estimation_result = matched_project.get("estimation_generation", {})

                update_project(str(cursor["_id"]), {
                    "tool_generation": tools_result,
                    "step_generation": steps_result,
                    "estimation_generation": estimation_result
                })

                reset_all_steps(str(cursor["_id"]))

                print("✅ Copied tools, steps, and estimation from matched project")

                update_project(str(cursor["_id"]), {"generation_status": "complete"})

                print("✅ project generation complete via RAG")

                continue

            if similar_result and 0.7 <= similar_result["best_score"] < 0.95:
                print(
                    f"🔍 Found similar project: {similar_result['project_id']} with score: {similar_result['best_score']}")
                print(f"⚠️ Similarity below threshold for reuse; proceeding with full generation")

                similar_project = project_collection.find_one({"_id": ObjectId(similar_result["project_id"])})
                if similar_project:
                    tools_agent = ToolsAgent(new_summary=cursor["summary"], matched_summary=similar_project["summary"],
                                             matched_tools=similar_project["tool_generation"]["tools"])
                else:
                    tools_agent = ToolsAgent()
            else:
                tools_agent = ToolsAgent()

            tools_result = tools_agent.recommend_tools(
                summary=cursor["summary"],
                include_json=True
            )

            # Generate tools using the independent agent
            if tools_result is None:
                print("LLM Generation tools failed")
                return {"message": "LLM Generation tools failed"}

            # FLOW 2: Compare and enhance tools with existing ones
            if "tools" in tools_result and tools_result["tools"]:
                print(f"🔄 FLOW 2: Comparing {len(tools_result['tools'])} generated tools with existing tools")

                try:

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
                                try:
                                    img = tools_agent._get_image_url(tool["name"])
                                    tool["image_link"] = img
                                except Exception:
                                    tool["image_link"] = None

                                safe = tools_agent._sanitize_for_amazon(tool["name"])
                                tool[
                                    "amazon_link"] = f"https://www.amazon.com/s?k={safe}&tag={tools_agent.amazon_affiliate_tag}"

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

            tools_result["status"] = "complete"

            update_project(str(cursor["_id"]), {"tool_generation": tools_result})

            # FLOW 1: Extract and save tools to tools_collection
            try:
                print(f"🔄 FLOW 1: Extracting generated tools to tools_collection")

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

            update_project(str(cursor["_id"]), {"step_generation": {"status": "in progress"}})

            # Initialize steps generation service
            steps_agent = StepsGenerationAgent()
            steps_service = StepsGenerationAgentService(steps_agent)

            # Prepare matched data if similarity found
            matched_summary = None
            matched_steps = None
            if similar_result and 0.7 <= similar_result["best_score"] < 0.95:
                print(
                    f"🔍 Steps Found similar project: {similar_result['project_id']} with score: {similar_result['best_score']}")
                print(f"⚠️ Similarity below threshold for reuse; proceeding with full generation")
                similar_project = project_collection.find_one({"_id": ObjectId(similar_result["project_id"])})
                if similar_project:
                    matched_summary = similar_project["summary"]
                    matched_steps = similar_project["step_generation"].get("steps")

            # Generate steps using service
            steps_result = steps_service.generate_steps(
                tools=cursor["tool_generation"],
                summary=cursor["summary"],
                user_answers=cursor.get("user_answers") or cursor.get("answers"),
                questions=cursor["questions"],
                matched_summary=matched_summary,
                matched_steps=matched_steps
            )

            if steps_result is None:
                print("LLM Generation steps failed")
                return {"message": "LLM Generation steps failed"}

            youtube_url = get_youtube_link(cursor["summary"])
            steps_result["youtube"] = youtube_url

            update_project(str(cursor["_id"]), {"step_generation": steps_result})

            enqueue_image_tasks(project, steps_result["steps"], size="1536x1024", summary=cursor["summary"])

            step_meta = {k: v for k, v in steps_result.items() if k != "steps"}
            step_meta["status"] = "complete"

            for step in steps_result.get("steps", []):
                step_doc = {
                    "projectId": ObjectId(project),
                    "order": step.get("order"),
                    "stepNumber": step.get("order"),  # keep for backward compatibility
                    "title": step.get("title", f"Step {step.get('order', 0)}"),
                    "instructions": step.get("instructions", []),
                    "description": " ".join(step.get("instructions", [])),
                    "est_time_min": step.get("est_time_min", 0),
                    "time_text": step.get("time_text", ""),
                    "tools_needed": step.get("tools_needed", []),
                    "safety_warnings": step.get("safety_warnings", []),
                    "tips": step.get("tips", []),
                    "image_url": step.get("image_url"),
                    "videoTutorialLink": youtube_url,
                    "referenceLinks": [],
                    "status": (step.get("status") or "pending").lower(),
                    "progress": 0,
                    "completed": False,
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                }
                steps_collection.insert_one(step_doc)

            print("Steps Generated")

            cursor = project_collection.find_one({"_id": ObjectId(project)})

            update_project(str(cursor["_id"]), {"estimation_generation": {"status": "in progress"}})

            estimation_agent = EstimationAgent()

            estimation_result = estimation_agent.generate_estimation(
                tools_data=cursor["tool_generation"],
                steps_data=cursor["step_generation"],
                summary=cursor["summary"]
            )

            if estimation_result is None:
                print("LLM Generation steps failed")
                return {"message": "LLM Generation steps failed"}

            estimation_result["status"] = "complete"

            update_project(str(cursor["_id"]), {"estimation_generation": estimation_result})

            update_project(str(cursor["_id"]), {"generation_status": "complete"})

            print("✅ project generation complete")
            return None

        except Exception as e:
            traceback.print_exc()
            return None
    return None


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
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)  # strip fences
    m = re.search(r"\{.*\}\s*$", s, flags=re.S)  # grab last JSON object
    if m: s = m.group(0)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")


def get_youtube_link(summary):
    youtube_key = settings.YOUTUBE_API_KEY
    openai_key = settings.OPENAI_API_KEY

    payload = {
        "model": "gpt-5-mini",  # or the model you prefer
        "messages": [
            {"role": "system", "content": (
                "You are a summarization agent for youtube searches"
                "Return one line in based of the text provided to search the most helpfull video"
                "Provide just a sentence max 8 words for youtube search, DONT INCLUNDE MEASURES"
            )},
            {"role": "user", "content": json.dumps({
                "description": summary
            })}
        ],
        "max_completion_tokens": 1500,
        "reasoning_effort": "low",
        "verbosity": "low",
    }
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {openai_key}"},
        json=payload, timeout=30
    )
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(content)

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": youtube_key,
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
    videos = [{
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
                "You are a video selection assistant."
                "Pick ONE video that best matches the given project "
                "The video MUST be RELATED to the main project topic."
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
        headers={"Authorization": f"Bearer {openai_key}"},
        json=payload, timeout=30
    )
    r.raise_for_status()
    data = r.json()
    print(r.json())
    content = data["choices"][0]["message"]["content"]
    verdict = clean_and_parse_json(content)
    best_id = verdict.get("best_videoId")
    best = next((c for c in videos if c["videoId"] == best_id), None)
    if not best:
        # fallback to top candidate
        best = videos[0]
    return f"https://www.youtube.com/embed/{best['videoId']}"
