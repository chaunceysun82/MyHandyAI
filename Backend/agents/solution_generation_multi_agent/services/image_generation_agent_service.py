"""Service — Gemini 2.5 Flash Image with anchor objects + step reference images."""

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
from agents.solution_generation_multi_agent.image_generation_agent.schemas import (
    ImageGenerationResult,
    AnchorObject,
    AnchorObjectsResult,
)
from agents.solution_generation_multi_agent.image_generation_agent.utils import (
    map_size_to_aspect,
    png_to_bytes_ensure_rgba,
    generate_anchor_s3_key,
    generate_s3_key,
    get_public_url,
    apply_physics_filter,
)
from agents.solution_generation_multi_agent.prompt_templates.v1.image_generation_agent import (
    IMAGE_GENERATION_PROMPT,
    VISUAL_DNA_PROMPT,
    ANCHOR_OBJECTS_PROMPT,
)
from config.settings import get_settings
from database.llm_consumption import record_google_image_generation, record_openai_response_usage

REFERENCE_IMAGE_BUFFER = 2          # prior step images to pass (keep low — anchor images take slots)
MAX_ANCHOR_IMAGES = 4               # Gemini 2.5 Flash Image supports up to 14 total refs
TOTAL_REF_BUDGET = 6                # anchor + step refs combined (stay well under 14)

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
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
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
            logger.debug(f"OpenAI response (attempt {attempt}): {json.dumps(data)[:400]}")
            choices = data.get("choices", [])
            if not choices:
                logger.warning(f"OpenAI attempt {attempt}: empty choices")
                continue
            content = choices[0].get("message", {}).get("content", "").strip()
            if not content:
                logger.warning(f"OpenAI attempt {attempt}: empty content")
                continue
            return content
        except Exception as e:
            logger.warning(f"OpenAI attempt {attempt} failed: {e}")
        if attempt <= retries:
            time.sleep(1.5 * attempt)
    logger.error("All OpenAI attempts failed")
    return None


def _parse_json_safe(content: str, context: str = "") -> Optional[dict]:
    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed [{context}]: {e} | raw: {content[:300]}")
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

    def generate_visual_dna(self, summary_text: str) -> dict:
        logger.info("Generating visual DNA")
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

        logger.warning("generate_visual_dna failed — using fallback")
        return {
            "domain": "general",
            "scene_prefix": "indoor home workspace, neutral background, natural lighting",
            "glove_color": "blue nitrile",
            "body_anchors": {
                "primary": "A photo of a person, their {glove_color} gloved hands",
                "elevated": "A photo of a person on a stepladder, their {glove_color} gloved hands",
                "ground_level": "A photo of a person crouching, their {glove_color} gloved hands",
                "standing": "A photo of a person at a workbench, their {glove_color} gloved hands",
            },
            "action_location_keywords": {
                "primary": [], "elevated": ["ladder", "ceiling"],
                "ground_level": ["floor"], "standing": ["workbench", "table"],
            },
            "physics_rules": [
                "Liquids flow downward only",
                "Heavy objects rest on surfaces",
                "Hands connect to visible arms and a body",
            ],
            "physics_redflags": [
                {"pattern": r"\bfloating\b", "label": "floating object"},
                {"pattern": r"\bupward\b.{0,20}\b(water|liquid)\b", "label": "upward liquid"},
            ],
            "simplification_rules": ["Pick the single most visual action from the step"],
        }

    # ─── Anchor objects ───────────────────────────────────────────────────────

    def get_anchor_objects(self, project_id: str) -> Optional[AnchorObjectsResult]:
        """Read stored anchor objects from MongoDB."""
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"image_anchor_objects": 1}
            )
            if doc and doc.get("image_anchor_objects"):
                return AnchorObjectsResult(**doc["image_anchor_objects"])
            return None
        except Exception as e:
            logger.warning(f"get_anchor_objects failed: {e}")
            return None

    def save_anchor_objects(self, project_id: str, result: AnchorObjectsResult) -> None:
        try:
            self.project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"image_anchor_objects": result.model_dump()}},
            )
            logger.info(f"Anchor objects saved: {[o.name for o in result.objects]}")
        except Exception as e:
            logger.warning(f"save_anchor_objects failed: {e}")

    def generate_anchor_objects(
            self,
            project_id: str,
            summary_text: str,
            size: str = "1:1",
    ) -> AnchorObjectsResult:
        """
        Extract central objects from summary, generate one isolated image per object,
        upload to S3, and persist to MongoDB.
        Called ONCE before any step images are generated.
        """
        logger.info(f"Generating anchor objects for project {project_id}")

        # 1. Ask GPT which objects to generate
        content = _call_openai(
            api_key=self.settings.OPENAI_API_KEY,
            system=ANCHOR_OBJECTS_PROMPT,
            user=summary_text,
            max_tokens=600,
        )

        anchor_defs = []
        if content:
            parsed = _parse_json_safe(content, context="anchor_objects")
            if parsed:
                anchor_defs = parsed.get("anchor_objects", [])

        if not anchor_defs:
            logger.warning("No anchor objects extracted — skipping anchor generation")
            return AnchorObjectsResult(objects=[], status="skipped")

        logger.info(f"Anchor objects to generate: {[a['name'] for a in anchor_defs]}")

        # 2. Generate one image per anchor object
        anchor_results: list[AnchorObject] = []
        for anchor in anchor_defs[:MAX_ANCHOR_IMAGES]:
            name = anchor.get("name", "object")
            prompt = anchor.get("prompt", "")
            if not prompt:
                continue

            # Wrap prompt to ensure isolated, clean reference image
            full_prompt = (
                f"A photorealistic studio photograph of {prompt}. "
                f"Single object only, centered, isolated on a clean neutral grey background. "
                f"No hands, no people, no scene context. "
                f"Sharp focus, 4K HDR, professional product photography. "
                f"No text, no labels, no watermarks."
            )

            logger.info(f"Generating anchor image for: {name}")
            try:
                raw_bytes = self.image_generation_agent.generate_image(
                    prompt=full_prompt,
                    reference_images=None,   # no references for anchor generation
                    aspect_ratio="1:1",      # square for isolated object shots
                    output_mime_type="image/png",
                )

                png_bytes = png_to_bytes_ensure_rgba(raw_bytes)
                s3_key = generate_anchor_s3_key(project_id, name)
                self.s3_client.put_object(
                    Bucket=self.settings.AWS_S3_BUCKET,
                    Key=s3_key,
                    Body=png_bytes,
                    ContentType="image/png",
                    Metadata={
                        "project_id": project_id,
                        "anchor_name": name,
                        "type": "anchor_object",
                    },
                )
                url = get_public_url(s3_key, self.settings.AWS_S3_PUBLIC_BASE)
                anchor_results.append(AnchorObject(
                    name=name,
                    description=prompt,
                    s3_key=s3_key,
                    url=url,
                    status="complete",
                ))
                logger.info(f"Anchor '{name}' generated and uploaded: {s3_key}")

            except Exception as e:
                logger.error(f"Failed to generate anchor image for '{name}': {e}")
                continue

        result = AnchorObjectsResult(objects=anchor_results, status="complete")
        self.save_anchor_objects(project_id, result)
        return result

    def fetch_anchor_images(self, project_id: str) -> list[PIL.Image.Image]:
        """
        Load anchor object PIL images from their stored URLs.
        These are passed as the FIRST reference images to every step generation.
        """
        anchor_result = self.get_anchor_objects(project_id)
        if not anchor_result or not anchor_result.objects:
            return []

        images = []
        for obj in anchor_result.objects:
            if obj.url and obj.status == "complete":
                pil_img = self.image_generation_agent.load_image_from_url(obj.url)
                if pil_img:
                    images.append(pil_img)
                    logger.info(f"Loaded anchor image: {obj.name}")
        return images

    # ─── Reference images (prior steps) ──────────────────────────────────────

    def fetch_reference_images(
            self,
            project_id: str,
            current_step_id: str,
            anchor_count: int = 0,
    ) -> list[PIL.Image.Image]:
        """
        Load prior step images. Respects TOTAL_REF_BUDGET minus anchor images already loaded.
        """
        step_budget = max(1, TOTAL_REF_BUDGET - anchor_count)

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

            result = ref_images[-step_budget:]
            logger.info(
                f"Step refs: {len(result)} loaded "
                f"(budget={step_budget}, anchors={anchor_count})"
            )
            return result

        except Exception as e:
            logger.warning(f"fetch_reference_images failed: {e}")
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
            # 1. Visual DNA
            dna: Optional[dict] = None
            if project_id:
                dna = self.get_visual_dna(project_id)
            if dna is None:
                dna = self.generate_visual_dna(summary_text or "general DIY repair project")
                if project_id:
                    self.save_visual_dna(project_id, dna)

            # 2. Anchor images — always loaded first, always passed first to model
            anchor_images: list[PIL.Image.Image] = []
            if project_id:
                anchor_images = self.fetch_anchor_images(project_id)
                logger.info(f"Anchor images loaded: {len(anchor_images)}")

            # 3. Prior step images — fill remaining reference budget
            step_ref_images: list[PIL.Image.Image] = []
            if project_id:
                step_ref_images = self.fetch_reference_images(
                    project_id, step_id,
                    anchor_count=len(anchor_images),
                )

            # 4. Combined reference list:
            #    [anchor_1, anchor_2, ..., prior_step_N-1, prior_step_N]
            #    Anchors first so model sees the canonical objects before the action context
            all_references = anchor_images + step_ref_images

            # 5. Build prompt
            prompt, state_summary = self._build_prompt(
                step_text=step_text,
                summary_text=summary_text,
                dna=dna,
                has_anchor_images=len(anchor_images) > 0,
                has_step_refs=len(step_ref_images) > 0,
                step_id=step_id,
                project_id=project_id,
                user_id=user_id,
            )

            logger.debug(f"Final prompt step {step_id}:\n{prompt}")

            # 6. Generate
            aspect_ratio = map_size_to_aspect(size)
            raw_bytes = self.image_generation_agent.generate_image(
                prompt=prompt,
                reference_images=all_references if all_references else None,
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
                    "anchor_images_count": len(anchor_images),
                    "step_refs_count": len(step_ref_images),
                    "domain": dna.get("domain", "unknown"),
                },
            )

            # 7. Upload
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
                    "anchor_count": str(len(anchor_images)),
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
            dna: dict,
            has_anchor_images: bool,
            has_step_refs: bool,
            step_id: str,
            project_id: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> tuple[str, str]:

        # Build reference instruction based on what images are being passed
        if has_anchor_images and has_step_refs:
            reference_instruction = (
                "You are given two sets of reference images:\n"
                "1. ANCHOR IMAGES (first images): isolated photos of the main objects "
                "in this project (e.g. the exact mirror, the exact wall type). "
                "Use these objects EXACTLY as shown — same shape, colour, size, finish.\n"
                "2. PRIOR STEP IMAGES (remaining images): photos from earlier steps "
                "showing the work in progress. Match the scene, environment, and "
                "work state shown in these.\n"
                "Combine both: use the anchor objects' exact appearance within the "
                "scene established by the prior step images."
            )
        elif has_anchor_images:
            reference_instruction = (
                "You are given ANCHOR IMAGES: isolated reference photos of the main "
                "objects in this project. Use these objects EXACTLY as shown — "
                "same shape, colour, size, finish, style. "
                "This is the first step, so establish a consistent scene around them."
            )
        elif has_step_refs:
            reference_instruction = (
                "You are given PRIOR STEP IMAGES from this project. "
                "Match the visual style exactly: same environment, objects, colours, "
                "lighting, and camera angle."
            )
        else:
            reference_instruction = (
                "No reference images provided. Establish a clear photorealistic style "
                "that will be maintained across all subsequent steps."
            )

        user_content = json.dumps({
            "project_summary": summary_text or "",
            "domain": dna.get("domain", "general"),
            "step_description": step_text,
            "reference_image_instruction": reference_instruction,
            "physics_rules": dna.get("physics_rules", []),
            "simplification_rules": dna.get("simplification_rules", []),
            "constraints": (
                "No text, no watermarks, no brand names. "
                "One primary action only. "
                "Do NOT describe object appearance, colours, or environment — "
                "those are visible in the reference images."
            ),
        }, indent=2)

        content = _call_openai(
            api_key=self.settings.OPENAI_API_KEY,
            system=IMAGE_GENERATION_PROMPT,
            user=user_content,
            max_tokens=500,
        )

        if content:
            parsed = _parse_json_safe(content, context=f"image_prompt_step_{step_id}")
            if parsed:
                return (
                    f"{reference_instruction}\n\nACTION: {parsed.get('imagen_prompt', step_text)}{_NEGATIVE_SUFFIX}",
                    parsed.get("state_summary", ""),
                )

        logger.warning(f"_build_prompt failed for step {step_id} — using fallback")
        return (
            f"{reference_instruction}\n\nACTION: Photorealistic image of: {step_text}{_NEGATIVE_SUFFIX}",
            "",
        )
