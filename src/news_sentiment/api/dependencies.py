"""FastAPI route dependencies for database sessions and rate limiting."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from news_sentiment.api.rate_limit import SimpleRateLimiter, get_rate_limiter
from news_sentiment.storage.database import get_db_session


def get_db() -> Iterator[Session]:
    """Provide a scoped SQLAlchemy database session for API endpoints."""
    with get_db_session() as session:
        yield session


def rate_limit_check(
    request: Request,
    limiter: Annotated[SimpleRateLimiter, Depends(get_rate_limiter)],
) -> None:
    """Evaluate sliding-window rate limit on incoming request."""
    limiter.check(request)
