"""Schemas for Image Generation Agent."""

from typing import Optional, List

from pydantic import BaseModel


class VisualContextFrame(BaseModel):
    """A single frame of visual context from a previously generated step image."""
    step_id: str
    url: str
    prompt_preview: str
    style_anchor: Optional[str] = None   # extracted style descriptor for continuity


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
    style_anchor: Optional[str] = None   # saved back to MongoDB for future steps
    status: str = "complete"
