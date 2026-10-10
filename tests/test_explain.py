"""Unit and integration tests for explainability, saliency methods, and evaluation metrics."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from news_sentiment.explain import (
    IntegratedGradientsExplainer,
    OcclusionExplainer,
    ShapExplainer,
    TokenAttribution,
    compute_faithfulness_curves,
    compute_jaccard_similarity,
    compute_token_f1,
    explain,
    explain_detailed,
    get_explainer,
    tokenize_with_spans,
)
from news_sentiment.models.base import Prediction, SentimentModel
from news_sentiment.models.vader import VaderModel
from news_sentiment.storage.models import Article, Base
from news_sentiment.storage.repository import ExplanationRepository


@pytest.fixture
def db_session() -> Session:
    """In-memory SQLite session with full schema initialized."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


def test_tokenize_with_spans() -> None:
    """Tokenize text into words and punctuation while tracking character offsets."""
    text = "Profits jumped 15%!"
    spans = tokenize_with_spans(text)
    assert len(spans) == 5
    tokens = [s.token for s in spans]
    assert tokens == ["Profits", "jumped", "15", "%", "!"]
    assert text[spans[0].start : spans[0].end] == "Profits"
    assert text[spans[1].start : spans[1].end] == "jumped"


def test_vader_negation_not_good() -> None:
    """Verify leave-one-out occlusion attributes negative weight to 'not' for 'not good'.

    For 'not good', the negative score must be attributed to 'not', and 'good'
    must not be presented as positive.
    """
    model = VaderModel()
    explainer = OcclusionExplainer()
    explanation = explainer.explain("not good", model)

    attr_map = {a.token: a.weight for a in explanation.attributions}
    assert "not" in attr_map
    assert "good" in attr_map

    # 'not' must be strongly negative (inversion driver)
    assert attr_map["not"] < 0.0
    # 'good' must NOT be positive
    assert attr_map["good"] <= 0.0

    # Specifically, occlusion delta: score("not good") - score("good") = -0.3412 - 0.4404 = -0.7816
    assert attr_map["not"] == pytest.approx(-0.7816, abs=0.01)
    assert attr_map["good"] == pytest.approx(-0.3412, abs=0.01)


def test_vader_negation_not_bad() -> None:
    """Verify leave-one-out occlusion attributes positive inversion weight to 'not' in 'not bad'."""
    model = VaderModel()
    explainer = OcclusionExplainer()
    explanation = explainer.explain("not bad", model)

    attr_map = {a.token: a.weight for a in explanation.attributions}
    # score("not bad") is positive (+0.431), score without 'not' ("bad") is negative (-0.5423)
    # delta: +0.431 - (-0.5423) = +0.9733
    assert attr_map["not"] > 0.0
    # 'bad' must NOT be negative in this context
    assert attr_map["bad"] >= 0.0


def test_sign_sanity_checks() -> None:
    """Verify sign consistency: positive words get positive weights, negative words get negative."""
    model = VaderModel()

    # Positive headline
    pos_exp = explain("Profits surged with great results", model, method="occlusion")
    pos_map = {a.token: a.weight for a in pos_exp}
    assert pos_map.get("great", 0.0) > 0.0
    assert pos_map.get("surged", 0.0) >= 0.0

    # Negative headline
    neg_exp = explain("Severe financial crisis and terrible disaster", model, method="occlusion")
    neg_map = {a.token: a.weight for a in neg_exp}
    assert neg_map.get("crisis", 0.0) < 0.0
    assert neg_map.get("terrible", 0.0) < 0.0
    assert neg_map.get("disaster", 0.0) < 0.0


def test_deterministic_outputs_fixed_seed() -> None:
    """Verify explanation methods produce deterministic outputs with fixed inputs."""
    model = VaderModel()
    text = "Tech giants announce massive quarterly dividend boost"

    for method in ["occlusion", "integrated_gradients", "shap"]:
        run1 = explain(text, model, method=method)
        run2 = explain(text, model, method=method)
        assert len(run1) == len(run2)
        for a1, a2 in zip(run1, run2, strict=True):
            assert a1.token == a2.token
            assert a1.weight == pytest.approx(a2.weight, abs=1e-6)


def test_explain_interface() -> None:
    """Test unified explain and explain_detailed interfaces."""
    model = VaderModel()
    text = "Company reported excellent earnings"

    # explain returns list[TokenAttribution]
    attrs = explain(text, model, method="occlusion")
    assert isinstance(attrs, list)
    assert all(isinstance(a, TokenAttribution) for a in attrs)
    assert any(a.token == "excellent" and a.weight > 0.0 for a in attrs)

    # explain_detailed returns Explanation
    det = explain_detailed(text, model, method="integrated_gradients")
    assert det.model_name == "vader"
    assert det.method == "integrated_gradients"
    assert det.prediction_label == "positive"
    assert det.prediction_score > 0.0
    assert len(det.attributions) == len(attrs)


def test_unknown_method_raises() -> None:
    """Raise ValueError when an unsupported explanation method is requested."""
    with pytest.raises(ValueError, match="Unknown explanation method"):
        get_explainer("unknown_method")


def test_faithfulness_curves_and_aopc() -> None:
    """Test deletion and insertion curves calculation and AOPC gain."""
    model = VaderModel()
    text = "Operating profit rose to EUR 13 mn with excellent growth"
    attrs = explain(text, model, method="occlusion")

    res = compute_faithfulness_curves(
        text=text,
        attributions=attrs,
        model=model,
        max_steps=4,
        random_samples=5,
        seed=42,
    )

    assert len(res.deletion_curve.step_scores) == 4
    assert len(res.deletion_curve.score_deltas) == 4
    assert res.deletion_curve.aopc >= 0.0
    assert len(res.insertion_curve.step_scores) == 4
    assert res.insertion_curve.aopc >= 0.0

    # Faithfulness gain should be positive (top tokens degrade score more than random tokens)
    assert res.deletion_aopc_gain > 0.0
    assert res.is_faithful() is True


def test_token_level_f1_plausibility() -> None:
    """Test token-level precision, recall, and F1 plausibility computation."""
    predicted = ["higher", "cooler", "inflation"]
    ground_truth = ["higher", "cooler"]

    prec, rec, f1 = compute_token_f1(predicted, ground_truth)
    assert prec == pytest.approx(2 / 3, abs=0.01)
    assert rec == pytest.approx(1.0, abs=0.01)
    assert f1 == pytest.approx(0.8, abs=0.01)

    # Disjoint tokens
    p0, r0, f0 = compute_token_f1(["apple"], ["orange"])
    assert p0 == 0.0 and r0 == 0.0 and f0 == 0.0

    # Empty tokens
    pe, re, fe = compute_token_f1([], ["orange"])
    assert pe == 0.0 and re == 0.0 and fe == 0.0


def test_jaccard_similarity() -> None:
    """Test top-3 token Jaccard overlap computation."""
    tokens_a = ["profit", "rose", "growth"]
    tokens_b = ["profit", "surged", "growth"]

    jaccard = compute_jaccard_similarity(tokens_a, tokens_b)
    # Intersection = {'profit', 'growth'} (2), Union = {'profit', 'rose', 'growth', 'surged'} (4)
    assert jaccard == pytest.approx(2 / 4, abs=0.01)

    # Identical sets
    assert compute_jaccard_similarity(["a", "b"], ["a", "b"]) == 1.0
    # Disjoint sets
    assert compute_jaccard_similarity(["a"], ["b"]) == 0.0
    # Both empty
    assert compute_jaccard_similarity([], []) == 1.0


def test_database_explanation_caching(db_session: Session) -> None:
    """Test caching explanations in the database and retrieving them without recomputation."""
    article = Article(
        title="European stock indexes rally as inflation moderates",
        normalized_title="european stock indexes rally as inflation moderates",
        url="https://news.example.com/stocks-rally",
        provider="gdelt",
        topic="markets",
        outlet="Reuters",
    )
    db_session.add(article)
    db_session.commit()

    model = VaderModel()

    # 1. Compute and save explanation with article_id
    exp1 = explain_detailed(
        text=article.title,
        model=model,
        method="occlusion",
        article_id=article.id,
        session=db_session,
        use_cache=True,
    )
    assert exp1 is not None

    # Verify saved row in database
    cached_db = ExplanationRepository.get_explanation(
        session=db_session,
        article_id=article.id,
        model_name="vader",
        model_version=model.version,
        method="occlusion",
    )
    assert cached_db is not None
    assert cached_db.prediction_label == exp1.prediction_label
    assert cached_db.prediction_score == pytest.approx(exp1.prediction_score, abs=1e-4)
    assert len(cached_db.attributions) == len(exp1.attributions)

    # 2. Retrieve via explain_detailed with use_cache=True
    exp2 = explain_detailed(
        text=article.title,
        model=model,
        method="occlusion",
        article_id=article.id,
        session=db_session,
        use_cache=True,
    )
    assert exp2.prediction_score == exp1.prediction_score
    assert len(exp2.attributions) == len(exp1.attributions)
    assert [a.token for a in exp2.attributions] == [a.token for a in exp1.attributions]


def test_custom_mock_model_explainers() -> None:
    """Test Integrated Gradients and SHAP explainers on a custom sentiment model."""

    class MockModel(SentimentModel):
        @property
        def name(self) -> str:
            return "mock_model"

        @property
        def version(self) -> str:
            return "1.0.0"

        def predict(self, texts: list[str]) -> list[Prediction]:
            preds = []
            for t in texts:
                t_lower = t.lower()
                if "surge" in t_lower:
                    preds.append(
                        Prediction(
                            label="positive",
                            score=0.8,
                            probabilities={"positive": 0.9, "neutral": 0.1, "negative": 0.0},
                        )
                    )
                elif "drop" in t_lower:
                    preds.append(
                        Prediction(
                            label="negative",
                            score=-0.8,
                            probabilities={"positive": 0.0, "neutral": 0.1, "negative": 0.9},
                        )
                    )
                else:
                    preds.append(
                        Prediction(
                            label="neutral",
                            score=0.0,
                            probabilities={"positive": 0.1, "neutral": 0.8, "negative": 0.1},
                        )
                    )
            return preds

    mock = MockModel()
    text = "Tech profits surge amid strong demand"

    ig_explainer = IntegratedGradientsExplainer()
    ig_exp = ig_explainer.explain(text, mock)
    ig_tokens = {a.token: a.weight for a in ig_exp.attributions}
    assert ig_tokens["surge"] > 0.0

    shap_explainer = ShapExplainer()
    shap_exp = shap_explainer.explain(text, mock)
    shap_tokens = {a.token: a.weight for a in shap_exp.attributions}
    assert shap_tokens["surge"] > 0.0


def test_explainer_empty_text_and_fallbacks() -> None:
    """Verify empty text handling and fallback behaviors in explainers."""

    class DummyModel(SentimentModel):
        @property
        def name(self) -> str:
            return "dummy"

        @property
        def version(self) -> str:
            return "0.1"

        def predict(self, texts: list[str]) -> list[Prediction]:
            return [
                Prediction(
                    label="neutral",
                    score=0.0,
                    probabilities={"positive": 0.0, "neutral": 1.0, "negative": 0.0},
                )
                for _ in texts
            ]

    dummy = DummyModel()
    ig_explainer = IntegratedGradientsExplainer()
    assert ig_explainer.explain("", dummy).attributions == []

    shap_explainer = ShapExplainer()
    assert shap_explainer.explain("", dummy).attributions == []


def test_run_shap_partition_mocked() -> None:
    """Verify _run_shap_partition with mocked shap library and pipeline."""
    import sys
    from unittest.mock import MagicMock, patch

    from news_sentiment.explain.shap_explainer import _run_real_shap

    class PipeModel(SentimentModel):
        @property
        def name(self) -> str:
            return "pipemodel"

        @property
        def version(self) -> str:
            return "1.0"

        def predict(self, texts: list[str]) -> list[Prediction]:
            return [
                Prediction(
                    label="positive",
                    score=0.8,
                    probabilities={"positive": 0.8, "neutral": 0.2, "negative": 0.0},
                )
                for _ in texts
            ]

    model = PipeModel()
    assert _run_real_shap("test", model) is None

    # Attach mock pipeline
    model._pipeline = MagicMock()  # type: ignore[attr-defined]

    mock_shap = MagicMock()
    mock_values = MagicMock()
    mock_values.values = [[0.65, -0.15]]
    mock_values.data = [["profit", "loss"]]
    mock_shap.Explainer.return_value = MagicMock(return_value=mock_values)

    with patch.dict(sys.modules, {"shap": mock_shap}):
        attrs = _run_real_shap("profit loss", model)
        assert attrs is not None
        assert len(attrs) == 2
        assert attrs[0].token == "profit"
        assert attrs[0].weight == 0.65

        # Also exercise ShapExplainer.explain branch when real_shap returns results
        expl = ShapExplainer().explain("profit loss", model)
        assert expl.attributions == attrs
        assert expl.method == "shap"


def test_run_captum_ig_mocked() -> None:
    """Verify _run_captum_ig with mocked torch and captum modules."""
    import sys
    from unittest.mock import MagicMock, patch

    from news_sentiment.explain.integrated_gradients import _run_captum_ig

    class PipeModel(SentimentModel):
        @property
        def name(self) -> str:
            return "pipemodel"

        @property
        def version(self) -> str:
            return "1.0"

        def predict(self, texts: list[str]) -> list[Prediction]:
            return [
                Prediction(
                    label="positive",
                    score=0.8,
                    probabilities={"positive": 0.8, "neutral": 0.2, "negative": 0.0},
                )
                for _ in texts
            ]

    model = PipeModel()
    assert _run_captum_ig("test", model) is None

    mock_torch = MagicMock()
    mock_probs = MagicMock()
    mock_probs.shape = [1, 3]
    mock_probs.__getitem__ = MagicMock(return_value=MagicMock(__sub__=lambda s, o: MagicMock()))
    mock_torch.softmax.return_value = mock_probs

    mock_captum_attr = MagicMock()
    mock_lig = MagicMock()
    mock_attr_tensor = MagicMock()
    attr_detached = mock_attr_tensor.sum.return_value.squeeze.return_value.detach.return_value
    attr_detached.cpu.return_value.numpy.return_value = [0.45, 0.25]
    mock_lig.attribute.return_value = (mock_attr_tensor, None)
    mock_captum_attr.LayerIntegratedGradients.return_value = mock_lig

    mock_tf = MagicMock()
    mock_pipe = MagicMock()
    mock_hf_model = MagicMock()
    mock_hf_model.roberta.embeddings = MagicMock()
    mock_pipe.model = mock_hf_model

    mock_tokenizer = MagicMock()
    mock_input_ids = MagicMock()
    mock_input_ids.squeeze.return_value.tolist.return_value = [101, 102]
    mock_tokenizer.return_value = {
        "input_ids": mock_input_ids,
        "attention_mask": MagicMock(),
    }
    mock_tokenizer.cls_token = "[CLS]"
    mock_tokenizer.sep_token = "[SEP]"
    mock_tokenizer.pad_token = "[PAD]"
    mock_tokenizer.convert_ids_to_tokens.return_value = ["surge", "profit"]
    mock_pipe.tokenizer = mock_tokenizer

    model._pipeline = mock_pipe  # type: ignore[attr-defined]

    with patch.dict(
        sys.modules,
        {
            "torch": mock_torch,
            "captum": MagicMock(),
            "captum.attr": mock_captum_attr,
            "transformers": mock_tf,
        },
    ):
        attrs = _run_captum_ig("surge profit", model)
        assert attrs is not None
        assert len(attrs) == 2
        assert attrs[0].token == "surge"

        # Also exercise IntegratedGradientsExplainer.explain branch
        expl = IntegratedGradientsExplainer().explain("surge profit", model)
        assert expl.attributions == attrs
        assert expl.method == "integrated_gradients"
