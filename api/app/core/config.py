"""Application configuration loaded from environment variables and .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings for the NIDS API.

    Values are read from environment variables first, then from a ``.env`` file
    located in the project root.  Defaults are provided for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://nids:nids@localhost:5432/nids"

    # ── API server ────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False
    API_CORS_ORIGINS: list[str] = ["*"]

    # ── MLflow ────────────────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # ── Metadata ──────────────────────────────────────────────────────────
    API_TITLE: str = "TheAutisticNIDS API"
    API_VERSION: str = "0.1.0"


# Module-level singleton – import this everywhere.
settings = Settings()
