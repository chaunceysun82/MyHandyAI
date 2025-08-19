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

from db import conversations_collection, project_collection

# ---------- Router ----------
router = APIRouter(prefix="/step-guidance", tags=["step-guidance"])

# ---------- Models ----------

class StartTaskPayload(BaseModel):
    user: str
    project: str
    task_name: str = Field(..., example="Locate Studs")
    total_steps: int = Field(..., ge=1, le=50, example=4)

    # Optional: real planner/agents data. If omitted, your frontend/planner should provide later.
    steps_data: Optional[Dict[int, Dict[str, Any]]] = None
    tools_data: Optional[Dict[str, Dict[str, Any]]] = None
    problem_summary: Optional[str] = None

class ChatPayload(BaseModel):
    message: str
    user: str
    project: str
    session_id: Optional[str] = None  # if None, a new session is created

class MoveToStepPayload(BaseModel):
    user: str
    project: str
    session_id: str
    step_number: int

class MarkCompletePayload(BaseModel):
    user: str
    project: str
    session_id: str
    notes: Optional[str] = None

class ResetPayload(BaseModel):
    user: str
    project: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    task_name: Optional[str] = None
    current_state: Optional[str] = None  # not used by StepGuidanceChatbot but kept for parity

class SessionInfo(BaseModel):
    session_id: str
    task_name: Optional[str]
    current_step: int
    total_steps: int
    tools_for_step: List[str] = []
    completed_steps: List[int] = []
    problem_summary: Optional[str] = None

# ---------- Helpers ----------

def _log_message(session_id: str, role: str, message: str, bot: StepGuidanceChatbot, user: str, project: str, msg_type="runtime"):
    # Persist the WHOLE chatbot execution agent (pickle) so we can restore exact state like your other bot
    doc = {
        "session_id": session_id,
        "user": user,
        "project": project,
        "role": role,
        "message": message,
        "chat_type": msg_type,
        "timestamp": datetime.utcnow(),
        "chatbot_state": pickle.dumps(bot),
        "current_state": "step_guidance"  # label for filtering; SG bot doesn’t have a finite-state machine like the other bot
    }
    conversations_collection.insert_one(doc)

def _get_latest_bot(session_id: str) -> StepGuidanceChatbot:
    doc = conversations_collection.find_one({"session_id": session_id}, sort=[("timestamp", DESCENDING)])
    if doc and "chatbot_state" in doc:
        return pickle.loads(doc["chatbot_state"])
    return StepGuidanceChatbot()

def _get_context(snapshot_bot: StepGuidanceChatbot) -> Dict[str, Any]:
    ctx = snapshot_bot.execution_agent.context_agent.get_current_context()
    return ctx or {}

def _normalize_steps_data(steps: Any) -> Optional[Dict[int, Dict[str, Any]]]:
    """
    Accepts either:
      - dict keyed by ints (ideal), OR
      - list of steps (1-based will be created)
    Converts to Dict[int, Dict[str, Any]].
    """
    if steps is None:
        return None
    if isinstance(steps, dict):
        # keys may arrive as strings via JSON — coerce to int
        fixed = {}
        for k, v in steps.items():
            try:
                fixed[int(k)] = v
            except Exception:
                # ignore keys that can’t become int
                continue
        return fixed
    if isinstance(steps, list):
        return {i + 1: step for i, step in enumerate(steps)}
    return None

# ---------- Endpoints ----------

@router.post("/start", response_model=ChatResponse)
def start_task(payload: StartTaskPayload):
    """
    Start a new Step Guidance session (or overwrite the last snapshot if session_id is reused on chat).
    Returns the welcome message and the generated session_id.
    """
    session_id = uuid.uuid4().hex

    bot = StepGuidanceChatbot()

    steps_data = _normalize_steps_data(payload.steps_data)
    tools_data = payload.tools_data or {}
    problem_summary = payload.problem_summary or ""

    welcome = bot.start_new_task(
        task_name=payload.task_name,
        total_steps=(len(steps_data) if steps_data else payload.total_steps),
        steps_data=steps_data,
        tools_data=tools_data,
        problem_summary=problem_summary
    )

    _log_message(session_id, "assistant", welcome, bot, payload.user, payload.project, msg_type="project_intro")
    ctx = _get_context(bot)

    return ChatResponse(
        response=welcome,
        session_id=session_id,
        current_step=ctx.get("current_step"),
        total_steps=ctx.get("total_steps"),
        task_name=ctx.get("task_name")
    )

@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatPayload):
    """
    Send a chat message to the Step Guidance bot. If session_id is missing, a new session is created with a default task.
    (For real use, call /start first to seed the task/steps.)
    """
    session_id = payload.session_id or uuid.uuid4().hex
    bot = _get_latest_bot(session_id)

    if bot.current_task is None:
        # If no task has been started for this session, bootstrap a trivial one.
        bot.start_new_task("Untitled Task", total_steps=1, steps_data={1: {"title": "Step 1", "instructions": "Describe your task to begin."}}, tools_data={}, problem_summary="")

    _log_message(session_id, "user", payload.message, bot, payload.user, payload.project)

    resp = bot.chat(payload.message)

    _log_message(session_id, "assistant", resp, bot, payload.user, payload.project)

    ctx = _get_context(bot)

    return ChatResponse(
        response=resp,
        session_id=session_id,
        current_step=ctx.get("current_step"),
        total_steps=ctx.get("total_steps"),
        task_name=ctx.get("task_name")
    )

@router.get("/session/{session_id}/status", response_model=SessionInfo)
def get_status(session_id: str):
    """
    Returns current step, total steps, tools for the step, completed steps, etc.
    """
    bot = _get_latest_bot(session_id)
    ctx = _get_context(bot)
    if not ctx:
        raise HTTPException(status_code=404, detail="Session not found")

    completed = [int(k) for k, v in (ctx.get("completion_status") or {}).items() if v.get("completed")]
    return SessionInfo(
        session_id=session_id,
        task_name=ctx.get("task_name"),
        current_step=ctx.get("current_step", 1),
        total_steps=ctx.get("total_steps", 1),
        tools_for_step=ctx.get("current_tools", []),
        completed_steps=sorted(completed),
        problem_summary=ctx.get("problem_summary")
    )

@router.post("/session/move-to-step", response_model=ChatResponse)
def move_to_step(payload: MoveToStepPayload):
    """
    Force the bot to a specific step (useful for UI step clicks).
    """
    session_id = payload.session_id
    bot = _get_latest_bot(session_id)

    ok = bot.execution_agent.context_agent.move_to_step(payload.step_number)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Invalid step number {payload.step_number}")

    ctx = _get_context(bot)
    msg = f"➡️ Moved to step {ctx.get('current_step')}: {ctx.get('current_step_data', {}).get('title','')}"
    _log_message(session_id, "assistant", msg, bot, payload.user, payload.project, msg_type="system")

    return ChatResponse(
        response=msg,
        session_id=session_id,
        current_step=ctx.get("current_step"),
        total_steps=ctx.get("total_steps"),
        task_name=ctx.get("task_name")
    )

@router.post("/session/mark-complete", response_model=ChatResponse)
def mark_complete(payload: MarkCompletePayload):
    """
    Mark the current step complete and auto-advance (uses the bot’s progression logic).
    Equivalent to sending a message like "I'm done with this step".
    """
    session_id = payload.session_id
    bot = _get_latest_bot(session_id)

    # mirror the chat phrase so we reuse the agent's progression logic
    user_msg = "I'm done with this step" if not payload.notes else f"I'm done with this step: {payload.notes}"
    _log_message(session_id, "user", user_msg, bot, payload.user, payload.project)

    resp = bot.chat(user_msg)
    _log_message(session_id, "assistant", resp, bot, payload.user, payload.project)

    ctx = _get_context(bot)
    return ChatResponse(
        response=resp,
        session_id=session_id,
        current_step=ctx.get("current_step"),
        total_steps=ctx.get("total_steps"),
        task_name=ctx.get("task_name")
    )

@router.post("/session/reset")
def reset_session(payload: ResetPayload):
    """
    Reset the bot for this session (clears state but keeps the same session id history).
    """
    session_id = payload.session_id
    bot = StepGuidanceChatbot()
    _log_message(session_id, "assistant", "Session reset.", bot, payload.user, payload.project, msg_type="reset")
    # Optional: return a fresh intro for UI
    msg = "Session reset. Start a task to begin."
    return {"message": msg}

@router.get("/session/{session_id}/history")
def get_history(session_id: str):
    """
    Return the raw chat history for a session (ordered ascending).
    """
    cursor = conversations_collection.find({"session_id": session_id}).sort("timestamp", 1)
    return [
        {
            "role": doc["role"],
            "message": doc["message"],
            "timestamp": doc["timestamp"]
        } for doc in cursor
    ]

@router.delete("/session/{session_id}")
def delete_session(session_id: str):
    """
    Delete all messages and state for a session.
    """
    conversations_collection.delete_many({"session_id": session_id})
    return {"message": f"Session {session_id} deleted successfully"}

@router.get("/health")
def health():
    return {"status": "healthy", "service": "StepGuidanceChatbot"}
