"""Service — Gemini 2.5 Flash Image with live image reference passing."""

import json
import re
from typing import Optional

import PIL.Image
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
)
from agents.solution_generation_multi_agent.prompt_templates.v1.image_generation_agent import (
    IMAGE_GENERATION_PROMPT,
    VISUAL_DNA_PROMPT,
)
from config.settings import get_settings
from database.llm_consumption import record_google_image_generation, record_openai_response_usage

# How many prior step images to load and pass as visual reference
REFERENCE_IMAGE_BUFFER = 3

_NEGATIVE_SUFFIX = (
    " Photorealistic, 4K HDR, sharp focus, professional photography. "
    "No text, no labels, no watermarks, no logos. "
    "No cartoon styling. Physically accurate. No floating objects."
)


class ImageGenerationAgentService:
    """
    Image generation service using Gemini 2.5 Flash Image.
    Prior step images are fetched from S3/CloudFront and passed DIRECTLY
    to the model as visual references — no text description of style needed.
    """

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

    # ─── Visual DNA (still used for domain physics rules) ─────────────────────

    def get_visual_dna(self, project_id: str) -> Optional[dict]:
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"image_visual_dna": 1}
            )
            return doc.get("image_visual_dna") if doc else None
        except Exception as e:
            logger.warning(f"get_visual_dna failed: {e}")
            return None

    def save_visual_dna(self, project_id: str, dna: dict) -> None:
        try:
            self.project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"image_visual_dna": dna}},
            )
            logger.info(f"Visual DNA saved — domain: {dna.get('domain')}")
        except Exception as e:
            logger.warning(f"save_visual_dna failed: {e}")

    def generate_visual_dna(self, summary_text: str) -> Optional[dict]:
        logger.info("Generating visual DNA")
        payload = {
            "model": "gpt-5-nano",
            "messages": [
                {"role": "system", "content": VISUAL_DNA_PROMPT},
                {"role": "user", "content": summary_text},
            ],
            "max_completion_tokens": 1200,
            "reasoning_effort": "low",
        }
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.OPENAI_API_KEY}"},
                json=payload, timeout=30,
            )
            r.raise_for_status()

            # Guard: log raw text before attempting JSON parse
            raw_text = r.text
            if not raw_text or not raw_text.strip():
                logger.error("generate_visual_dna: empty response body from OpenAI")
                return None

            resp_json = r.json()
            content = resp_json["choices"][0]["message"]["content"]
            if not content or not content.strip():
                logger.error("generate_visual_dna: empty content field in OpenAI response")
                return None

            content = content.strip()
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content).strip()

            if not content:
                logger.error("generate_visual_dna: content empty after stripping markdown fences")
                return None

            return json.loads(content)

        except requests.HTTPError as e:
            logger.error(f"generate_visual_dna HTTP error {e.response.status_code}: {e.response.text[:300]}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"generate_visual_dna JSON parse failed: {e} — raw content: {content!r:.200}")
            return None
        except Exception as e:
            logger.error(f"generate_visual_dna failed: {e}")
            return None

    # ─── Reference image fetching — THE KEY METHOD ────────────────────────────

    def fetch_reference_images(
            self,
            project_id: str,
            current_step_id: str,
    ) -> list[PIL.Image.Image]:
        """
        Load the last REFERENCE_IMAGE_BUFFER completed step images as PIL Images.
        These are passed directly to Gemini 2.5 Flash Image as visual references.

        The model SEES the actual pixels of prior steps, not text descriptions.
        This is what enforces real visual consistency — same cabinet, same gloves,
        same pipes, same lighting — because the model literally looks at prior images.
        """
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"step_generation.steps": 1}
            )
            if not doc:
                return []

            steps = doc.get("step_generation", {}).get("steps", [])
            current_idx = int(current_step_id) - 1

            ref_images: list[PIL.Image.Image] = []
            for step in steps[:current_idx]:
                img_meta = step.get("image", {})
                if not isinstance(img_meta, dict):
                    continue
                url = img_meta.get("url")
                status = img_meta.get("status")

                if url and status == "complete":
                    pil_img = self.image_generation_agent.load_image_from_url(url)
                    if pil_img:
                        ref_images.append(pil_img)
                        logger.info(f"Loaded reference image from step {step.get('order')}: {url[:60]}...")

            result = ref_images[-REFERENCE_IMAGE_BUFFER:]
            logger.info(f"Passing {len(result)} reference image(s) to Gemini for step {current_step_id}")
            return result

        except Exception as e:
            logger.warning(f"fetch_reference_images failed (non-fatal): {e}")
            return []

    # ─── Main entry ───────────────────────────────────────────────────────────

    def generate_step_image(
            self,
            step_id: str,
            step_text: str,
            summary_text: Optional[str] = None,
            size: str = "1536x1024",
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> ImageGenerationResult:
        logger.info(f"Generating image for step {step_id}")

        try:
            # 1. Get or generate Visual DNA (for physics rules + domain context)
            dna: Optional[dict] = None
            if project_id:
                dna = self.get_visual_dna(project_id)
            if dna is None and summary_text:
                dna = self.generate_visual_dna(summary_text)
                if dna and project_id:
                    self.save_visual_dna(project_id, dna)

            # 2. Fetch prior step images as PIL objects — passed directly to model
            reference_images: list[PIL.Image.Image] = []
            if project_id:
                reference_images = self.fetch_reference_images(project_id, step_id)

            # 3. Build text prompt (action description + physics rules)
            prompt, state_summary = self._build_prompt(
                step_text=step_text,
                summary_text=summary_text,
                dna=dna,
                has_references=len(reference_images) > 0,
                project_id=project_id,
                user_id=user_id,
            )

            # 4. Generate — pass real images + text prompt together
            aspect_ratio = map_size_to_aspect(size)
            raw_bytes = self.image_generation_agent.generate_image(
                prompt=prompt,
                reference_images=reference_images,   # ← actual pixels, not URLs
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png",
            )

            record_google_image_generation(
                model=self.image_generation_agent.model,
                operation="image_generation",
                project_id=project_id,
                user_id=user_id,
                image_count=1,
                metadata={
                    "step_id": step_id,
                    "size": size,
                    "aspect_ratio": aspect_ratio,
                    "reference_images_count": len(reference_images),
                    "domain": dna.get("domain") if dna else "unknown",
                },
            )

            # 5. Normalize, upload, return
            png_bytes = png_to_bytes_ensure_rgba(raw_bytes)
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
                    "reference_count": str(len(reference_images)),
                },
            )
            url = get_public_url(s3_key, self.settings.AWS_S3_PUBLIC_BASE)
            logger.info(f"Image uploaded: {s3_key}")

            return ImageGenerationResult(
                message="ok",
                step_id=step_id,
                project_id=project_id or "",
                s3_key=s3_key,
                url=url,
                size=size,
                model=self.image_generation_agent.model,
                prompt_preview=prompt,
                state_summary=state_summary,
                status="complete"
                
            )

        except Exception as e:
            logger.error(f"Error generating step image: {e}")
            raise

    # ─── Prompt builder ───────────────────────────────────────────────────────

    def _build_prompt(
            self,
            step_text: str,
            summary_text: Optional[str],
            dna: Optional[dict],
            has_references: bool,
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Build the text prompt. Since Gemini 2.5 Flash Image receives actual
        prior images, the prompt now focuses purely on:
          - What action to perform in this step
          - Physics constraints for the domain
          - An instruction to maintain visual consistency with the reference images
        """
        physics_rules = dna.get("physics_rules", []) if dna else []
        domain = dna.get("domain", "general") if dna else "general"

        reference_instruction = (
            "You have been given reference images showing earlier steps of this SAME project. "
            "MATCH the visual style exactly: same environment, same fixtures, same colours, "
            "same gloves, same lighting, same camera angle. "
            "Show the state of the work AFTER the action described below is performed."
            if has_references else
            "This is the first step. Establish a clear, consistent, photorealistic style "
            "that can be maintained across all subsequent steps."
        )

        payload = {
            "model": "gpt-5-nano",
            "messages": [
                {"role": "system", "content": IMAGE_GENERATION_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps({
                        "project_summary": summary_text or "",
                        "domain": domain,
                        "step_description": step_text,
                        "reference_image_instruction": reference_instruction,
                        "physics_rules": physics_rules,
                        "constraints": (
                            "No text, no watermarks, no brand names. "
                            "One primary action only. "
                            "Describe the action and immediate objects only — "
                            "do NOT describe the environment; it is provided as reference images."
                        ),
                    }, indent=2),
                },
            ],
            "max_completion_tokens": 500,
            "reasoning_effort": "low",
        }

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

        content = data["choices"][0]["message"]["content"].strip()
        try:
            parsed = json.loads(content)
            action_prompt = parsed.get("imagen_prompt", content).strip()
            state_summary = parsed.get("state_summary", "")
        except json.JSONDecodeError:
            action_prompt = content.strip()
            state_summary = ""

        # Final prompt: reference instruction + action + negative suffix
        final_prompt = (
            f"{reference_instruction}\n\n"
            f"ACTION FOR THIS STEP: {action_prompt}"
            f"{_NEGATIVE_SUFFIX}"
        )
        return final_prompt, state_summary
