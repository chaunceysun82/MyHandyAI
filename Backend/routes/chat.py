# in a new file: chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pymongo import DESCENDING
from bson import ObjectId
from db import conversations_collection
from datetime import datetime
import pickle
from chatbot.agents import AgenticChatbot

router = APIRouter()

class UserMessage(BaseModel):
    userId: str
    projectId: str
    type: str = "firstBot"
    message: str

def log_message(session_id, role, message, chatbot, type, userId, projectId):
    doc = {
        "session_id": session_id,
        "userId": userId, 
        "projectId":projectId,
        "role": role,
        "message": message,
        "type": type,
        "timestamp": datetime.utcnow(),
        "chatbot_state": pickle.dumps(chatbot),
        "current_state": getattr(chatbot, "current_state", None)
    }
    conversations_collection.insert_one(doc)

# @router.post("/chat/user-message")
# def create_or_append_user_message(data: UserMessage):
#     user_obj = ObjectId(data.userId)
#     project_obj = ObjectId(data.projectId)

#     # Check if a conversation already exists
#     conversation = conversations_collection.find_one({
#         "userId": user_obj,
#         "projectId": project_obj,
#         "type": data.type
#     })

#     message_entry = {
#         "user": data.message,
#         "llm": "",
#         "status": "in-progress",
#         "timestamp": datetime.utcnow()
#     }

#     if conversation:
#         conversations_collection.update_one(
#             {"_id": conversation["_id"]},
#             {"$push": {"messages": message_entry}}
#         )
#         return {"conversationId": str(conversation["_id"]), "message": "Message appended"}
#     else:
#         new_conv = {
#             "userId": user_obj,
#             "projectId": project_obj,
#             "type": data.type,
#             "messages": [message_entry]
#         }
#         result = conversations_collection.insert_one(new_conv)
#         return {"conversationId": str(result.inserted_id), "message": "New conversation created"}
    
def get_conversation(user_id: str, project_id: str, conv_type: str = "firstBot", session_id: str = None):
    query = {}

    if session_id:
        query["session_id"] = session_id
    else:
        query = {
            "userId": user_id,
            "projectId": project_id,
            "message_type": conv_type  # or 'type' if you still use that field
        }

    conversation = list(conversations_collection.find(query).sort("timestamp", 1))
    
    if not conversation:
        return None
    
    return conversation

def get_latest_chatbot(session_id):
    doc = conversations_collection.find_one({"session_id": session_id}, sort=[("timestamp", DESCENDING)])
    if doc and "chatbot_state" in doc:
        return pickle.loads(doc["chatbot_state"])
    else:
        return AgenticChatbot()
    
def get_session(user_id: str, project_id: str, type:str = "firstBot"):
    if user_id and project_id:
        return conversations_collection.find({
            "userId": user_id,
            "projectId": project_id,
            "message_type": type
        })["session_id"]
    else:
        return "No valid user or project"

# class LLMResponse(BaseModel):
#     conversationId: str
#     response: str

# @router.post("/chat/llm-response")
# def store_llm_response(data: LLMResponse):
#     conv_id = ObjectId(data.conversationId)
#     conversation = conversations_collection.find_one({"_id": conv_id})
#     if not conversation:
#         raise HTTPException(status_code=404, detail="Conversation not found")

#     for i in reversed(range(len(conversation["messages"]))):
#         if conversation["messages"][i]["status"] == "in-progress":
#             conversation["messages"][i]["llm"] = data.response
#             conversation["messages"][i]["status"] = "complete"
#             break
#     else:
#         raise HTTPException(status_code=400, detail="No message in progress to update")

#     conversations_collection.update_one(
#         {"_id": conv_id},
#         {"$set": {"messages": conversation["messages"]}}
#     )

#     return {"message": "LLM response updated"}