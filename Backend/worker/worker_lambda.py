import os
import json
import traceback
from datetime import datetime
from bson.objectid import ObjectId
from db import project_collection, steps_collection
from datetime import datetime
from planner import ToolsAgent, StepsAgentJSON, EstimationAgent

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
