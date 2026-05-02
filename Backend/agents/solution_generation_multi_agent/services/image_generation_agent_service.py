# image_generation_agent_service.py

import json
import re
import time
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
    apply_physics_filter,
)
from agents.solution_generation_multi_agent.prompt_templates.v1.image_generation_agent import (
    IMAGE_GENERATION_PROMPT,
    VISUAL_DNA_PROMPT,
)
from config.settings import get_settings
from database.llm_consumption import record_google_image_generation, record_openai_response_usage

REFERENCE_IMAGE_BUFFER = 3

_NEGATIVE_SUFFIX = (
    " Photorealistic, 4K HDR, sharp focus, professional photography. "
    "No text, no labels, no watermarks, no logos. "
    "No cartoon styling. Physically accurate. No floating objects."
)


def _call_openai(
        api_key: str,
        system: str,
        user: str,
        max_tokens: int = 1200,
        retries: int = 2,
) -> Optional[str]:
    """
    Minimal OpenAI call with retries and full response logging.
    Uses only stable parameters — no reasoning_effort / verbosity
    which can cause empty responses on some models.
    Returns the raw content string or None on failure.
    """
    payload = {
        "model": "gpt-4o-mini",          # stable model, reliable JSON output
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,              # low temp = consistent structured output
        "response_format": {"type": "json_object"},  # force JSON mode
    }

    for attempt in range(1, retries + 2):
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=40,
            )
            r.raise_for_status()
            data = r.json()

            # Log the raw response so we can see exactly what came back
            logger.debug(f"OpenAI raw response (attempt {attempt}): {json.dumps(data)[:500]}")

            choices = data.get("choices", [])
            if not choices:
                logger.warning(f"OpenAI attempt {attempt}: empty choices — retrying")
                continue

            content = choices[0].get("message", {}).get("content", "").strip()
            if not content:
                logger.warning(f"OpenAI attempt {attempt}: empty content — retrying")
                continue

            return content

        except requests.HTTPError as e:
            logger.warning(f"OpenAI attempt {attempt} HTTP error: {e} — retrying")
        except Exception as e:
            logger.warning(f"OpenAI attempt {attempt} failed: {e} — retrying")

        if attempt <= retries:
            time.sleep(1.5 * attempt)

    logger.error("All OpenAI attempts failed")
    return None


def _parse_json_safe(content: str, context: str = "") -> Optional[dict]:
    """
    Parse JSON from OpenAI response safely.
    Strips markdown fences if present. Logs the raw string on failure.
    """
    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed [{context}]: {e} | raw content: {content[:300]}")
        return None


class ImageGenerationAgentService:

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

    # ─── Visual DNA ───────────────────────────────────────────────────────────

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
        """
        Generate domain-specific visual DNA from the project summary.
        Uses _call_openai() with json_object response format to prevent empty responses.
        Falls back to a safe generic DNA if generation fails so the pipeline never stalls.
        """
        logger.info("Generating visual DNA from project summary")

        content = _call_openai(
            api_key=self.settings.OPENAI_API_KEY,
            system=VISUAL_DNA_PROMPT,
            user=summary_text,
            max_tokens=1200,
        )

        if content:
            dna = _parse_json_safe(content, context="visual_dna")
            if dna:
                logger.info(f"Visual DNA generated — domain: {dna.get('domain')}")
                return dna

        # ── Fallback: generic DNA so pipeline never runs with dna=None ──────
        logger.warning("generate_visual_dna failed — using generic fallback DNA")
        return {
            "domain": "general",
            "scene_prefix": "indoor home workspace, neutral background, natural lighting",
            "glove_color": "blue nitrile",
            "body_anchors": {
                "primary": "A photo of a person, their {glove_color} gloved hands",
                "elevated": "A photo of a person standing on a stepladder, their {glove_color} gloved hands",
                "ground_level": "A photo of a person crouching on the floor, their {glove_color} gloved hands",
                "standing": "A photo of a person standing at a workbench, their {glove_color} gloved hands",
            },
            "action_location_keywords": {
                "primary": [], "elevated": ["ladder", "ceiling", "roof"],
                "ground_level": ["floor", "ground"], "standing": ["workbench", "table"],
            },
            "physics_rules": [
                "Liquids flow downward only",
                "Heavy objects rest on surfaces, never float",
                "Hands connect to visible arms and a body",
            ],
            "physics_redflags": [
                {"pattern": r"\bfloating\b", "label": "floating object"},
                {"pattern": r"\bupward\b.{0,20}\b(water|liquid|flow)\b", "label": "upward liquid"},
            ],
            "simplification_rules": [
                "Pick the single most visual action from the step"
            ],
        }

    # ─── Reference images ─────────────────────────────────────────────────────

    def fetch_reference_images(
            self,
            project_id: str,
            current_step_id: str,
    ) -> list[PIL.Image.Image]:
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"step_generation.steps": 1}
            )
            if not doc:
                return []

            steps = doc.get("step_generation", {}).get("steps", [])
            current_idx = int(current_step_id) - 1

            ref_images = []
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
                        logger.info(f"Loaded ref image step {step.get('order')}")

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
            # 1. Get or generate Visual DNA — never None after this point
            dna: Optional[dict] = None
            if project_id:
                dna = self.get_visual_dna(project_id)
            if dna is None:
                # generate_visual_dna() always returns at least the fallback
                dna = self.generate_visual_dna(summary_text or "general DIY repair project")
                if project_id:
                    self.save_visual_dna(project_id, dna)

            # 2. Fetch prior step images
            reference_images: list[PIL.Image.Image] = []
            if project_id:
                reference_images = self.fetch_reference_images(project_id, step_id)

            # 3. Build prompt
            prompt, state_summary = self._build_prompt(
                step_text=step_text,
                summary_text=summary_text,
                dna=dna,
                has_references=len(reference_images) > 0,
                step_id=step_id,
                project_id=project_id,
                user_id=user_id,
            )

            logger.debug(f"Final prompt for step {step_id}:\n{prompt}")

            # 4. Generate
            aspect_ratio = map_size_to_aspect(size)
            raw_bytes = self.image_generation_agent.generate_image(
                prompt=prompt,
                reference_images=reference_images,
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
                    "domain": dna.get("domain", "unknown"),
                },
            )

            # 5. Normalize and upload
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
                status="complete",
            )

        except Exception as e:
            logger.error(f"Error generating step image: {e}")
            raise

    # ─── Prompt builder ───────────────────────────────────────────────────────

    def _build_prompt(
            self,
            step_text: str,
            summary_text: Optional[str],
            dna: dict,                           # never None at this point
            has_references: bool,
            step_id: str,
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> tuple[str, str]:

        physics_rules = dna.get("physics_rules", [])
        domain = dna.get("domain", "general")

        reference_instruction = (
            "Reference images of earlier steps are provided. "
            "MATCH the visual style exactly: same environment, fixtures, colours, "
            "gloves, lighting, and camera angle. "
            "Show the work state AFTER this step's action is completed."
            if has_references else
            "No prior images exist. Establish a clear photorealistic style "
            "that will be maintained across all subsequent steps."
        )

        user_content = json.dumps({
            "project_summary": summary_text or "",
            "domain": domain,
            "step_description": step_text,
            "reference_image_instruction": reference_instruction,
            "physics_rules": physics_rules,
            "simplification_rules": dna.get("simplification_rules", []),
            "constraints": (
                "No text, no watermarks, no brand names. "
                "One primary action only. "
                "Describe the action and immediate objects only — "
                "do NOT describe environment, gloves, or pipe colours "
                "as those are visible in the reference images."
            ),
        }, indent=2)

        content = _call_openai(
            api_key=self.settings.OPENAI_API_KEY,
            system=IMAGE_GENERATION_PROMPT,
            user=user_content,
            max_tokens=500,
        )

        # Record usage
        # Note: _call_openai abstracts the raw response so we log approximate usage
        logger.debug(f"Prompt built for step — domain: {domain}, has_refs: {has_references}")

        if content:
            parsed = _parse_json_safe(content, context=f"image_prompt_step")
            if parsed:
                return (
                    (
                        f"{reference_instruction}\n\n"
                        f"ACTION: {parsed.get('imagen_prompt', step_text)}"
                        f"{_NEGATIVE_SUFFIX}"
                    ),
                    parsed.get("state_summary", ""),
                )

        # ── Fallback: use step text directly so image is at least on-topic ──
        logger.warning(f"_build_prompt failed for step {step_id if hasattr(self, 'step_id') else '?'} — using step text as fallback prompt")
        return (
            f"{reference_instruction}\n\n"
            f"ACTION: Photorealistic image of: {step_text}"
            f"{_NEGATIVE_SUFFIX}"
        ), ""
