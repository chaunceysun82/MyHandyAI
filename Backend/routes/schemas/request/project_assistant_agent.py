from pydantic import BaseModel, Field


class InitializeConversationRequest(BaseModel):
    """Request to initialize a conversation with the project assistant agent."""
    thread_id: str = Field(..., description="Existing thread ID from information gathering agent")
    project_id: str = Field(..., description="Project ID associated with this conversation")
    step_number: int | None = Field(None, description="Current step number (-1 for overview, 0 for tools, >=1 for specific step)")


class ChatMessageRequest(BaseModel):
    """Request to send a chat message to the project assistant agent."""
    project_id: str = Field(..., description="Project ID associated with this conversation")
    text: str | None = Field(None, description="Text message from user")
    image_base64: str | None = Field(None, description="Base64-encoded image")
    image_mime_type: str | None = Field(None, description="MIME type of the image (e.g., 'image/jpeg')")
    step_number: int | None = Field(None, description="Current step number (-1 for overview, 0 for tools, >=1 for specific step)")
