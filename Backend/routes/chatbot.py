from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import base64
import uuid
from pymongo import DESCENDING
import pickle
from db import conversations_collection, project_collection
from datetime import datetime
from .project import update_project
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from bson import ObjectId
from openai import OpenAI
from qdrant_client.http.exceptions import UnexpectedResponse
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

from chatbot.agents import AgenticChatbot

router = APIRouter(prefix="/chatbot", tags=["chatbot"])
client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatMessage(BaseModel):
    message: str
    user: str
    project: str
    session_id: Optional[str] = None
    uploaded_image: Optional[str] = None

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


def log_message(session_id, role, message, chatbot, user, project, message_type="project_intro"):
    doc = {
        "session_id": session_id,
        "user": user,
        "project": project,
        "role": role,
        "message": message,
        "chat_type": message_type,
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

@router.get("/session/{project}")
def get_session(project):
    cursor = conversations_collection.find_one({"project":project,"chat_type":"project_intro"})
    if not cursor:
        return {"session": None}
    return {"session": cursor["session_id"]}


def reset_session(session_id, user, project):
    chatbot = AgenticChatbot()
    log_message(session_id, "assistant", "Session reset.", chatbot, user, project, message_type="reset")
    return chatbot

def delete_session_docs(session_id):
    conversations_collection.delete_many({"session_id": session_id})


chatbot_instances = {}

def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    """
    Simple character-based chunker. Produces chunks of <= max_chars.
    (You can replace with token-based chunking if desired.)
    """
    if not text:
        return []
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks

def create_embeddings_for_texts(texts, model: str = "text-embedding-3-small"):
    """
    Creates embeddings via OpenAI for a list of strings (batched).
    Returns list of embedding vectors in same order as texts.
    """
    if not texts:
        return []
    
    resp = client.embeddings.create(model=model, input=texts)
    
    return [item.embedding for item in resp.data]

def upsert_embeddings_to_qdrant(
        mongo_hex_id: str,
        embeddings: List[List[float]],
        texts: List[str],
        extra_payload: Optional[dict] = None,
        collection_name: Optional[str] = None
    ) -> dict:

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection_name = collection_name or "projects"

    if not qdrant_url or not qdrant_api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in env")

    qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)

    if not embeddings:
        return {"status": "no_embeddings"}

    vector_size = len(embeddings[0])

    
    try:
        qclient.get_collection(collection_name=collection_name)
    except UnexpectedResponse as ex:
        if ex.status_code == 404:
            
            qclient.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        else:
            raise

    
    points = []
    for idx, (vec, txt) in enumerate(zip(embeddings, texts)):
        unique_str = f"{mongo_hex_id}-{idx}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_str))

        payload = {
            "mongo_id": mongo_hex_id,
            "chunk_index": idx,
            "text_preview": txt,
        }
        print(payload)
        if extra_payload:
            payload.update(extra_payload)

        points.append(PointStruct(id=point_id, vector=vec, payload=payload))

    qclient.upsert(collection_name=collection_name, points=points)
    return {"status": "ok", "num_points": len(points), "collection": collection_name}

def create_and_store_summary_embeddings_for_project(summary: str, mongo_project_id, extra_payload: Optional[dict] = None):
    """
    Orchestrator: chunk summary, create embeddings, upsert to Qdrant using mongo id(s).
    mongo_project_id: ObjectId or hex string
    """
    if not summary:
        return {"status": "no_summary"}

    if isinstance(mongo_project_id, ObjectId):
        mongo_hex = str(mongo_project_id)
    else:
        mongo_hex = str(mongo_project_id)

  
    chunks = chunk_text(summary, max_chars=len(summary))
    embeddings = create_embeddings_for_texts(chunks, model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    qresult = upsert_embeddings_to_qdrant(mongo_hex, embeddings, chunks, extra_payload=extra_payload)
    return qresult

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

        print(getattr(chatbot, "current_state", None))

        if getattr(chatbot, "current_state", None) == "complete":
            await save_information(session_id=session_id)
            await qdrant_function(project_id=chat_message.project)

        return ChatResponse(
            response=response,
            session_id=session_id,
            current_state=getattr(chatbot, "current_state", None)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")

@router.get("/start", response_model=ChatSession)
async def start_new_session(payload: StartChat):
    """
    Starts a new chat session and returns the session_id and intro messages.
    """
    session_id = uuid.uuid4().hex
    chatbot = AgenticChatbot()
    intro_message = chatbot.greet()
    log_message(session_id, "assistant", intro_message, chatbot, payload.user, payload.project, message_type="project_intro")
    return ChatSession(session_id=session_id, intro_message=intro_message)


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
async def reset_conversation(payload: ResetChat):
    """
    Resets a session and logs the reset.
    """
    chatbot = reset_session(payload.session, payload.user, payload.project)
    intro_message = chatbot.greet()
    return {"message": "Conversation reset successfully", "intro_message": intro_message}



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



@router.post("/session/{session_id}/save")
async def save_information(session_id: str):
    bot=get_latest_chatbot(session_id)
    conv=conversations_collection.find_one({"session_id":session_id})
    if bot.current_state == "complete":
        print (str(conv["project"]))
        answers = bot.user_answers
        if isinstance(answers, dict):
            answers = {str(k): v for k, v in answers.items()}
        update_project(str(conv["project"]), {"user_description":bot.user_description,
                                         "summary": bot.summary,
                                         "image_analysis":bot.image_analysis,
                                         "questions":bot.questions,
                                         "answers":answers})
        
        
        return {"message":"Data saved Successfully"}
    else:
        return {"messaage":"chat not complete"}
    
@router.post("/save/embeddings/{project_id}")
async def qdrant_function(project_id: str):

    try:
        obj_id = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project_id format")

    project = project_collection.find_one({"_id": obj_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    summary = project.get("summary")
    if not summary:
        raise HTTPException(status_code=400, detail="No summary to embed")
    
    qresult = create_and_store_summary_embeddings_for_project(
        summary=summary,
        mongo_project_id=str(project["_id"]),
        extra_payload={"project": str(project["_id"])}
    )

    return {
        "message": "Embeddings upserted successfully",
        "project_id": str(project["_id"]),
        "result": qresult
    }

@router.get("/debug/projects")
async def debug_projects():
    docs = project_collection.find().limit(3)
    output = []
    for p in docs:
        output.append({
            "id": str(p["_id"]),
            "type": str(type(p["_id"]))
        })
    return output
