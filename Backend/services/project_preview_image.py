import base64
import time
from typing import Optional
from uuid import uuid4

import boto3
import requests
from bson import ObjectId
from loguru import logger
from openai import OpenAI
from pymongo.collection import Collection

from config.settings import get_settings
from database.mongodb import mongodb


MODEL = "gpt-image-2"


def _public_url(key: str, public_base: Optional[str]) -> Optional[str]:
    if not public_base:
        return None
    return f"{public_base.rstrip('/')}/{key}"


def _build_preview_prompt(project: dict, prefer_draft: bool = False) -> str:
    title = project.get("projectTitle") or "DIY project"
    draft = project.get("summary_preview") or {}
    summary = (
        draft.get("summary")
        if prefer_draft and draft.get("summary")
        else project.get("summary") or draft.get("summary") or project.get("user_description") or ""
    )
    hypotheses = (
        draft.get("hypotheses")
        if prefer_draft and draft.get("hypotheses")
        else project.get("hypotheses") or draft.get("hypotheses") or ""
    )
    image_analysis = project.get("image_analysis") or ""

    return f"""
Create a realistic finished-result preview for a home improvement project.

Project title: {title}

Confirmed project summary:
{summary}

Expert hypothesis/context:
{hypotheses}

Visual details gathered from user-uploaded images, if any:
{image_analysis or "No uploaded image analysis was provided."}

Render the likely completed result after a safe, tidy repair or installation. Show the finished outcome clearly in a realistic home environment. Preserve known materials, room type, location, colors, and constraints from the summary. Do not show people, text labels, logos, measurements, unsafe wiring, exposed hazards, or step-by-step instruction diagrams. The image should feel like a polished preview of the final result, not an advertisement.
""".strip()


def _image_bytes_from_response(response) -> bytes:
    first = response.data[0]
    image_b64 = getattr(first, "b64_json", None)
    if image_b64:
        return base64.b64decode(image_b64)

    image_url = getattr(first, "url", None)
    if image_url:
        result = requests.get(image_url, timeout=30)
        result.raise_for_status()
        return result.content

    raise ValueError("OpenAI image response did not include image data")


def ensure_project_preview_image(project_id: str, prefer_draft: bool = False) -> Optional[dict]:
    settings = get_settings()
    projects: Collection = mongodb.get_collection("Project")

    project = projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        logger.warning(f"Cannot generate preview image. Project not found: {project_id}")
        return None

    existing = project.get("result_preview_image") or {}
    if existing.get("url"):
        return existing

    draft = project.get("summary_preview") or {}
    summary = draft.get("summary") if prefer_draft else project.get("summary") or draft.get("summary")
    if not summary:
        logger.warning(f"Cannot generate preview image. Project has no summary: {project_id}")
        return None

    prompt = _build_preview_prompt(project, prefer_draft=prefer_draft)
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        response = client.images.generate(
            model=MODEL,
            prompt=prompt,
            size="1024x1024",
            n=1,
            response_format="b64_json",
        )
        image_bytes = _image_bytes_from_response(response)
    except Exception as exc:
        logger.error(f"Result preview image generation failed for {project_id}: {exc}")
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"result_preview_image.status": "failed", "result_preview_image.error": str(exc)}},
        )
        return None

    key = f"project_{project_id}/generated-images/previews/result_preview_{int(time.time())}_{uuid4().hex}.png"
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType="image/png",
        Metadata={
            "project_id": project_id,
            "source": "information-gathering-result-preview",
            "model": MODEL,
        },
    )

    preview = {
        "status": "complete",
        "model": MODEL,
        "bucket": settings.AWS_S3_BUCKET,
        "key": key,
        "url": _public_url(key, settings.AWS_S3_PUBLIC_BASE),
        "prompt_version": "result-preview-v1",
    }

    projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"result_preview_image": preview}},
    )

    logger.info(f"Stored result preview image for project {project_id}: {key}")
    return preview
