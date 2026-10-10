"""Base dataclasses and interfaces for model explainability and token attributions."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from news_sentiment.models.base import SentimentModel


@dataclass(frozen=True)
class TokenAttribution:
    """Token-level attribution weight explaining a model's prediction score."""

    token: str
    weight: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {"token": self.token, "weight": round(self.weight, 4)}


@dataclass(frozen=True)
class Explanation:
    """Complete feature attribution explanation for a text prediction."""

    text: str
    model_name: str
    model_version: str
    method: str
    prediction_label: str
    prediction_score: float
    attributions: list[TokenAttribution]

    def top_k(self, k: int = 3, absolute: bool = True) -> list[TokenAttribution]:
        """Extract top-k most influential tokens by weight magnitude."""
        if absolute:
            return sorted(self.attributions, key=lambda a: abs(a.weight), reverse=True)[:k]
        return sorted(self.attributions, key=lambda a: a.weight, reverse=True)[:k]

    def top_k_tokens(self, k: int = 3, absolute: bool = True) -> list[str]:
        """Extract the token strings of the top-k most influential tokens."""
        return [a.token for a in self.top_k(k=k, absolute=absolute)]

    def to_dict(self) -> dict[str, Any]:
        """Convert explanation to JSON-serializable dictionary."""
        return {
            "text": self.text,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "method": self.method,
            "prediction_label": self.prediction_label,
            "prediction_score": round(self.prediction_score, 4),
            "attributions": [asdict(a) for a in self.attributions],
            "top_3_tokens": self.top_k_tokens(k=3),
        }


class BaseExplainer(ABC):
    """Abstract explainer interface generating token attributions for sentiment models."""

    @abstractmethod
    def explain(self, text: str, model: SentimentModel) -> Explanation:
        """Generate token attributions explaining the model's continuous prediction score."""
        raise NotImplementedError
