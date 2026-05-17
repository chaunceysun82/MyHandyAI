# utils.py
"""Utility functions for Image Generation Agent."""

import io
import re
import time
from typing import Optional
from uuid import uuid4

from PIL import Image


def map_size_to_aspect(size_str: str) -> str:
    """
    Map "WxH" size string to Gemini 2.5 Flash Image supported aspect ratios.

    Gemini 2.5 Flash Image supported ratios:
        "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"

    Note: Imagen used a different set ("16:9", "4:3", "1:1", "3:4", "9:16").
    Gemini adds "2:3", "4:5", "5:4", "21:9" and drops nothing from Imagen's set.
    """
    try:
        w, h = [int(x) for x in size_str.lower().split("x")]
        ar = w / h

        # Match to nearest supported ratio
        if ar >= 1.8:        # ~21:9 (2.33) or ~16:9 (1.78)
            return "21:9" if ar >= 2.0 else "16:9"
        if ar >= 1.2:        # ~5:4 (1.25) or ~4:3 (1.33)
            return "5:4" if ar < 1.29 else "4:3"
        if 0.95 <= ar < 1.2: # ~1:1
            return "1:1"
        if 0.78 <= ar < 0.95: # ~4:5 (0.80) or ~3:4 (0.75)
            return "4:5" if ar >= 0.78 else "3:4"
        if 0.6 <= ar < 0.78: # ~2:3 (0.67) or ~3:4 (0.75)
            return "2:3" if ar < 0.72 else "3:4"
        return "9:16"        # very tall

    except Exception:
        return "16:9"


def png_to_bytes_ensure_rgba(raw_bytes: bytes) -> bytes:
    """
    Normalize raw image bytes (PNG or JPEG) to RGBA PNG format.
    Gemini 2.5 Flash Image may return JPEG — this normalizes either format.
    """
    im = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def generate_s3_key(step_id: str, project_id: Optional[str]) -> str:
    ts = int(time.time())
    suffix = uuid4().hex
    return (
        f"project_{project_id or 'na'}/generated-images/"
        f"steps/{step_id}/image_{ts}_{suffix}.png"
    )


def generate_anchor_s3_key(project_id: Optional[str], anchor_name: str) -> str:
    ts = int(time.time())
    safe_name = re.sub(r"[^a-zA-Z0-9_.=-]+", "-", anchor_name).strip("-") or "anchor"
    suffix = uuid4().hex
    return (
        f"project_{project_id or 'na'}/generated-images/"
        f"anchors/{safe_name}/anchor_{ts}_{suffix}.png"
    )


def get_public_url(key: str, public_base: Optional[str]) -> Optional[str]:
    if public_base:
        return f"{public_base.rstrip('/')}/{key}"
    return None


def apply_physics_filter(prompt: str, physics_redflags: list[dict]) -> tuple[str, list[str]]:
    """
    Strip clauses matching domain-specific physics red-flag patterns.
    physics_redflags is a list of {"pattern": str, "label": str} from the Visual DNA.
    Returns (cleaned_prompt, list_of_violation_labels_found).
    """
    violations = []
    cleaned = prompt
    for flag in physics_redflags:
        pattern = flag.get("pattern", "")
        label = flag.get("label", "unknown")
        if not pattern:
            continue
        try:
            if re.search(pattern, cleaned, flags=re.IGNORECASE):
                violations.append(label)
                cleaned = re.sub(
                    r'[^.,]*' + pattern + r'[^.,]*[.,]?',
                    '',
                    cleaned,
                    flags=re.IGNORECASE,
                ).strip()
        except re.error:
            continue  # Malformed pattern from GPT — skip silently
    return cleaned, violations
