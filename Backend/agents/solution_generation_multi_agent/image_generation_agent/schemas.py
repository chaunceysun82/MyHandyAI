"""Schemas for Image Generation Agent."""

from typing import Optional

from pydantic import BaseModel


class ImageRequest(BaseModel):
    """Request schema for image generation."""
    step_text: str
    summary_text: Optional[str] = None
    size: str = "1024x1024"
    project_id: str


class ImageGenerationResult(BaseModel):
    """Result schema for image generation."""
    message: str = "ok"
    step_id: str
    project_id: str
    s3_key: str
    url: Optional[str] = None
    size: str
    model: str
    prompt_preview: Optional[str] = None
    status: str = "complete"