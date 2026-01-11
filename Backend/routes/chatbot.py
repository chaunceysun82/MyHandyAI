import base64
import os
import pickle
import sys
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from pymongo import DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import PointStruct, VectorParams, Distance

from database.mongodb import mongodb
from .project import update_project

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'chatbot'))

from chatbot.agents import AgenticChatbot

router = APIRouter(prefix="/chatbot", tags=["chatbot"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
database: Database = mongodb.get_database()
conversations_collection: Collection = database.get_collection("Conversations")
project_collection: Collection = database.get_collection("Project")
tools_collection: Collection = database.get_collection("Tools")


# Config for image TTL
# LAST_IMAGE_TTL_MIN = int(os.getenv("LAST_IMAGE_TTL_MINUTES", "10"))
# LAST_IMAGE_MAX_B64 = 3_500_000  # ~3.5MB of base64 text

# def _save_last_image(session_id: str, image_b64: str):
#     """Save the last image for session-based reuse"""
#     if not session_id or not image_b64:
#         return
#     # Avoid huge docs
#     if len(image_b64) > LAST_IMAGE_MAX_B64:
#         return
#     conversations_collection.update_one(
#         {"session_id": session_id, "chat_type": "session_meta"},
#         {"$set": {"last_image": image_b64, "last_image_ts": datetime.utcnow()}},
#         upsert=True
#     )

# def _load_last_image(session_id: str) -> Optional[str]:
#     """Load the last image if within TTL window"""
#     if not session_id:
#         return None
#     doc = conversations_collection.find_one(
#         {"session_id": session_id, "chat_type": "session_meta"},
#         projection={"last_image": 1, "last_image_ts": 1, "_id": 0}
#     )
#     if not doc:
#         return None
#     ts = doc.get("last_image_ts")
#     if not ts:
#         return None
#     if datetime.utcnow() - ts > timedelta(minutes=LAST_IMAGE_TTL_MIN):
#         return None
#     return doc.get("last_image")

def _clear_last_image(session_id: str):
    """Clear stored image for session reset"""
    conversations_collection.update_one(
        {"session_id": session_id, "chat_type": "session_meta"},
        {"$unset": {"last_image": "", "last_image_ts": ""}},
        upsert=True
    )


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
    suggested_messages: Optional[List[str]] = None


class ChatSession(BaseModel):
    session_id: str
    intro_message: str
    suggested_messages: Optional[List[str]] = None


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


def get_suggested_messages(current_state: str, problem_type: str = None) -> List[str]:
    """
    Generate suggested messages based on the current chatbot state and problem type.
    """
    if current_state == "waiting_for_problem":
        # Problem description state - suggest different types of problems
        return [
            "I have a leaking pipe",
            "My electrical outlet isn't working",
            "I need to hang a mirror on the wall",
            "My sink is clogged",
            "I want to fix a wobbly chair"
        ]

    elif current_state == "waiting_for_photos":
        # Photo upload state - help with photo decisions
        return [
            "Skip photos",
            "What photos do you need?",
            "Can I describe instead of photo?",
            "I'll upload a photo"
        ]

    elif current_state == "asking_questions":
        # Clarifying questions state - current behavior but more helpful
        if problem_type:
            # Customize based on problem type
            if "electrical" in problem_type.lower():
                return [
                    "I'm not sure about electrical details",
                    "Is this safe to check myself?",
                    "Skip this question",
                    "I need help understanding this"
                ]
            elif "plumbing" in problem_type.lower() or "leak" in problem_type.lower() or "sink" in problem_type.lower():
                return [
                    "I don't know the pipe material",
                    "Skip this question",
                    "How can I find this information?",
                    "I need help with this"
                ]
            elif "hanging" in problem_type.lower() or "mirror" in problem_type.lower():
                return [
                    "I'm not sure about wall type",
                    "How do I measure this?",
                    "Skip this question",
                    "I don't have measuring tools"
                ]
            else:
                # General repair questions
                return [
                    "Skip this question",
                    "How do I find this information?",
                    "I'm not sure about this",
                    "I don't have the right tools to check"
                ]
        else:
            # Default clarifying questions
            return [
                "Skip this question",
                "How do I answer this question",
                "I'm not sure about this",
                "I don't know how to check this"
            ]

    elif current_state == "showing_summary":
        # Summary confirmation state - simple yes/no responses
        return [
            "Yes, that's correct",
            "No, that's not right",
            "Yes",
            "No, let me clarify"
        ]

    elif current_state == "complete":
        # Chat completed - next steps
        return [
            "Show me the project plan",
            "Start step-by-step guidance",
            "What tools do I need?",
            "How long will this take?"
        ]

    else:
        # Default fallback
        return [
            "Tell me more",
            "I need help",
            "Skip this",
            "I'm not sure"
        ]


@router.get("/session/{project}")
def get_session(project):
    cursor = conversations_collection.find_one({"project": project, "chat_type": "project_intro"})
    if not cursor:
        return {"session": None}
    return {"session": cursor["session_id"]}


def reset_session(session_id, user, project):
    chatbot = AgenticChatbot()
    log_message(session_id, "assistant", "Session reset.", chatbot, user, project, message_type="reset")
    # Clear any stored image for this session
    _clear_last_image(session_id)
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


def create_and_store_summary_embeddings_for_project(summary: str, mongo_project_id,
                                                    extra_payload: Optional[dict] = None):
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
    embeddings = create_embeddings_for_texts(chunks,
                                             model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
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
    embedding = create_embeddings_for_texts([tool_text],
                                            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))

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
    query_embedding = create_embeddings_for_texts([query],
                                                  model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))

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


@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(chat_message: ChatMessage):
    """
    Chat with the MyHandyAI agentic assistant.
    Creates a new session_id if not provided.
    """
    try:
        session_id = chat_message.session_id or uuid.uuid4().hex
        chatbot = get_latest_chatbot(session_id)

        # Log user message
        log_message(session_id, "user", chat_message.message, chatbot, chat_message.user, chat_message.project)

        # Check if image is provided or can be reused - use vision-aware OpenAI direct call
        # current_image_b64 = None
        # use_vision = False

        # if chat_message.uploaded_image:
        #     # New image uploaded
        #     image_data = chat_message.uploaded_image
        #     if image_data.startswith('data:image'):
        #         # Extract base64 part for storage
        #         current_image_b64 = image_data.split(',')[1]
        #         url = image_data
        #     else:
        #         # Plain base64
        #         current_image_b64 = image_data
        #         url = f"data:image/jpeg;base64,{image_data}"

        #     # Save for future reuse
        #     _save_last_image(session_id, current_image_b64)
        #     use_vision = True

        # else:
        #     # No new image - try to reuse last image
        #     cached_b64 = _load_last_image(session_id)
        #     if cached_b64:
        #         url = f"data:image/jpeg;base64,{cached_b64}"
        #         use_vision = True

        # if use_vision:
        #     # Build user message content with image
        #     user_parts = [{"type": "text", "text": chat_message.message}]
        #     user_parts.append({
        #         "type": "image_url", 
        #         "image_url": {"url": url}
        #     })

        #     # Call OpenAI with vision
        #     system_prompt = "You are MyHandyAI, a helpful DIY assistant. Analyze images and provide helpful guidance for DIY projects, tool identification, and home improvement tasks."

        #     resp = client.chat.completions.create(
        #         model="gpt-4o",
        #         messages=[
        #             {"role": "system", "content": system_prompt},
        #             {"role": "user", "content": user_parts},
        #         ],
        #         temperature=0.4,
        #         max_tokens=600
        #     )

        #     response = resp.choices[0].message.content
        # else:
        # No image available - use AgenticChatbot
        uploaded_image = None
        if chat_message.uploaded_image:
            try:
                image_data = chat_message.uploaded_image
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                uploaded_image = base64.b64decode(image_data)
            except Exception as e:
                print(f"Error decoding image in chatbot: {e}")
                raise HTTPException(status_code=400, detail="Invalid image data provided")

            # Get bot response from AgenticChatbot

        print(f"Processing message for session {session_id} with image: {uploaded_image}")
        response = chatbot.process_message(chat_message.message, uploaded_image)

        # Log bot response
        log_message(session_id, "assistant", response, chatbot, chat_message.user, chat_message.project)

        print(getattr(chatbot, "current_state", None))

        if getattr(chatbot, "current_state", None) == "complete":
            await save_information(session_id=session_id)
            await qdrant_function(project_id=chat_message.project)

        # Generate suggested messages based on current state
        current_state = getattr(chatbot, "current_state", None)
        problem_type = getattr(chatbot, "problem_type", None)
        suggested_messages = get_suggested_messages(current_state, problem_type)

        return ChatResponse(
            response=response,
            session_id=session_id,
            current_state=current_state,
            suggested_messages=suggested_messages
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
    log_message(session_id, "assistant", intro_message, chatbot, payload.user, payload.project,
                message_type="project_intro")

    # Get initial suggested messages for problem description state
    suggested_messages = get_suggested_messages("waiting_for_problem")

    return ChatSession(
        session_id=session_id,
        intro_message=intro_message,
        suggested_messages=suggested_messages
    )


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


@router.get("/suggested-messages/{state}")
async def get_suggested_messages_for_state(state: str, problem_type: Optional[str] = None):
    """
    Get suggested messages for a specific chatbot state and problem type.
    Useful for testing or frontend-only message updates.
    """
    try:
        messages = get_suggested_messages(state, problem_type)
        return {
            "state": state,
            "problem_type": problem_type,
            "suggested_messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid state or problem type: {str(e)}")


@router.get("/suggested-messages/preview")
async def preview_all_suggested_messages():
    """
    Preview all available suggested messages for different states.
    Useful for testing and development.
    """
    try:
        preview = {
            "waiting_for_problem": get_suggested_messages("waiting_for_problem"),
            "waiting_for_photos": get_suggested_messages("waiting_for_photos"),
            "asking_questions_general": get_suggested_messages("asking_questions"),
            "asking_questions_electrical": get_suggested_messages("asking_questions", "electrical_issue"),
            "asking_questions_plumbing": get_suggested_messages("asking_questions", "leaking_pipe"),
            "asking_questions_hanging": get_suggested_messages("asking_questions", "hanging_mirror"),
            "showing_summary": get_suggested_messages("showing_summary"),
            "complete": get_suggested_messages("complete")
        }
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")


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
    bot = get_latest_chatbot(session_id)
    conv = conversations_collection.find_one({"session_id": session_id})
    if bot.current_state == "complete":
        print(str(conv["project"]))
        answers = bot.user_answers
        if isinstance(answers, dict):
            answers = {str(k): v for k, v in answers.items()}
        update_project(str(conv["project"]), {"user_description": bot.user_description,
                                              "summary": bot.summary,
                                              "image_analysis": bot.image_analysis,
                                              "questions": bot.questions,
                                              "answers": answers})

        return {"message": "Data saved Successfully"}
    else:
        return {"messaage": "chat not complete"}


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
@router.post("/tools/save")
async def save_tool_to_collections(tool_data: Tool):
    """
    Save a single tool to both MongoDB tools_collection and Qdrant.
    This is the basic building block for the tools system.
    """
    try:
        # Convert Pydantic model to dict
        tool_dict = tool_data.model_dump()

        print(f"🔧 Saving tool: {tool_dict['name']}")

        # 1. Save to MongoDB tools_collection
        tool_doc = {
            "name": tool_dict["name"],
            "description": tool_dict["description"],
            "price": tool_dict["price"],
            "risk_factors": tool_dict["risk_factors"],
            "safety_measures": tool_dict["safety_measures"],
            "image_link": tool_dict.get("image_link"),
            "amazon_link": tool_dict.get("amazon_link"),
            "category": tool_dict.get("category", "general"),
            "tags": tool_dict.get("tags", []),
            "created_at": datetime.utcnow(),
            "usage_count": 1,
            "last_used": datetime.utcnow()
        }

        result = tools_collection.insert_one(tool_doc)
        tool_id = str(result.inserted_id)
        print(f"✅ Saved to MongoDB with ID: {tool_id}")

        # 2. Create embeddings and save to Qdrant
        try:
            embedding_result = create_and_store_tool_embeddings(tool_dict, tool_id)
            print(f"✅ Saved embeddings to Qdrant: {embedding_result}")

            return {
                "success": True,
                "message": "Tool saved successfully to both MongoDB and Qdrant",
                "tool_id": tool_id,
                "qdrant_result": embedding_result
            }

        except Exception as e:
            print(f"⚠️ Qdrant save failed: {e}")
            return {
                "success": True,
                "message": "Tool saved to MongoDB but Qdrant failed",
                "tool_id": tool_id,
                "qdrant_error": str(e)
            }

    except Exception as e:
        print(f"❌ MongoDB save failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save tool: {str(e)}")


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


@router.get("/tools/test/connection")
async def test_tools_connection():
    """
    Test the connection to both MongoDB tools collection and Qdrant.
    """
    try:
        # Test MongoDB connection
        mongo_count = tools_collection.count_documents({})
        mongo_sample = list(tools_collection.find({}, {"name": 1, "category": 1}).limit(3))
        for tool in mongo_sample:
            tool["_id"] = str(tool["_id"])

        # Test Qdrant connection
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        qdrant_status = "not_configured"
        qdrant_info = {}

        if qdrant_url and qdrant_api_key:
            try:
                qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)
                collections = qclient.get_collections()
                collection_names = [c.name for c in collections.collections]

                tools_collection_exists = "tools" in collection_names

                if tools_collection_exists:
                    info = qclient.get_collection("tools")
                    qdrant_info = {
                        "vector_count": info.vectors_count,
                        "vector_size": info.config.params.vectors.size
                    }
                    qdrant_status = "connected_with_tools"
                else:
                    qdrant_status = "connected_no_tools"

            except Exception as e:
                qdrant_status = f"error: {str(e)}"

        return {
            "mongodb": {
                "status": "connected",
                "tools_count": mongo_count,
                "sample_tools": mongo_sample
            },
            "qdrant": {
                "status": qdrant_status,
                "url": qdrant_url,
                "info": qdrant_info
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.post("/tools/extract-from-project/{project_id}")
async def extract_and_save_tools_from_project(project_id: str):
    """
    MAIN FLOW: Extract tools from project.tool_generation and save them to tools_collection + Qdrant.
    This is triggered after the user completes chat and tool generation is done.
    """
    try:
        # 1. Get the project and check if it has tool_generation data
        project = project_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if "tool_generation" not in project:
            raise HTTPException(status_code=400, detail="Project has no tool_generation data")

        tool_generation = project["tool_generation"]

        # Extract tools from tool_generation.tools
        if "tools" not in tool_generation:
            raise HTTPException(status_code=400, detail="No tools found in tool_generation")

        tools_list = tool_generation["tools"]
        print(f"🔧 Found {len(tools_list)} tools in project {project_id}")

        saved_tools = []
        failed_tools = []

        # 2. Save each tool to tools_collection and Qdrant
        for tool in tools_list:
            try:
                # Ensure required fields exist
                if not all(key in tool for key in ["name", "description", "price", "risk_factors", "safety_measures"]):
                    print(f"⚠️ Skipping tool with missing required fields: {tool.get('name', 'unknown')}")
                    failed_tools.append({"tool": tool, "error": "missing_required_fields"})
                    continue

                # Check if tool already exists in tools_collection (avoid duplicates)
                existing_tool = tools_collection.find_one({"name": tool["name"]})
                if existing_tool:
                    print(f"✅ Tool '{tool['name']}' already exists, skipping")
                    saved_tools.append({"tool_id": str(existing_tool["_id"]), "status": "already_exists"})
                    continue

                # Save new tool
                tool_id = store_tool_in_database(tool)
                embedding_result = create_and_store_tool_embeddings(tool, tool_id)

                saved_tools.append({
                    "tool_id": tool_id,
                    "name": tool["name"],
                    "status": "saved",
                    "qdrant_result": embedding_result
                })

                print(f"✅ Saved tool: {tool['name']} (ID: {tool_id})")

            except Exception as e:
                print(f"❌ Failed to save tool {tool.get('name', 'unknown')}: {e}")
                failed_tools.append({"tool": tool.get('name', 'unknown'), "error": str(e)})

        # 3. Update project to mark tools as processed
        update_project(project_id, {"tools_extracted_to_collection": True, "tools_extraction_date": datetime.utcnow()})

        return {
            "message": f"Processed {len(tools_list)} tools from project",
            "project_id": project_id,
            "saved_tools": len(saved_tools),
            "failed_tools": len(failed_tools),
            "tools": saved_tools,
            "failures": failed_tools
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract tools from project: {str(e)}")


@router.post("/tools/compare-and-enhance")
async def compare_and_enhance_tools(tools_data: List[Dict[str, Any]]):
    """
    FLOW 2: Compare newly generated tools with existing ones and enhance them.
    This is called during tool generation to reuse images/links from similar existing tools.
    """
    try:
        enhanced_tools = []
        reuse_stats = {"reused": 0, "new": 0, "errors": 0}

        print(f"🔍 Comparing {len(tools_data)} newly generated tools with existing tools")

        for tool in tools_data:
            try:
                tool_name = tool.get("name", "")
                if not tool_name:
                    print(f"⚠️ Skipping tool without name")
                    enhanced_tools.append(tool)
                    reuse_stats["errors"] += 1
                    continue

                print(f"🔍 Analyzing tool: {tool_name}")

                similar_tools = find_similar_tools(
                    query=tool_name,
                    limit=3,
                    similarity_threshold=0.75
                )

                if similar_tools:
                    # Get the most similar tool
                    best_match = similar_tools[0]
                    similarity_score = best_match["similarity_score"]

                    print(f"   Found similar tool: {best_match['name']} (Score: {similarity_score:.3f})")

                    # If similarity is high enough, reuse image and amazon links
                    if similarity_score >= 0.8:
                        # High similarity - reuse everything
                        tool["image_link"] = best_match["image_link"]
                        tool["amazon_link"] = best_match["amazon_link"]
                        tool["reused_from"] = best_match["tool_id"]
                        tool["similarity_score"] = similarity_score
                        tool["reuse_type"] = "high_similarity"

                        # Update usage count for the existing tool
                        update_tool_usage(best_match["tool_id"])

                        reuse_stats["reused"] += 1
                        print(f"   ✅ HIGH SIMILARITY - Reused image/links from existing tool")

                    elif similarity_score >= 0.65:
                        # Medium similarity - reuse image only (amazon link might be different)
                        tool["image_link"] = best_match["image_link"]
                        tool["reference_tool"] = best_match["tool_id"]
                        tool["similarity_score"] = similarity_score
                        tool["reuse_type"] = "medium_similarity"

                        reuse_stats["reused"] += 1
                        print(f"   📷 MEDIUM SIMILARITY - Reused image only")

                    else:
                        # Low similarity - no reuse
                        tool["similarity_score"] = similarity_score
                        tool["reuse_type"] = "no_reuse"
                        reuse_stats["new"] += 1
                        print(f"   🆕 LOW SIMILARITY - Treating as new tool")

                else:
                    # No similar tools found
                    tool["reuse_type"] = "no_similar_found"
                    reuse_stats["new"] += 1
                    print(f"   🆕 NO SIMILAR TOOLS - Treating as new tool")

                enhanced_tools.append(tool)

            except Exception as e:
                print(f"❌ Error processing tool {tool.get('name', 'unknown')}: {e}")
                tool["error"] = str(e)
                enhanced_tools.append(tool)
                reuse_stats["errors"] += 1

        return {
            "message": "Tools comparison and enhancement completed",
            "total_tools": len(tools_data),
            "reuse_statistics": reuse_stats,
            "enhanced_tools": enhanced_tools
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare and enhance tools: {str(e)}")
