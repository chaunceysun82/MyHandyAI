"""Utility functions for Image Generation Agent."""

import io
import re
import time
from typing import Optional

import requests
from PIL import Image


def map_size_to_aspect(size_str: str) -> str:
    try:
        w, h = [int(x) for x in size_str.lower().split("x")]
        ar = w / h
        if 1.66 <= ar <= 1.90:
            return "16:9"
        if 1.25 <= ar < 1.66:
            return "4:3"
        if 0.90 <= ar < 1.25:
            return "1:1"
        if 0.75 <= ar < 0.90:
            return "3:4"
        return "9:16"
    except Exception:
        return "16:9"


def png_to_bytes_ensure_rgba(png_bytes: bytes) -> bytes:
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()


def generate_s3_key(step_id: str, project_id: Optional[str]) -> str:
    ts = int(time.time())
    base = f"project_{project_id or 'na'}/steps/{step_id}"
    return f"{base}/image_{ts}.png"


def get_public_url(key: str, public_base: Optional[str]) -> Optional[str]:
    if public_base:
        return f"{public_base.rstrip('/')}/{key}"
    return None


# ─── Style lock ──────────────────────────────────────────────────────────────

def extract_style_lock(openai_api_key: str, step1_prompt: str) -> str:
    """
    Call GPT once after step 1 to extract a reusable style lock string.
    This is a short, precise descriptor of every visual constant in the scene.
    It is prepended verbatim to ALL subsequent Imagen prompts for this project.

    Example output:
        "white shaker-style under-sink cabinet, grey stone countertop,
         stainless steel drop-in sink, white PVC P-trap pipes, blue nitrile
         gloves, warm natural lighting from upper-left, eye-level medium shot,
         grey painted drywall background"
    """
    payload = {
        "model": "gpt-5-nano",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a visual consistency assistant for an image generation pipeline. "
                    "Given an Imagen prompt, extract ONLY the static scene descriptors — "
                    "the elements that must stay identical across all steps of the project. "
                    "Output a single comma-separated string of 15-25 words. "
                    "Include: cabinet style+colour, countertop material+colour, sink type, "
                    "pipe material+colour, glove colour+type, lighting direction+tone, "
                    "camera angle, wall/floor material. "
                    "Do NOT include actions, tools being used, or step-specific details. "
                    "Output ONLY the descriptor string, nothing else."
                ),
            },
            {
                "role": "user",
                "content": f"Extract the style lock from this prompt:\n\n{step1_prompt}",
            },
        ],
        "max_completion_tokens": 120,
        "reasoning_effort": "low",
    }
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai_api_key}"},
            json=payload,
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""
