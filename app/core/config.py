from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Transaction Processing Pipeline"
    api_prefix: str = "/api/v1"
    environment: str = "local"

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@db:5432/transactions"
    )
    redis_url: str = "redis://redis:6379/0"

    upload_dir: Path = Path("uploads")
    max_upload_mb: int = 10

    llm_provider: Literal["heuristic", "gemini", "openai", "ollama"] = "heuristic"
    llm_model: str = "gemini-1.5-flash"
    llm_api_key: str | None = None
    ollama_base_url: str = "http://ollama:11434"
    llm_timeout_seconds: int = 45

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
