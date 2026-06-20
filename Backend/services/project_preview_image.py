import base64
import time
from io import BytesIO
from typing import Optional
from uuid import uuid4

import boto3
import requests
from bson import ObjectId
from loguru import logger
from openai import APITimeoutError, OpenAI, OpenAIError
from pymongo.collection import Collection

from config.settings import get_settings
from database.mongodb import mongodb


MODEL = "gpt-image-2"
OPENAI_IMAGE_TIMEOUT_SECONDS = 25.0
MAX_REFERENCE_IMAGES = 8


def _failed_preview(stage: str, message: str) -> dict:
    return {
        "status": "failed",
        "stage": stage,
        "error": message,
        "model": MODEL,
    }


def _public_url(key: str, public_base: Optional[str]) -> Optional[str]:
    if not public_base:
        return None
    return f"{public_base.rstrip('/')}/{key}"


# ─── NEW: user uploaded image fetching ────────────────────────────────────────

def _fetch_user_uploaded_image_urls(project: dict) -> list[str]:
    """Read user-uploaded image URLs stored on the project document."""
    uploads = project.get("information_gathering_uploads", [])  # ← matches actual route field
    return [u["url"] for u in uploads if u.get("url")]


def _download_image_bytes(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.warning(f"Failed to download reference image {url}: {e}")
        return None


def _prepare_reference_files(urls: list[str]) -> list[tuple]:
    """Download user images and prepare as (filename, bytes_io, content_type) tuples."""
    files = []
    for i, url in enumerate(urls[:MAX_REFERENCE_IMAGES]):
        image_bytes = _download_image_bytes(url)
        if not image_bytes:
            continue
        ext = url.split(".")[-1].lower().split("?")[0]
        content_type = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp",
        }.get(ext, "image/png")
        filename = f"reference_{i}.{ext if ext in ('jpg', 'jpeg', 'png', 'webp') else 'png'}"
        files.append((filename, BytesIO(image_bytes), content_type))
    return files


def _build_preview_prompt(project: dict, prefer_draft: bool = False, has_reference_images: bool = False) -> str:
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

    # NEW: instruction prepended only when reference images are being passed
    reference_instruction = (
        "Reference photos of the user's actual room/object are provided as input images. "
        "Use them as the visual ground truth: preserve the exact room layout, wall colors, "
        "existing fixtures, furniture, and object appearance shown in these photos. "
        "Generate the same space with the repair/installation completed, "
        "keeping everything else in the photos consistent.\n\n"
        if has_reference_images else ""
    )

    return f"""
Create a realistic finished-result preview for a home improvement project.

{reference_instruction}Project title: {title}

Confirmed project summary:
{summary}

Expert hypothesis/context:
{hypotheses}

Visual details gathered from user-uploaded images, if any:
{image_analysis or "No uploaded image analysis was provided."}

Render the likely completed result after a safe, tidy repair or installation. Show the finished outcome clearly in a realistic home environment. Preserve known materials, room type, location, colors, and constraints from the summary. Do not show people, text labels, logos, measurements, unsafe wiring, exposed hazards, or step-by-step instruction diagrams. The image should feel like a polished preview of the final result, not an advertisement.
""".strip()


def _image_bytes_from_response(response) -> bytes:
    if not getattr(response, "data", None):
        raise ValueError("OpenAI image response had no data items")

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


def ensure_project_preview_image(
        project_id: str,
        prefer_draft: bool = False,
        timeout_seconds: float = OPENAI_IMAGE_TIMEOUT_SECONDS,
) -> Optional[dict]:
    settings = get_settings()
    projects: Collection = mongodb.get_collection("Project")

    logger.info(
        f"Preview generation requested project_id={project_id} "
        f"prefer_draft={prefer_draft} model={MODEL}"
    )

    project = projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        preview = _failed_preview("project_lookup", "Project not found")
        logger.warning(f"Cannot generate preview image. {preview['error']}: {project_id}")
        return preview

    existing = project.get("result_preview_image") or {}
    if existing.get("url"):
        logger.info(f"Preview already exists project_id={project_id} key={existing.get('key')}")
        return existing

    draft = project.get("summary_preview") or {}
    summary = draft.get("summary") if prefer_draft else project.get("summary") or draft.get("summary")
    if not summary:
        preview = _failed_preview("summary_lookup", "Project has no summary or draft summary")
        logger.warning(f"Cannot generate preview image. {preview['error']}: {project_id}")
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"result_preview_image": preview}},
        )
        return preview

    # ── NEW: fetch user uploaded images for this project ──────────────────────
    user_image_urls = _fetch_user_uploaded_image_urls(project)
    reference_files = _prepare_reference_files(user_image_urls) if user_image_urls else []
    has_reference_images = len(reference_files) > 0

    logger.info(
        f"Preview reference images project_id={project_id} "
        f"user_uploads_found={len(user_image_urls)} "
        f"downloaded_for_edit={len(reference_files)}"
    )

    prompt = _build_preview_prompt(project, prefer_draft=prefer_draft, has_reference_images=has_reference_images)
    logger.info(
        f"Preview prompt prepared project_id={project_id} "
        f"summary_chars={len(summary)} prompt_chars={len(prompt)} "
        f"has_image_analysis={bool(project.get('image_analysis'))} "
        f"has_reference_images={has_reference_images}"
    )
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=timeout_seconds,
        max_retries=0,
    )

    try:
        started_at = time.time()
        logger.info(
            f"Calling OpenAI image generation project_id={project_id} "
            f"model={MODEL} timeout_seconds={timeout_seconds} "
            f"mode={'edit' if has_reference_images else 'generate'}"
        )

        if has_reference_images:
            for _, buf, _ in reference_files:
                buf.seek(0)
            image_param = (
                [(fname, buf, ctype) for fname, buf, ctype in reference_files]
                if len(reference_files) > 1
                else reference_files[0]
            )
            response = client.images.edit(
                model=MODEL,
                image=image_param,
                prompt=prompt,
                size="1024x1024",
                n=1,
            )
        else:
            response = client.images.generate(
                model=MODEL,
                prompt=prompt,
                size="1024x1024",
                n=1,
            )

        image_bytes = _image_bytes_from_response(response)
        logger.info(
            f"OpenAI returned preview image project_id={project_id} "
            f"bytes={len(image_bytes)} elapsed_seconds={time.time() - started_at:.2f}"
        )
    except APITimeoutError as exc:
        preview = _failed_preview(
            "openai_timeout",
            f"OpenAI image generation exceeded {timeout_seconds} seconds",
        )
        logger.exception(
            f"Result preview OpenAI timeout project_id={project_id} "
            f"timeout_seconds={timeout_seconds}"
        )
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"result_preview_image": preview}},
        )
        return preview
    except OpenAIError as exc:
        preview = _failed_preview("openai_generation", f"{exc.__class__.__name__}: {exc}")
        logger.exception(f"Result preview OpenAI generation failed project_id={project_id}")
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"result_preview_image": preview}},
        )
        return preview
    except Exception as exc:
        preview = _failed_preview("image_response_decode", f"{exc.__class__.__name__}: {exc}")
        logger.exception(f"Result preview image response decode failed project_id={project_id}")
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"result_preview_image": preview}},
        )
        return preview

    key = f"project_{project_id}/generated-images/previews/result_preview_{int(time.time())}_{uuid4().hex}.png"
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    try:
        logger.info(
            f"Uploading preview to S3 project_id={project_id} "
            f"bucket={settings.AWS_S3_BUCKET} key={key}"
        )
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
    except Exception as exc:
        preview = _failed_preview("s3_upload", f"{exc.__class__.__name__}: {exc}")
        logger.exception(f"Result preview S3 upload failed project_id={project_id} key={key}")
        projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"result_preview_image": preview}},
        )
        return preview

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

    logger.info(
        f"Stored result preview image project_id={project_id} "
        f"key={key} has_public_url={bool(preview.get('url'))}"
    )
    return preview
