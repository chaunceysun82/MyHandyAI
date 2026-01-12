import json
import os
# Import tools reuse functions from chatbot
import sys
from datetime import datetime

import boto3
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pymongo.collection import Collection
from pymongo.database import Database

from content_generation.planner import ToolsAgent, StepsAgentJSON, EstimationAgent
from database.mongodb import mongodb

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from routes.utils import find_similar_tools, update_tool_usage, extract_and_save_tools_from_project, update_project

router = APIRouter(prefix="/generation", tags=["generation"])
database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")
steps_collection: Collection = database.get_collection("ProjectSteps")


# Pydantic models for request/response

@router.get("/tools/{project_id}")
async def get_generated_tools(project_id: str):
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"tool_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if "tool_generation" not in doc or doc["tool_generation"] is None:
        raise HTTPException(status_code=404, detail="Tools not generated yet")
    return {"project_id": project_id, "tools_data": doc["tool_generation"]}


@router.get("/steps/{project_id}")
async def get_generated_steps(project_id: str):
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"step_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    steps_payload = doc.get("step_generation")
    if not steps_payload:
        raise HTTPException(status_code=404, detail="Steps not generated yet")
    return {"project_id": project_id, "steps_data": steps_payload}


# @router.get("/steps/{project_id}")
# async def get_generated_steps(project_id: str):
#     steps_cur = steps_collection.find(
#         {"projectId": ObjectId(project_id)},
#         {"projectId": 0}
#     ).sort("order", 1)
#     steps = []
#     for s in steps_cur:
#         s["_id"] = str(s["_id"])
#         steps.append(s)

#     if not steps:
#         doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"step_generation": 1})
#         if not doc or not doc.get("step_generation"):
#             raise HTTPException(status_code=404, detail="Steps not generated yet")
#         return {"project_id": project_id, "steps_data": doc["step_generation"]}

#     proj = project_collection.find_one(
#         {"_id": ObjectId(project_id)},
#         {"step_generation": 1}
#     )
#     meta = {}
#     if proj and proj.get("step_generation"):
#         meta = {k: v for k, v in proj["step_generation"].items() if k != "steps"}

#     return {
#         "project_id": project_id,
#         "steps_data": {
#             "steps": steps,
#             **meta
#         }
#     }


# @router.get("/steps/{project_id}")
# async def get_generated_steps(project_id: str):
#     steps = list(steps_collection.find({"projectId": ObjectId(project_id)}))
#     if not steps:
#         raise HTTPException(status_code=404, detail="Steps not generated yet")
#     for step in steps:
#         step["_id"] = str(step["_id"])
#         step["projectId"] = str(step["projectId"])
#     return {"project_id": project_id, "steps_data": steps}

@router.get("/estimation/{project_id}")
async def get_generated_estimation(project_id: str):
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"estimation_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if "estimation_generation" not in doc or doc["estimation_generation"] is None:
        raise HTTPException(status_code=404, detail="Estimation not generated yet")
    return {"project_id": project_id, "estimation_data": doc["estimation_generation"]}


@router.post("/tools/{project}")
async def generate_tools(project: str):
    """
    Generate tools and materials for a DIY project.
    This endpoint runs independently to avoid timeout issues.
    Now integrates with tools reuse system for better image management.
    """
    try:
        # Validate project exists
        cursor = project_collection.find_one({"_id": ObjectId(project)})
        if not cursor:
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate tools using the independent agent
        tools_agent = ToolsAgent()
        tools_result = tools_agent.recommend_tools(
            summary=cursor["summary"],
            include_json=True
        )
        if tools_result is None:
            raise HTTPException(status_code=400,
                                detail="Missing required fields (summary, answers, questions) on project")

        # FLOW 2: Compare and enhance tools with existing ones
        if "tools" in tools_result and tools_result["tools"]:
            print(f"🔄 FLOW 2: Comparing {len(tools_result['tools'])} generated tools with existing tools")

            try:
                # Use the direct function call instead of HTTP request
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

        update_project(str(cursor["_id"]), {"tool_generation": tools_result})

        # FLOW 1: Extract and save tools to tools_collection after generation
        try:
            print(f"🔄 FLOW 1: Extracting generated tools to tools_collection")

            # Extract tools from the project we just updated
            extraction_result = await extract_and_save_tools_from_project(project)

            # Add Flow 1 results to response
            tools_result["flow1_extraction"] = extraction_result

            print(f"✅ FLOW 1: Completed - tools extracted to collection")

        except Exception as e:
            print(f"⚠️ FLOW 1: Failed to extract tools: {e}")
            tools_result["flow1_extraction"] = {"error": str(e)}

        return {
            "success": True,
            "project_id": project,
            "tools_data": tools_result,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tools: {str(e)}")


@router.post("/all/{project}")
async def generate(project):
    try:
        cursor = project_collection.find_one({"_id": ObjectId(project)})
        if not cursor:
            print("Project not found")
            return {"message": "Project not found"}

        sqs = boto3.client("sqs")
        message = {
            "project": project
        }

        update_project(str(cursor["_id"]), {"generation_status": "in-progress"})

        sqs.send_message(
            QueueUrl=os.getenv("SQS_URL"),
            MessageBody=json.dumps(message)
        )

        return {"message": "Request In progress"}
    except:
        return {"message": "Request could not be processed"}


@router.get("/status/{project}")
async def status(project):
    cursor = project_collection.find_one({"_id": ObjectId(project)})
    if not cursor:
        print("Project not found")
        return {"message": "Project not found"}

    if not "generation_status" in cursor:
        return {"message": "Generation not started"}

    if "tool_generation" in cursor and "status" in cursor["tool_generation"]:
        tools = cursor["tool_generation"]["status"]
    else:
        tools = "Not started"

    if "step_generation" in cursor and "status" in cursor["step_generation"]:
        steps = cursor["step_generation"]["status"]
    else:
        steps = "Not started"

    if "estimation_generation" in cursor and "status" in cursor["estimation_generation"]:
        estimation = cursor["estimation_generation"]["status"]
    else:
        estimation = "Not started"

    if cursor["generation_status"] == "complete":
        return {"message": "generation completed",
                "tools": tools,
                "steps": steps,
                "estimation": estimation}

    if cursor["generation_status"] == "in-progress":
        return {"message": "generation in progress",
                "tools": tools,
                "steps": steps,
                "estimation": estimation}

    return {"message": "Something went wrong"}


@router.post("/steps/{project}")
async def generate_steps(project):
    """
    Generate step-by-step plan for a DIY project.
    This endpoint runs independently to avoid timeout issues.
    """
    try:
        # Validate project exists
        cursor = project_collection.find_one({"_id": ObjectId(project)})
        if not cursor:
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate steps using the independent agent
        steps_agent = StepsAgentJSON()
        steps_result = steps_agent.generate(
            tools=cursor["tool_generation"],
            summary=cursor["summary"],
            user_answers=cursor.get("user_answers") or cursor.get("answers"),
            questions=cursor["questions"]
        )

        print("Steps Generated")

        step_meta = {k: v for k, v in steps_result.items() if k != "steps"}
        step_meta["status"] = "complete"
        update_project(str(cursor["_id"]), {"step_generation": step_meta})
        # update_project(str(cursor["_id"]), {"step_generation":steps_result})

        for step in steps_result["steps"]:
            step_doc = {
                "projectId": ObjectId(project),

                "stepNumber": step["order"],

                "order": step["order"],
                "title": step["title"],
                "est_time_min": step.get("est_time_min", 0),
                "time_text": step.get("time_text", ""),
                "instructions": step.get("instructions", []),

                "status": (step.get("status") or "pending").lower(),
                "progress": 0,
                "tools_needed": step.get("tools_needed", []),
                "safety_warnings": step.get("safety_warnings", []),
                "tips": step.get("tips", []),

                "completed": False,
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
            }
            steps_collection.insert_one(step_doc)

        return {
            "success": True,
            "project_id": project,
            "steps_data": steps_result,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate steps: {str(e)}")


@router.post("/estimation/{project}")
async def generate_estimation(project):
    """
    Generate cost and time estimations for a DIY project.
    This endpoint runs independently to avoid timeout issues.
    """
    try:
        # Validate project exists
        cursor = project_collection.find_one({"_id": ObjectId(project)})
        if not cursor:
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate estimation using the independent agent
        estimation_agent = EstimationAgent()

        meta = cursor.get("step_generation") or {}

        cur = steps_collection.find({"projectId": ObjectId(project)}).sort("order", 1)
        steps_for_est = [{
            "order": s.get("order"),
            "title": s.get("title", ""),
            "estimated_time_min": s.get("est_time_min", 0),
            "time_text": s.get("time_text", "")
        } for s in cur]

        steps_data_for_est = {
            "steps": steps_for_est,
            "total_est_time_min": meta.get("total_est_time_min", 0),
            "total_steps": meta.get("total_steps", len(steps_for_est)),
        }

        estimation_result = estimation_agent.generate_estimation(
            tools_data=cursor["tool_generation"],
            steps_data=steps_data_for_est
        )
        # estimation_result = estimation_agent.generate_estimation(
        #     tools_data=cursor["tool_generation"],
        #     steps_data=cursor["step_generation"]
        # )

        update_project(str(cursor["_id"]), {"estimation_generation": estimation_result})

        return {
            "success": True,
            "project_id": project,
            "estimation_data": estimation_result,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate estimation: {str(e)}")

# Legacy endpoints for backward compatibility (can be removed later)
# @router.post("/tools/legacy")
# async def get_tools_legacy(projectId: str):
#     """Legacy endpoint - kept for backward compatibility"""
#     cursor = project_collection.find_one({"_id": ObjectId(projectId)})
#     if not cursor:
#         raise HTTPException(status_code=404, detail="Project not found")

#     user = cursor['userId']
#     tools = ToolsAgent()
#     return tools.("I want to hang a mirror")

# @router.post("/steps/legacy")
# async def get_steps_legacy(projectId: str):
#     """Legacy endpoint - kept for backward compatibility"""
#     cursor = project_collection.find_one({"_id": ObjectId(projectId)})
#     if not cursor:
#         raise HTTPException(status_code=404, detail="Project not found")

#     user = cursor['userId']
#     steps = StepsAgentJSON()
#     return steps.generate("There is a hole in my living room I want to repair it")
