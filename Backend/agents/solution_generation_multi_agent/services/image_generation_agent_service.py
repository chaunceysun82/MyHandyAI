"""Service for image generation with business logic for prompt building and image processing."""

import json
from typing import Optional

import requests
from loguru import logger

from agents.solution_generation_multi_agent.image_generation_agent.image_generation_agent import ImageGenerationAgent
from agents.solution_generation_multi_agent.image_generation_agent.schemas import ImageGenerationResult
from agents.solution_generation_multi_agent.image_generation_agent.utils import (
    map_size_to_aspect,
    png_to_bytes_ensure_rgba,
    generate_s3_key,
    get_public_url
)
from agents.solution_generation_multi_agent.prompt_templates.v1.image_generation_agent import IMAGE_GENERATION_PROMPT
from config.settings import get_settings


class ImageGenerationAgentService:
    """Service for image generation with business logic for prompt building and S3 upload."""

    def __init__(
            self,
            image_generation_agent: ImageGenerationAgent,
            s3_client
    ):
        """
        Initialize the Image Generation Agent Service.
        
        Args:
            image_generation_agent: ImageGenerationAgent instance
            s3_client: Boto3 S3 client for uploading images
            settings: Settings instance (defaults to get_settings())
        """
        self.image_generation_agent = image_generation_agent
        self.s3_client = s3_client
        self.settings = get_settings()

    def generate_step_image(
            self,
            step_id: str,
            step_text: str,
            summary_text: Optional[str] = None,
            size: str = "1536x1024",
            project_id: Optional[str] = None
    ) -> ImageGenerationResult:
        """
        Generate image for a step with prompt building and S3 upload.
        
        Args:
            step_id: Step identifier
            step_text: Text description of the current step
            summary_text: Overall project summary (for context)
            size: Image size in format "WxH" (e.g., "1536x1024")
            project_id: Project identifier
            
        Returns:
            ImageGenerationResult with S3 key, URL, and metadata
        """
        logger.info(f"Generating image for step {step_id}, size: {size}")

        try:
            # 1. Build prompt using OpenAI (prompt engineering)
            prompt = self._build_prompt(step_text, summary_text)

            # 2. Map size to aspect ratio
            aspect_ratio = map_size_to_aspect(size)

            # 3. Generate image using Google Imagen
            raw_png = self.image_generation_agent.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png"
            )

            # 4. Normalize PNG to RGBA
            png_bytes = png_to_bytes_ensure_rgba(raw_png)

            # 5. Generate S3 key
            s3_key = generate_s3_key(step_id, project_id)

            # 6. Upload to S3
            self.s3_client.put_object(
                Bucket=self.settings.AWS_S3_BUCKET,
                Key=s3_key,
                Body=png_bytes,
                ContentType="image/png",
                Metadata={
                    "step_id": step_id,
                    "project_id": project_id or "",
                    "size": size,
                    "model": self.image_generation_agent.model
                },
            )

            # 7. Generate public URL
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
                status="complete"
            )

        except Exception as e:
            logger.error(f"Error generating step image: {e}")
            raise

    def _build_prompt(self, step_text: str, summary_text: Optional[str] = None) -> str:
        """
        Build image generation prompt using OpenAI to generate an optimized Imagen prompt.
        
        Args:
            step_text: Text description of the current step
            summary_text: Overall project summary (for context)
            
        Returns:
            Final prompt string for Imagen
        """
        logger.debug("Building image generation prompt")

        # Use OpenAI to generate an optimized prompt for Imagen
        payload = {
            "model": "gpt-5-nano",
            "messages": [
                {
                    "role": "system",
                    "content": IMAGE_GENERATION_PROMPT
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
                        "constraints": "no text, no watermarks, no logos, photorealistic only"
                    }, indent=2)
                }
            ],
            "max_completion_tokens": 2000,
            "reasoning_effort": "low",
            "verbosity": "low"
        }

        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.OPENAI_API_KEY}"},
                json=payload,
                timeout=30
            )
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON response to extract imagen_prompt
            try:
                prompt_json = json.loads(content)
                imagen_prompt = prompt_json.get("imagen_prompt", content)
            except json.JSONDecodeError:
                # Fallback: use content directly if not JSON
                imagen_prompt = content

            return imagen_prompt.strip()

        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            raise
