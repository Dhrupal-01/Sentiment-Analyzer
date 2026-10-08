"""FastAPI web application entrypoint for News Sentiment Analyzer."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from news_sentiment.config.logging import configure_logging, get_logger
from news_sentiment.config.settings import Settings, get_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycles."""
    settings = get_settings()
    configure_logging(log_level=settings.log_level, log_format=settings.log_format)
    logger.info(
        "Starting %s (v%s) in %s mode",
        settings.app_name,
        settings.app_version,
        settings.environment,
        extra={"environment": settings.environment, "version": settings.app_version},
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_settings = settings or get_settings()

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "News Sentiment Analyzer API: collect headlines, classify sentiment, "
            "explain predictions, and track sentiment trends over time."
        ),
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", tags=["System"])
    def health_check() -> dict[str, Any]:
        """System health and liveness probe."""
        return {
            "status": "healthy",
            "app": app_settings.app_name,
            "version": app_settings.app_version,
            "environment": app_settings.environment,
        }

    @application.get("/", tags=["System"])
    def root() -> dict[str, str]:
        """API service root information."""
        return {
            "message": f"Welcome to {app_settings.app_name}",
            "docs_url": "/docs",
            "health_url": "/health",
        }

    return application


app = create_app()
