from chatbot.planner import ToolsAgentJSON,StepsAgentJSON
from chatbot.agents import load_prompt, clean_and_parse_json, AgenticChatbot
from fastapi import APIRouter, HTTPException, UploadFile, File
from .chatbot import get_session, get_latest_chatbot
from pydantic import BaseModel
from bson import ObjectId

from typing import List, Dict, Any, Optional
import sys
import os
import base64
import uuid
from pymongo import DESCENDING
from db import project_collection
from datetime import datetime

router = APIRouter(prefix="/generation", tags=["generation"])

@router.post("/tools")
def get_tools(projectId:str):
    cursor = project_collection.find_one({"_id": ObjectId(projectId)})
    user=cursor['user']
    tools= ToolsAgentJSON()
    return tools.generate("I want to hang a mirror")