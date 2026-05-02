"""Service for image generation with style-lock visual consistency."""

import json
from typing import Optional, List

import requests
from bson.objectid import ObjectId
from loguru import logger
from pymongo.collection import Collection

from agents.solution_generation_multi_agent.image_generation_agent.image_generation_agent import ImageGenerationAgent
from agents.solution_generation_multi_agent.image_generation_agent.schemas import ImageGenerationResult
from agents.solution_generation_multi_agent.image_generation_agent.utils import (
    map_size_to_aspect,
    png_to_bytes_ensure_rgba,
    generate_s3_key,
    get_public_url,
    extract_style_lock,
)
from agents.solution_generation_multi_agent.prompt_templates.v1.image_generation_agent import IMAGE_GENERATION_PROMPT
from config.settings import get_settings
from database.llm_consumption import record_google_image_generation, record_openai_response_usage


class ImageGenerationAgentService:
    """Service for image generation with style-lock visual consistency and S3 upload."""

    def __init__(
            self,
            image_generation_agent: ImageGenerationAgent,
            s3_client,
            project_collection: Collection,
    ):
        self.image_generation_agent = image_generation_agent
        self.s3_client = s3_client
        self.project_collection = project_collection
        self.settings = get_settings()

    # ─────────────────────────────────────────────────────────────────────────
    # Style lock — read and write
    # ─────────────────────────────────────────────────────────────────────────

    def get_style_lock(self, project_id: str) -> Optional[str]:
        """
        Read the project-level style lock from MongoDB.
        Returns None if not yet established (i.e. this is step 1).
        """
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"image_style_lock": 1}
            )
            if doc:
                return doc.get("image_style_lock") or None
            return None
        except Exception as e:
            logger.warning(f"get_style_lock failed (non-fatal): {e}")
            return None

    def save_style_lock(self, project_id: str, style_lock: str) -> None:
        """Persist the style lock on the project document after step 1."""
        try:
            self.project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"image_style_lock": style_lock}},
            )
            logger.info(f"Style lock saved for project {project_id}: {style_lock}")
        except Exception as e:
            logger.warning(f"save_style_lock failed (non-fatal): {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────────

    def generate_step_image(
            self,
            step_id: str,
            step_text: str,
            summary_text: Optional[str] = None,
            size: str = "1536x1024",
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> ImageGenerationResult:
        logger.info(f"Generating image for step {step_id}, size: {size}")

        try:
            # 1. Read existing style lock (None on step 1)
            style_lock: Optional[str] = None
            if project_id:
                style_lock = self.get_style_lock(project_id)
                if style_lock:
                    logger.info(f"Style lock loaded: {style_lock[:80]}...")
                else:
                    logger.info("No style lock yet — this is the establishing step")

            # 2. Build Imagen prompt (GPT call)
            raw_prompt = self._build_raw_prompt(
                step_text, summary_text,
                project_id=project_id, user_id=user_id,
            )

            # 3. Prepend style lock to the Imagen prompt
            #    This is the key fix: the same tokens appear at the start of
            #    EVERY prompt so Imagen always sees the same scene descriptors.
            if style_lock:
                final_prompt = (
                    f"SCENE: {style_lock}. "
                    f"ACTION: {raw_prompt}"
                )
            else:
                final_prompt = raw_prompt

            logger.debug(f"Final Imagen prompt:\n{final_prompt}")

            # 4. Map size → aspect ratio
            aspect_ratio = map_size_to_aspect(size)

            # 5. Generate image
            raw_png = self.image_generation_agent.generate_image(
                prompt=final_prompt,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png",
            )
            record_google_image_generation(
                model=self.image_generation_agent.model,
                operation="image_generation",
                project_id=project_id,
                user_id=user_id,
                image_count=1,
                metadata={"step_id": step_id, "size": size, "aspect_ratio": aspect_ratio},
            )

            # 6. If step 1 (no lock yet), extract and save the style lock now
            #    so all subsequent steps use it.
            if not style_lock and project_id:
                extracted = extract_style_lock(
                    openai_api_key=self.settings.OPENAI_API_KEY,
                    step1_prompt=final_prompt,
                )
                if extracted:
                    self.save_style_lock(project_id, extracted)
                    style_lock = extracted

            # 7. Normalize PNG → RGBA
            png_bytes = png_to_bytes_ensure_rgba(raw_png)

            # 8. Upload to S3
            s3_key = generate_s3_key(step_id, project_id)
            self.s3_client.put_object(
                Bucket=self.settings.AWS_S3_BUCKET,
                Key=s3_key,
                Body=png_bytes,
                ContentType="image/png",
                Metadata={
                    "step_id": step_id,
                    "project_id": project_id or "",
                    "size": size,
                    "model": self.image_generation_agent.model,
                },
            )

            url = get_public_url(s3_key, self.settings.AWS_S3_PUBLIC_BASE)
            logger.info(f"Successfully generated and uploaded image: {s3_key}")

            return ImageGenerationResult(
                message="ok",
                step_id=step_id,
                project_id=project_id or "",
                s3_key=s3_key,
                url=url,
                size=size,
                model=self.image_generation_agent.model,
                prompt_preview=final_prompt,
                status="complete",
            )

        except Exception as e:
            logger.error(f"Error generating step image: {e}")
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # Raw prompt builder (GPT call — action only, no style)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_raw_prompt(
            self,
            step_text: str,
            summary_text: Optional[str] = None,
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> str:
        """
        Ask GPT to write the ACTION portion of the Imagen prompt only.
        The style lock is prepended separately so it is never paraphrased or
        altered by the LLM between steps.
        """
        logger.debug("Building raw action prompt via GPT")

        payload = {
            "model": "gpt-5-nano",
            "messages": [
                {
                    "role": "system",
                    "content": IMAGE_GENERATION_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "project_summary": summary_text or "",
                        "description": step_text,
                        "image_type": "photorealistic instructional DIY/repair image",
                        "style": "4K HDR studio photo, professional photographer",
                        "camera_preference": "close-up or medium shot for detail",
                        "lighting_preference": "natural or studio lighting",
                        "background_preference": "minimal, uncluttered workspace",
                        "focus": "clear visibility of tools, materials, and the action being performed",
                        "human_elements": "gloved hands if safety needed, no faces, hands cropped above wrist",
                        "constraints": "no text, no watermarks, no logos, photorealistic only",
                        "important": (
                            "Describe ONLY the current action and tools involved. "
                            "Do NOT describe the environment, cabinet, countertop, "
                            "glove colour, pipe colour, or background — those are "
                            "controlled separately and will be prepended to your output."
                        ),
                    }, indent=2),
                },
            ],
            "max_completion_tokens": 2000,
            "reasoning_effort": "low",
            "verbosity": "low",
        }

        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.OPENAI_API_KEY}"},
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()

            record_openai_response_usage(
                data,
                model=payload["model"],
                operation="image_prompt_generation",
                project_id=project_id,
                user_id=user_id,
                endpoint="/v1/chat/completions",
                metadata={"step_text": step_text[:120]},
            )

            content = data["choices"][0]["message"]["content"]
            try:
                parsed = json.loads(content)
                return parsed.get("imagen_prompt", content).strip()
            except json.JSONDecodeError:
                return content.strip()

        except Exception as e:
            logger.error(f"Error building raw prompt: {e}")
            raise
