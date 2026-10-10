"""Router for sentiment classification analysis endpoints."""

from fastapi import APIRouter, Depends

from news_sentiment.api.dependencies import rate_limit_check
from news_sentiment.api.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from news_sentiment.api.service import analyze_texts

router = APIRouter(prefix="", tags=["Sentiment Analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Classify sentiment for one or more headlines",
    description=(
        "Classify sentiment polarity (score in [-1.0, 1.0]) and class probabilities "
        "(positive, neutral, negative) across one or more news headlines using selected models. "
        "Supports batch evaluation up to 50 items."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid model selection"},
        422: {"model": ErrorResponse, "description": "Validation error on input texts or limits"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def analyze_headlines(payload: AnalyzeRequest) -> AnalyzeResponse:
    """Classify sentiment across one or more headlines with registered models."""
    return analyze_texts(texts=payload.texts, model_names=payload.models)
