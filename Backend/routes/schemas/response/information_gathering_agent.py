from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class InitializeConversationResponse(BaseModel):
    """Response from initializing a conversation."""
    thread_id: UUID = Field(..., description="Thread ID for the conversation")
    initial_message: str = Field(..., description="Initial agent greeting message")


class ChatMessageResponse(BaseModel):
    """Response to a chat message."""
    thread_id: UUID = Field(..., description="Thread ID for the conversation")
    agent_response: str = Field(..., description="Agent's response message")

class HistoryMessage(BaseModel):
    role: str
    content: str

class ConversationHistoryResponse(BaseModel):
    thread_id: UUID = Field(..., description="Thread ID for the conversation")
    messages: List[HistoryMessage]