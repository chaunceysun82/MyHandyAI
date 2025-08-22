from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import base64
import uuid
from pymongo import DESCENDING
import pickle
from db import conversations_collection, project_collection, tools_collection
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

class Tool(BaseModel):
    name: str
    description: str
    price: float
    risk_factors: str
    safety_measures: str
    image_link: Optional[str] = None
    amazon_link: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class ToolSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    similarity_threshold: Optional[float] = 0.7


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

def store_tool_in_database(tool_data: Dict[str, Any]) -> str:
    """
    Store a tool in the MongoDB tools collection.
    Returns the tool ID.
    """
    tool_doc = {
        "name": tool_data["name"],
        "description": tool_data["description"],
        "price": tool_data["price"],
        "risk_factors": tool_data["risk_factors"],
        "safety_measures": tool_data["safety_measures"],
        "image_link": tool_data.get("image_link"),
        "amazon_link": tool_data.get("amazon_link"),
        "category": tool_data.get("category", "general"),
        "tags": tool_data.get("tags", []),
        "created_at": datetime.utcnow(),
        "usage_count": 1,
        "last_used": datetime.utcnow()
    }
    
    result = tools_collection.insert_one(tool_doc)
    return str(result.inserted_id)

def update_tool_usage(tool_id: str):
    """
    Update the usage count and last used timestamp for a tool.
    """
    tools_collection.update_one(
        {"_id": ObjectId(tool_id)},
        {
            "$inc": {"usage_count": 1},
            "$set": {"last_used": datetime.utcnow()}
        }
    )

def create_and_store_tool_embeddings(tool_data: Dict[str, Any], tool_id: str):
    """
    Create embeddings for a tool and store them in Qdrant tools collection.
    """
    # Create text representation for embedding
    tool_text = f"{tool_data['name']} {tool_data['description']} {tool_data.get('category', '')} {' '.join(tool_data.get('tags', []))}"
    
    # Generate embedding
    embedding = create_embeddings_for_texts([tool_text], model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    
    if not embedding:
        return {"status": "embedding_failed"}
    
    # Store in Qdrant tools collection
    qresult = upsert_embeddings_to_qdrant(
        mongo_hex_id=tool_id,
        embeddings=embedding,
        texts=[tool_text],
        extra_payload={
            "tool_id": tool_id,
            "tool_name": tool_data["name"],
            "category": tool_data.get("category", "general"),
            "collection": "tools"
        },
        collection_name="tools"
    )
    return qresult

def find_similar_tools(query: str, limit: int = 5, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find similar tools in Qdrant based on semantic similarity.
    """
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url or not qdrant_api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in env")
    
    qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)
    
    # Generate embedding for the query
    query_embedding = create_embeddings_for_texts([query], model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    
    if not query_embedding:
        return []
    
    try:
        # Search in tools collection
        search_result = qclient.search(
            collection_name="tools",
            query_vector=query_embedding[0],
            limit=limit,
            score_threshold=similarity_threshold
        )
        
        similar_tools = []
        for result in search_result:
            if result.score >= similarity_threshold:
                # Get tool details from MongoDB
                tool_id = result.payload.get("tool_id")
                if tool_id:
                    tool_doc = tools_collection.find_one({"_id": ObjectId(tool_id)})
                    if tool_doc:
                        tool_info = {
                            "tool_id": str(tool_doc["_id"]),
                            "name": tool_doc["name"],
                            "description": tool_doc["description"],
                            "price": tool_doc["price"],
                            "risk_factors": tool_doc["risk_factors"],
                            "safety_measures": tool_doc["safety_measures"],
                            "image_link": tool_doc.get("image_link"),
                            "amazon_link": tool_doc.get("amazon_link"),
                            "category": tool_doc.get("category"),
                            "similarity_score": result.score,
                            "usage_count": tool_doc.get("usage_count", 0)
                        }
                        similar_tools.append(tool_info)
        
        return similar_tools
        
    except Exception as e:
        print(f"Error searching tools in Qdrant: {e}")
        return []

def process_tools_with_reuse(tools_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process a list of tools, reusing existing ones when possible and storing new ones.
    """
    processed_tools = []
    
    for tool in tools_list:
        # Search for similar existing tools
        similar_tools = find_similar_tools(tool["name"], limit=3, similarity_threshold=0.8)
        
        if similar_tools and similar_tools[0]["similarity_score"] >= 0.8:
            # Reuse existing tool
            existing_tool = similar_tools[0]
            tool["image_link"] = existing_tool["image_link"]
            tool["amazon_link"] = existing_tool["amazon_link"]
            tool["reused_from"] = existing_tool["tool_id"]
            
            # Update usage count
            update_tool_usage(existing_tool["tool_id"])
            
            print(f"Reused existing tool: {tool['name']} (ID: {existing_tool['tool_id']})")
        else:
            # Store new tool
            tool_id = store_tool_in_database(tool)
            tool["tool_id"] = tool_id
            
            # Store embeddings
            create_and_store_tool_embeddings(tool, tool_id)
            
            print(f"Stored new tool: {tool['name']} (ID: {tool_id})")
        
        processed_tools.append(tool)
    
    return processed_tools

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

@router.post("/start", response_model=ChatSession)
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

# Tools Management Endpoints
@router.post("/tools/search")
async def search_tools(search_request: ToolSearchRequest):
    """
    Search for tools using semantic similarity.
    """
    try:
        similar_tools = find_similar_tools(
            query=search_request.query,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold
        )
        
        return {
            "query": search_request.query,
            "tools_found": len(similar_tools),
            "tools": similar_tools
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool search failed: {str(e)}")

@router.get("/tools/{tool_id}")
async def get_tool_details(tool_id: str):
    """
    Get detailed information about a specific tool.
    """
    try:
        tool_doc = tools_collection.find_one({"_id": ObjectId(tool_id)})
        if not tool_doc:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        return {
            "tool_id": str(tool_doc["_id"]),
            "name": tool_doc["name"],
            "description": tool_doc["description"],
            "price": tool_doc["price"],
            "risk_factors": tool_doc["risk_factors"],
            "safety_measures": tool_doc["safety_measures"],
            "image_link": tool_doc.get("image_link"),
            "amazon_link": tool_doc.get("amazon_link"),
            "category": tool_doc.get("category"),
            "tags": tool_doc.get("tags", []),
            "usage_count": tool_doc.get("usage_count", 0),
            "created_at": tool_doc.get("created_at"),
            "last_used": tool_doc.get("last_used")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tool details: {str(e)}")

@router.get("/tools")
async def list_tools(
    category: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    sort_by: str = "usage_count"
):
    """
    List tools with optional filtering and sorting.
    """
    try:
        # Build query
        query = {}
        if category:
            query["category"] = category
        
        # Build sort
        sort_field = sort_by if sort_by in ["usage_count", "created_at", "last_used", "name"] else "usage_count"
        sort_direction = DESCENDING if sort_field in ["usage_count", "created_at", "last_used"] else 1
        
        # Execute query
        cursor = tools_collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
        
        tools = []
        for doc in cursor:
            tools.append({
                "tool_id": str(doc["_id"]),
                "name": doc["name"],
                "description": doc["description"],
                "price": doc["price"],
                "category": doc.get("category"),
                "image_link": doc.get("image_link"),
                "usage_count": doc.get("usage_count", 0),
                "created_at": doc.get("created_at")
            })
        
        # Get total count
        total_count = tools_collection.count_documents(query)
        
        return {
            "tools": tools,
            "total_count": total_count,
            "limit": limit,
            "skip": skip,
            "has_more": (skip + limit) < total_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")

@router.post("/tools/process")
async def process_tools_for_reuse(tools_data: List[Tool]):
    """
    Process a list of tools, reusing existing ones when possible.
    This endpoint can be called after LLM generates tools to optimize storage and reuse.
    """
    try:
        # Convert Pydantic models to dictionaries
        tools_list = [tool.model_dump() for tool in tools_data]
        
        # Process tools with reuse logic
        processed_tools = process_tools_with_reuse(tools_list)
        
        return {
            "message": "Tools processed successfully",
            "total_tools": len(processed_tools),
            "reused_tools": len([t for t in processed_tools if "reused_from" in t]),
            "new_tools": len([t for t in processed_tools if "reused_from" not in t]),
            "tools": processed_tools
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process tools: {str(e)}")

@router.delete("/tools/{tool_id}")
async def delete_tool(tool_id: str):
    """
    Delete a tool from both MongoDB and Qdrant.
    """
    try:
        # Delete from MongoDB
        result = tools_collection.delete_one({"_id": ObjectId(tool_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        # Delete from Qdrant (you might want to implement this)
        # For now, we'll just return success
        return {"message": "Tool deleted successfully", "tool_id": tool_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete tool: {str(e)}")

@router.get("/tools/stats")
async def get_tools_statistics():
    """
    Get statistics about the tools collection.
    """
    try:
        total_tools = tools_collection.count_documents({})
        
        # Category distribution
        category_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        category_stats = list(tools_collection.aggregate(category_pipeline))
        
        # Most used tools
        most_used = list(tools_collection.find().sort("usage_count", DESCENDING).limit(5))
        most_used_formatted = []
        for tool in most_used:
            most_used_formatted.append({
                "name": tool["name"],
                "usage_count": tool.get("usage_count", 0),
                "category": tool.get("category")
            })
        
        # Recent tools
        recent_tools = list(tools_collection.find().sort("created_at", DESCENDING).limit(5))
        recent_formatted = []
        for tool in recent_tools:
            recent_formatted.append({
                "name": tool["name"],
                "created_at": tool.get("created_at"),
                "category": tool.get("category")
            })
        
        return {
            "total_tools": total_tools,
            "category_distribution": category_stats,
            "most_used_tools": most_used_formatted,
            "recent_tools": recent_formatted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tools statistics: {str(e)}")
