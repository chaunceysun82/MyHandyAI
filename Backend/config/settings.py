import os
from functools import lru_cache

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
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_SQS_URL: str
    AWS_S3_BUCKET: str
    AWS_S3_PUBLIC_BASE: str

    # Google/Gemini settings
    GOOGLE_API_KEY: str
    GOOGLE_IMAGE_MODEL: str

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
