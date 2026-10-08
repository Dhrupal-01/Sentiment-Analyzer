"""Sentiment model layer: interfaces, implementations, registry, and inference pipeline."""

from news_sentiment.models.base import Prediction, SentimentLabel, SentimentModel
from news_sentiment.models.metrics import (
    DisagreementItem,
    PairwiseMetric,
    compare_model_predictions,
    compute_agreement_rate,
    compute_cohen_kappa,
)
from news_sentiment.models.pipeline import (
    InferencePipeline,
    InferenceSummary,
    ModelComparisonReport,
)
from news_sentiment.models.registry import (
    get_model,
    get_model_domain,
    list_models,
    register_model,
)
from news_sentiment.models.transformer import HFTransformerModel
from news_sentiment.models.vader import VaderModel

__all__ = [
    "DisagreementItem",
    "HFTransformerModel",
    "InferencePipeline",
    "InferenceSummary",
    "ModelComparisonReport",
    "PairwiseMetric",
    "Prediction",
    "SentimentLabel",
    "SentimentModel",
    "VaderModel",
    "compare_model_predictions",
    "compute_agreement_rate",
    "compute_cohen_kappa",
    "get_model",
    "get_model_domain",
    "list_models",
    "register_model",
]
