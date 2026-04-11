from uuid import UUID

from fastapi import APIRouter, status
from loguru import logger

from agents.project_assistant_agent.dependencies import ProjectAssistantAgentServiceDependency
from routes.schemas.request.project_assistant_agent import ChatMessageRequest, InitializeConversationRequest
from routes.schemas.response.project_assistant_agent import ChatMessageResponse, ConversationHistoryResponse, HistoryMessage, InitializeConversationResponse

router = APIRouter(prefix="/project-assistant-agent")


@router.post("/initialize", response_model=InitializeConversationResponse, status_code=status.HTTP_200_OK)
async def initialize_conversation(
        request: InitializeConversationRequest,
        orchestrator: ProjectAssistantAgentServiceDependency
) -> InitializeConversationResponse:
    """Initialize a conversation with the project assistant agent using an existing thread_id."""
    logger.info(f"initialize_conversation called for thread_id: {request.thread_id}, project_id: {request.project_id}, step_number: {request.step_number}")

    thread_id = UUID(request.thread_id)
    initial_message = orchestrator.initialize_conversation(
        thread_id=thread_id,
        project_id=request.project_id,
        step_number=request.step_number
    )

    return InitializeConversationResponse(
        thread_id=thread_id,
        initial_message=initial_message
    )


@router.post("/chat/{thread_id}", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
async def chat(
        thread_id: UUID,
        request: ChatMessageRequest,
        orchestrator: ProjectAssistantAgentServiceDependency
) -> ChatMessageResponse:
    """Send a chat message to the project assistant agent."""
    logger.info(f"chat called with thread_id: {thread_id}, project_id: {request.project_id}, step_number: {request.step_number}")

    agent_response, _ = orchestrator.process_message(
        thread_id=thread_id,
        project_id=request.project_id,
        text=request.text,
        image_base64=request.image_base64,
        image_mime_type=request.image_mime_type,
        step_number=request.step_number
    )

    return ChatMessageResponse(
        thread_id=thread_id,
        agent_response=agent_response
    )


@router.get("/thread/{project_id}",
            status_code=status.HTTP_200_OK)
async def get_thread_id(
        project_id: str,
        orchestrator: ProjectAssistantAgentServiceDependency
) -> dict:
    """
    Return existing thread_id for a given project_id, if any.
    Uses the same thread_id as the information gathering agent since they share the same conversation thread.
    """
    logger.info(f"get_thread_id called with project_id: {project_id}")
    return orchestrator.get_thread_id(project_id)


@router.get("/chat/{thread_id}/history",
            response_model=ConversationHistoryResponse,
            status_code=status.HTTP_200_OK)
async def get_conversation_history(
        thread_id: UUID,
        orchestrator: ProjectAssistantAgentServiceDependency
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
