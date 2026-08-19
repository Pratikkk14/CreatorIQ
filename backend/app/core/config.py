import os
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Support both case variations or exact from user env
    postgres_db: str = Field(alias="POSTGRES_DB", default="")
    database_url: str = Field(alias="DATABASE_URL", default="")
    
    youtube_api_key: str = Field(alias="Youtube_API_KEY", default="")
    youtube_api_base_url: str = Field(alias="YOUTUBE_API_BASE_URL", default="https://www.googleapis.com/youtube/v3")
    youtube_api_timeout: int = Field(alias="YOUTUBE_API_TIMEOUT_SECONDS", default=30)
    youtube_api_max_retries: int = Field(alias="YOUTUBE_API_MAX_RETRIES", default=3)
    youtube_api_retry_backoff: float = Field(alias="YOUTUBE_API_RETRY_BACKOFF_SECONDS", default=2.0)
    
    gemini_api_key: str = Field(alias="Gemini_API_Key", default="")
    
    ollama_base_url: str = Field(alias="OLLAMA_BASE_URL", default="http://localhost:11434")
    ollama_embedding_model: str = Field(alias="OLLAMA_EMBEDDING_MODEL", default="nomic-embed-text")
    
    app_env: str = Field(alias="APP_ENV", default="development")
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")
    
    # Path to YAML configs
    config_dir: str = Field(default=str(BASE_DIR / "config"))
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )

    def get_db_url(self) -> str:
        url = self.database_url or self.postgres_db
        if not url:
            raise ValueError("No database URL configured. Please set POSTGRES_DB or DATABASE_URL.")
        # Replace postgresql:// with postgresql+psycopg2:// for SQLAlchemy standard driver
        if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

# Instantiate settings
settings = Settings()

# Helper functions to load YAML configurations
def load_yaml_config(filename: str) -> Dict[str, Any]:
    path = Path(settings.config_dir) / filename
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def get_concepts_config() -> List[Dict[str, Any]]:
    config = load_yaml_config("concepts.yaml")
    return config.get("concepts", [])

def get_pipeline_config() -> Dict[str, Any]:
    return load_yaml_config("pipeline.yaml").get("pipeline", {})

def get_selection_config() -> Dict[str, Any]:
    return load_yaml_config("selection.yaml").get("selection", {})
