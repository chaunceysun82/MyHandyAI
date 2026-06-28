import io
import time
import urllib.request
from typing import Optional

import PIL.Image
from google import genai
from google.genai.types import GenerateContentConfig, ImageConfig
from loguru import logger

from config.settings import get_settings

# Model that accepts image inputs AND generates images natively
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"


class ImageGenerationAgent:

    def __init__(self, model: Optional[str] = None):
        self.settings = get_settings()
        self.model = GEMINI_IMAGE_MODEL
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

                if not response:
                    logger.warning(f"Attempt {attempt}: null response")
                    continue

                candidates = getattr(response, "candidates", None)
                if not candidates:
                    # Try response.parts directly (some SDK versions)
                    parts = getattr(response, "parts", None)
                    if parts:
                        for part in parts:
                            inline = getattr(part, "inline_data", None)
                            if inline and getattr(inline, "data", None):
                                logger.info("Image extracted from response.parts")
                                return inline.data
                    logger.warning(f"Attempt {attempt}: no candidates or parts in response")
                    continue

                # Standard path: candidates[0].content.parts
                content = getattr(candidates[0], "content", None)
                if not content:
                    logger.warning(f"Attempt {attempt}: candidate has no content")
                    continue

                parts = getattr(content, "parts", None) or []
                for part in parts:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        logger.info(f"Image generated successfully ({len(inline.data):,} bytes)")
                        return inline.data

                logger.warning(f"Attempt {attempt}: no image part found in response")

            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {e}")

            if attempt <= max_retries:
                time.sleep(2 ** attempt)

        raise ValueError(f"Image generation failed after {max_retries + 1} attempts")

    @staticmethod
    def _pil_to_part(img: PIL.Image.Image):
        from google.genai import types
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")
