from pydantic import BaseModel, Field


class InitializeConversationRequest(BaseModel):
    """Request to initialize a new conversation."""
    pass


class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""
    thread_id: str = Field(..., description="Thread ID for conversation persistence")
    text: str | None = Field(None, description="Text message from user")
    image_base64: str | None = Field(None, description="Base64-encoded image")
    image_mime_type: str | None = Field(None, description="MIME type of the image (e.g., 'image/jpeg')")
