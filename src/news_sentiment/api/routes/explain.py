from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from news_sentiment.api.dependencies import get_db, rate_limit_check
from news_sentiment.api.schemas import ErrorResponse, ExplainRequest, ExplainResponse
from news_sentiment.api.service import explain_text

router = APIRouter(prefix="", tags=["Explainability"])


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Generate token attributions explaining a prediction score",
    description=(
        "Compute signed feature attribution weights in [-1.0, 1.0] explaining a specific model's "
        "sentiment prediction score on a headline. Supported methods include 'occlusion' "
        "(leave-one-out), 'integrated_gradients' (Captum path-integral), and 'shap' "
        "(partition explainer). Caches results in SQLite if an article_id is supplied."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid model or explanation method"},
        422: {"model": ErrorResponse, "description": "Validation error on headline text limits"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def explain_headline(
    payload: ExplainRequest,
    session: Annotated[Session, Depends(get_db)],
) -> ExplainResponse:
    """Explain prediction score on a headline using the requested attribution method."""
    return explain_text(
        text=payload.text,
        model_name=payload.model,
        method=payload.method,
        article_id=payload.article_id,
        session=session,
    )
