"""Image Generation Agent — Google Imagen with text-free, physics-accurate prompts."""

from typing import Optional
import re

from google import genai
from google.genai.types import GenerateImagesConfig
from loguru import logger

from config.settings import get_settings


# ─── Hard negative suffix appended to EVERY Imagen prompt ───────────────────
# This bypasses the LLM entirely — guaranteed to reach the model.
_NEGATIVE_SUFFIX = (
    ", photorealistic, 4K HDR, sharp focus, professional photography. "
    "No text, no labels, no letters, no numbers, no annotations, no captions, "
    "no watermarks, no signs, no UI elements. No cartoon or CGI styling. "
    "No physically impossible arrangements. Faces not visible."
)

# ─── Domain-aware physics constraint snippets ────────────────────────────────
_DOMAIN_PHYSICS: dict[str, str] = {
    "plumbing": (
        "All plumbing follows gravity: drain pipes descend below fixtures, "
        "P-trap curves downward then upward to the drain wall connection, "
        "supply lines enter from wall or floor below the basin. "
        "Sink basin is mounted above all drain components."
    ),
    "electrical": (
        "Wires routed correctly along wall studs or conduit, "
        "junction boxes flush-mounted, no exposed live conductors, "
        "panel breakers in correct vertical orientation."
    ),
    "carpentry": (
        "Wood grain direction consistent, joints flush and square, "
        "fasteners countersunk correctly, surfaces level."
    ),
    "roofing": (
        "Shingles overlap downslope, flashing tucked under upper shingles, "
        "water flows away from structure."
    ),
}

# ─── Keywords that trigger each domain ──────────────────────────────────────
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "plumbing": ["sink", "drain", "pipe", "faucet", "p-trap", "toilet",
                  "plumb", "basin", "valve", "water line", "supply line"],
    "electrical": ["wire", "circuit", "breaker", "outlet", "panel",
                    "switch", "conduit", "junction", "electrical"],
    "carpentry": ["wood", "board", "joist", "stud", "frame",
                   "nail", "screw", "joint", "trim", "lumber"],
    "roofing": ["roof", "shingle", "flashing", "gutter", "fascia"],
}


def detect_domain(prompt: str) -> Optional[str]:
    """Return the first matching domain for physics-constraint injection."""
    lower = prompt.lower()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return domain
    return None


def build_final_prompt(imagen_prompt: str) -> str:
    """
    Inject domain physics constraints + hard negative suffix into the prompt.
    This runs client-side, so it always applies regardless of LLM output.
    """
    domain = detect_domain(imagen_prompt)
    physics_insert = ""
    if domain:
        physics_insert = f" IMPORTANT PHYSICAL ACCURACY: {_DOMAIN_PHYSICS[domain]}"
        logger.info(f"Injecting physics constraints for domain: {domain}")

    # Strip any stray text-related words the LLM may have slipped in
    sanitized = re.sub(
        r'\b(label|text overlay|annotation|caption|watermark|sign|written|letter[s]?)\b',
        "",
        imagen_prompt,
        flags=re.IGNORECASE,
    ).strip()

    return f"{sanitized}{physics_insert}{_NEGATIVE_SUFFIX}"


class ImageGenerationAgent:
    """Agent for generating step-by-step DIY images using Google Imagen."""

    def __init__(self, model: Optional[str] = None):
        self.settings = get_settings()
        self.model = model or self.settings.GOOGLE_IMAGE_MODEL
        self.client = genai.Client(api_key=self.settings.GOOGLE_API_KEY)
        logger.info(f"ImageGenerationAgent ready — model: {self.model}")

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        output_mime_type: str = "image/png",
        max_retries: int = 2,
    ) -> bytes:
        """
        Generate a step image.

        Args:
            prompt:           Raw Imagen prompt from the prompt-engineer LLM.
            aspect_ratio:     "16:9" | "4:3" | "1:1" | "3:4" | "9:16"
            output_mime_type: Default "image/png"
            max_retries:      Retry on empty/failed response (default 2)

        Returns:
            PNG/JPEG bytes of the generated image.
        """
        final_prompt = build_final_prompt(prompt)
        logger.debug(f"Final Imagen prompt ({len(final_prompt)} chars):\n{final_prompt}")

        for attempt in range(1, max_retries + 2):
            try:
                logger.info(f"Generating image — attempt {attempt}, ratio: {aspect_ratio}")
                resp = self.client.models.generate_images(
                    model=self.model,
                    prompt=final_prompt,
                    config=GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                        output_mime_type=output_mime_type,
                    ),
                )

                if not resp.generated_images:
                    logger.warning(f"Attempt {attempt}: no images returned — retrying")
                    continue

                image_bytes = resp.generated_images[0].image.image_bytes
                logger.info(f"Image generated successfully ({len(image_bytes):,} bytes)")
                return image_bytes

            except Exception as e:
                if attempt <= max_retries:
                    logger.warning(f"Attempt {attempt} failed: {e} — retrying")
                else:
                    logger.error(f"All {max_retries + 1} attempts failed: {e}")
                    raise

        raise ValueError("Image generation failed after all retries")
