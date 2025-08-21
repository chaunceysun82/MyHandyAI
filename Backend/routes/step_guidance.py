from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import sys
import uuid
import pickle
from datetime import datetime
from bson import ObjectId
from pymongo import DESCENDING
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))
from chatbot.step_guidance_chatbot import StepGuidanceChatbot

from db import conversations_collection, project_collection, steps_collection  # noqa: F401

router = APIRouter(prefix="/step-guidance", tags=["step-guidance"])

# -------------------- Models --------------------

class StartTaskRequest(BaseModel):
    user: str
    project: str

class ChatMessage(BaseModel):
    message: str
    user: str
    project: str
    session_id: Optional[str] = None
    uploaded_image: Optional[str] = None  # placeholder; not used by this bot

class ChatResponse(BaseModel):
    response: str
    session_id: str
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    task_name: Optional[str] = None

class TaskStatus(BaseModel):
    session_id: str
    task_name: str
    current_step: int
    total_steps: int
    progress_percentage: float
    current_step_data: Optional[Dict[str, Any]] = None
    tools_needed: List[str]
    materials_needed: List[str]
    completion_status: Dict[str, Any]

class StepCompletionRequest(BaseModel):
    user: Optional[str] = None
    project: Optional[str] = None
    completion_notes: Optional[str] = ""

class ToolGuidanceRequest(BaseModel):
    tool_name: str
    user_message: Optional[str] = ""

class SafetyCheckRequest(BaseModel):
    user_message: Optional[str] = ""

class StepInstructionRequest(BaseModel):
    user_message: Optional[str] = ""

# -------------------- In-proc cache --------------------
step_guidance_instances: Dict[str, StepGuidanceChatbot] = {}

# -------------------- Helpers --------------------

CHAT_TYPE = "step_guidance"

def _normalize_steps_data(steps: Any) -> Optional[Dict[int, Dict[str, Any]]]:
    if steps is None:
        return None
    if isinstance(steps, dict):
        fixed = {}
        for k, v in steps.items():
            try:
                fixed[int(k)] = v
            except Exception:
                continue
        return fixed
    if isinstance(steps, list):
        return {i + 1: step for i, step in enumerate(steps)}
    return None

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
        "current_step": getattr(bot.execution_agent.context_agent, "current_step", None),
        "task_name": getattr(bot.execution_agent.context_agent, "task_name", None),
    }
    conversations_collection.insert_one(doc)

def _get_last_doc(session_id: str):
    return conversations_collection.find_one(
        {"session_id": session_id, "chat_type": CHAT_TYPE},
        sort=[("timestamp", DESCENDING)]
    )

def _restore_bot(session_id: str) -> Optional[StepGuidanceChatbot]:
    doc = _get_last_doc(session_id)
    if doc and "chatbot_state" in doc:
        return pickle.loads(doc["chatbot_state"])
    return None

def _get_user_project(session_id: str, fallback_user="unknown", fallback_project="unknown"):
    doc = _get_last_doc(session_id)
    return (doc.get("user", fallback_user) if doc else fallback_user,
            doc.get("project", fallback_project) if doc else fallback_project)

def _update_step_completion_in_db(project_id: str, step_number: int, completed: bool = True):
    """Update step completion status in the database"""
    try:
        if isinstance(project_id, str):
            project_id = ObjectId(project_id)
        
        # Update the step completion status
        result = steps_collection.update_one(
            {"projectId": project_id, "stepNumber": step_number},
            {"$set": {"completed": completed}}
        )
        
        if result.matched_count == 0:
            print(f"Warning: No step found with projectId {project_id} and stepNumber {step_number}")
        
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating step completion: {e}")
        return False

def _fetch_project_data(project_id: str) -> Dict[str, Any]:
    """Fetch project and its steps/tools from DB; map to chatbot schema."""
    try:
        pid = ObjectId(project_id) if isinstance(project_id, str) else project_id
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
        task_name = project.get("projectTitle") or project.get("title") or "Untitled Task"
        problem_summary = project.get("summary") or project.get("user_description") or ""

        # Fallback: if no steps were found, create a single placeholder step
        if total_steps == 0:
            steps_data = {
                1: {
                    "title": "Describe your task",
                    "instructions": [],
                    "estimated_time": "",
                    "tools_needed": [],
                    "materials_needed": [],
                    "safety_warnings": [],
                    "tips": [],
                }
            }
            total_steps = 1
            
        print("task_name ", task_name)
        print("total_steps ", total_steps)
        print("steps_data ", steps_data)
        print("tools_data ", tools_data)
        print("problem_summary ", problem_summary)
        

        return {
            "task_name": task_name,
            "total_steps": total_steps,
            "steps_data": steps_data,
            "tools_data": tools_data,
            "problem_summary": problem_summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project data: {str(e)}")

def _get_or_restore(session_id: str) -> StepGuidanceChatbot:
    bot = step_guidance_instances.get(session_id)
    if bot:
        return bot
    bot = _restore_bot(session_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Step guidance session not found")
    step_guidance_instances[session_id] = bot
    return bot

# -------------------- Endpoints --------------------

@router.post("/start", response_model=ChatResponse)
def start_step_guidance_task(payload: StartTaskRequest):
    session_id = uuid.uuid4().hex
    bot = StepGuidanceChatbot()

    # Fetch project data from database
    project_data = _fetch_project_data(payload.project)
    
    # Normalize steps data if it exists
    steps_data = _normalize_steps_data(project_data.get("steps_data"))
    tools_data = project_data.get("tools_data", {})
    total_steps = project_data.get("total_steps", 1)

    welcome = bot.start_new_task(
        task_name=project_data["task_name"],
        total_steps=total_steps,
        steps_data=steps_data,
        tools_data=tools_data,
        problem_summary=project_data.get("problem_summary", "")
    )

    _log(session_id, "assistant", welcome, bot, payload.user, payload.project)
    step_guidance_instances[session_id] = bot

    ctx = bot.execution_agent.context_agent.get_current_context()
    return ChatResponse(
        response=welcome,
        session_id=session_id,
        current_step=ctx.get("current_step"),
        total_steps=ctx.get("total_steps"),
        task_name=ctx.get("task_name"),
    )

@router.post("/chat", response_model=ChatResponse)
def chat_with_step_guidance(payload: ChatMessage):
    session_id = payload.session_id or uuid.uuid4().hex
    bot = step_guidance_instances.get(session_id) or _restore_bot(session_id)
    print("chat_data: ", bot.get_current_status())

    # If chat is called before start, bootstrap a minimal task so it doesn't 404.
    if not bot:
        bot = StepGuidanceChatbot()
        bot.start_new_task("Untitled Task", total_steps=1,
                           steps_data={1: {"title": "Step 1", "instructions": "Describe your task to begin."}},
                           tools_data={}, problem_summary="")
        _log(session_id, "assistant", "Session auto-bootstrap.", bot, payload.user, payload.project)

    step_guidance_instances[session_id] = bot

    _log(session_id, "user", payload.message, bot, payload.user, payload.project)
    reply = bot.chat(payload.message)
    _log(session_id, "assistant", reply, bot, payload.user, payload.project)

    ctx = bot.execution_agent.context_agent.get_current_context()
    return ChatResponse(
        response=reply,
        session_id=session_id,
        current_step=ctx.get("current_step"),
        total_steps=ctx.get("total_steps"),
        task_name=ctx.get("task_name"),
    )

@router.get("/session/{session_id}/status", response_model=TaskStatus)
def get_task_status(session_id: str):
    bot = _get_or_restore(session_id)
    ctx = bot.execution_agent.context_agent.get_current_context()

    completed = len([s for s in ctx.get("completion_status", {}).values() if s.get("completed")])
    total = max(1, ctx.get("total_steps", 1))
    pct = (completed / total) * 100

    current_step_data = bot.get_current_step_data()

    return TaskStatus(
        session_id=session_id,
        task_name=ctx.get("task_name", ""),
        current_step=ctx.get("current_step", 1),
        total_steps=ctx.get("total_steps", 1),
        progress_percentage=pct,
        current_step_data=current_step_data,
        tools_needed=ctx.get("current_tools", []),
        materials_needed=ctx.get("current_materials", []),
        completion_status=ctx.get("completion_status", {}),
    )

@router.post("/session/{session_id}/complete-step")
def complete_current_step(session_id: str, payload: StepCompletionRequest):
    bot = _get_or_restore(session_id)
    user, project = _get_user_project(session_id, payload.user or "unknown", payload.project or "unknown")

    # Get current context
    ctx = bot.execution_agent.context_agent.get_current_context()
    current_step = ctx.get("current_step", 1)
    total_steps = ctx.get("total_steps", 1)
    
    # Mark current step as complete
    bot.execution_agent.context_agent.mark_step_complete(current_step, payload.completion_notes or "")
    
    # Update step completion in database
    _update_step_completion_in_db(project, current_step, True)
    
    # Check if we can move to next step
    if current_step < total_steps:
        next_step = current_step + 1
        bot.execution_agent.context_agent.move_to_step(next_step)
        
        # Get next step data
        next_step_data = bot.execution_agent.context_agent.get_step_instructions(next_step)
        
        # Log the step completion
        _log(session_id, "assistant", f"Step {current_step} completed. Moving to step {next_step}.", bot, user, project)
        
        return {
            "message": f"Step {current_step} completed successfully!",
            "next_step": next_step,
            "next_step_data": next_step_data,
            "progress": f"{current_step}/{total_steps} steps completed",
            "task_completed": False
        }
    else:
        # Task completed
        _log(session_id, "assistant", "All steps completed! Task finished successfully.", bot, user, project)
        
        return {
            "message": "Congratulations! All steps completed successfully!",
            "task_completed": True,
            "progress": f"{current_step}/{total_steps} steps completed"
        }

@router.post("/session/{session_id}/tool-guidance")
def get_tool_guidance(session_id: str, payload: ToolGuidanceRequest):
    bot = _get_or_restore(session_id)
    user, project = _get_user_project(session_id)

    ctx = bot.execution_agent.context_agent.get_current_context()
    current_step = ctx.get("current_step", 1)

    guidance = bot.execution_agent.tool_agent.get_tool_guidance(
        payload.tool_name, current_step, payload.user_message or "", ctx
    )

    _log(session_id, "user", f"Tool guidance request for: {payload.tool_name}", bot, user, project)
    _log(session_id, "assistant", guidance, bot, user, project)

    return {"tool_name": payload.tool_name, "guidance": guidance, "current_step": current_step}

@router.post("/session/{session_id}/safety-check")
def check_step_safety(session_id: str, payload: SafetyCheckRequest):
    bot = _get_or_restore(session_id)
    user, project = _get_user_project(session_id)

    ctx = bot.execution_agent.context_agent.get_current_context()
    safety_info = bot.execution_agent.safety_agent.validate_step_safety(ctx, payload.user_message or "")

    _log(session_id, "user", f"Safety check request: {payload.user_message or 'General safety check'}", bot, user, project)
    _log(session_id, "assistant", f"Safety assessment: {safety_info.get('safety_level','unknown')}", bot, user, project)

    return {"safety_info": safety_info, "current_step": ctx.get("current_step", 1), "task_name": ctx.get("task_name", "")}

@router.post("/session/{session_id}/step-instructions")
def get_step_instructions(session_id: str, payload: StepInstructionRequest):
    bot = _get_or_restore(session_id)
    user, project = _get_user_project(session_id)

    ctx = bot.execution_agent.context_agent.get_current_context()
    current_step_data = ctx.get("current_step_data")
    if not current_step_data:
        raise HTTPException(status_code=400, detail="No step data available for current step")

    text = bot.execution_agent.step_instruction_agent.get_step_guidance(
        current_step_data, payload.user_message or "", ctx
    )

    _log(session_id, "user", f"Step instruction request: {payload.user_message or 'Get step instructions'}", bot, user, project)
    _log(session_id, "assistant", text, bot, user, project)

    return {
        "step_number": ctx.get("current_step", 1),
        "step_title": current_step_data.get("title", ""),
        "instructions": text,
        "tools_needed": current_step_data.get("tools_needed", []),
        "materials_needed": current_step_data.get("materials_needed", []),
        "estimated_time": current_step_data.get("estimated_time", current_step_data.get("time")),
    }

@router.get("/session/{session_id}/history")
def get_step_guidance_history(session_id: str):
    cursor = conversations_collection.find(
        {"session_id": session_id, "chat_type": CHAT_TYPE}
    ).sort("timestamp", 1)
    history = [
        {"role": doc["role"], "message": doc["message"], "timestamp": doc["timestamp"]}
        for doc in cursor
    ]
    return {"session_id": session_id, "history": history}

@router.post("/session/{session_id}/reset")
def reset_step_guidance_session(session_id: str):
    user, project = _get_user_project(session_id)
    bot = StepGuidanceChatbot()
    _log(session_id, "assistant", "Session reset.", bot, user, project, msg_type=CHAT_TYPE)
    step_guidance_instances[session_id] = bot
    return {"message": "Step guidance session reset successfully"}

@router.delete("/session/{session_id}")
def delete_step_guidance_session(session_id: str):
    conversations_collection.delete_many({"session_id": session_id, "chat_type": CHAT_TYPE})
    if session_id in step_guidance_instances:
        del step_guidance_instances[session_id]
    return {"message": f"Step guidance session {session_id} deleted successfully"}

@router.get("/health")
def health_check():
    return {"status": "healthy", "message": "Step Guidance API is running", "active_sessions": len(step_guidance_instances)}

@router.get("/debug/sessions")
def debug_sessions():
    return {"active_sessions": len(step_guidance_instances), "session_ids": list(step_guidance_instances.keys())}

@router.get("/project/{project_id}/steps")
def get_project_steps(project_id: str):
    """Get all steps for a specific project directly from the database"""
    try:
        if isinstance(project_id, str):
            project_id = ObjectId(project_id)
        
        # Fetch project info
        project = project_collection.find_one({"_id": project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Fetch all steps
        steps_cursor = steps_collection.find({"projectId": project_id}).sort("stepNumber", 1)
        steps = []
        
        for step_doc in steps_cursor:
            steps.append({
                "step_number": step_doc.get("stepNumber"),
                "title": step_doc.get("title"),
                "description": step_doc.get("description"),
                "tools": step_doc.get("tools", []),
                "materials": step_doc.get("materials", []),
                "video_tutorial": step_doc.get("videoTutorialLink"),
                "reference_links": step_doc.get("referenceLinks", []),
                "images": step_doc.get("images", []),
                "completed": step_doc.get("completed", False)
            })
        
        return {
            "project_id": str(project_id),
            "project_title": project.get("projectTitle", "Untitled"),
            "total_steps": len(steps),
            "steps": steps
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project steps: {str(e)}")
