"""FastAPI web application entrypoint for News Sentiment Analyzer."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from news_sentiment.api.dependencies import get_db
from news_sentiment.api.errors import register_error_handlers
from news_sentiment.api.rate_limit import get_rate_limiter
from news_sentiment.api.router import api_v1_router
from news_sentiment.api.schemas import HealthResponse
from news_sentiment.config.logging import configure_logging, get_logger
from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.models.base import SentimentModel
from news_sentiment.models.registry import get_model, list_models
from news_sentiment.storage.database import init_db

logger = get_logger(__name__)


def preload_registered_models() -> dict[str, SentimentModel]:
    """Preload sentiment models into memory once at application startup for CPU inference."""
    loaded: dict[str, SentimentModel] = {}
    for name in list_models():
        try:
            model = get_model(name)
            # Warm up model prediction pipeline
            model.predict_one("System startup warmup check")
            loaded[name] = model
            logger.info("Preloaded sentiment model: '%s' (v%s)", model.name, model.version)
        except Exception as exc:
            logger.warning(
                "Model '%s' could not be initialized during startup warmup: %s",
                name,
                exc,
                extra={"model_name": name, "error": str(exc)},
            )
    return loaded


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup, database schema initialization, and model preloading."""
    settings = get_settings()
    configure_logging(log_level=settings.log_level, log_format=settings.log_format)
    logger.info(
        "Starting %s (v%s) in %s mode",
        settings.app_name,
        settings.app_version,
        settings.environment,
        extra={"environment": settings.environment, "version": settings.app_version},
    )

    # 1. Initialize database schema
    try:
        init_db()
        logger.info("Database schema initialized successfully")
    except Exception as exc:
        logger.error("Failed to initialize database schema: %s", exc)

    # 2. Configure rate limiter settings
    rate_limiter = get_rate_limiter()
    rate_limiter.requests_per_minute = settings.api_rate_limit_per_minute
    rate_limiter.enabled = (
        settings.environment != "testing" or settings.api_rate_limit_per_minute > 0
    )

    # 3. Preload all registered models once at startup (CPU inference)
    preloaded = preload_registered_models()
    app.state.models = preloaded
    logger.info("Completed startup model preloading: %s", list(preloaded.keys()))

    yield

    logger.info("Shutting down %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_settings = settings or get_settings()

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Production-quality News Sentiment Analyzer API: collect headlines, classify "
            "sentiment with multi-model inference, explain predictions with token attributions, "
            "and track thematic sentiment trends over time."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    if settings is not None:
        application.dependency_overrides[get_settings] = lambda: settings
        limiter = get_rate_limiter()
        limiter.requests_per_minute = settings.api_rate_limit_per_minute

    # 1. Register consistent error handlers
    register_error_handlers(application, debug=app_settings.debug)

    # 2. Configure CORS middleware for frontend origin
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Mount versioned API routes under /api/v1
    application.include_router(api_v1_router)

    # 4. Root system health probe
    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="Service liveness and health probe",
        description="Check API status, database connectivity, and preloaded models.",
    )
    def root_health_check(session: Annotated[Session, Depends(get_db)]) -> HealthResponse:
        db_status = "connected"
        try:
            session.execute(text("SELECT 1"))
        except Exception:
            db_status = "error"

        models = list_models()
        overall = "healthy" if db_status == "connected" else "degraded"

        return HealthResponse(
            status=overall,
            app=app_settings.app_name,
            version=app_settings.app_version,
            environment=app_settings.environment,
            database=db_status,
            models_loaded=models,
        )

    @application.get("/", tags=["System"], summary="API service index")
    def root() -> dict[str, Any]:
        """API service root information."""
        return {
            "name": app_settings.app_name,
            "version": app_settings.app_version,
            "environment": app_settings.environment,
            "docs_url": "/docs",
            "api_v1": "/api/v1",
            "health_url": "/health",
        }

    return application


app = create_app()
