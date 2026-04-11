"""Image Generation Agent for creating step-by-step DIY/repair images using Google Imagen."""

from typing import Optional

from google import genai
from google.genai.types import GenerateImagesConfig
from loguru import logger

from config.settings import get_settings


class ImageGenerationAgent:
    """Agent for generating images using Google Imagen via Gemini API."""

    def __init__(self, model: Optional[str] = None):
        """
        Initialize the Image Generation Agent.
        
        Args:
            model: Google Gemini image model (defaults to GOOGLE_GEMINI_IMAGE_MODEL from settings)
        """
        self.settings = get_settings()
        self.model = model or self.settings.GOOGLE_IMAGE_MODEL

        # Initialize Google GenAI client
        # Credentials automatically handled by SDK (env variable GOOGLE_API_KEY)
        self.client = genai.Client(api_key=self.settings.GOOGLE_API_KEY)

        logger.info(f"Initialized ImageGenerationAgent with model: {self.model}")

    def generate_image(
            self,
            prompt: str,
            aspect_ratio: str = "16:9",
            output_mime_type: str = "image/png"
    ) -> bytes:
        """
        Generate image bytes using Google Imagen.
        
        Args:
            prompt: Text prompt for image generation
            aspect_ratio: Aspect ratio (e.g., "16:9", "4:3", "1:1", "3:4", "9:16")
            output_mime_type: Output MIME type (default: "image/png")
            
        Returns:
            Image bytes
        """
        logger.info(f"Generating image with aspect ratio: {aspect_ratio}")

        try:
            resp = self.client.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    output_mime_type=output_mime_type
                ),
            )

            if not resp.generated_images or len(resp.generated_images) == 0:
                raise ValueError("No images generated in response")

            image_bytes = resp.generated_images[0].image.image_bytes
            logger.info(f"Successfully generated image ({len(image_bytes)} bytes)")

            return image_bytes

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise
