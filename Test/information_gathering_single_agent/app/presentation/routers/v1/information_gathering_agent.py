from fastapi import APIRouter, status
from loguru import logger

from presentation.dependencies import InformationGatheringAgentServiceDependency
from presentation.schemas.request.information_gathering_agent import ChatMessageRequest
from presentation.schemas.response.information_gathering_agent import InitializeConversationResponse, \
    ChatMessageResponse

router = APIRouter(prefix="/information-gathering-agent")


@router.post("/initialize", response_model=InitializeConversationResponse, status_code=status.HTTP_200_OK)
async def initialize_conversation(
        orchestrator: InformationGatheringAgentServiceDependency
) -> InitializeConversationResponse:
    """Initialize a new conversation with the information gathering agent."""
    logger.info("initialize_conversation called")

    thread_id, initial_message = orchestrator.initialize_conversation()

    return InitializeConversationResponse(
        thread_id=thread_id,
        initial_message=initial_message
    )


@router.post("/chat", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
async def chat(
        request: ChatMessageRequest,
        orchestrator: InformationGatheringAgentServiceDependency
) -> ChatMessageResponse:
    """Send a chat message to the information gathering agent."""
    logger.info(f"chat called with thread_id: {request.thread_id}")

    agent_response = orchestrator.process_message(
        thread_id=request.thread_id,
        text=request.text,
        image_base64=request.image_base64,
        image_mime_type=request.image_mime_type
    )

    return ChatMessageResponse(
        thread_id=request.thread_id,
        agent_response=agent_response
    )
