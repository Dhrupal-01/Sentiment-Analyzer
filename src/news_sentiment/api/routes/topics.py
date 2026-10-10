"""Router for news tracking topics, headlines, summaries, and trends."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from news_sentiment.api.dependencies import get_db, rate_limit_check
from news_sentiment.api.schemas import (
    ErrorResponse,
    PaginatedHeadlinesResponse,
    TopicCreateRequest,
    TopicResponse,
    TopicsListResponse,
    TopicSummaryResponse,
    TopicTrendResponse,
)
from news_sentiment.api.service import (
    create_topic_service,
    get_topic_headlines_service,
    get_topic_summary_service,
    get_topic_trend_service,
    list_topics_service,
)

router = APIRouter(prefix="/topics", tags=["Topics & Headlines"])


@router.get(
    "",
    response_model=TopicsListResponse,
    summary="List all news tracking topics",
    description="Retrieve all configured topics alongside their current ingested article counts.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def list_topics(
    session: Annotated[Session, Depends(get_db)],
    active_only: Annotated[bool, Query(description="Filter only active tracking topics")] = False,
) -> TopicsListResponse:
    """List configured news tracking topics."""
    return list_topics_service(session=session, active_only=active_only)


@router.post(
    "",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a tracking topic",
    description="Register a new thematic news topic and query string for automated ingestion.",
    responses={
        422: {"model": ErrorResponse, "description": "Validation error on name or query length"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def create_topic(
    payload: TopicCreateRequest,
    session: Annotated[Session, Depends(get_db)],
) -> TopicResponse:
    """Create a new news tracking topic."""
    return create_topic_service(
        session=session,
        name=payload.name,
        query=payload.query,
        is_active=payload.is_active,
    )


@router.get(
    "/{id}/headlines",
    response_model=PaginatedHeadlinesResponse,
    summary="Get paginated headlines for a topic",
    description=(
        "Retrieve paginated articles for a specific topic, filterable by date range, "
        "news publisher outlet, predicted sentiment label, and sentiment model."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Topic not found"},
        422: {"model": ErrorResponse, "description": "Invalid pagination parameters"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def get_topic_headlines(
    id: int,
    session: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page (max 100)")] = 20,
    start_date: Annotated[datetime | None, Query(description="Earliest publication date")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest publication date")] = None,
    source: Annotated[
        str | None, Query(description="Filter by publisher outlet or provider")
    ] = None,
    label: Annotated[str | None, Query(description="Filter by sentiment label")] = None,
    model: Annotated[str | None, Query(description="Filter predictions by model name")] = None,
) -> PaginatedHeadlinesResponse:
    """Retrieve paginated headlines filtered by date, source, label, and model."""
    return get_topic_headlines_service(
        session=session,
        topic_id=id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        source=source,
        label=label,
        model=model,
    )


@router.get(
    "/{id}/summary",
    response_model=TopicSummaryResponse,
    summary="Get sentiment distribution and average score for a topic",
    description=(
        "Compute overall sentiment distribution (counts and percentages) and average "
        "continuous score for a topic within an optional date range."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Topic not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def get_topic_summary(
    id: int,
    session: Annotated[Session, Depends(get_db)],
    model: Annotated[str, Query(description="Sentiment model to aggregate scores from")] = "vader",
    start_date: Annotated[datetime | None, Query(description="Earliest publication date")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest publication date")] = None,
) -> TopicSummaryResponse:
    """Retrieve aggregate sentiment statistics for a topic."""
    return get_topic_summary_service(
        session=session,
        topic_id=id,
        model_name=model,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/{id}/trend",
    response_model=TopicTrendResponse,
    summary="Get daily sentiment and headline volume trend",
    description=(
        "Retrieve a daily chronological time series of sentiment scores and publication "
        "volumes for charting."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Topic not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def get_topic_trend(
    id: int,
    session: Annotated[Session, Depends(get_db)],
    model: Annotated[str, Query(description="Sentiment model to aggregate scores from")] = "vader",
    start_date: Annotated[datetime | None, Query(description="Earliest publication date")] = None,
    end_date: Annotated[datetime | None, Query(description="Latest publication date")] = None,
) -> TopicTrendResponse:
    """Retrieve daily sentiment and headline volume time series for a topic."""
    return get_topic_trend_service(
        session=session,
        topic_id=id,
        model_name=model,
        start_date=start_date,
        end_date=end_date,
    )
