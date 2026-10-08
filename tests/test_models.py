"""Tests for sentiment models, registry, transformer wrappers, and statistical metrics."""

from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from news_sentiment.models.base import Prediction, SentimentModel
from news_sentiment.models.metrics import (
    compare_model_predictions,
    compute_agreement_rate,
    compute_cohen_kappa,
)
from news_sentiment.models.pipeline import InferencePipeline
from news_sentiment.models.registry import (
    get_model,
    get_model_domain,
    list_models,
    register_model,
)
from news_sentiment.models.transformer import HFTransformerModel
from news_sentiment.models.vader import VaderModel
from news_sentiment.storage.database import init_db
from news_sentiment.storage.models import Article
from news_sentiment.storage.models import Prediction as DBPrediction


class MockSentimentModel(SentimentModel):
    """Mock model with deterministic responses for tests."""

    def __init__(self, name: str, fixed_label: str = "positive", score: float = 0.8) -> None:
        self._name = name
        self.fixed_label = fixed_label
        self.fixed_score = score

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "1.0.0-mock"

    def predict(self, texts: list[str]) -> list[Prediction]:
        return [
            Prediction(
                label=self.fixed_label,  # type: ignore[arg-type]
                score=self.fixed_score,
                probabilities={"positive": 0.8, "neutral": 0.1, "negative": 0.1},
            )
            for _ in texts
        ]


# ---------------------------------------------------------------------------
# Prediction Dataclass & Validation
# ---------------------------------------------------------------------------


def test_prediction_dataclass_clamping() -> None:
    """Verify continuous score clamping to [-1.0, 1.0]."""
    pred_high = Prediction(
        label="positive",
        score=2.5,
        probabilities={"positive": 1.0, "neutral": 0.0, "negative": 0.0},
    )
    assert pred_high.score == 1.0

    pred_low = Prediction(
        label="negative",
        score=-1.8,
        probabilities={"positive": 0.0, "neutral": 0.0, "negative": 1.0},
    )
    assert pred_low.score == -1.0


# ---------------------------------------------------------------------------
# VADER Model Tests
# ---------------------------------------------------------------------------


def test_vader_model_metadata() -> None:
    """Verify VADER model properties."""
    vader = VaderModel()
    assert vader.name == "vader"
    assert vader.version == "3.3.2"


def test_vader_model_predictions() -> None:
    """Verify VADER classification and score boundaries."""
    vader = VaderModel()

    # Positive headline
    res_pos = vader.predict_one("Company achieves record high revenue and excellent stock profits!")
    assert res_pos.label == "positive"
    assert res_pos.score >= 0.05
    assert res_pos.probabilities["positive"] > 0
    assert "positive" in res_pos.probabilities

    # Negative headline
    res_neg = vader.predict_one("Catastrophic loss and terrible financial collapse reported.")
    assert res_neg.label == "negative"
    assert res_neg.score <= -0.05
    assert res_neg.probabilities["negative"] > 0

    # Neutral headline
    res_neu = vader.predict_one("The committee will convene on Tuesday afternoon.")
    assert res_neu.label == "neutral"
    assert -0.05 < res_neu.score < 0.05


def test_vader_threshold_boundaries() -> None:
    """Verify exact threshold boundaries of +/- 0.05."""
    vader = VaderModel(pos_threshold=0.05, neg_threshold=-0.05)

    # Empty string is neutral
    res_empty = vader.predict_one("")
    assert res_empty.label == "neutral"
    assert res_empty.score == 0.0


# ---------------------------------------------------------------------------
# Transformer Model Wrapper Tests
# ---------------------------------------------------------------------------


def test_transformer_wrapper_missing_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify clear error message when torch or transformers are missing."""
    model = HFTransformerModel(model_id="test/model")

    # Force import to fail
    import builtins

    real_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in ("torch", "transformers"):
            raise ImportError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    with pytest.raises(RuntimeError, match="Install the ML extra"):
        model.predict(["Sample headline text"])


def test_transformer_wrapper_mock_pipeline() -> None:
    """Verify transformer scoring logic: score = P(pos) - P(neg)."""

    # Mock pipeline returns probabilities
    def mock_pipeline_factory(model_id: str, revision: str) -> Any:
        def _pipeline(texts: list[str]) -> list[list[dict[str, Any]]]:
            # For each text, return simulated label distributions
            return [
                [
                    {"label": "LABEL_2", "score": 0.85},  # positive
                    {"label": "LABEL_1", "score": 0.10},  # neutral
                    {"label": "LABEL_0", "score": 0.05},  # negative
                ]
                for _ in texts
            ]

        return _pipeline

    model = HFTransformerModel(
        model_id="cardiffnlp/twitter-roberta-base-sentiment-latest",
        name="roberta",
        pipeline_factory=mock_pipeline_factory,
    )

    preds = model.predict(["Markets are booming today"])
    assert len(preds) == 1
    p = preds[0]

    assert p.label == "positive"
    # P(pos) - P(neg) = 0.85 - 0.05 = 0.80
    assert abs(p.score - 0.80) < 1e-4
    assert abs(p.probabilities["positive"] - 0.85) < 1e-4
    assert abs(p.probabilities["negative"] - 0.05) < 1e-4
    assert abs(p.probabilities["neutral"] - 0.10) < 1e-4


def test_transformer_wrapper_finbert_labels() -> None:
    """Verify FinBERT label mappings (LABEL_0=pos, LABEL_1=neg, LABEL_2=neu)."""

    def mock_pipeline_factory(model_id: str, revision: str) -> Any:
        def _pipeline(texts: list[str]) -> list[list[dict[str, Any]]]:
            return [
                [
                    {"label": "LABEL_0", "score": 0.10},  # positive
                    {"label": "LABEL_1", "score": 0.70},  # negative
                    {"label": "LABEL_2", "score": 0.20},  # neutral
                ]
            ]

        return _pipeline

    model = HFTransformerModel(
        model_id="ProsusAI/finbert",
        name="finbert",
        pipeline_factory=mock_pipeline_factory,
    )

    preds = model.predict(["Earnings dropped sharply by 40%"])
    assert len(preds) == 1
    p = preds[0]

    assert p.label == "negative"
    # P(pos) - P(neg) = 0.10 - 0.70 = -0.60
    assert abs(p.score - (-0.60)) < 1e-4


def test_transformer_empty_texts() -> None:
    """Verify predict([]) returns empty list."""
    model = HFTransformerModel(model_id="test/model")
    assert model.predict([]) == []


@pytest.mark.slow
def test_real_transformer_model_slow() -> None:
    """Integration test with actual Hugging Face model (skipped by default)."""
    pytest.importorskip("transformers")
    pytest.importorskip("torch")

    model = HFTransformerModel(
        model_id="cardiffnlp/twitter-roberta-base-sentiment-latest",
        name="roberta",
    )
    res = model.predict(["Exceptional technological innovation announced!"])
    assert len(res) == 1
    assert res[0].label in ("positive", "neutral", "negative")


# ---------------------------------------------------------------------------
# Registry Tests
# ---------------------------------------------------------------------------


def test_registry_discovery() -> None:
    """Verify model discovery, instantiation, and training domains."""
    models = list_models()
    assert "vader" in models
    assert "roberta" in models
    assert "finbert" in models

    vader = get_model("vader")
    assert isinstance(vader, VaderModel)
    assert get_model("vader") is vader  # cached singleton

    # Domain descriptions
    vader_domain = get_model_domain("vader")
    assert "VADER Lexicon" in vader_domain

    roberta_domain = get_model_domain("roberta")
    assert "Twitter" in roberta_domain

    finbert_domain = get_model_domain("finbert")
    assert "Financial" in finbert_domain

    with pytest.raises(KeyError, match="Unknown model 'nonexistent'"):
        get_model("nonexistent")


def test_registry_custom_registration() -> None:
    """Verify register_model enables registering custom model factories."""
    register_model("mock_custom", lambda: MockSentimentModel("mock_custom"))
    assert "mock_custom" in list_models()

    instance = get_model("mock_custom")
    assert instance.name == "mock_custom"
    assert instance.predict_one("Test").label == "positive"


# ---------------------------------------------------------------------------
# Statistical Metrics & Cohen's Kappa Tests
# ---------------------------------------------------------------------------


def test_agreement_rate_calculation() -> None:
    """Verify pairwise percentage agreement calculation."""
    # Empty
    assert compute_agreement_rate([], []) == 0.0
    assert compute_agreement_rate(["pos"], []) == 0.0

    # 100% agreement
    assert compute_agreement_rate(["pos", "neg", "neu"], ["pos", "neg", "neu"]) == 1.0

    # Partial agreement (2 / 4 = 50%)
    labels_a = ["pos", "pos", "neu", "neg"]
    labels_b = ["pos", "neg", "neu", "pos"]
    assert compute_agreement_rate(labels_a, labels_b) == 0.5


def test_cohen_kappa_calculation() -> None:
    """Verify Cohen's kappa coefficient (κ) edge cases and values."""
    # Empty
    assert compute_cohen_kappa([], []) == 0.0

    # Perfect agreement
    labels_a = ["pos", "neg", "neu", "pos", "neg"]
    assert compute_cohen_kappa(labels_a, labels_a) == 1.0

    # Near chance agreement (orthogonal classifications)
    l1 = ["pos", "pos", "neg", "neg"]
    l2 = ["pos", "neg", "pos", "neg"]
    kappa = compute_cohen_kappa(l1, l2)
    assert abs(kappa - 0.0) < 1e-4

    # All identical single category
    single_cat = ["pos", "pos", "pos"]
    assert compute_cohen_kappa(single_cat, single_cat) == 1.0


def test_compare_model_predictions_multi_model() -> None:
    """Verify pairwise calculation across 3 models."""
    data = {
        "m1": ["pos", "neg", "neu"],
        "m2": ["pos", "neg", "neg"],
        "m3": ["pos", "pos", "neu"],
    }
    metrics = compare_model_predictions(data)
    # 3 pairs: (m1, m2), (m1, m3), (m2, m3)
    assert len(metrics) == 3
    pair_names = {(m.model_a, m.model_b) for m in metrics}
    assert ("m1", "m2") in pair_names
    assert ("m1", "m3") in pair_names
    assert ("m2", "m3") in pair_names


# ---------------------------------------------------------------------------
# Inference Pipeline & Database Persistence Tests
# ---------------------------------------------------------------------------


def test_inference_pipeline_unprocessed_batch_scoring() -> None:
    """Verify batch inference scores unanalyzed articles idempotently without overwriting."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    with Session(engine) as session:
        # 1. Insert 3 articles
        for idx in range(1, 4):
            session.add(
                Article(
                    title=f"Sample Market Headline {idx}",
                    normalized_title=f"sample market headline {idx}",
                    url=f"https://example.org/article/{idx}",
                    topic="markets",
                    provider="rss",
                )
            )
        session.commit()

        pipeline = InferencePipeline()
        vader = VaderModel()

        # First run: scores 3 articles
        summary1 = pipeline.score_unprocessed(model=vader, topic="markets", session=session)
        assert summary1.articles_scored == 3

        # Verify Prediction records in database
        preds = list(session.scalars(select(DBPrediction)).all())
        assert len(preds) == 3
        for p in preds:
            assert p.model_name == "vader"
            assert p.model_version == "3.3.2"
            assert p.label in ("positive", "neutral", "negative")
            assert -1.0 <= p.score <= 1.0
            assert "positive" in p.probabilities

        # Second run with same model & version: scores 0 articles (no-op)
        summary2 = pipeline.score_unprocessed(model=vader, topic="markets", session=session)
        assert summary2.articles_scored == 0
        assert len(session.scalars(select(DBPrediction)).all()) == 3

        # Run with a second model: adds 3 new records without deleting or overwriting vader
        mock_model = MockSentimentModel("mock_transformer", fixed_label="positive", score=0.9)
        summary3 = pipeline.score_unprocessed(model=mock_model, topic="markets", session=session)
        assert summary3.articles_scored == 3

        all_preds = list(session.scalars(select(DBPrediction)).all())
        assert len(all_preds) == 6
        vader_preds = [p for p in all_preds if p.model_name == "vader"]
        mock_preds = [p for p in all_preds if p.model_name == "mock_transformer"]
        assert len(vader_preds) == 3
        assert len(mock_preds) == 3


def test_inference_pipeline_compare_models_report() -> None:
    """Verify multi-model comparison report and disagreement isolation."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    with Session(engine) as session:
        # Insert 2 articles
        session.add(
            Article(
                title="Stocks soaring to record highs",
                normalized_title="stocks soaring to record highs",
                url="https://example.org/pos",
                topic="stocks",
                provider="gdelt",
            )
        )
        session.add(
            Article(
                title="Markets hit by devastating crash and collapse",
                normalized_title="markets hit by devastating crash and collapse",
                url="https://example.org/neg",
                topic="stocks",
                provider="gdelt",
            )
        )
        session.commit()

        m_pos = MockSentimentModel("m_pos", fixed_label="positive", score=0.9)
        m_neg = MockSentimentModel("m_neg", fixed_label="negative", score=-0.9)

        pipeline = InferencePipeline()
        report = pipeline.compare_models(
            topic="stocks",
            models=[m_pos, m_neg],
            session=session,
        )

        assert report.sample_size == 2
        assert len(report.pairwise_metrics) == 1
        pair = report.pairwise_metrics[0]
        assert pair.agreement_rate == 0.0  # complete disagreement
        assert len(report.disagreements) == 2
        assert report.disagreements[0].title in (
            "Stocks soaring to record highs",
            "Markets hit by devastating crash and collapse",
        )
