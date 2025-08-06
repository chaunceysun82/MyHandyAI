from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import base64
import uuid
from pymongo import DESCENDING
import pickle
from db import conversations_collection
from datetime import datetime


# Add the chatbot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

from chatbot.agents import AgenticChatbot

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

class ChatMessage(BaseModel):
    message: str
    user: str
    project: str
    session_id: Optional[str] = None
    uploaded_image: Optional[str] = None

class StartChat(BaseModel):
    user: str
    project: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    current_state: Optional[str] = None

class ChatSession(BaseModel):
    session_id: str
    intro_messages: List[Dict[str, Any]]

class SessionInfo(BaseModel):
    session_id: str
    current_state: str
    problem_type: Optional[str] = None
    questions_remaining: Optional[int] = None

# ==== Utility Functions ====

def log_message(session_id, role, message, chatbot, user, project, message_type="text"):
    doc = {
        "session_id": session_id,
        "user": user,
        "project": project,
        "role": role,
        "message": message,
        "message_type": message_type,
        "timestamp": datetime.utcnow(),
        "chatbot_state": pickle.dumps(chatbot),
        "current_state": getattr(chatbot, "current_state", None)
    }
    conversations_collection.insert_one(doc)

def get_latest_chatbot(session_id):
    doc = conversations_collection.find_one(
        {"session_id": session_id},
        sort=[("timestamp", DESCENDING)]
    )
    if doc and "chatbot_state" in doc:
        return pickle.loads(doc["chatbot_state"])
    else:
        return AgenticChatbot()

def get_conversation_history(session_id):
    cursor = conversations_collection.find({"session_id": session_id}).sort("timestamp", 1)
    return [{"role": doc["role"], "message": doc["message"], "timestamp": doc["timestamp"]} for doc in cursor]

def reset_session(session_id, user, project):
    chatbot = AgenticChatbot()
    log_message(session_id, "assistant", "Session reset.", chatbot, user, project, message_type="reset")
    return chatbot

def delete_session_docs(session_id):
    conversations_collection.delete_many({"session_id": session_id})

# Store chatbot instances by session
chatbot_instances = {}

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage):
    """
    Chat with the MyHandyAI agentic assistant.
    Creates a new session_id if not provided.
    """
    try:
        session_id = chat_message.session_id or uuid.uuid4().hex
        chatbot = get_latest_chatbot(session_id)

        # Decode uploaded image if present
        uploaded_image = None
        if chat_message.uploaded_image:
            image_data = chat_message.uploaded_image
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            uploaded_image = base64.b64decode(image_data)

        # Log user message
        log_message(session_id, "user", chat_message.message, chatbot, chat_message.user, chat_message.project)

        # Get bot response and log it
        response = chatbot.process_message(chat_message.message, uploaded_image)
        log_message(session_id, "assistant", response, chatbot, chat_message.user, chat_message.project)

        return ChatResponse(
            response=response,
            session_id=session_id,
            current_state=getattr(chatbot, "current_state", None)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")

@router.post("/start", response_model=ChatSession)
async def start_new_session(payload: StartChat):
    """
    Starts a new chat session and returns the session_id and intro messages.
    """
    session_id = uuid.uuid4().hex
    chatbot = AgenticChatbot()
    intro_messages = [
        {"role": "assistant", "content": "Thanks for using MyHandyAI! Tell me what you'd like to do or fix."},
        {"role": "assistant", "content": "Hi User! Let's get started with your project!"},
        {"role": "assistant", "content": "What home project can we help with today?"}
    ]
    log_message(session_id, "assistant", intro_messages[0]["content"], chatbot, payload.user, payload.project, message_type="intro")
    return ChatSession(session_id=session_id, intro_messages=intro_messages)

@router.get("/session/{session_id}/history")
async def get_chat_history(session_id: str):
    """
    Returns the full message history for a session.
    """
    return get_conversation_history(session_id)

@router.get("/session/{session_id}/info", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """
    Returns the latest state for a session.
    """
    doc = conversations_collection.find_one(
        {"session_id": session_id},
        sort=[("timestamp", DESCENDING)]
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    chatbot = pickle.loads(doc["chatbot_state"])
    questions_remaining = None
    if getattr(chatbot, "current_state", None) == "asking_questions":
        questions_remaining = len(chatbot.questions) - chatbot.current_question_index
    return SessionInfo(
        session_id=session_id,
        current_state=getattr(chatbot, "current_state", None),
        problem_type=getattr(chatbot, "problem_type", None),
        questions_remaining=questions_remaining
    )

@router.post("/session/{session_id}/reset")
async def reset_conversation(session_id: str, user: str, project: str):
    """
    Resets a session and logs the reset.
    """
    chatbot = reset_session(session_id, user, project)
    intro_messages = [
        {"role": "assistant", "content": "Thanks for using MyHandyAI! Tell me what you'd like to do or fix."},
        {"role": "assistant", "content": "Hi User! Let's get started with your project!"},
        {"role": "assistant", "content": "What home project can we help with today?"}
    ]
    return {"message": "Conversation reset successfully", "intro_messages": intro_messages}

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Deletes all messages and state for a session.
    """
    delete_session_docs(session_id)
    return {"message": f"Session {session_id} deleted successfully"}

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Chatbot API is running"}