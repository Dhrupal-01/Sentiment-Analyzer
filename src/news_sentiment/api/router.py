"""Aggregator router for versioned /api/v1 endpoints."""

from fastapi import APIRouter

from news_sentiment.api.routes.analyze import router as analyze_router
from news_sentiment.api.routes.explain import router as explain_router
from news_sentiment.api.routes.health import router as health_router
from news_sentiment.api.routes.jobs import router as jobs_router
from news_sentiment.api.routes.models import router as models_router
from news_sentiment.api.routes.topics import router as topics_router

api_v1_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(analyze_router)
api_v1_router.include_router(explain_router)
api_v1_router.include_router(topics_router)
api_v1_router.include_router(models_router)
api_v1_router.include_router(jobs_router)

__all__ = ["api_v1_router"]
