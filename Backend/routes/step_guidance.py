from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import sys
import uuid
import json
import pickle
import re
import base64
from datetime import datetime
from bson import ObjectId
from pymongo import DESCENDING
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))
from chatbot.step_guidance_chatbot import StepGuidanceChatbot

from db import conversations_step_collection, project_collection, conversations_collection  # noqa: F401

router = APIRouter(prefix="/step-guidance", tags=["step-guidance"])

# -------------------- Models --------------------

class StartTaskRequest(BaseModel):
    project: str

class ChatMessage(BaseModel):
    message: str
    project: str
    step: int
    uploaded_image: Optional[str] = None  # base64 image for step guidance and troubleshooting

class ChatResponse(BaseModel):
    response: str
    session_id: str
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    suggested_messages: Optional[List[str]] = None

# class TaskStatus(BaseModel):
#     session_id: str
#     task_name: str
#     current_step: int
#     total_steps: int
#     progress_percentage: float
#     current_step_data: Optional[Dict[str, Any]] = None
#     tools_needed: List[str]
#     materials_needed: List[str]
#     completion_status: Dict[str, Any]

# class StepCompletionRequest(BaseModel):
#     user: Optional[str] = None
#     project: Optional[str] = None
#     completion_notes: Optional[str] = ""

# class ToolGuidanceRequest(BaseModel):
#     tool_name: str
#     user_message: Optional[str] = ""

# class SafetyCheckRequest(BaseModel):
#     user_message: Optional[str] = ""

# class StepInstructionRequest(BaseModel):
#     user_message: Optional[str] = ""

# -------------------- In-proc cache --------------------
# step_guidance_instances: Dict[str, StepGuidanceChatbot] = {}

# -------------------- Helpers --------------------

CHAT_TYPE = "step_guidance"

# def _normalize_steps_data(steps: Any) -> Optional[Dict[int, Dict[str, Any]]]:
#     if steps is None:
#         return None
#     if isinstance(steps, dict):
#         fixed = {}
#         for k, v in steps.items():
#             try:
#                 fixed[int(k)] = v
#             except Exception:
#                 continue
#         return fixed
#     if isinstance(steps, list):
#         return {i + 1: step for i, step in enumerate(steps)}
#     return None

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

def _log(session_id: str, role: str, message: str, bot: StepGuidanceChatbot,
         user: str, project: str, msg_type: str = CHAT_TYPE):
    doc = {
        "session_id": session_id,
        "user": user,
        "project": project,
        "role": role,
        "message": message,
        "chat_type": msg_type,
        "timestamp": datetime.utcnow(),
        "chatbot_state": pickle.dumps(bot),
    }
    conversations_step_collection.insert_one(doc)

def get_latest_chatbot(session_id):
    doc = conversations_step_collection.find_one(
        {"session_id": session_id},
        sort=[("timestamp", DESCENDING)]
    )
    if doc and "chatbot_state" in doc:
        return pickle.loads(doc["chatbot_state"])
    else:
        return StepGuidanceChatbot()
    
def get_conversation_history(session_id):
    cursor = conversations_step_collection.find({"session_id": session_id}).sort("timestamp", 1)
    return [{"role": doc["role"], "message": doc["message"], "timestamp": doc["timestamp"]} for doc in cursor]

def get_step_guidance_suggested_messages(current_step: int, total_steps: int, step_data: Dict = None) -> List[str]:
    """
    Generate suggested messages for step guidance based on current step and context.
    """
    if current_step == -1:
        # Starting step guidance
        return [
            "Let's start with step 1",
            "Show me the tools I need",
            "What safety precautions should I take?",
            "I'm ready to begin"
        ]
    elif current_step == 0:
        # At the beginning
        return [
            "I'm ready for the first step",
            "What tools do I need first?",
            "Any safety warnings?",
            "Let's get started"
        ]
    elif 1 <= current_step <= total_steps:
        # During step execution
        if step_data and step_data.get("completed"):
            return [
                "Next step please",
                "I've completed this step",
                "Continue to next step",
                "What's the next step?"
            ]
        else:
            return [
                "I need help with this step",
                "I'm stuck on this part",
                "Can you clarify this instruction?",
                "Mark this step as complete"
            ]
    elif current_step > total_steps:
        # Project completed
        return [
            "Great! Project completed",
            "Any final tips?",
            "What should I check?",
            "Thank you for the guidance"
        ]
    else:
        # Default fallback
        return [
            "I need help",
            "Next step",
            "Clarify please",
            "I'm confused"
        ]

def _fetch_project_data(project_id: str) -> Dict[str, Any]:
    """Fetch project and its steps/tools from DB; map to chatbot schema."""
    try:
        pid = ObjectId(project_id)
        project = project_collection.find_one({"_id": pid})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 1) Load steps from ProjectSteps, sorted by stepNumber
        steps_cursor = project["step_generation"]["steps"]
        steps_data: Dict[int, Dict[str, Any]] = {}
        for doc in steps_cursor:
            i = int(doc.get("order", 0)) or (len(steps_data) + 1)
            steps_data[i] = {
                "title": doc.get("title", f"Step {i}"),
                # DB has "description" -> chatbot expects "instructions"
                "instructions": doc.get("instructions", []),
                "time_text": doc.get("time_text", ""),  # if you store it; else keep ""
                "tools_needed": doc.get("tools_needed", []),
                "safety_warnings": doc.get("safety_warnings", []),
                "tips": doc.get("tips", []),
                # Optional extras the UI might want:
                "images": doc.get("images", []),
                "video": doc.get("videoTutorialLink", ""),
                "reference_links": doc.get("referenceLinks", []),
                "completed": bool(doc.get("completed", False)),
            }
            
        print ("steps_data: ", steps_data)

        total_steps = len(steps_data)

        # 2) Tools: if you keep a tools dictionary on Project, pass it through
        tools_data = project.get("tools", {}) or project.get("tool_generation", {}) or {}

        # 3) Map project fields to chatbot expectations
        problem_summary = project.get("summary") or project.get("user_description") or ""
            
        print("total_steps ", total_steps)
        print("steps_data ", steps_data)
        print("tools_data ", tools_data)
        print("problem_summary ", problem_summary)
        

        return {
            "total_steps": total_steps,
            "steps_data": steps_data,
            "tools_data": tools_data,
            "problem_summary": problem_summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project data: {str(e)}")

# -------------------- Endpoints --------------------

@router.get("/started/{project}")
def is_started(project):
    cursor = conversations_step_collection.find_one({"project":project, "chat_type":CHAT_TYPE})
    if cursor:
        return True
    return False

@router.get("/session/{project}")
def get_session(project):
    cursor = conversations_step_collection.find_one({"project":project})
    if not cursor:
        return {"session": None}
    return {"session": cursor["session_id"]}

def get_prev_session(project):
    cursor = conversations_collection.find_one({"project":project})
    if not cursor:
        return {"session": None}
    return {"session": cursor["session_id"]}

@router.post("/start", response_model=ChatResponse)
def start_step_guidance_task(payload: StartTaskRequest):
    session_id = get_prev_session(payload.project)['session']
    bot = StepGuidanceChatbot()

    # Fetch project data from database
    project_data = _fetch_project_data(payload.project)
    
    # Normalize steps data if it exists
    steps_data = project_data.get("steps_data",{})
    tools_data = project_data.get("tools_data", {})
    total_steps = project_data.get("total_steps", 1)

    welcome = bot.start_new_task(
        total_steps=total_steps,
        steps_data=steps_data,
        tools_data=tools_data,
        problem_summary=project_data.get("problem_summary", "")
    )
    
    project = project_collection.find_one({"_id": ObjectId(payload.project)})

    _log(session_id, "assistant", welcome, bot, project["userId"], payload.project)

    # Get suggested messages for starting step guidance
    suggested_messages = get_step_guidance_suggested_messages(-1, total_steps)

    return ChatResponse(
        response=welcome,
        session_id=session_id,
        current_step=-1,
        total_steps=total_steps,
        suggested_messages=suggested_messages
    )

@router.post("/chat", response_model=ChatResponse)
def chat_with_step_guidance(payload: ChatMessage):
    session_id = get_session(payload.project)['session']
    bot = get_latest_chatbot(session_id)
    
    print (payload)
    
    project = project_collection.find_one({"_id": ObjectId(payload.project)})

    _log(session_id, "user", payload.message, bot, project["userId"], payload.project)
    
    # Process uploaded image if provided
    uploaded_image = None
    if payload.uploaded_image:
        image_data = payload.uploaded_image
        if image_data.startswith('data:image'):
            # Extract base64 part if it includes data URL prefix
            image_data = image_data.split(',')[1]
        uploaded_image = base64.b64decode(image_data)
    
    # Call chat method with image support
    reply = bot.chat(payload.message, payload.step, uploaded_image)
    _log(session_id, "assistant", reply, bot, project["userId"], payload.project)

    # Get current step info and generate suggested messages
    current_step = getattr(bot, "current_step", None)
    total_steps = getattr(bot, "total_steps", None)
    
    # Get step data if available
    step_data = None
    if hasattr(bot, "steps_data") and current_step and current_step in bot.steps_data:
        step_data = bot.steps_data[current_step]
    
    suggested_messages = get_step_guidance_suggested_messages(
        current_step or -1, 
        total_steps or 1, 
        step_data
    )

    return ChatResponse(
        response=reply,
        session_id=session_id,
        current_step=current_step,
        total_steps=total_steps,
        suggested_messages=suggested_messages
    )

@router.get("/session/{session_id}/history")
def get_step_guidance_history(session_id: str):
    cursor1 = conversations_collection.find(
        {"session_id": session_id}
    ).sort("timestamp", 1)
    history1 = [
        {"role": doc["role"], "message": doc["message"], "timestamp": doc["timestamp"]}
        for doc in cursor1
    ]

    cursor2 = conversations_step_collection.find(
        {"session_id": session_id}
    ).sort("timestamp", 1)
    history2 = [
        {"role": doc["role"], "message": doc["message"], "timestamp": doc["timestamp"]}
        for doc in cursor2
    ]

    # Merge both lists
    history = history1 + history2

    # Sort merged list by timestamp
    history = sorted(history, key=lambda x: x["timestamp"])
    return history

@router.post("/session/{session_id}/reset")
def reset_step_guidance_session(session_id: str, project: str, user: str):
    bot = StepGuidanceChatbot()
    _log(session_id, "assistant", "Session reset.", bot, user, project, msg_type=CHAT_TYPE)
    return {"message": "Step guidance session reset successfully"}

@router.delete("/session/{session_id}")
def delete_step_guidance_session(session_id: str):
    conversations_step_collection.delete_many({"session_id": session_id, "chat_type": CHAT_TYPE})
    return {"message": f"Step guidance session {session_id} deleted successfully"}

@router.get("/health")
def health_check():
    return {"status": "healthy", "message": "Step Guidance API is running"}