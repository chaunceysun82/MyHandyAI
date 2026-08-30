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
    ENVIRONMENT: str = "production"
    APP_NAME: str = "MyHandyAI"
    APP_VERSION: str = "0.1.0"
    APP_PORT: int = 8000

    # OpenAI settings
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # LangSmith settings
    LANGSMITH_TRACING: str = "false"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "myhandyai"

    # Qdrant settings
    QDRANT_API_KEY: str = ""
    QDRANT_URL: str = ""

    # MongoDB settings
    MONGODB_URI: str = ""
    MONGODB_DATABASE: str = "MyHandyAI"

    # SerpAPI settings
    SERPAPI_API_KEY: str = ""

    # AWS settings
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-2"
    AWS_SQS_URL: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_S3_PUBLIC_BASE: str = ""

    # Google/Gemini settings
    GOOGLE_API_KEY: str = ""
    GOOGLE_IMAGE_MODEL: str = "imagen-4"

    # YouTube settings
    YOUTUBE_API_KEY: str = ""

    # Step guidance agent settings
    PROJECT_ASSISTANT_AGENT_MODEL: str = "gpt-5-mini"

    # Information gathering agent settings
    INFORMATION_GATHERING_AGENT_MODEL: str = "gpt-5-mini"

    # MyHandyAI agents settings
    MYHANDYAI_AGENTS_CHECKPOINT_DATABASE: str = "MyHandyAI"
    MYHANDYAI_AGENTS_CHECKPOINT_COLLECTION_NAME: str = "AgentCheckpoints"
    MYHANDYAI_AGENTS_CHECKPOINT_WRITES_COLLECTION_NAME: str = "AgentCheckpointWrites"

    # Cognito auth settings
    COGNITO_REGION: Optional[str] = None
    COGNITO_USER_POOL_ID: Optional[str] = None
    COGNITO_APP_CLIENT_ID: Optional[str] = None

    class Config:
        env_file = get_env_filename()


@lru_cache
def get_settings():
    return Settings()
