"""Image Generation Agent — Gemini 2.5 Flash Image with native visual reference input."""

import io
import urllib.request
from typing import Optional

import PIL.Image
from google import genai
from google.genai.types import GenerateContentConfig, ImageConfig
from loguru import logger

from config.settings import get_settings

# Model that accepts image inputs AND generates images natively
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"


class ImageGenerationAgent:
    """Agent using Gemini 2.5 Flash Image for visually consistent step generation."""

    def __init__(self, model: Optional[str] = None):
        self.settings = get_settings()
        self.model = model or GEMINI_IMAGE_MODEL
        self.client = genai.Client(api_key=self.settings.GOOGLE_API_KEY)
        logger.info(f"ImageGenerationAgent ready — model: {self.model}")

    @staticmethod
    def load_image_from_url(url: str) -> Optional[PIL.Image.Image]:
        """
        Fetch an image from a public URL (e.g. CloudFront/S3) and return
        as a PIL Image. Returns None on failure so callers can degrade gracefully.
        """
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return PIL.Image.open(io.BytesIO(resp.read())).convert("RGB")
        except Exception as e:
            logger.warning(f"Could not load reference image from {url}: {e}")
            return None

    def generate_image(
        self,
        prompt: str,
        reference_images: Optional[list[PIL.Image.Image]] = None,
        aspect_ratio: str = "16:9",
        output_mime_type: str = "image/png",
        max_retries: int = 2,
) -> bytes:
        contents: list = []
        if reference_images:
            contents.extend(self._pil_to_part(img) for img in reference_images)
            logger.info(f"Passing {len(reference_images)} reference image(s) to model")
        contents.append(prompt)

        config = GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=ImageConfig(aspect_ratio=aspect_ratio),
        )

        max_attempts = max_retries + 1
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Generating image — attempt {attempt}")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                candidate = response.candidates[0] if response.candidates else None
                if candidate is None:
                    logger.warning(f"Attempt {attempt}: no candidates — retrying")
                    continue

                if candidate.content is None:
                    finish_reason = getattr(candidate, "finish_reason", "unknown")
                    logger.warning(f"Attempt {attempt}: content is None (finish_reason={finish_reason}) — retrying")
                    continue

                for part in candidate.content.parts:
                    if part.inline_data is not None:
                        logger.info("Image generated successfully")
                        return part.inline_data.data

                logger.warning(f"Attempt {attempt}: no image part in response — retrying")

            except Exception as e:
                if attempt < max_attempts:
                    logger.warning(f"Attempt {attempt} failed: {e} — retrying")
                else:
                    logger.error(f"All {max_attempts} attempts failed: {e}")
                    raise

        raise ValueError("Image generation failed after all retries")

    @staticmethod
    def _pil_to_part(img: PIL.Image.Image):
        from google.genai import types
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")
