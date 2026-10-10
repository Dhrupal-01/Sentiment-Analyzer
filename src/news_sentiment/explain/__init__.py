"""Explainability module: token attributions, saliency methods, and evaluation metrics."""

from news_sentiment.explain.base import BaseExplainer, Explanation, TokenAttribution
from news_sentiment.explain.evaluation import (
    FaithfulnessResult,
    PerturbationCurve,
    compute_faithfulness_curves,
    compute_jaccard_similarity,
    compute_token_f1,
)
from news_sentiment.explain.integrated_gradients import IntegratedGradientsExplainer
from news_sentiment.explain.occlusion import OcclusionExplainer
from news_sentiment.explain.service import explain, explain_detailed, get_explainer
from news_sentiment.explain.shap_explainer import ShapExplainer
from news_sentiment.explain.tokenizer import TokenSpan, tokenize_with_spans

__all__ = [
    "BaseExplainer",
    "Explanation",
    "FaithfulnessResult",
    "IntegratedGradientsExplainer",
    "OcclusionExplainer",
    "PerturbationCurve",
    "ShapExplainer",
    "TokenAttribution",
    "TokenSpan",
    "compute_faithfulness_curves",
    "compute_jaccard_similarity",
    "compute_token_f1",
    "explain",
    "explain_detailed",
    "get_explainer",
    "tokenize_with_spans",
]
