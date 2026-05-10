from typing import Optional, List
from pydantic import BaseModel


class AnchorObject(BaseModel):
    """A single anchor object image generated from the project summary."""
    name: str                        # e.g. "mirror", "wall", "sink"
    description: str                 # what was prompted
    s3_key: str
    url: Optional[str] = None
    status: str = "complete"


class AnchorObjectsResult(BaseModel):
    """All anchor object images for a project."""
    objects: List[AnchorObject] = []
    status: str = "complete"

    
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
    state_summary: Optional[str] = None    # ← NEW: memory for future steps
    status: str = "complete"
