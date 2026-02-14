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
    # Process each incoming message (SQS records etc.)
    for record in event.get("Records", []):
        try:
            payload = json.loads(record.get("body", "{}"))
            task = payload.get("task", "full")

            if task == "image_step":
                # Image-only job (runs in parallel for each step)
                try:
                    handle_image_step(payload)
                except Exception as e:
                    print(f"❌ handle_image_step failed: {e}")
                continue

            project_id_str = payload.get("project")
            if not project_id_str:
                print("⚠️ Incomplete message: missing project id")
                continue

            print(f"📦 Received job for project {project_id_str}")

            # Validate project exists in Mongo
            cursor = project_collection.find_one({"_id": ObjectId(project_id_str)})
            if not cursor:
                print("⚠️ Project not found in Mongo -> skipping")
                continue

            # Avoid duplicate generation
            gen_status = cursor.get("generation_status")
            if gen_status == "complete":
                print(f"⚠️ Project {project_id_str} already generated (status=complete) -> skipping")
                continue

            # Build or get summary
            summary = cursor.get("summary")
            if not summary or not isinstance(summary, str) or not summary.strip():
                # Attempt to build from structured fields
                print("⚠️ Project has no valid summary → skipping RAG and generation")
                update_project(str(cursor["_id"]), {"generation_status": "failed", "error": "Missing summary"})
                continue

            # If we have a usable summary, try similarity; otherwise skip RAG
            similar_result = None
            if summary and summary.strip():
                print("🔍 Searching for similar projects")
                try:
                    similar_result = similar_by_project(str(cursor["_id"]))
                    print(f"🔍 similar_result: {similar_result}")
                except Exception as e:
                    print(f"⚠️ similar_by_project failed: {e}")
                    similar_result = None

            # Normalize similar_result shape: if it's the 'collection missing' form, treat as no match
            if similar_result and isinstance(similar_result, dict) and "matches" in similar_result:
                print("🔍 Qdrant collection missing (or no data) -> treating as no match")
                similar_result = None

            # If a match was returned, ensure the matched project still exists in Mongo and has generated data if we plan to copy
            matched_project = None
            if similar_result and "project_id" in similar_result and similar_result.get("best_score") is not None:
                matched_id = similar_result["project_id"]
                try:
                    matched_project = project_collection.find_one({"_id": ObjectId(matched_id)})
                except Exception:
                    matched_project = None

                if not matched_project:
                    print(f"⚠️ Orphan vector: matched project {matched_id} not present in Mongo -> skipping reuse")
                    similar_result = None
                    matched_project = None

            # COPY PATH: very high similarity -> copy tools/steps/estimation
            if similar_result and similar_result["best_score"] >= 0.95 and matched_project:
                # ensure matched project actually has generated content to copy
                tools_result = matched_project.get("tool_generation")
                steps_result = matched_project.get("step_generation")
                estimation_result = matched_project.get("estimation_generation")

                if not tools_result or not steps_result:
                    print("⚠️ Matched project missing generated tools/steps -> falling back to generation")
                    similar_result = None
                    matched_project = None
                else:
                    print(f"🔗 Using similar project {matched_project['_id']} as reference (score: {similar_result['best_score']})")

                    update_project(str(cursor["_id"]), {
                        "tool_generation": tools_result,
                        "step_generation": steps_result,
                        "estimation_generation": estimation_result
                    })

                    reset_all_steps(str(cursor["_id"]))

                    update_project(str(cursor["_id"]), {"generation_status": "complete"})
                    print("✅ project generation complete via RAG (copy)")
                    # done with this record
                    continue

            # MODIFY PATH: medium similarity -> use matched project as context for agents
            tools_agent = None
            if similar_result and 0.7 <= similar_result["best_score"] < 0.95 and matched_project:
                print(f"🔍 Found similar project: {similar_result['project_id']} with score: {similar_result['best_score']}")
                # If matched project has generation data, pass matched tools/summary as context; otherwise proceed with plain agent
                matched_tools = matched_project.get("tool_generation", {}).get("tools") if matched_project else None
                matched_summary = matched_project.get("summary") if matched_project else None

                try:
                    tools_agent = ToolsAgent(
                        new_summary=summary,
                        matched_summary=matched_summary,
                        matched_tools=matched_tools
                    )
                except Exception:
                    print("⚠️ ToolsAgent init with matched context failed, falling back to default ToolsAgent")
                    tools_agent = ToolsAgent()
            else:
                # no suitable match -> default agent
                tools_agent = ToolsAgent()

            # Generate tools (LLM)
            try:
                tools_result = tools_agent.recommend_tools(
                    summary=summary,
                    include_json=True
                )
            except Exception as e:
                print(f"❌ tools_agent.recommend_tools failed: {e}")
                tools_result = None

            if tools_result is None:
                print("❌ LLM Generation tools failed -> skipping this record")
                # mark failure optionally
                update_project(str(cursor["_id"]), {"generation_status": "failed"})
                continue

            # FLOW 2: Compare and enhance tools with existing tools collection (reuse images/amazon links)
            if tools_result and "tools" in tools_result and tools_result["tools"]:
                try:
                    enhanced_tools = []
                    reuse_stats = {"reused": 0, "new": 0, "errors": 0}

                    for tool in tools_result["tools"]:
                        try:
                            # Use tool name as query for similarity
                            similar_tools = find_similar_tools(
                                query=tool.get("name", ""),
                                limit=3,
                                similarity_threshold=0.75
                            )

                            if similar_tools and similar_tools[0].get("similarity_score", 0) >= 0.8:
                                best_match = similar_tools[0]
                                tool["image_link"] = best_match.get("image_link")
                                tool["amazon_link"] = best_match.get("amazon_link")
                                tool["reused_from"] = best_match.get("tool_id")
                                tool["similarity_score"] = best_match.get("similarity_score")
                                update_tool_usage(best_match["tool_id"])
                                reuse_stats["reused"] += 1
                                print(f"   ✅ Reused image/links for: {tool.get('name')}")
                            else:
                                reuse_stats["new"] += 1
                                print(f"   🆕 New tool: {tool.get('name')}")
                                try:
                                    img = tools_agent._get_image_url(tool.get("name", ""))
                                    tool["image_link"] = img
                                except Exception:
                                    tool["image_link"] = None
                                safe = tools_agent._sanitize_for_amazon(tool.get("name", ""))
                                tool["amazon_link"] = f"https://www.amazon.com/s?k={safe}&tag={tools_agent.amazon_affiliate_tag}"

                            enhanced_tools.append(tool)

                        except Exception as e:
                            print(f"❌ Error processing tool {tool.get('name', 'unknown')}: {e}")
                            enhanced_tools.append(tool)
                            reuse_stats["errors"] += 1

                    tools_result["tools"] = enhanced_tools
                    tools_result["reuse_metadata"] = reuse_stats
                    print(f"✅ FLOW 2 completed: {reuse_stats['reused']} reused, {reuse_stats['new']} new")

                except Exception as e:
                    print(f"⚠️ FLOW 2 comparison error: {e}")
                    tools_result.setdefault("reuse_metadata", {"error": str(e)})

            tools_result["status"] = "complete"
            update_project(str(cursor["_id"]), {"tool_generation": tools_result})

            # FLOW 1: Extract and save new tools to tools_collection
            try:
                print("🔄 FLOW 1: Extracting generated tools to tools_collection")
                saved_tools = []
                failed_tools = []
                if tools_result and "tools" in tools_result and tools_result["tools"]:
                    for tool in tools_result["tools"]:
                        try:
                            existing_tool = tools_collection.find_one({"name": tool.get("name")})
                            if existing_tool:
                                print(f"✅ Tool '{tool.get('name')}' already exists, skipping")
                                continue

                            tool_id = store_tool_in_database(tool)
                            # create embeddings and upsert into Qdrant tools collection
                            try:
                                embedding_result = create_and_store_tool_embeddings(tool, tool_id)
                            except Exception as ee:
                                print(f"⚠️ Failed creating/storing embeddings for tool {tool.get('name')}: {ee}")

                            saved_tools.append({"tool_id": tool_id, "name": tool.get("name"), "status": "saved"})
                            print(f"✅ FLOW 1: Saved tool '{tool.get('name')}'")
                        except Exception as e:
                            print(f"❌ FLOW 1: Failed to save tool {tool.get('name', 'unknown')}: {e}")
                            failed_tools.append({"tool": tool.get('name', 'unknown'), "error": str(e)})

                print(f"✅ FLOW 1: Completed - saved {len(saved_tools)} tools")
            except Exception as e:
                print(f"⚠️ FLOW 1: Failed to extract tools: {e}")

            # Refresh cursor for steps generation
            cursor = project_collection.find_one({"_id": ObjectId(project_id_str)})
            update_project(str(cursor["_id"]), {"step_generation": {"status": "in progress"}})

            # Prepare matched data for steps if modify path
            matched_summary = None
            matched_steps = None
            if similar_result and 0.7 <= similar_result["best_score"] < 0.95 and matched_project:
                matched_summary = matched_project.get("summary")
                matched_steps = matched_project.get("step_generation", {}).get("steps")

            # Generate steps
            try:
                steps_agent = StepsGenerationAgent()
                steps_service = StepsGenerationAgentService(steps_agent)
                steps_result = steps_service.generate_steps(
                    tools=cursor.get("tool_generation"),
                    summary=cursor.get("summary"),
                    user_answers=cursor.get("user_answers") or cursor.get("answers"),
                    questions=cursor.get("questions", []),
                    matched_summary=matched_summary,
                    matched_steps=matched_steps
                )
            except Exception as e:
                print(f"❌ Steps generation failed: {e}")
                update_project(str(cursor["_id"]), {"step_generation": {"status": "failed"}})
                continue

            if not steps_result:
                print("❌ LLM Generation steps failed -> skipping")
                update_project(str(cursor["_id"]), {"step_generation": {"status": "failed"}})
                continue

            # Add youtube link & persist steps
            try:
                youtube_url = get_youtube_link(cursor.get("summary", ""))
                steps_result["youtube"] = youtube_url
                update_project(str(cursor["_id"]), {"step_generation": steps_result})
                enqueue_image_tasks(project_id_str, steps_result.get("steps", []), size="1536x1024", summary=cursor.get("summary", ""))
            except Exception as e:
                print(f"⚠️ Failed after steps generation: {e}")

            # save individual step docs
            try:
                step_meta = {k: v for k, v in steps_result.items() if k != "steps"}
                step_meta["status"] = "complete"

                for step in steps_result.get("steps", []):
                    step_doc = {
                        "projectId": ObjectId(project_id_str),
                        "order": step.get("order"),
                        "stepNumber": step.get("order"),
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

                print("✅ Steps Generated and saved")
            except Exception as e:
                print(f"⚠️ Saving steps to DB failed: {e}")

            # Refresh cursor and generate estimation
            cursor = project_collection.find_one({"_id": ObjectId(project_id_str)})
            update_project(str(cursor["_id"]), {"estimation_generation": {"status": "in progress"}})

            try:
                estimation_agent = EstimationAgent()
                estimation_result = estimation_agent.generate_estimation(
                    tools_data=cursor.get("tool_generation"),
                    steps_data=cursor.get("step_generation"),
                    summary=cursor.get("summary")
                )
            except Exception as e:
                print(f"❌ Estimation generation failed: {e}")
                update_project(str(cursor["_id"]), {"estimation_generation": {"status": "failed"}})
                continue

            if not estimation_result:
                print("❌ Estimation generation returned None -> skipping")
                update_project(str(cursor["_id"]), {"estimation_generation": {"status": "failed"}})
                continue

            estimation_result["status"] = "complete"
            update_project(str(cursor["_id"]), {"estimation_generation": estimation_result})

            # mark project complete
            update_project(str(cursor["_id"]), {"generation_status": "complete"})
            print(f"✅ project generation complete for {project_id_str}")

            # continue to next record
            continue

        except Exception as e:
            traceback.print_exc()
            # Continue processing remaining records instead of returning early
            continue

    # finished processing all records
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
