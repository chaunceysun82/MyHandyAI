import base64
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import DESCENDING

# Add the chatbot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

# <-- IMPORTANT: this is your new orchestration -->
from chatbot.langagents import run_chat_step  # make sure this exists
from database.mongodb import mongodb
from pymongo.database import Database
from pymongo.collection import Collection

router = APIRouter(prefix="/lang", tags=["chatbot"])
database: Database = mongodb.get_database()
conversations_collection: Collection = database.get_collection("Conversations")

# ---------- Config ----------
INITIAL_STATE = "greetings"  # change if your graph starts elsewhere


# ---------- Schemas ----------
class ChatMessage(BaseModel):
    message: str
    user: str
    project: str
    session_id: Optional[str] = None
    uploaded_image: Optional[str] = None  # base64 data URL or raw base64


class StartChat(BaseModel):
    user: str
    project: str


class ResetChat(BaseModel):
    user: str
    project: str
    session: str


class ChatResponse(BaseModel):
    response: str
    session_id: str
    current_state: Optional[str] = None


class ChatSession(BaseModel):
    session_id: str
    intro_message: str


class SessionInfo(BaseModel):
    session_id: str
    current_state: str
    problem_type: Optional[str] = None
    questions_remaining: Optional[int] = None


# ---------- Helpers ----------
def _decode_image(maybe_data_url: str) -> bytes:
    """Accepts data URL (data:image/xxx;base64,...) or plain base64."""
    raw = maybe_data_url
    if raw.startswith("data:image"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def _get_latest_state(session_id: str) -> tuple[Dict[str, Any], str]:
    """
    Returns (chat_state, current_state). Initializes if not found.
    We store both on every insert so we can always recover the latest.
    """
    doc = conversations_collection.find_one(
        {"session_id": session_id},
        sort=[("timestamp", DESCENDING)],
        projection={"chat_state": 1, "current_state": 1, "_id": 0},
    )
    if doc and "chat_state" in doc and "current_state" in doc:
        return doc["chat_state"] or {}, doc["current_state"] or INITIAL_STATE
    return {}, INITIAL_STATE


def _log_entry(
        *,
        session_id: str,
        role: str,
        message: str,
        user: str,
        project: str,
        chat_state: Dict[str, Any],
        current_state: str,
        message_type: str = "text",
):
    conversations_collection.insert_one(
        {
            "session_id": session_id,
            "user": user,
            "project": project,
            "role": role,  # 'user' | 'assistant' | 'system'
            "message": message,
            "message_type": message_type,
            "timestamp": datetime.utcnow(),
            "chat_state": chat_state,
            "current_state": current_state,
        }
    )


def _conversation_history(session_id: str):
    cur = conversations_collection.find(
        {"session_id": session_id},
    ).sort("timestamp", 1)
    return [
        {
            "role": d.get("role"),
            "message": d.get("message"),
            "timestamp": d.get("timestamp"),
            "current_state": d.get("current_state"),
        }
        for d in cur
    ]


def _delete_session(session_id: str):
    conversations_collection.delete_many({"session_id": session_id})


def _questions_remaining(chat_state: Dict[str, Any], current_state: str) -> Optional[int]:
    if current_state != "asking_questions":
        return None
    qs = chat_state.get("questions") or []
    idx = chat_state.get("current_question_index", 0)
    return max(len(qs) - idx, 0)


# ---------- Endpoints ----------
@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage):
    """
    Single-turn interaction:
    - Loads the latest state for the session (or initializes)
    - Adds user input (and optional image) into chat_state
    - Runs one graph step
    - Logs user + assistant turns with updated state
    """
    try:
        session_id = chat_message.session_id or uuid.uuid4().hex
        chat_state, current_state = _get_latest_state(session_id)

        # merge user message into state
        chat_state["user_message"] = chat_message.message

        # handle optional image
        if chat_message.uploaded_image:
            try:
                chat_state["uploaded_image"] = _decode_image(chat_message.uploaded_image)
            except Exception:
                # If bad image payload, clear it and continue (don’t break the chat)
                chat_state["uploaded_image"] = None

        # Log user message with *pre-run* state
        _log_entry(
            session_id=session_id,
            role="user",
            message=chat_message.message,
            user=chat_message.user,
            project=chat_message.project,
            chat_state=chat_state,
            current_state=current_state,
        )

        # Run one step of the graph
        next_state, new_state = run_chat_step(current_state, chat_state)

        # Bot response
        response_text = new_state.get("response_message") or ""

        # Log assistant response with *post-run* state
        _log_entry(
            session_id=session_id,
            role="assistant",
            message=response_text,
            user=chat_message.user,
            project=chat_message.project,
            chat_state=new_state,
            current_state=next_state,
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            current_state=next_state,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")


@router.post("/start", response_model=ChatSession)
async def start_new_session(payload: StartChat):
    """
    Creates a new session and triggers the greeting node (INITIAL_STATE).
    We run a no-op user message so the greetings node can produce text.
    """
    try:
        session_id = uuid.uuid4().hex

        # Start: empty state, enter graph at INITIAL_STATE
        chat_state: Dict[str, Any] = {}
        current_state = INITIAL_STATE

        # Option A: immediately run the greeting node
        next_state, new_state = run_chat_step(current_state, chat_state)
        intro_message = new_state.get("response_message") or "Hi! Tell me what you’d like to fix."

        # Log the assistant greeting
        _log_entry(
            session_id=session_id,
            role="assistant",
            message=intro_message,
            user=payload.user,
            project=payload.project,
            chat_state=new_state,
            current_state=next_state,
            message_type="intro",
        )

        return ChatSession(session_id=session_id, intro_message=intro_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Start error: {str(e)}")


@router.get("/session/{session_id}/history")
async def get_chat_history(session_id: str):
    """Returns full message history for a session."""
    return _conversation_history(session_id)


@router.get("/session/{session_id}/info", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """
    Returns latest state info for a session, derived from the most recent log entry.
    """
    doc = conversations_collection.find_one(
        {"session_id": session_id},
        sort=[("timestamp", DESCENDING)],
        projection={"chat_state": 1, "current_state": 1, "_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    chat_state = doc.get("chat_state") or {}
    current_state = doc.get("current_state") or INITIAL_STATE
    return SessionInfo(
        session_id=session_id,
        current_state=current_state,
        problem_type=chat_state.get("problem_type"),
        questions_remaining=_questions_remaining(chat_state, current_state),
    )


@router.post("/session/{session_id}/reset")
async def reset_conversation(payload: ResetChat):
    """
    Clears state by inserting a system reset marker + starts at greetings again.
    (We don't delete history here; we just continue the log.)
    """
    try:
        # Insert a reset marker (optional)
        _log_entry(
            session_id=payload.session,
            role="system",
            message="Session reset.",
            user=payload.user,
            project=payload.project,
            chat_state={},
            current_state=INITIAL_STATE,
            message_type="reset",
        )

        # Run greetings again and log
        next_state, new_state = run_chat_step(INITIAL_STATE, {})
        intro_message = new_state.get("response_message") or "Hi! Tell me what you’d like to fix."

        _log_entry(
            session_id=payload.session,
            role="assistant",
            message=intro_message,
            user=payload.user,
            project=payload.project,
            chat_state=new_state,
            current_state=next_state,
            message_type="intro",
        )

        return {"message": "Conversation reset successfully", "intro_message": intro_message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Deletes all messages and state for a session."""
    _delete_session(session_id)
    return {"message": f"Session {session_id} deleted successfully"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Chatbot API is running"}
