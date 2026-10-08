"""VADER rule-based lexicon sentiment model baseline."""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from news_sentiment.models.base import Prediction, SentimentLabel, SentimentModel


class VaderModel(SentimentModel):
    """Lexicon and rule-based sentiment model using VADER (Valence Aware Dictionary)."""

    def __init__(self, pos_threshold: float = 0.05, neg_threshold: float = -0.05) -> None:
        self.analyzer = SentimentIntensityAnalyzer()
        self.pos_threshold = pos_threshold
        self.neg_threshold = neg_threshold

    @property
    def name(self) -> str:
        return "vader"

    @property
    def version(self) -> str:
        return "3.3.2"

    def predict(self, texts: list[str]) -> list[Prediction]:
        """Classify texts using VADER lexicon polarity compound thresholds."""
        predictions: list[Prediction] = []

        for text in texts:
            scores = self.analyzer.polarity_scores(text)
            compound = float(scores.get("compound", 0.0))

            # Apply standard VADER classification thresholds
            if compound >= self.pos_threshold:
                label: SentimentLabel = "positive"
            elif compound <= self.neg_threshold:
                label = "negative"
            else:
                label = "neutral"

            # Note: pos, neu, neg proportions represent lexicon density,
            # not calibrated probabilities
            probabilities = {
                "positive": float(scores.get("pos", 0.0)),
                "neutral": float(scores.get("neu", 0.0)),
                "negative": float(scores.get("neg", 0.0)),
            }

            predictions.append(
                Prediction(
                    label=label,
                    score=compound,
                    probabilities=probabilities,
                    metadata={"compound": compound},
                )
            )

        return predictions
