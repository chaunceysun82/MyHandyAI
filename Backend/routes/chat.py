# in a new file: chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from db import conversations_collection

router = APIRouter()

class UserMessage(BaseModel):
    userId: str
    projectId: str
    message: str

@router.post("/chat/user-message")
def store_user_message(data: UserMessage):
    message_data = {
        "userId": ObjectId(data.userId),
        "projectId": ObjectId(data.projectId),
        "message": data.message,
        "sender": "user",
        "status": "in-progress"
    }
    result = conversations_collection.insert_one(message_data)
    return {"conversationId": str(result.inserted_id)}

class LLMResponse(BaseModel):
    conversationId: str
    response: str

@router.post("/chat/llm-response")
def store_llm_response(data: LLMResponse):
    conversation = conversations_collection.find_one({"_id": ObjectId(data.conversationId)})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = conversations_collection.insert_one({
        "userId": conversation["userId"],
        "projectId": conversation["projectId"],
        "message": data.response,
        "sender": "llm",
        "status": "complete"
    })
    return {"llmResponseId": str(result.inserted_id)}