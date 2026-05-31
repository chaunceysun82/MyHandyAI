from uuid import UUID

from bson import ObjectId
from fastapi import APIRouter, Depends, status
from loguru import logger

from agents.information_gathering_agent.dependencies import InformationGatheringAgentServiceDependency
from routes.schemas.request.information_gathering_agent import ChatMessageRequest
from routes.schemas.request.information_gathering_agent import InitializeConversationRequest
from routes.schemas.response.information_gathering_agent import InitializeConversationResponse, \
    ChatMessageResponse, ConversationHistoryResponse, HistoryMessage
from security.current_user import get_current_app_user
from database.enums.project import InformationGatheringConversationStatus
from database.mongodb import mongodb
from services.project_preview_image import ensure_project_preview_image
from services.user_upload_storage import store_user_uploaded_image

router = APIRouter(prefix="/information-gathering-agent")
project_collection = mongodb.get_collection("Project")


@router.post("/initialize", response_model=InitializeConversationResponse, status_code=status.HTTP_200_OK)
async def initialize_conversation(
        request: InitializeConversationRequest,
        orchestrator: InformationGatheringAgentServiceDependency,
        current_user: dict = Depends(get_current_app_user),
) -> InitializeConversationResponse:
    """Initialize a new conversation with the information gathering agent."""
    logger.info(f"initialize_conversation called for project_id: {request.project_id}")

    thread_id, initial_message, conversation_status = orchestrator.initialize_conversation(
        project_id=request.project_id)

    return InitializeConversationResponse(
        thread_id=thread_id,
        initial_message=initial_message,
        conversation_status=conversation_status
    )


@router.post("/chat/{thread_id}", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
async def chat(
        thread_id: UUID,
        request: ChatMessageRequest,
        orchestrator: InformationGatheringAgentServiceDependency,
        current_user: dict = Depends(get_current_app_user),
) -> ChatMessageResponse:
    """Send a chat message to the information gathering agent."""
    logger.info(f"chat called with thread_id: {thread_id}, project_id: {request.project_id}")

    if request.image_base64:
        upload = store_user_uploaded_image(
            image_base64=request.image_base64,
            image_mime_type=request.image_mime_type,
            user_id=current_user.get("id") or current_user.get("sub"),
            project_id=request.project_id,
            thread_id=thread_id,
            source="information-gathering-agent",
        )
        logger.info(f"Stored information gathering upload: {upload['key']}")
        project_collection.update_one(
            {"_id": ObjectId(request.project_id)},
            {"$push": {"information_gathering_uploads": upload}},
        )

    agent_response, conversation_status = orchestrator.process_message(
        thread_id=thread_id,
        project_id=request.project_id,
        text=request.text,
        image_base64=request.image_base64,
        image_mime_type=request.image_mime_type
    )

    preview_image_url = None
    preview_image_status = None
    if conversation_status == InformationGatheringConversationStatus.COMPLETED.value:
        project = project_collection.find_one({"_id": ObjectId(request.project_id)})
        preview = (project or {}).get("result_preview_image") or {}
        preview_image_url = preview.get("url") if preview else None
        preview_image_status = preview.get("status") if preview_image_url else "generating"
        logger.info(
            f"chat preview status project_id={request.project_id} "
            f"conversation_status={conversation_status} preview_status={preview.get('status')} "
            f"has_url={bool(preview_image_url)} stage={preview.get('stage')}"
        )
    else:
        project = project_collection.find_one({"_id": ObjectId(request.project_id)})
        if project and project.get("summary_preview"):
            preview = project.get("result_preview_image") or {}
            preview_image_url = preview.get("url") if preview else None
            preview_image_status = preview.get("status") if preview_image_url else "generating"
            logger.info(
                f"chat draft preview status project_id={request.project_id} "
                f"conversation_status={conversation_status} preview_status={preview.get('status')} "
                f"has_url={bool(preview_image_url)} stage={preview.get('stage')}"
            )

    return ChatMessageResponse(
        thread_id=thread_id,
        agent_response=agent_response,
        conversation_status=conversation_status,
        preview_image_url=preview_image_url,
        preview_image_status=preview_image_status
    )


@router.post("/preview/{project_id}", status_code=status.HTTP_200_OK)
async def generate_project_preview(
        project_id: str,
        current_user: dict = Depends(get_current_app_user),
) -> dict:
    """Generate or fetch the visual result preview for a project."""
    logger.info(f"generate_project_preview called for project_id: {project_id}")
    project = project_collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        logger.warning(f"generate_project_preview project not found project_id={project_id}")
        return {
            "status": "failed",
            "url": None,
            "stage": "project_lookup",
            "error": "Project not found",
        }

    if project and str(project.get("userId")) != str(current_user.get("id")):
        logger.warning(
            f"generate_project_preview user mismatch project_id={project_id} "
            f"project_user={project.get('userId')} current_user={current_user.get('id')}"
        )
        return {
            "status": "failed",
            "url": None,
            "stage": "authorization",
            "error": "Current user does not own this project",
        }

    prefer_draft = bool(project and project.get("summary_preview") and not project.get("summary"))
    logger.info(
        f"generate_project_preview context project_id={project_id} "
        f"prefer_draft={prefer_draft} has_summary={bool(project.get('summary'))} "
        f"has_summary_preview={bool(project.get('summary_preview'))} "
        f"existing_preview_status={(project.get('result_preview_image') or {}).get('status')}"
    )
    preview = ensure_project_preview_image(project_id, prefer_draft=prefer_draft)
    logger.info(
        f"generate_project_preview result project_id={project_id} "
        f"status={(preview or {}).get('status')} has_url={bool((preview or {}).get('url'))} "
        f"stage={(preview or {}).get('stage')}"
    )
    return {
        "status": preview.get("status") if preview else "failed",
        "url": preview.get("url") if preview else None,
        "stage": preview.get("stage") if preview else "unknown",
        "error": preview.get("error") if preview else "Preview generation returned no result",
    }


@router.get("/chat/{thread_id}/history",
            response_model=ConversationHistoryResponse,
            status_code=status.HTTP_200_OK)
async def get_conversation_history(
        thread_id: UUID,
        orchestrator: InformationGatheringAgentServiceDependency,
        current_user: dict = Depends(get_current_app_user),
) -> ConversationHistoryResponse:
    """
    Return full conversation history for a given thread_id.
    """
    logger.info(f"get_conversation_history called with thread_id: {thread_id}")

    history_dicts = orchestrator.get_history(thread_id=thread_id)

    messages = [HistoryMessage(**m) for m in history_dicts]

    return ConversationHistoryResponse(
        thread_id=thread_id,
        messages=messages
    )


@router.get("/thread/{project_id}",
            status_code=status.HTTP_200_OK)
async def get_thread_id(
        project_id: str,
        orchestrator: InformationGatheringAgentServiceDependency,
        current_user: dict = Depends(get_current_app_user),
) -> dict:
    """
    Return existing thread_id and conversation_status for a given project_id, if any.
    """
    logger.info(f"get_thread_id called with project_id: {project_id}")
    return orchestrator.get_thread_id(project_id)
