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
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins for the frontend",
    )
    api_rate_limit_per_minute: int = Field(
        default=120,
        description="Maximum requests per minute per IP",
    )
    api_max_batch_size: int = Field(
        default=50,
        description="Maximum texts batch size for /analyze endpoint",
    )
    api_max_text_length: int = Field(
        default=1000,
        description="Maximum character length per analyzed text",
    )
    newsapi_key: str | None = Field(
        default=None,
        description="Optional NewsAPI API key (developer/free tier)",
    )
    request_timeout: float = Field(
        default=15.0,
        description="HTTP request timeout in seconds",
    )
    rate_limit_gdelt: float = Field(
        default=1.0,
        description="Minimum seconds interval between GDELT requests",
    )
    rate_limit_rss: float = Field(
        default=0.5,
        description="Minimum seconds interval between RSS feed requests",
    )
    rate_limit_newsapi: float = Field(
        default=1.0,
        description="Minimum seconds interval between NewsAPI requests",
    )
    default_rss_feeds: list[str] = Field(
        default=[
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "https://feeds.npr.org/1004/rss.xml",
            "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=markets&sort=date",
        ],
        description="Default list of publisher RSS feed URLs for ingestion",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
