import json
import re
import time
from typing import Optional

import PIL.Image
import requests
from bson.objectid import ObjectId
from loguru import logger
from pymongo.collection import Collection

from agents.solution_generation_multi_agent.image_generation_agent.image_generation_agent import (
    ImageGenerationAgent,
)
from agents.solution_generation_multi_agent.image_generation_agent.schemas import (
    ImageGenerationResult,
    AnchorObject,
    AnchorObjectsResult,
)
from agents.solution_generation_multi_agent.image_generation_agent.utils import (
    map_size_to_aspect,
    png_to_bytes_ensure_rgba,
    generate_s3_key,
    get_public_url,
)
from agents.solution_generation_multi_agent.prompt_templates.v1.image_generation_agent import (
    IMAGE_GENERATION_PROMPT,
    VISUAL_DNA_PROMPT,
    CONTEXT_IMAGE_PLANNER_PROMPT,
    STEP_PLANNER_PROMPT,
    DOMAIN_PHYSICS_LIBRARY,
    CAMERA_ANGLE_GUIDE,
    OBJECT_ALIGNMENT_RULES,
    HAND_RULES,
)
from config.settings import get_settings
from database.llm_consumption import record_google_image_generation, record_openai_response_usage

GEMINI_IMAGE_MODEL_FLASH = "gemini-2.5-flash-image"

REFERENCE_IMAGE_BUDGET = 8
MAX_CONTEXT_IMAGES = 3
MAX_PRIOR_STEP_REFS = 5

_NEGATIVE_SUFFIX = (
    " Photorealistic, 4K HDR, sharp focus, professional photography. "
    "No text, no labels, no watermarks, no logos, no brand names. "
    "No cartoon or CGI styling. Physically accurate. "
    "No floating objects. Maximum two hands — never three."
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
            {"role": "user", "content": user},
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
        logger.info("Generating Visual DNA")
        content = _call_openai(
            api_key=self.settings.OPENAI_API_KEY,
            system=VISUAL_DNA_PROMPT,
            user=summary_text,
            max_tokens=1000,
        )
        if content:
            dna = _parse_json_safe(content, "visual_dna")
            if dna:
                logger.info(f"Visual DNA — domain: {dna.get('domain')}")
                return dna

        logger.warning("Visual DNA failed — using fallback")
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
            "object_colors": {},
            "simplification_rules": ["Pick the single most visual action from the step"],
        }

    # ─── User uploaded images ─────────────────────────────────────────────────

    def fetch_user_uploaded_image_urls(self, project_id: str) -> list[str]:
        """
        List all user-uploaded images for this project from S3.
        Path pattern: user-uploads/*/projects/{project_id}/*
        Returns public URLs ordered by LastModified ascending (oldest first).
        """
        try:
            prefix = f"user-uploads/"
            paginator = self.s3_client.get_paginator("list_objects_v2")
            all_objects = []

            # S3 doesn't support mid-path wildcards — list broad prefix and filter
            for page in paginator.paginate(
                Bucket=self.settings.AWS_S3_BUCKET,
                Prefix=prefix,
            ):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    # Match: user-uploads/{user_id}/projects/{project_id}/...
                    if f"/projects/{project_id}/" in key:
                        all_objects.append(obj)

            # Sort oldest → newest so context images are in chronological order
            all_objects.sort(key=lambda o: o["LastModified"])

            urls = []
            for obj in all_objects:
                url = get_public_url(obj["Key"], self.settings.AWS_S3_PUBLIC_BASE)
                if url:
                    urls.append(url)

            logger.info(
                f"User uploaded images for project {project_id}: {len(urls)} found"
            )
            return urls

        except Exception as e:
            logger.warning(f"fetch_user_uploaded_image_urls failed: {e}")
            return []

    def load_user_uploaded_images(self, project_id: str) -> list[PIL.Image.Image]:
        """
        Load all user-uploaded images for this project as PIL images.
        Returns empty list if none found or loading fails.
        """
        urls = self.fetch_user_uploaded_image_urls(project_id)
        images = []
        for url in urls:
            pil = self.image_generation_agent.load_image_from_url(url)
            if pil:
                images.append(pil)
                logger.info(f"Loaded user image: {url.split('/')[-1]}")
        logger.info(f"User images loaded as PIL: {len(images)}/{len(urls)}")
        return images

    # ─── Context image planning — smart merge with user uploads ───────────────

    def _plan_needed_context_images(
            self,
            summary_text: str,
            dna: dict,
            user_image_count: int,
    ) -> list[dict]:
        """
        Ask GPT how many context images are needed and what they should show.
        Returns the full plan list — caller decides which to generate vs skip.
        """
        domain = dna.get("domain", "general")
        object_colors = dna.get("object_colors", {})

        content = _call_openai(
            api_key=self.settings.OPENAI_API_KEY,
            system=CONTEXT_IMAGE_PLANNER_PROMPT,
            user=json.dumps({
                "summary": summary_text,
                "domain": domain,
                "object_colors": object_colors,
                "scene_prefix": dna.get("scene_prefix", ""),
            }),
            max_tokens=1000,
        )

        if content:
            parsed = _parse_json_safe(content, "context_image_planner")
            if parsed:
                return parsed.get("context_images", [])

        logger.warning("Context image planning returned no plans")
        return []

    def get_context_images(self, project_id: str) -> Optional[AnchorObjectsResult]:
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"image_context_images": 1}
            )
            if doc and doc.get("image_context_images"):
                return AnchorObjectsResult(**doc["image_context_images"])
            return None
        except Exception as e:
            logger.warning(f"get_context_images failed: {e}")
            return None

    def save_context_images(self, project_id: str, result: AnchorObjectsResult) -> None:
        try:
            self.project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"image_context_images": result.model_dump()}},
            )
            logger.info(f"Context images saved: {[o.name for o in result.objects]}")
        except Exception as e:
            logger.warning(f"save_context_images failed: {e}")

    def build_context_images(
            self,
            project_id: str,
            summary_text: str,
            dna: dict,
    ) -> AnchorObjectsResult:
        """
        Smart context image builder — three cases:

        Case 1: User provided NO images
            → Plan 2-3 context images from summary, generate all of them.

        Case 2: User provided ALL needed images (count >= planned count)
            → Use user images directly, generate nothing.

        Case 3: User provided SOME images (count < planned count)
            → Use user images for the slots they fill (oldest first),
              generate only the remaining slots.

        All results (user + generated) are stored in MongoDB as image_context_images
        so fetch_context_pil_images() works identically regardless of case.
        """
        logger.info(f"Building context images for project {project_id}")

        # 1. Load user uploads
        user_images_pil = self.load_user_uploaded_images(project_id)
        user_image_urls = self.fetch_user_uploaded_image_urls(project_id)
        user_count = len(user_images_pil)

        # 2. Plan what context images are needed
        image_plans = self._plan_needed_context_images(
            summary_text=summary_text,
            dna=dna,
            user_image_count=user_count,
        )
        planned_count = len(image_plans)

        logger.info(
            f"Context image plan: {planned_count} needed, "
            f"{user_count} user-provided — "
            f"Case {'1' if user_count == 0 else '2' if user_count >= planned_count else '3'}"
        )

        results: list[AnchorObject] = []

        # ── Case 2: user provided everything — use as-is ─────────────────────
        if user_count >= planned_count and planned_count > 0:
            logger.info("Case 2: all context images provided by user — no generation needed")
            for i, (plan, url) in enumerate(zip(image_plans, user_image_urls)):
                results.append(AnchorObject(
                    name=plan.get("name", f"user_image_{i + 1}"),
                    description=plan.get("purpose", "User provided image"),
                    s3_key=url.replace(
                        self.settings.AWS_S3_PUBLIC_BASE.rstrip("/") + "/", ""
                    ) if self.settings.AWS_S3_PUBLIC_BASE else url,
                    url=url,
                    status="complete",
                ))
            result = AnchorObjectsResult(objects=results, status="complete")
            self.save_context_images(project_id, result)
            return result

        # ── Case 1 or 3: generate missing slots ──────────────────────────────
        flash_agent = ImageGenerationAgent(model=GEMINI_IMAGE_MODEL_FLASH)

        # Fill slots with user images first (Case 3), then generate the rest
        user_slots_used = 0
        for i, plan in enumerate(image_plans[:MAX_CONTEXT_IMAGES]):
            name = plan.get("name", f"context_{i + 1}")

            # Use a user-provided image for this slot if available
            if user_slots_used < user_count:
                url = user_image_urls[user_slots_used]
                logger.info(
                    f"Slot {i + 1} ('{name}'): using user-provided image "
                    f"{url.split('/')[-1]}"
                )
                results.append(AnchorObject(
                    name=name,
                    description=plan.get("purpose", "User provided image"),
                    s3_key=url.replace(
                        self.settings.AWS_S3_PUBLIC_BASE.rstrip("/") + "/", ""
                    ) if self.settings.AWS_S3_PUBLIC_BASE else url,
                    url=url,
                    status="complete",
                ))
                user_slots_used += 1
                continue

            # No user image available — generate this slot
            prompt = plan.get("prompt", "")
            if not prompt:
                continue

            full_prompt = (
                f"{prompt} "
                f"No people, no hands. Static scene only. "
                f"Photorealistic, 4K HDR, professional photography. "
                f"No text, no labels, no watermarks."
            )

            logger.info(
                f"Slot {i + 1} ('{name}'): generating — "
                f"{plan.get('angle', '')} shot"
            )
            try:
                raw_bytes = flash_agent.generate_image(
                    prompt=full_prompt,
                    reference_images=None,
                    aspect_ratio="16:9",
                    output_mime_type="image/png",
                )
                png_bytes = png_to_bytes_ensure_rgba(raw_bytes)
                s3_key = (
                    f"project_{project_id}/context/"
                    f"{name}_{int(time.time())}.png"
                )
                self.s3_client.put_object(
                    Bucket=self.settings.AWS_S3_BUCKET,
                    Key=s3_key,
                    Body=png_bytes,
                    ContentType="image/png",
                    Metadata={
                        "project_id": project_id,
                        "context_name": name,
                        "angle": plan.get("angle", ""),
                        "type": "context_image_generated",
                    },
                )
                url = get_public_url(s3_key, self.settings.AWS_S3_PUBLIC_BASE)
                results.append(AnchorObject(
                    name=name,
                    description=plan.get("purpose", prompt[:100]),
                    s3_key=s3_key,
                    url=url,
                    status="complete",
                ))
                logger.info(f"Generated context image '{name}': {s3_key}")
            except Exception as e:
                logger.error(f"Failed to generate context image '{name}': {e}")
                continue

        # Case 1 with no plans at all — fall back to user images directly
        if not results and user_count > 0:
            logger.info("No plans generated — using all user images as context directly")
            for i, url in enumerate(user_image_urls):
                results.append(AnchorObject(
                    name=f"user_image_{i + 1}",
                    description="User provided image (no plan available)",
                    s3_key=url.replace(
                        self.settings.AWS_S3_PUBLIC_BASE.rstrip("/") + "/", ""
                    ) if self.settings.AWS_S3_PUBLIC_BASE else url,
                    url=url,
                    status="complete",
                ))

        result = AnchorObjectsResult(objects=results, status="complete")
        self.save_context_images(project_id, result)
        logger.info(
            f"Context images ready: {len(results)} total "
            f"({user_slots_used} from user, {len(results) - user_slots_used} generated)"
        )
        return result

    def fetch_context_pil_images(self, project_id: str) -> list[PIL.Image.Image]:
        """Load context PIL images from stored URLs for passing to Gemini."""
        ctx = self.get_context_images(project_id)
        if not ctx or not ctx.objects:
            return []
        images = []
        for obj in ctx.objects:
            if obj.url and obj.status == "complete":
                pil = self.image_generation_agent.load_image_from_url(obj.url)
                if pil:
                    images.append(pil)
                    logger.info(f"Loaded context image: {obj.name}")
        return images

    # ─── Prior step memory ────────────────────────────────────────────────────

    def fetch_prior_step_states(
            self,
            project_id: str,
            current_step_id: str,
    ) -> list[dict]:
        try:
            doc = self.project_collection.find_one(
                {"_id": ObjectId(project_id)},
                {"step_generation.steps": 1}
            )
            if not doc:
                return []
            steps = doc.get("step_generation", {}).get("steps", [])
            current_idx = int(current_step_id) - 1
            states = []
            for step in steps[:current_idx]:
                img = step.get("image", {})
                if isinstance(img, dict) and img.get("state_summary") and img.get("status") == "complete":
                    states.append({
                        "step_id": str(step.get("order", "")),
                        "state_summary": img["state_summary"],
                    })
            return states[-MAX_PRIOR_STEP_REFS:]
        except Exception as e:
            logger.warning(f"fetch_prior_step_states failed: {e}")
            return []

    def fetch_prior_step_images(
            self,
            project_id: str,
            current_step_id: str,
            budget: int,
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
            images = []
            for step in steps[:current_idx]:
                img_meta = step.get("image", {})
                if not isinstance(img_meta, dict):
                    continue
                url = img_meta.get("url")
                status = img_meta.get("status")
                if url and status == "complete":
                    pil = self.image_generation_agent.load_image_from_url(url)
                    if pil:
                        images.append(pil)
            result = images[-budget:]
            logger.info(f"Prior step images: {len(result)} loaded (budget={budget})")
            return result
        except Exception as e:
            logger.warning(f"fetch_prior_step_images failed: {e}")
            return []

    # ─── Step planning ────────────────────────────────────────────────────────

    def plan_step_image(
        self,
        step_id: str,
        step_text: str,
        summary_text: Optional[str],
        dna: dict,
        prior_states: list[dict],
        project_id: Optional[str],
        user_id: Optional[str],
) -> tuple[str, str]:
    """
    Use GPT to fully plan the image before generating it.
    Injects domain physics, color lock, safety equipment, face rule, shooting plan.
    Returns (structured_imagen_prompt, state_summary).
    """
    domain = dna.get("domain", "general")
    domain_physics = DOMAIN_PHYSICS_LIBRARY.get(
        domain, DOMAIN_PHYSICS_LIBRARY["general"]
    )
    object_colors = dna.get("object_colors", {})
    color_lock = dna.get("color_lock", {})
    safety_equipment = dna.get("safety_equipment", {})
    step_shooting_plan = dna.get("step_shooting_plan", {})
    face_rule = dna.get("face_rule", "Person's face must not be visible.")

    user_content = json.dumps({
        "project_summary": summary_text or "",
        "domain": domain,
        "step_description": step_text,
        "previous_step_states": prior_states,
        "object_color_registry": object_colors,
        "color_lock": color_lock,
        "color_lock_instruction": (
            "These colors are LOCKED and must appear verbatim in imagen_prompt. "
            f"Wall color is '{color_lock.get('wall', 'as specified')}' — "
            "never substitute a different color. Copy these exact strings into the prompt."
        ),
        "safety_equipment_rules": safety_equipment,
        "face_rule": face_rule,
        "step_shooting_plan": step_shooting_plan,
        "domain_physics_rules": domain_physics["physics"],
        "domain_hand_rules": domain_physics["hand_rules"],
        "domain_camera_guide": domain_physics["camera"],
        "domain_alignment_rules": domain_physics.get("alignment", []),
        "domain_impossible_states": domain_physics["impossible_states"],
        "universal_camera_guide": CAMERA_ANGLE_GUIDE,
        "universal_alignment_rules": OBJECT_ALIGNMENT_RULES,
        "universal_hand_rules": HAND_RULES,
    }, indent=2)

    content = _call_openai(
        api_key=self.settings.OPENAI_API_KEY,
        system=STEP_PLANNER_PROMPT,
        user=user_content,
        max_tokens=900,
    )

    if content:
        record_openai_response_usage(
            {"choices": [{"message": {"content": content}}]},
            model="gpt-4o-mini",
            operation="step_image_planning",
            project_id=project_id,
            user_id=user_id,
            endpoint="/v1/chat/completions",
            metadata={"step_id": step_id, "step_text": step_text[:100]},
        )
        parsed = _parse_json_safe(content, f"step_planner_{step_id}")
        if parsed:
            imagen_prompt = parsed.get("imagen_prompt", "")
            state_summary = parsed.get("state_summary", "")
            camera = parsed.get("camera_angle", "medium")
            orientation = parsed.get("orientation_note", "")

            # Inject locked wall color directly — bypasses any GPT paraphrasing
            wall_color = color_lock.get("wall", "")
            color_injection = (
                f"LOCKED WALL COLOR: {wall_color} painted wall — do not substitute. "
                if wall_color else ""
            )

            # Inject face rule directly
            face_injection = (
                "Person's face is NOT visible — shown from behind or side facing away. "
            )

            # Inject safety equipment directly
            safety_this_step = parsed.get("safety_equipment_this_step", [])
            safety_injection = (
                f"Person is wearing: {', '.join(safety_this_step)}. "
                if safety_this_step else ""
            )

            final_prompt = (
                f"CAMERA: {camera} shot. "
                f"{color_injection}"
                f"{face_injection}"
                f"{safety_injection}"
                f"{imagen_prompt} "
                f"{'ORIENTATION: ' + orientation + '. ' if orientation else ''}"
                f"Reference images show exact scene — match all colors except "
                f"wall which is {wall_color or 'as specified in prompt'}. "
                f"{_NEGATIVE_SUFFIX}"
            )
            logger.info(
                f"Step {step_id} plan — camera: {camera}, "
                f"wall: {wall_color}, "
                f"safety: {safety_this_step}, "
                f"action: {parsed.get('primary_action', '')[:60]}"
            )
            return final_prompt, state_summary

    # Fallback — stays on topic even if GPT fails
    logger.warning(f"Step planning failed for step {step_id} — using fallback")
    wall_color = color_lock.get("wall", "")
    return (
        f"CAMERA: medium shot. "
        f"{'LOCKED WALL COLOR: ' + wall_color + ' wall. ' if wall_color else ''}"
        f"Person face not visible — shown from behind. "
        f"Photorealistic image of a person performing: {step_text}. "
        f"Maximum two hands. Objects face toward viewer. "
        f"{_NEGATIVE_SUFFIX}"
    ), ""
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

            # 2. Context images (user uploads + generated — set by preflight)
            context_images: list[PIL.Image.Image] = []
            if project_id:
                context_images = self.fetch_context_pil_images(project_id)
                logger.info(f"Context images loaded: {len(context_images)}")

            # 3. Prior step states — text memory
            prior_states: list[dict] = []
            if project_id:
                prior_states = self.fetch_prior_step_states(project_id, step_id)
                logger.info(f"Prior step states: {len(prior_states)}")

            # 4. Prior step images — visual memory
            prior_image_budget = max(1, REFERENCE_IMAGE_BUDGET - len(context_images))
            prior_step_images: list[PIL.Image.Image] = []
            if project_id:
                prior_step_images = self.fetch_prior_step_images(
                    project_id, step_id, budget=prior_image_budget,
                )

            # 5. Plan the step image
            planned_prompt, state_summary = self.plan_step_image(
                step_id=step_id,
                step_text=step_text,
                summary_text=summary_text,
                dna=dna,
                prior_states=prior_states,
                project_id=project_id,
                user_id=user_id,
            )

            logger.debug(f"Planned prompt step {step_id}:\n{planned_prompt}")

            # 6. Assemble references: context first, then prior steps
            all_references = context_images + prior_step_images
            logger.info(
                f"References: {len(context_images)} context + "
                f"{len(prior_step_images)} prior steps = {len(all_references)} total"
            )

            # 7. Generate
            aspect_ratio = map_size_to_aspect(size)
            raw_bytes = self.image_generation_agent.generate_image(
                prompt=planned_prompt,
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
                    "context_images_count": len(context_images),
                    "step_refs_count": len(prior_step_images),
                    "domain": dna.get("domain", "unknown"),
                },
            )

            # 8. Upload
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
                    "context_count": str(len(context_images)),
                },
            )
            url = get_public_url(s3_key, self.settings.AWS_S3_PUBLIC_BASE)
            logger.info(f"Step {step_id} uploaded: {s3_key}")

            return ImageGenerationResult(
                message="ok",
                step_id=step_id,
                project_id=project_id or "",
                s3_key=s3_key,
                url=url,
                size=size,
                model=self.image_generation_agent.model,
                prompt_preview=planned_prompt,
                state_summary=state_summary,
                status="complete",
            )

        except Exception as e:
            logger.error(f"Error generating step {step_id}: {e}")
            raise
