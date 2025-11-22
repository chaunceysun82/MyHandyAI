from uuid import UUID

from fastapi import APIRouter, status
from loguru import logger

from information_gathering_agent.dependencies import InformationGatheringAgentServiceDependency
from routes.schemas.request.information_gathering_agent import ChatMessageRequest
from routes.schemas.request.information_gathering_agent import InitializeConversationRequest
from routes.schemas.response.information_gathering_agent import InitializeConversationResponse, \
    ChatMessageResponse

router = APIRouter(prefix="/information-gathering-agent")


@router.post("/initialize", response_model=InitializeConversationResponse, status_code=status.HTTP_200_OK)
async def initialize_conversation(
        request: InitializeConversationRequest,
        orchestrator: InformationGatheringAgentServiceDependency
) -> InitializeConversationResponse:
    """Initialize a new conversation with the information gathering agent."""
    logger.info(f"initialize_conversation called for project_id: {request.project_id}")

    thread_id, initial_message = orchestrator.initialize_conversation(project_id=request.project_id)

    return InitializeConversationResponse(
        thread_id=thread_id,
        initial_message=initial_message
    )


@router.post("/chat/{thread_id}", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
async def chat(
        thread_id: UUID,
        request: ChatMessageRequest,
        orchestrator: InformationGatheringAgentServiceDependency
) -> ChatMessageResponse:
    """Send a chat message to the information gathering agent."""
    logger.info(f"chat called with thread_id: {thread_id}, project_id: {request.project_id}")

    agent_response = orchestrator.process_message(
        thread_id=thread_id,
        project_id=request.project_id,
        text=request.text,
        image_base64=request.image_base64,
        image_mime_type=request.image_mime_type
    )

    return ChatMessageResponse(
        thread_id=thread_id,
        agent_response=agent_response
    )
