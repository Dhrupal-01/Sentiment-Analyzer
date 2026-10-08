"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration settings for News Sentiment Analyzer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(
        default="News Sentiment Analyzer",
        description="Application display name",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Application semantic version",
    )
    environment: Literal["development", "testing", "staging", "production"] = Field(
        default="development",
        description="Execution environment",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_format: Literal["console", "json"] = Field(
        default="console",
        description="Structured log format ('console' or 'json')",
    )
    database_url: str = Field(
        default="sqlite:///./news_sentiment.db",
        description="Database connection URL (Postgres or SQLite)",
    )
    api_host: str = Field(
        default="127.0.0.1",
        description="Host interface for the FastAPI server",
    )
    api_port: int = Field(
        default=8000,
        description="Port for the FastAPI server",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins for the frontend",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
