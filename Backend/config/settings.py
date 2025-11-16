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
    ENVIRONMENT: str
    APP_NAME: str
    APP_VERSION: str
    APP_PORT: int

    OPENAI_API_KEY: str

    LANGSMITH_TRACING: str
    LANGSMITH_ENDPOINT: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str

    QDRANT_API_KEY: str
    QDRANT_URL: str

    MONGODB_URI: str
    MONGODB_DATABASE: str

    SERPAPI_API_KEY: str

    SQS_URL: str

    INFORMATION_GATHERING_AGENT_MODEL: str
    INFORMATION_GATHERING_AGENT_CHECKPOINT_DATABASE: str
    INFORMATION_GATHERING_AGENT_CHECKPOINT_COLLECTION_NAME: str
    INFORMATION_GATHERING_AGENT_CHECKPOINT_WRITES_COLLECTION_NAME: str

    class Config:
        env_file = get_env_filename()


@lru_cache
def get_settings():
    return Settings()
