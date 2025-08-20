from content_generation.planner import ToolsAgent, StepsAgentJSON, EstimationAgent
from chatbot.agents import load_prompt, clean_and_parse_json, AgenticChatbot
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from bson import ObjectId
from .project import update_project
from typing import List, Dict, Any, Optional
import json
import os
import base64
import uuid
import boto3
from pymongo import DESCENDING
from db import project_collection, steps_collection
from datetime import datetime

router = APIRouter(prefix="/generation", tags=["generation"])

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
    steps = list(steps_collection.find({"projectId": ObjectId(project_id)}))
    if not steps:
        raise HTTPException(status_code=404, detail="Steps not generated yet")
    for step in steps:
        step["_id"] = str(step["_id"])
        step["projectId"] = str(step["projectId"])
    return {"project_id": project_id, "steps_data": steps}

@router.get("/estimation/{project_id}")
async def get_generated_estimation(project_id: str):
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"estimation_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if "estimation_generation" not in doc or doc["estimation_generation"] is None:
        raise HTTPException(status_code=404, detail="Estimation not generated yet")
    return {"project_id": project_id, "estimation_data": doc["estimation_generation"]}

@router.post("/tools/{project}")
async def generate_tools(project:str):
    """
    Generate tools and materials for a DIY project.
    This endpoint runs independently to avoid timeout issues.
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
            raise HTTPException(status_code=400, detail="Missing required fields (summary, answers, questions) on project")

        update_project(str(cursor["_id"]), {"tool_generation":tools_result})
        
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
                "project":project
            }
        
        update_project(str(cursor["_id"]), {"generation_status":"in-progress"})
        
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
        tools= cursor["tool_generation"]["status"]
    else:
        tools= "Not started"
        
    if "step_generation" in cursor and "status" in cursor["step_generation"]:
        steps= cursor["step_generation"]["status"]
    else:
        steps= "Not started"
        
    if "estimation_generation" in cursor and "status" in cursor["estimation_generation"]:
        estimation= cursor["estimation_generation"]["status"]
    else:
        estimation= "Not started"
    
    if cursor["generation_status"]=="complete":
        return {"message": "generation completed",
                "tools":tools,
                "steps": steps,
                "estimation":estimation}
    
    if cursor["generation_status"]=="in-progress":
        return {"message": "generation in progress",
                "tools":tools,
                "steps": steps,
                "estimation":estimation}
        
    return {"message":"Something went wrong"}

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
            tools= cursor["tool_generation"],
            summary=cursor["summary"],
            user_answers=cursor.get("user_answers") or cursor.get("answers"),
            questions=cursor["questions"]
        )

        print("Steps Generated")

        update_project(str(cursor["_id"]), {"step_generation":steps_result})
        
        for idx, step in enumerate(steps_result["steps"], start=1):
            step_doc = {
                "projectId": ObjectId(project),
                "stepNumber": step["order"],
                "title": step["title"],
                "description": " ".join(step.get("instructions", [])),
                "tools": [], #update
                "materials": [],
                "images": [],
                "videoTutorialLink": None,
                "referenceLinks": [],
                "completed": False,
                "createdAt": datetime.utcnow()
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
        estimation_result = estimation_agent.generate_estimation(
            tools_data=cursor["tool_generation"],
            steps_data=cursor["step_generation"]
        )

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