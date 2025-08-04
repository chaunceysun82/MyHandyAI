from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os

# Add the chatbot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

from chatbot.grok_chatbot import GrokChatbot

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_history: List[Dict[str, Any]]

class ChatSession(BaseModel):
    session_id: str
    intro_messages: List[Dict[str, Any]]

# Store chatbot instances by session
chatbot_instances = {}

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage):
    """Chat with the MyHandyAI assistant"""
    try:
        session_id = chat_message.session_id or "default"
        
        # Get or create chatbot instance for this session
        if session_id not in chatbot_instances:
            chatbot_instances[session_id] = GrokChatbot()
        
        chatbot = chatbot_instances[session_id]
        
        # Get response from chatbot
        response = chatbot.chat(chat_message.message)
        
        # Get conversation history
        history = chatbot.get_conversation_history()
        
        return ChatResponse(
            response=response,
            conversation_history=history
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")

@router.get("/session/{session_id}", response_model=ChatSession)
async def get_chat_session(session_id: str):
    """Get or create a new chat session"""
    try:
        # Create new chatbot instance if it doesn't exist
        if session_id not in chatbot_instances:
            chatbot_instances[session_id] = GrokChatbot()
        
        chatbot = chatbot_instances[session_id]
        intro_messages = chatbot.get_intro_messages()
        
        return ChatSession(
            session_id=session_id,
            intro_messages=intro_messages
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session error: {str(e)}")

@router.get("/session/{session_id}/history")
async def get_conversation_history(session_id: str):
    """Get the conversation history for a session"""
    try:
        if session_id not in chatbot_instances:
            raise HTTPException(status_code=404, detail="Session not found")
        
        chatbot = chatbot_instances[session_id]
        history = chatbot.get_conversation_history()
        
        return {"conversation_history": history}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History error: {str(e)}")

@router.post("/session/{session_id}/reset")
async def reset_conversation(session_id: str):
    """Reset the conversation for a session"""
    try:
        if session_id not in chatbot_instances:
            chatbot_instances[session_id] = GrokChatbot()
        else:
            chatbot_instances[session_id].reset_conversation()
        
        chatbot = chatbot_instances[session_id]
        intro_messages = chatbot.get_intro_messages()
        
        return {
            "message": "Conversation reset successfully",
            "intro_messages": intro_messages
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session"""
    try:
        if session_id in chatbot_instances:
            del chatbot_instances[session_id]
        
        return {"message": f"Session {session_id} deleted successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete error: {str(e)}") 