"""Utility functions for Image Generation Agent."""

import io
import time
from typing import Optional

from PIL import Image


def map_size_to_aspect(size_str: str) -> str:
    """
    Map "WxH" size string to Imagen aspect ratio.
    
    Args:
        size_str: Size string in format "WxH" (e.g., "1536x1024")
        
    Returns:
        Aspect ratio string (e.g., "16:9", "4:3", "1:1", "3:4", "9:16")
    """
    try:
        w, h = [int(x) for x in size_str.lower().split("x")]
        ar = w / h
        if 1.66 <= ar <= 1.90:  # ~16:9
            return "16:9"
        if 1.25 <= ar < 1.66:  # ~4:3
            return "4:3"
        if 0.90 <= ar < 1.25:  # ~1:1
            return "1:1"
        if 0.75 <= ar < 0.90:  # ~3:4
            return "3:4"
        return "9:16"
    except Exception:
        return "16:9"


def png_to_bytes_ensure_rgba(png_bytes: bytes) -> bytes:
    """
    Normalize PNG bytes to RGBA format.
    
    Args:
        png_bytes: Raw PNG bytes
        
    Returns:
        Normalized PNG bytes in RGBA format
    """
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def generate_s3_key(step_id: str, project_id: Optional[str]) -> str:
    """
    Generate S3 key for step image.
    
    Args:
        step_id: Step identifier
        project_id: Project identifier (optional)
        
    Returns:
        S3 key string
    """
    ts = int(time.time())
    base = f"project_{project_id or 'na'}/steps/{step_id}"
    return f"{base}/image_{ts}.png"


def get_public_url(key: str, public_base: Optional[str]) -> Optional[str]:
    """
    Generate public URL from S3 key.
    
    Args:
        key: S3 key
        public_base: Public base URL (e.g., CloudFront URL)
        
    Returns:
        Public URL or None
    """
    if public_base:
        return f"{public_base.rstrip('/')}/{key}"
    return None
