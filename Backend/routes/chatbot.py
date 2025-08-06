from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import base64

# Add the chatbot directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

from chatbot.agents import AgenticChatbot

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    uploaded_image: Optional[str] = None  # base64 encoded image

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

# Store chatbot instances by session
chatbot_instances = {}

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage):
    """Chat with the MyHandyAI agentic assistant"""
    try:
        session_id = chat_message.session_id or "default"
        
        # Get or create chatbot instance for this session
        if session_id not in chatbot_instances:
            chatbot_instances[session_id] = AgenticChatbot()
        
        chatbot = chatbot_instances[session_id]
        
        # Convert base64 image to bytes if provided
        uploaded_image = None
        if chat_message.uploaded_image:
            try:
                # Remove data URL prefix if present
                image_data = chat_message.uploaded_image
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                uploaded_image = base64.b64decode(image_data)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")
        
        # Get response from agentic chatbot
        response = chatbot.process_message(chat_message.message, uploaded_image)
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            current_state=chatbot.current_state
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")

@router.post("/upload-image")
async def upload_image(
    session_id: str,
    file: UploadFile = File(...)
):
    """Upload an image for the chatbot to analyze"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        image_data = await file.read()
        
        # Store image data in session (you might want to store this in a database)
        if session_id not in chatbot_instances:
            chatbot_instances[session_id] = AgenticChatbot()
        
        # For now, we'll return the base64 encoded image
        # In a real implementation, you'd store this and reference it by ID
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return {
            "message": "Image uploaded successfully",
            "image_id": f"img_{session_id}_{len(image_base64)}",  # Simple ID generation
            "image_base64": image_base64
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@router.get("/session/{session_id}", response_model=ChatSession)
async def get_chat_session(session_id: str):
    """Get or create a new chat session"""
    try:
        # Create new chatbot instance if it doesn't exist
        if session_id not in chatbot_instances:
            chatbot_instances[session_id] = AgenticChatbot()
        
        chatbot = chatbot_instances[session_id]
        
        # Create intro messages similar to the agentic system
        intro_messages = [
            {"role": "assistant", "content": "Thanks for using MyHandyAI! Tell me what you'd like to do or fix."},
            {"role": "assistant", "content": "Hi User! Let's get started with your project!"},
            {"role": "assistant", "content": "What home project can we help with today?"}
        ]
        
        return ChatSession(
            session_id=session_id,
            intro_messages=intro_messages
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session error: {str(e)}")

@router.get("/session/{session_id}/info", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """Get current session information"""
    try:
        if session_id not in chatbot_instances:
            raise HTTPException(status_code=404, detail="Session not found")
        
        chatbot = chatbot_instances[session_id]
        
        questions_remaining = None
        if chatbot.current_state == "asking_questions":
            questions_remaining = len(chatbot.questions) - chatbot.current_question_index
        
        return SessionInfo(
            session_id=session_id,
            current_state=chatbot.current_state,
            problem_type=chatbot.problem_type,
            questions_remaining=questions_remaining
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session info error: {str(e)}")

@router.post("/session/{session_id}/reset")
async def reset_conversation(session_id: str):
    """Reset the conversation for a session"""
    try:
        if session_id not in chatbot_instances:
            chatbot_instances[session_id] = AgenticChatbot()
        else:
            chatbot_instances[session_id].reset()
        
        chatbot = chatbot_instances[session_id]
        
        # Create intro messages
        intro_messages = [
            {"role": "assistant", "content": "Thanks for using MyHandyAI! Tell me what you'd like to do or fix."},
            {"role": "assistant", "content": "Hi User! Let's get started with your project!"},
            {"role": "assistant", "content": "What home project can we help with today?"}
        ]
        
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

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Chatbot API is running"} 