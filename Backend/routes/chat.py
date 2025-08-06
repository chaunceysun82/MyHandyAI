# in a new file: chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from db import conversations_collection
from datetime import datetime

router = APIRouter()

class UserMessage(BaseModel):
    userId: str
    projectId: str
    type: str = "firstBot"
    message: str

@router.post("/chat/user-message")
def create_or_append_user_message(data: UserMessage):
    user_obj = ObjectId(data.userId)
    project_obj = ObjectId(data.projectId)

    # Check if a conversation already exists
    conversation = conversations_collection.find_one({
        "userId": user_obj,
        "projectId": project_obj,
        "type": data.type
    })

    message_entry = {
        "user": data.message,
        "llm": "",
        "status": "in-progress",
        "timestamp": datetime.utcnow()
    }

    if conversation:
        conversations_collection.update_one(
            {"_id": conversation["_id"]},
            {"$push": {"messages": message_entry}}
        )
        return {"conversationId": str(conversation["_id"]), "message": "Message appended"}
    else:
        new_conv = {
            "userId": user_obj,
            "projectId": project_obj,
            "type": data.type,
            "messages": [message_entry]
        }
        result = conversations_collection.insert_one(new_conv)
        return {"conversationId": str(result.inserted_id), "message": "New conversation created"}
    
def get_conversation(user_id: str, project_id: str, conv_type: str = "firstBot"):
    conversation = conversations_collection.find_one({
        "userId": ObjectId(user_id),
        "projectId": ObjectId(project_id),
        "type": conv_type
    })

    if not conversation:
        return None

    conversation["_id"] = str(conversation["_id"])
    conversation["userId"] = str(conversation["userId"])
    conversation["projectId"] = str(conversation["projectId"])
    return conversation

class LLMResponse(BaseModel):
    conversationId: str
    response: str

@router.post("/chat/llm-response")
def store_llm_response(data: LLMResponse):
    conv_id = ObjectId(data.conversationId)
    conversation = conversations_collection.find_one({"_id": conv_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    for i in reversed(range(len(conversation["messages"]))):
        if conversation["messages"][i]["status"] == "in-progress":
            conversation["messages"][i]["llm"] = data.response
            conversation["messages"][i]["status"] = "complete"
            break
    else:
        raise HTTPException(status_code=400, detail="No message in progress to update")

    conversations_collection.update_one(
        {"_id": conv_id},
        {"$set": {"messages": conversation["messages"]}}
    )

    return {"message": "LLM response updated"}