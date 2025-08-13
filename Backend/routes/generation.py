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
from db import project_collection
from datetime import datetime

router = APIRouter(prefix="/generation", tags=["generation"])

# Pydantic models for request/response

@router.post("/tools")
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
            user_answers=cursor["user_answers"],
            questions=cursor["questions"]
        )

        update_project(str(cursor["_id"]), {"tool_generation":tools_result})
        
        return {
            "success": True,
            "project_id": project,
            "tools_data": tools_result,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tools: {str(e)}")

@router.post("/steps")
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
            user_answers=cursor["user_answers"],
            questions=cursor["questions"]
        )

        update_project(str(cursor["_id"]), {"step_generation":steps_result})
        
        return {
            "success": True,
            "project_id": project,
            "steps_data": steps_result,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate steps: {str(e)}")

@router.post("/estimation")
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