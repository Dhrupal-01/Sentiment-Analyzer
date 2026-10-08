"""Sentiment model interface, standardized prediction schemas, and label types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

SentimentLabel = Literal["positive", "neutral", "negative"]


@dataclass(frozen=True)
class Prediction:
    """Standardized sentiment prediction outcome."""

    label: SentimentLabel
    score: float  # Continuous sentiment polarity score in [-1.0, 1.0]
    probabilities: dict[str, float]  # Class distribution summing to ~1.0
    metadata: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)

    def __post_init__(self) -> None:
        # Validate score bounds
        clamped_score = max(-1.0, min(1.0, float(self.score)))
        if clamped_score != self.score:
            object.__setattr__(self, "score", clamped_score)


class SentimentModel(ABC):
    """Abstract interface contract for all sentiment classification models."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique model identifier (e.g. 'vader', 'roberta', 'finbert')."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Version or revision identifier for traceability and provenance."""

    @abstractmethod
    def predict(self, texts: list[str]) -> list[Prediction]:
        """Classify a batch of headline texts into standardized Predictions.

        Args:
            texts: List of headline strings to classify.

        Returns:
            List of Prediction dataclass instances matching the input order.
        """

    def predict_one(self, text: str) -> Prediction:
        """Convenience method to classify a single text."""
        results = self.predict([text])
        return results[0]
