"""Service for image generation with business logic for prompt building and image processing."""

import json
from typing import Optional, List

import requests
from bson.objectid import ObjectId
from loguru import logger
from pymongo.collection import Collection

from agents.solution_generation_multi_agent.image_generation_agent.image_generation_agent import ImageGenerationAgent
from agents.solution_generation_multi_agent.image_generation_agent.schemas import (
    ImageGenerationResult,
    VisualContextFrame,
)
from agents.solution_generation_multi_agent.image_generation_agent.utils import (
    map_size_to_aspect,
    png_to_bytes_ensure_rgba,
    generate_s3_key,
    get_public_url,
)
from agents.solution_generation_multi_agent.prompt_templates.v1.image_generation_agent import IMAGE_GENERATION_PROMPT
from config.settings import get_settings
from database.llm_consumption import record_google_image_generation, record_openai_response_usage

VISUAL_CONTEXT_BUFFER = 3


class ImageGenerationAgentService:
    """Service for image generation with visual context buffer and S3 upload."""

    def __init__(
            self,
            image_generation_agent: ImageGenerationAgent,
            s3_client,
            project_collection: Collection,      # ← NEW: for reading visual context
    ):
        self.image_generation_agent = image_generation_agent
        self.s3_client = s3_client
        self.project_collection = project_collection
        self.settings = get_settings()

    # ─────────────────────────────────────────────────────────────────────────
    # Visual context fetching
    # ─────────────────────────────────────────────────────────────────────────

    def fetch_visual_context(
            self,
            project_id: str,
            current_step_id: str,
    ) -> List[VisualContextFrame]:
        """
        Read the last VISUAL_CONTEXT_BUFFER completed step images from MongoDB.
        Only steps before current_step_id with status='complete' and a URL are
        included. Returns frames ordered oldest → newest.
        """
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"step_generation.steps": 1}
            )
            if not doc:
                return []

            steps = doc.get("step_generation", {}).get("steps", [])
            current_idx = int(current_step_id) - 1      # step_id is 1-based

            frames: List[VisualContextFrame] = []
            for step in steps[:current_idx]:
                img = step.get("image", {})
                if not isinstance(img, dict):
                    continue
                url = img.get("url")
                status = img.get("status")
                prompt = img.get("prompt_preview", "")
                anchor = img.get("style_anchor", "")

                if url and status == "complete":
                    frames.append(VisualContextFrame(
                        step_id=str(step.get("order", "")),
                        url=url,
                        prompt_preview=prompt or "",
                        style_anchor=anchor or "",
                    ))

            return frames[-VISUAL_CONTEXT_BUFFER:]

        except Exception as e:
            logger.warning(f"fetch_visual_context failed (non-fatal): {e}")
            return []

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
            user_id: Optional[str] = None,           # ← preserved from your original
    ) -> ImageGenerationResult:
        logger.info(f"Generating image for step {step_id}, size: {size}")

        try:
            # 1. Fetch prior visual context from MongoDB
            visual_context: List[VisualContextFrame] = []
            if project_id:
                visual_context = self.fetch_visual_context(project_id, step_id)
                logger.info(f"Visual context: {len(visual_context)} prior frame(s) loaded")

            # 2. Build prompt — now receives visual context
            prompt, style_anchor = self._build_prompt(
                step_text,
                summary_text,
                visual_context=visual_context,
                project_id=project_id,
                user_id=user_id,
            )

            # 3. Map size to aspect ratio
            aspect_ratio = map_size_to_aspect(size)

            # 4. Generate image using Google Imagen
            raw_png = self.image_generation_agent.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png",
            )

            # 5. Record Google image generation usage (preserved from your original)
            record_google_image_generation(
                model=self.image_generation_agent.model,
                operation="image_generation",
                project_id=project_id,
                user_id=user_id,
                image_count=1,
                metadata={"step_id": step_id, "size": size, "aspect_ratio": aspect_ratio},
            )

            # 6. Normalize PNG to RGBA
            png_bytes = png_to_bytes_ensure_rgba(raw_png)

            # 7. Generate S3 key and upload
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

            # 8. Build public URL
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
                prompt_preview=prompt if prompt else "Prompt not available",
                style_anchor=style_anchor,           # ← persisted so future steps can read it
                status="complete",
            )

        except Exception as e:
            logger.error(f"Error generating step image: {e}")
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # Prompt building
    # ─────────────────────────────────────────────────────────────────────────

    def _build_prompt(
            self,
            step_text: str,
            summary_text: Optional[str] = None,
            visual_context: Optional[List[VisualContextFrame]] = None,
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Build image generation prompt using OpenAI.
        Injects visual context so GPT maintains consistent environment across steps.

        Returns:
            (imagen_prompt, style_anchor)
        """
        logger.debug("Building image generation prompt")

        context_block = self._format_visual_context(visual_context or [])

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
                        "background_preference": "minimal, uncluttered workspace or neutral background",
                        "focus": "clear visibility of tools, materials, and the action being performed",
                        "human_elements": "gloved hands if safety needed, no faces, hands cropped above wrist",
                        "constraints": "no text, no watermarks, no logos, photorealistic only",
                        "visual_continuity_context": context_block,   # ← NEW
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

            # Preserved from your original — record OpenAI token usage
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
                imagen_prompt = parsed.get("imagen_prompt", content)
                style_anchor = parsed.get("style_anchor", "")
            except json.JSONDecodeError:
                # Fallback: content used directly, no style_anchor extractable
                imagen_prompt = content
                style_anchor = ""

            return imagen_prompt.strip(), style_anchor.strip()

        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _format_visual_context(frames: List[VisualContextFrame]) -> dict:
        """
        Format prior frames into a structured dict for the GPT user message.
        """
        if not frames:
            return {
                "available": False,
                "instruction": (
                    "No prior step images exist yet. Establish a clear, consistent visual "
                    "style for this project — choose specific wall colour, fixture material, "
                    "flooring type, and lighting direction. These become the project's visual identity."
                ),
            }

        return {
            "available": True,
            "instruction": (
                "IMPORTANT: The images below are from earlier steps of this SAME project. "
                "You MUST maintain visual consistency: same room/environment design, same "
                "fixture colours and styles, same background, same lighting tone, same "
                "camera distance and angle. Reference these images explicitly in your "
                "imagen_prompt by describing the environment they establish."
            ),
            "prior_steps": [
                {
                    "step_id": f.step_id,
                    "image_url": f.url,
                    "style_anchor": f.style_anchor or "not available",
                    "prompt_excerpt": f.prompt_preview[:200] if f.prompt_preview else "",
                }
                for f in frames
            ],
        }
