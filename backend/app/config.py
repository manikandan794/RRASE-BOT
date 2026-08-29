"""
Central application configuration.

All configuration is read from environment variables (via a .env file in
development). Nothing in this file should ever contain a real secret -
only defaults that are safe for local development.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Application ---
    APP_ENV: str = "development"
    APP_NAME: str = "RRASE College AI Assistant"
    SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg://rrase_user:change_me@localhost:5432/rrase_college_ai"
    )

    # --- JWT / Auth (Phase 2+) ---
    JWT_SECRET_KEY: str = "dev-only-insecure-jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- AI Providers ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    AI_REQUEST_TIMEOUT_SECONDS: int = 30

    # --- Vector store / RAG ---
    VECTOR_DB_PATH: str = "./vector_store"
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 120
    RAG_TOP_K: int = 4
    RAG_MIN_SIMILARITY: float = 0.15

    # --- Official website import ---
    COLLEGE_WEBSITE_URL: str = "https://rrase.com/"

    # --- Uploads ---
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000"

    # --- Rate limiting (Phase 8+) ---
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> "Settings":
    """Cached settings instance - avoids re-reading the .env file per request."""
    return Settings()
