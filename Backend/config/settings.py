import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


@lru_cache
def get_env_filename():
    runtime_env = os.getenv("ENV")
    return f".env.{runtime_env}" if runtime_env else ".env"


class Settings(BaseSettings):
    # Application settings
    ENVIRONMENT: str
    APP_NAME: str
    APP_VERSION: str
    APP_PORT: int

    # OpenAI settings
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # LangSmith settings
    LANGSMITH_TRACING: str
    LANGSMITH_ENDPOINT: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str

    # Qdrant settings
    QDRANT_API_KEY: str
    QDRANT_URL: str

    # MongoDB settings
    MONGODB_URI: str
    MONGODB_DATABASE: str

    # SerpAPI settings
    SERPAPI_API_KEY: str

    # AWS settings
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-2"
    SQS_URL: str
    AWS_IMAGES_SQS_URL: Optional[str] = None
    AWS_S3_BUCKET: str = "handyimages"
    AWS_S3_PUBLIC_BASE: str = "https://handyimages.s3.us-east-2.amazonaws.com"

    # Google/Gemini settings
    GOOGLE_API_KEY: str
    GEMINI_IMAGE_MODEL: str = "imagen-3.0-generate-002"

    # YouTube settings
    YOUTUBE_API_KEY: str

    # Step guidance agent settings
    STEP_GUIDANCE_MODEL: str = "gpt-5-nano"
    STEP_GUIDANCE_CLASSIFIER_MODEL: str = "gpt-5-nano"
    STEP_GUIDANCE_MAX_TURNS: int = 10
    STEP_GUIDANCE_MIN_REL: float = 0.35

    # Information gathering agent settings
    INFORMATION_GATHERING_AGENT_MODEL: str
    INFORMATION_GATHERING_AGENT_CHECKPOINT_DATABASE: str
    INFORMATION_GATHERING_AGENT_CHECKPOINT_COLLECTION_NAME: str
    INFORMATION_GATHERING_AGENT_CHECKPOINT_WRITES_COLLECTION_NAME: str

    class Config:
        env_file = get_env_filename()


@lru_cache
def get_settings():
    return Settings()
