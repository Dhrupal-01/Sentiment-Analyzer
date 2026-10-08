"""Hugging Face sequence classification transformer model wrapper."""

from collections.abc import Callable
from typing import Any

from news_sentiment.models.base import Prediction, SentimentLabel, SentimentModel

DEFAULT_LABEL_MAPPINGS: dict[str, dict[str, SentimentLabel]] = {
    "cardiffnlp/twitter-roberta-base-sentiment-latest": {
        "positive": "positive",
        "neutral": "neutral",
        "negative": "negative",
        "LABEL_0": "negative",
        "LABEL_1": "neutral",
        "LABEL_2": "positive",
    },
    "ProsusAI/finbert": {
        "positive": "positive",
        "neutral": "neutral",
        "negative": "negative",
        "LABEL_0": "positive",
        "LABEL_1": "negative",
        "LABEL_2": "neutral",
    },
}

MODEL_TRAINING_DOMAINS: dict[str, str] = {
    "cardiffnlp/twitter-roberta-base-sentiment-latest": (
        "Twitter / X English social media corpus (approx. 124M tweets). "
        "Domain characteristics: conversational shorthand, informal syntax, slang, "
        "high emotional variance."
    ),
    "ProsusAI/finbert": (
        "Financial PhraseBank and corporate financial communications. "
        "Domain characteristics: financial market terminology, corporate earnings, "
        "M&A statements, macro indicators."
    ),
}


class HFTransformerModel(SentimentModel):
    """Sequence-classification transformer model loaded from Hugging Face Hub."""

    def __init__(
        self,
        model_id: str,
        name: str | None = None,
        revision: str = "main",
        label_mapping: dict[str, SentimentLabel] | None = None,
        pipeline_factory: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.model_id = model_id
        self._name = name or model_id.split("/")[-1]
        self.revision = revision
        self.label_mapping = label_mapping or DEFAULT_LABEL_MAPPINGS.get(model_id, {})
        self.pipeline_factory = pipeline_factory
        self._pipeline: Any = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return f"{self.model_id}@{self.revision}"

    @property
    def training_domain(self) -> str:
        """Documented domain on which this model was pre-trained or fine-tuned."""
        return MODEL_TRAINING_DOMAINS.get(self.model_id, "General natural language corpus.")

    def _get_pipeline(self) -> Any:
        """Lazily initialize the transformer inference pipeline."""
        if self._pipeline is not None:
            return self._pipeline

        if self.pipeline_factory is not None:
            self._pipeline = self.pipeline_factory(self.model_id, self.revision)
            return self._pipeline

        try:
            import torch  # noqa: F401
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Transformers or PyTorch is not installed. "
                "Install the ML extra with: pip install 'news-sentiment[ml]'"
            ) from exc

        self._pipeline = pipeline(
            "text-classification",
            model=self.model_id,
            revision=self.revision,
            top_k=None,
            truncation=True,
        )
        return self._pipeline

    def predict(self, texts: list[str]) -> list[Prediction]:
        """Classify texts using the transformer model and compute P(pos) - P(neg) score."""
        if not texts:
            return []

        pipe = self._get_pipeline()
        raw_outputs = pipe(texts)

        predictions: list[Prediction] = []
        for output in raw_outputs:
            probs: dict[SentimentLabel, float] = {
                "positive": 0.0,
                "neutral": 0.0,
                "negative": 0.0,
            }

            for item in output:
                raw_label = str(item.get("label", ""))
                score = float(item.get("score", 0.0))
                std_label = self.label_mapping.get(raw_label, "neutral")
                probs[std_label] = probs.get(std_label, 0.0) + score

            # Normalize probabilities if sum deviates slightly from 1.0
            total_prob = sum(probs.values())
            if total_prob > 0.0:
                probs = {k: v / total_prob for k, v in probs.items()}

            # Label is the argmax
            best_label: SentimentLabel = max(probs, key=lambda k: probs[k])

            # Continuous score: P(positive) - P(negative) in [-1.0, 1.0]
            continuous_score = float(probs["positive"] - probs["negative"])

            predictions.append(
                Prediction(
                    label=best_label,
                    score=continuous_score,
                    probabilities={
                        "positive": probs["positive"],
                        "neutral": probs["neutral"],
                        "negative": probs["negative"],
                    },
                    metadata={
                        "model_id": self.model_id,
                        "revision": self.revision,
                    },
                )
            )

        return predictions
