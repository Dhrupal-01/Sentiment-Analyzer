"""Protected automation endpoints for scheduled collection and analysis jobs."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from news_sentiment.api.dependencies import get_db
from news_sentiment.api.errors import BadRequestError, UnauthorizedError
from news_sentiment.api.schemas import (
    JobCollectAndAnalyzeRequest,
    JobCollectAndAnalyzeResponse,
)
from news_sentiment.config.logging import get_logger
from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.models.pipeline import InferencePipeline
from news_sentiment.models.registry import get_model
from news_sentiment.sources.service import IngestionService
from news_sentiment.storage.repository import TopicRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs & Automation"])


def verify_cron_auth(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> None:
    """Validate API key authorization for scheduled automated background tasks."""
    provided_token: str | None = None
    if x_api_key:
        provided_token = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_token = authorization[7:].strip()

    if settings.cron_api_key:
        if not provided_token or provided_token != settings.cron_api_key:
            raise UnauthorizedError(
                message="Invalid or missing X-API-Key for protected scheduled job."
            )
    elif settings.environment == "production":
        raise UnauthorizedError(
            message="CRON_API_KEY must be configured in production to execute jobs."
        )


@router.post(
    "/collect-and-analyze",
    response_model=JobCollectAndAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger scheduled collection and model analysis",
    description=(
        "Ingest fresh headlines for active topics and run model inference on unprocessed articles."
    ),
)
def run_collect_and_analyze_job(
    request: JobCollectAndAnalyzeRequest,
    _auth: Annotated[None, Depends(verify_cron_auth)] = None,
    session: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> JobCollectAndAnalyzeResponse:
    """Execute scheduled batch collection and inference pipeline."""
    start_time = time.perf_counter()
    logger.info(
        "Starting scheduled collection & analysis job (source=%s, limit=%d, models=%s)",
        request.source,
        request.limit_per_topic,
        request.models,
    )

    ingestion_service = IngestionService()
    pipeline = InferencePipeline()

    # 1. Collect headlines
    articles_fetched = 0
    articles_inserted = 0
    duplicates_found = 0
    topics_processed = 0

    if request.topic:
        topic_obj = TopicRepository.get_topic(session, request.topic)
        if not topic_obj:
            raise BadRequestError(f"Topic '{request.topic}' not found.")
        summary = ingestion_service.ingest_topic(
            topic=topic_obj.name,
            source=request.source,
            query=topic_obj.query,
            limit=request.limit_per_topic,
            session=session,
        )
        topics_processed = 1
        articles_fetched = summary.articles_fetched
        articles_inserted = summary.articles_inserted
        duplicates_found = summary.duplicates_found
    else:
        summaries = ingestion_service.collect_all(
            source=request.source,
            limit=request.limit_per_topic,
            session=session,
        )
        topics_processed = len(summaries)
        articles_fetched = sum(s.articles_fetched for s in summaries)
        articles_inserted = sum(s.articles_inserted for s in summaries)
        duplicates_found = sum(s.duplicates_found for s in summaries)

    # 2. Run analysis for each specified model
    articles_scored: dict[str, int] = {}
    for model_name in request.models:
        try:
            model = get_model(model_name)
            inf_summary = pipeline.score_unprocessed(
                model=model,
                topic=request.topic,
                batch_size=32,
                session=session,
            )
            articles_scored[model_name] = inf_summary.articles_scored
        except Exception as exc:
            logger.error("Failed to run inference for model '%s': %s", model_name, exc)
            articles_scored[model_name] = 0

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Scheduled job completed in %.2fs: %d fetched, %d inserted, %d scored",
        elapsed,
        articles_fetched,
        articles_inserted,
        sum(articles_scored.values()),
    )

    return JobCollectAndAnalyzeResponse(
        status="completed",
        topics_processed=topics_processed,
        articles_fetched=articles_fetched,
        articles_inserted=articles_inserted,
        duplicates_found=duplicates_found,
        articles_scored=articles_scored,
        elapsed_seconds=round(elapsed, 3),
    )
