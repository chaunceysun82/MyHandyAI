from content_generation.planner import ToolsAgentJSON, StepsAgentJSON, EstimationAgent
from chatbot.agents import load_prompt, clean_and_parse_json, AgenticChatbot
from fastapi import APIRouter, HTTPException, UploadFile, File
from .chatbot import get_session, get_latest_chatbot
from pydantic import BaseModel
from bson import ObjectId
from .project import update_project
from typing import List, Dict, Any, Optional
import sys
import os
import base64
import uuid
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
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"step_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if "step_generation" not in doc or doc["step_generation"] is None:
        raise HTTPException(status_code=404, detail="Steps not generated yet")
    return {"project_id": project_id, "steps_data": doc["step_generation"]}

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
        tools_agent = ToolsAgentJSON()
        tools_result = tools_agent.generate(
            summary=cursor["summary"],
            user_answers=cursor.get("user_answers") or cursor.get("answers"),
            questions=cursor["questions"]
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
@router.post("/tools/legacy")
async def get_tools_legacy(projectId: str):
    """Legacy endpoint - kept for backward compatibility"""
    cursor = project_collection.find_one({"_id": ObjectId(projectId)})
    if not cursor:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user = cursor['userId']
    tools = ToolsAgentJSON()
    return tools.generate("I want to hang a mirror")

@router.post("/steps/legacy")
async def get_steps_legacy(projectId: str):
    """Legacy endpoint - kept for backward compatibility"""
    cursor = project_collection.find_one({"_id": ObjectId(projectId)})
    if not cursor:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user = cursor['userId']
    steps = StepsAgentJSON()
    return steps.generate("There is a hole in my living room I want to repair it")