import json
import json
import re
import traceback
from datetime import datetime
import time
from typing import Any

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
from helper import (
    similar_by_project,
    store_tool_in_database,
    create_and_store_tool_embeddings,
    find_similar_tools,
    update_tool_usage,
    search_kb_by_summary,        # NEW — KB similarity search
    KB_SIMILARITY_THRESHOLD,     # NEW — 0.7 constant
)
from database.llm_consumption import record_openai_response_usage

settings = get_settings()
s3 = boto3.client("s3", region_name=settings.AWS_REGION)
sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")
steps_collection: Collection = database.get_collection("ProjectSteps")
tools_collection: Collection = database.get_collection("Tools")
users_collection: Collection = database.get_collection("Users")

def _get_image_service() -> ImageGenerationAgentService:
    """Create a fresh ImageGenerationAgentService. Called per-invocation."""
    return ImageGenerationAgentService(
        image_generation_agent=ImageGenerationAgent(),
        s3_client=s3,
        project_collection=project_collection,
    )


def _format_profile_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, list):
        cleaned_items = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(cleaned_items) if cleaned_items else None
    return str(value)


def _build_user_profile_context(project: dict) -> str:
    """
    Build concise, non-sensitive user profile context for generation prompts.
    Avoid auth identifiers and email; only include details that can improve DIY guidance.
    """
    user_id = project.get("userId")
    if not user_id:
        return ""

    try:
        user_object_id = user_id if isinstance(user_id, ObjectId) else ObjectId(str(user_id))
        user = users_collection.find_one({"_id": user_object_id})
    except Exception as e:
        print(f"Unable to load user profile context: {e}")
        return ""

    if not user:
        return ""

    profile_fields = [
        ("Experience level", user.get("experienceLevel")),
        ("DIY confidence", user.get("confidence")),
        ("Tools available", user.get("tools")),
        ("Interested project types", user.get("interestedProjects")),
        ("Country", user.get("country")),
        ("State", user.get("state")),
        ("User notes", user.get("describe")),
    ]

    lines = ["## User Profile Context"]
    for label, value in profile_fields:
        formatted = _format_profile_value(value)
        if formatted:
            lines.append(f"- {label}: {formatted}")

    if len(lines) == 1:
        return ""

    lines.append(
        "Use this context to tailor difficulty, safety warnings, tool choices, and explanation detail. "
        "Do not mention this profile unless it is directly helpful."
    )
    return "\n".join(lines)


def _append_user_profile_context(summary: str, user_profile_context: str) -> str:
    if not user_profile_context:
        return summary
    return f"{summary.strip()}\n\n{user_profile_context}"


def preflight_image_setup(project_id: str, summary: str) -> None:
    service = _get_image_service()

    # 1. Visual DNA
    existing_dna = service.get_visual_dna(project_id)
    if existing_dna:
        print(f"✅ Visual DNA exists — domain: {existing_dna.get('domain')}")
        dna = existing_dna
    else:
        print(f"🔍 Generating Visual DNA for project {project_id}")
        dna = service.generate_visual_dna(summary)
        service.save_visual_dna(project_id, dna)
        print(f"✅ Visual DNA saved — domain: {dna.get('domain')}, "
              f"objects: {list(dna.get('object_colors', {}).keys())}")

    # 2. Context images — build_context_images handles all three cases
    existing_ctx = service.get_context_images(project_id)
    if existing_ctx and existing_ctx.objects:
        print(f"✅ Context images exist: {[o.name for o in existing_ctx.objects]}")
    else:
        print(f"🔍 Building context images for project {project_id}")
        try:
            ctx_result = service.build_context_images(
                project_id=project_id,
                summary_text=summary,
                dna=dna,
            )
            user_count = sum(
                1 for o in ctx_result.objects
                if "user-uploads" in (o.s3_key or "")
            )
            gen_count = len(ctx_result.objects) - user_count
            print(
                f"✅ Context images ready: {len(ctx_result.objects)} total "
                f"({user_count} from user, {gen_count} generated)"
            )
        except Exception as e:
            print(f"⚠️ Context image build failed (non-fatal): {e}")

def enqueue_image_tasks(
        project_id: str,
        steps: list[dict],
        size: str = "1536x1024",
        summary: str = "",
) -> None:
    """
    1. Run preflight (DNA + anchors) synchronously — blocks until complete.
    2. Enqueue one SQS message per step, staggered so earlier steps
       complete before later ones start fetching their references.
    """
    images_sqs_url = settings.AWS_SQS_URL
    if not images_sqs_url:
        print("⚠️ AWS_SQS_URL not set; skipping enqueue")
        return

    # ── PREFLIGHT: must complete before ANY SQS message is sent ─────────────
    if summary:
        preflight_image_setup(project_id, summary)

    # ── ENQUEUE: staggered so step N-1 likely finishes before step N starts ──
    for i, step in enumerate(steps, start=1):
        sum_text = "Overall summary: " + summary + "\n"
        step_text = "CURRENT STEP: " + ", ".join(
            s for s in step.get("instructions", []) if s and s.strip()
        )
        body = {
            "task": "image_step",
            "project": project_id,
            "step_id": str(i),
            "step_text": step_text,
            "summary_text": sum_text,
            "size": size,
        }
        project_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {f"step_generation.steps.{i - 1}.image.status": "in-progress"}}
        )
        sqs.send_message(
            QueueUrl=images_sqs_url,
            MessageBody=json.dumps(body),
            # Stagger: step1=0s, step2=15s, step3=30s...
            # 15s gives each step time to generate + upload before next reads it
            DelaySeconds=min((i - 1) * 15, 900),
        )
        print(f"📤 Enqueued step {i} with {(i-1)*15}s delay")

def handle_image_step(msg: dict) -> None:
    """Generate + upload image for a single step and persist result."""
    project_id = msg["project"]
    step_id = msg["step_id"]
    step_text = msg["step_text"]
    summary_text = msg.get("summary_text")
    size = msg.get("size", "1536x1024")

    service = _get_image_service()

    # ── Readiness check: wait for DNA + anchors if preflight is still running ─
    # This handles edge cases where preflight and step1 overlap
    max_wait_secs = 60
    waited = 0
    while waited < max_wait_secs:
        dna = service.get_visual_dna(project_id)
        if dna:
            break
        print(f"⏳ Step {step_id} waiting for Visual DNA... ({waited}s)")
        time.sleep(5)
        waited += 5

    if not dna:
        print(f"⚠️ Step {step_id}: Visual DNA not ready after {max_wait_secs}s — generating fallback")

    result = service.generate_step_image(
        step_id=step_id,
        step_text=step_text,
        summary_text=summary_text,
        size=size,
        project_id=project_id,
    )

    # Single write — model_dump() includes all fields: url, state_summary, etc.
    project_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {f"step_generation.steps.{int(step_id) - 1}.image": result.model_dump()}},
    )
    print(f"✅ Step {step_id} image complete: {result.url}")


def reset_all_steps(project_id):
    cursor = project_collection.find_one({"_id": ObjectId(project_id)})
    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        print("there is steps")
        project_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"step_generation.steps.$[].completed": False, "completed": False}}
        )
        return {"message": "Project/Steps updated"}
    return {"message": "No steps found"}


# ---------------------------------------------------------------------------
# KB knowledge helper
# ---------------------------------------------------------------------------

def _build_kb_knowledge_str(kb_result: dict) -> str:
    """
    Flatten a KB result dict into a structured string suitable for passing
    to ToolsAgent / StepsGenerationAgent as additional context.
    """
    lines = [
        "=== KNOWLEDGE BASE REFERENCE ===",
        f"Source: {kb_result.get('url', 'N/A')}",
        "",
        "Summary:",
        kb_result.get("summary", "N/A"),
        "",
        "Tools found in similar job:",
        ", ".join(kb_result.get("tools", [])) or "None",
        "",
        "Materials found in similar job:",
        ", ".join(kb_result.get("materials", [])) or "None",
        "",
        "Safety warnings found in similar job:",
        "\n".join(f"- {w}" for w in kb_result.get("warnings", [])) or "None",
        "=================================",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    for record in event.get("Records", []):
        try:
            payload = json.loads(record.get("body", "{}"))
            task = payload.get("task", "full")

            if task == "image_step":
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

            cursor = project_collection.find_one({"_id": ObjectId(project_id_str)})
            if not cursor:
                print("⚠️ Project not found in Mongo -> skipping")
                continue

            gen_status = cursor.get("generation_status")
            if gen_status == "complete":
                print(f"⚠️ Project {project_id_str} already generated (status=complete) -> skipping")
                continue

            summary = cursor.get("summary")
            if not summary or not isinstance(summary, str) or not summary.strip():
                print("⚠️ Project has no valid summary → skipping RAG and generation")
                update_project(str(cursor["_id"]), {"generation_status": "failed", "error": "Missing summary"})
                continue

            user_profile_context = _build_user_profile_context(cursor)
            summary_with_user_context = _append_user_profile_context(summary, user_profile_context)
            if user_profile_context:
                print("User profile context will be included in generation prompts")

            # ------------------------------------------------------------------
            # STEP 1 — Project-level similarity (existing logic, unchanged)
            # ------------------------------------------------------------------
            similar_result = None
            if summary and summary.strip():
                print("🔍 Searching for similar projects")
                try:
                    similar_result = similar_by_project(str(cursor["_id"]))
                    print(f"🔍 similar_result: {similar_result}")
                except Exception as e:
                    print(f"⚠️ similar_by_project failed: {e}")
                    similar_result = None

            if similar_result and isinstance(similar_result, dict) and "matches" in similar_result:
                print("🔍 Qdrant collection missing (or no data) -> treating as no match")
                similar_result = None

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

            # ------------------------------------------------------------------
            # STEP 2 — KB similarity (new logic, runs for cases 2 & 3 only)
            # We query once here so the result is available across both branches.
            # ------------------------------------------------------------------
            kb_result = None
            project_score = similar_result["best_score"] if similar_result else -1.0

            # Only bother querying KB when we are NOT in the copy path (score >= 0.95)
            if project_score < 0.95:
                print("🔍 Searching KB for similar summary")
                try:
                    kb_result = search_kb_by_summary(summary, top_k=1)
                    if kb_result:
                        print(f"🔍 KB best score={kb_result['score']:.4f} url={kb_result.get('url')}")
                    else:
                        print("🔍 No KB match returned")
                except Exception as e:
                    print(f"⚠️ search_kb_by_summary failed: {e}")
                    kb_result = None

            # Decide whether the KB result clears the threshold
            kb_knowledge_str = None
            if kb_result and kb_result["score"] >= KB_SIMILARITY_THRESHOLD:
                kb_knowledge_str = _build_kb_knowledge_str(kb_result)
                print(f"✅ KB knowledge will be injected (score={kb_result['score']:.4f})")
            else:
                print("ℹ️ KB score below threshold or no KB match — agents run without KB context")

            # ------------------------------------------------------------------
            # CASE 1 — Very high project similarity -> COPY (unchanged)
            # ------------------------------------------------------------------
            if similar_result and similar_result["best_score"] >= 0.95 and matched_project:
                tools_result = matched_project.get("tool_generation")
                steps_result = matched_project.get("step_generation")
                estimation_result = matched_project.get("estimation_generation")

                if not tools_result or not steps_result:
                    print("⚠️ Matched project missing generated tools/steps -> falling back to generation")
                    similar_result = None
                    matched_project = None
                else:
                    print(f"🔗 Copying from similar project {matched_project['_id']} "
                          f"(score: {similar_result['best_score']})")
                    update_project(str(cursor["_id"]), {
                        "tool_generation": tools_result,
                        "step_generation": steps_result,
                        "estimation_generation": estimation_result
                    })
                    reset_all_steps(str(cursor["_id"]))
                    update_project(str(cursor["_id"]), {"generation_status": "complete"})
                    print("✅ project generation complete via RAG (copy)")
                    continue

            # ------------------------------------------------------------------
            # CASE 2 — Medium project similarity -> MODIFY using matched project
            #          + optionally inject KB knowledge into agents
            # ------------------------------------------------------------------
            tools_agent = None
            if similar_result and 0.7 <= similar_result["best_score"] < 0.95 and matched_project:
                print(f"🔍 CASE 2 — Modify path. Project score={similar_result['best_score']:.4f}")

                matched_tools = matched_project.get("tool_generation", {}).get("tools") if matched_project else None
                matched_summary = matched_project.get("summary") if matched_project else None

                try:
                    tools_agent = ToolsAgent(
                        new_summary=summary_with_user_context,
                        matched_summary=matched_summary,
                        matched_tools=matched_tools,
                        # NEW: pass KB knowledge if available
                        kb_knowledge=kb_knowledge_str,
                    )
                    print(f"✅ ToolsAgent initialised with matched project context"
                          + (" + KB knowledge" if kb_knowledge_str else ""))
                except Exception:
                    print("⚠️ ToolsAgent init with matched context failed, falling back")
                    try:
                        tools_agent = ToolsAgent(kb_knowledge=kb_knowledge_str)
                    except Exception:
                        tools_agent = ToolsAgent()

            # ------------------------------------------------------------------
            # CASE 3 — No project match (or low score) -> DEFAULT generation
            #          + optionally inject KB knowledge into agents
            # ------------------------------------------------------------------
            else:
                print(f"🔍 CASE 3 — No suitable project match (score={project_score:.4f}). "
                      + ("Using KB knowledge." if kb_knowledge_str else "Running default agents."))
                try:
                    tools_agent = ToolsAgent(
                        # NEW: pass KB knowledge if available; ToolsAgent handles None gracefully
                        kb_knowledge=kb_knowledge_str,
                    )
                except Exception:
                    tools_agent = ToolsAgent()

            # ------------------------------------------------------------------
            # Generate tools (LLM)
            # ------------------------------------------------------------------
            try:
                tools_result = tools_agent.recommend_tools(
                    summary=summary_with_user_context,
                    include_json=True
                )
            except Exception as e:
                print(f"❌ tools_agent.recommend_tools failed: {e}")
                tools_result = None

            if tools_result is None:
                print("❌ LLM Generation tools failed -> skipping this record")
                update_project(str(cursor["_id"]), {"generation_status": "failed"})
                continue

            # ------------------------------------------------------------------
            # FLOW 2 — Compare and enhance tools with existing Tools collection
            # ------------------------------------------------------------------
            if tools_result and "tools" in tools_result and tools_result["tools"]:
                try:
                    enhanced_tools = []
                    reuse_stats = {"reused": 0, "new": 0, "errors": 0}

                    for tool in tools_result["tools"]:
                        try:
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

            # ------------------------------------------------------------------
            # FLOW 1 — Extract and save new tools to tools_collection
            # ------------------------------------------------------------------
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
                            try:
                                create_and_store_tool_embeddings(tool, tool_id)
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

            # ------------------------------------------------------------------
            # Steps generation — carry KB + matched-project context through
            # ------------------------------------------------------------------
            cursor = project_collection.find_one({"_id": ObjectId(project_id_str)})
            update_project(str(cursor["_id"]), {"step_generation": {"status": "in progress"}})

            # Build matched-project context for steps (case 2 only)
            matched_summary_for_steps = None
            matched_steps_for_steps = None
            if similar_result and 0.7 <= similar_result.get("best_score", -1) < 0.95 and matched_project:
                matched_summary_for_steps = matched_project.get("summary")
                matched_steps_for_steps = matched_project.get("step_generation", {}).get("steps")

            try:
                steps_agent = StepsGenerationAgent()
                steps_service = StepsGenerationAgentService(steps_agent)
                steps_result = steps_service.generate_steps(
                    tools=cursor.get("tool_generation"),
                    summary=summary_with_user_context,
                    user_answers=cursor.get("user_answers") or cursor.get("answers"),
                    questions=cursor.get("questions", []),
                    matched_summary=matched_summary_for_steps,
                    matched_steps=matched_steps_for_steps,
                    # NEW: pass KB knowledge if available
                    kb_knowledge=kb_knowledge_str,
                )
            except Exception as e:
                print(f"❌ Steps generation failed: {e}")
                update_project(str(cursor["_id"]), {"step_generation": {"status": "failed"}})
                continue

            if not steps_result:
                print("❌ LLM Generation steps failed -> skipping")
                update_project(str(cursor["_id"]), {"step_generation": {"status": "failed"}})
                continue

            # Persist steps
            try:
                youtube_url = get_youtube_link(cursor.get("summary", ""))
                steps_result["youtube"] = youtube_url
                update_project(str(cursor["_id"]), {"step_generation": steps_result})
                enqueue_image_tasks(project_id_str, steps_result.get("steps", []),
                                    size="1536x1024", summary=summary_with_user_context)
            except Exception as e:
                print(f"⚠️ Failed after steps generation: {e}")

            try:
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

            # ------------------------------------------------------------------
            # Estimation generation
            # ------------------------------------------------------------------
            cursor = project_collection.find_one({"_id": ObjectId(project_id_str)})
            update_project(str(cursor["_id"]), {"estimation_generation": {"status": "in progress"}})

            try:
                estimation_agent = EstimationAgent()
                estimation_result = estimation_agent.generate_estimation(
                    tools_data=cursor.get("tool_generation"),
                    steps_data=cursor.get("step_generation"),
                    summary=summary_with_user_context
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
            update_project(str(cursor["_id"]), {"generation_status": "complete"})
            print(f"✅ project generation complete for {project_id_str}")

        except Exception as e:
            traceback.print_exc()
            continue

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
    if raw_str is None:
        raise ValueError("No input string")
    s = raw_str.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    m = re.search(r"\{.*\}\s*$", s, flags=re.S)
    if m:
        s = m.group(0)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")


def get_youtube_link(summary, project_id: str | None = None, user_id: str | None = None):
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
    record_openai_response_usage(
        data,
        model=payload["model"],
        operation="youtube_search_query_generation",
        project_id=project_id,
        user_id=user_id,
        endpoint="/v1/chat/completions",
    )
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
    record_openai_response_usage(
        data,
        model=payload["model"],
        operation="youtube_video_selection",
        project_id=project_id,
        user_id=user_id,
        endpoint="/v1/chat/completions",
    )
    print(r.json())
    content = data["choices"][0]["message"]["content"]
    verdict = clean_and_parse_json(content)
    best_id = verdict.get("best_videoId")
    best = next((c for c in videos if c["videoId"] == best_id), None)
    if not best:
        # fallback to top candidate
        best = videos[0]
    return f"https://www.youtube.com/embed/{best['videoId']}"
