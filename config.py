import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, ValidationError

# Load .env during local development (no impact in prod where env vars are set)
load_dotenv(dotenv_path=Path(".env"))


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    # Embeddings provider (local HuggingFace model)
    embedding_model_name: str = Field(
        default="BAAI/bge-small-en-v1.5",
        env="EMBEDDING_MODEL_NAME",
        description="Name of the local HuggingFace embedding model.",
    )

    # Qdrant configuration (optional when using local path in qdrant_client)
    qdrant_url: Optional[str] = Field(default=None, env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(
        default=None,
        env="QDRANT_API_KEY",
        description="Optional: API key for managed Qdrant (not needed for local).",
    )
    qdrant_collection_name: str = Field(
        default="loan_documents",
        env="QDRANT_COLLECTION_NAME",
        description="Default collection used for loan document chunks.",
    )

    # LLM for War Room agents (OpenAI-compatible: Ollama, Groq, etc.; no OpenAI API key)
    llm_base_url: Optional[str] = Field(
        default="http://localhost:11434/v1",
        env="LLM_BASE_URL",
        description="Base URL for LLM API (e.g. Ollama http://localhost:11434/v1).",
    )
    llm_model: str = Field(
        default="llama3.1",
        env="LLM_MODEL",
        description="Model name for War Room agents.",
    )
    llm_api_key: Optional[str] = Field(
        default=None,
        env="LLM_API_KEY",
        description="Optional API key (e.g. GROQ_API_KEY for Groq). Leave blank for Ollama.",
    )

    # General
    environment: str = Field(
        default="local",
        env="ENVIRONMENT",
        description="Environment label (local, dev, prod, etc.).",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; fails fast if env is misconfigured."""
    try:
        return Settings()  # type: ignore[arg-type]
    except ValidationError as exc:
        # Surface a readable error early instead of failing deep in the pipeline.
        raise RuntimeError(
            f"Configuration error. Check your environment variables or .env file. "
            f"Details: {exc}"
        ) from exc


def get_collection_name(override: Optional[str] = None) -> str:
    """Resolve collection name from CLI override or environment."""
    if override:
        return override
    return get_settings().qdrant_collection_name