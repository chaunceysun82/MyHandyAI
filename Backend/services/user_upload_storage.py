import base64
import binascii
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import boto3
from loguru import logger

from config.settings import get_settings


DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[a-zA-Z0-9.+-]+);base64,(?P<data>.+)$")
EXTENSIONS_BY_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


class UserUploadStorageError(ValueError):
    pass


def _clean_path_part(value: Optional[str], fallback: str) -> str:
    if not value:
        return fallback

    cleaned = re.sub(r"[^a-zA-Z0-9_.=-]+", "-", str(value)).strip("-")
    return cleaned or fallback


def _decode_image(image_base64: str, image_mime_type: Optional[str]) -> tuple[bytes, str]:
    image_data = image_base64.strip()
    mime_type = image_mime_type or "image/jpeg"

    match = DATA_URL_RE.match(image_data)
    if match:
        mime_type = match.group("mime")
        image_data = match.group("data")

    if not mime_type.startswith("image/"):
        raise UserUploadStorageError("Uploaded file must be an image")

    try:
        return base64.b64decode(image_data, validate=True), mime_type
    except (binascii.Error, ValueError) as exc:
        raise UserUploadStorageError("Invalid base64 image data") from exc


def store_user_uploaded_image(
    *,
    image_base64: str,
    image_mime_type: Optional[str],
    user_id: Optional[str],
    project_id: str,
    thread_id: UUID,
    source: str,
    step_number: Optional[int] = None,
) -> dict:
    settings = get_settings()
    image_bytes, mime_type = _decode_image(image_base64, image_mime_type)
    extension = EXTENSIONS_BY_MIME.get(mime_type.lower(), "bin")
    now = datetime.now(timezone.utc)

    user_folder = _clean_path_part(user_id, "anonymous")
    project_folder = _clean_path_part(project_id, "unknown-project")
    source_folder = _clean_path_part(source, "chat")
    filename = f"{now.strftime('%Y%m%dT%H%M%S')}-{uuid4().hex}.{extension}"

    key = (
        f"user-uploads/{user_folder}/projects/{project_folder}/"
        f"{source_folder}/threads/{thread_id}/{filename}"
    )

    metadata = {
        "user_id": user_folder,
        "project_id": project_folder,
        "thread_id": str(thread_id),
        "source": source_folder,
    }
    if step_number is not None:
        metadata["step_number"] = str(step_number)

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType=mime_type,
        Metadata=metadata,
    )

    url = (
        f"{settings.AWS_S3_PUBLIC_BASE.rstrip('/')}/{key}"
        if settings.AWS_S3_PUBLIC_BASE
        else None
    )

    logger.info(
        "Stored user uploaded image in S3",
        bucket=settings.AWS_S3_BUCKET,
        key=key,
        source=source_folder,
    )

    return {
        "bucket": settings.AWS_S3_BUCKET,
        "key": key,
        "url": url,
        "content_type": mime_type,
        "size_bytes": len(image_bytes),
    }
