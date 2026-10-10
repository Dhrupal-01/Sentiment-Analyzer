"""Router for model registry metadata and benchmark evaluation metrics."""

from fastapi import APIRouter, Depends

from news_sentiment.api.dependencies import rate_limit_check
from news_sentiment.api.schemas import ErrorResponse, ModelsRegistryResponse
from news_sentiment.api.service import get_models_registry_service

router = APIRouter(prefix="/models", tags=["Models Registry"])


@router.get(
    "",
    response_model=ModelsRegistryResponse,
    summary="List registered sentiment models and evaluation metrics",
    description=(
        "Retrieve all models currently registered in the system (e.g. VADER baseline, "
        "RoBERTa, FinBERT, fine-tuned DistilRoBERTa), their training domains, benchmark "
        "contamination status, accuracy/F1 performance scores, and explainability metrics."
    ),
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_check)],
)
def list_models_registry() -> ModelsRegistryResponse:
    """Retrieve all models from the registry with metadata and benchmark metrics."""
    return get_models_registry_service()
