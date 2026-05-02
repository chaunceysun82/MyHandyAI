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
        """
        Generate a step image using Gemini 2.5 Flash Image.

        Args:
            prompt:           Text prompt describing the action for this step.
            reference_images: PIL images from prior steps — passed directly to
                              the model as visual context. The model sees them
                              natively, not as text descriptions.
            aspect_ratio:     "16:9" | "4:3" | "1:1" | "3:4" | "9:16"
            output_mime_type: "image/png" (default) or "image/jpeg"
            max_retries:      Retry count on empty response.

        Returns:
            Raw image bytes.
        """
        # Build contents: [ref_image_1, ref_image_2, ..., prompt_text]
        # Gemini 2.5 Flash Image reads the images, then follows the text instruction.
        contents: list = []
        if reference_images:
            contents.extend(reference_images)
            logger.info(f"Passing {len(reference_images)} reference image(s) to model")
        contents.append(prompt)

        config = GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=ImageConfig(aspect_ratio=aspect_ratio),
        )

        for attempt in range(1, max_retries + 2):
            try:
                logger.info(f"Generating image — attempt {attempt}")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                # Extract image bytes from response
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        logger.info("Image generated successfully")
                        return part.inline_data.data

                logger.warning(f"Attempt {attempt}: no image part in response — retrying")

            except Exception as e:
                if attempt <= max_retries:
                    logger.warning(f"Attempt {attempt} failed: {e} — retrying")
                else:
                    logger.error(f"All attempts failed: {e}")
                    raise

        raise ValueError("Image generation failed after all retries")
