from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from news_sentiment.api.dependencies import get_db
from news_sentiment.api.schemas import HealthResponse
from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.models.registry import list_models

router = APIRouter(prefix="", tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health and liveness probe",
    description="Check API service availability, runtime environment, DB connectivity, and models.",
)
def get_health(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Evaluate database connectivity, model availability, and runtime status."""

    # Verify database connection
    db_status = "connected"
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    models = list_models()
    overall = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall,
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        models_loaded=models,
    )
