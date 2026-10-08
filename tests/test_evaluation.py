"""Tests for evaluation metrics, contamination checks, error analysis, and benchmark runner."""

import tempfile
from pathlib import Path

from news_sentiment.evaluation.benchmarks import (
    BenchmarkItem,
    ensure_financial_phrasebank,
    load_benchmark_split,
)
from news_sentiment.evaluation.contamination import check_contamination
from news_sentiment.evaluation.error_analysis import (
    analyze_model_errors,
    categorize_misclassification,
)
from news_sentiment.evaluation.metrics import (
    compute_bootstrap_macro_f1_ci,
    compute_classification_metrics,
    compute_confusion_matrix,
)
from news_sentiment.evaluation.runner import BenchmarkRunner
from news_sentiment.models.base import Prediction, SentimentModel


class MockEvalModel(SentimentModel):
    """Deterministic mock model for evaluation testing."""

    def __init__(self, name: str = "mock_model", fixed_pred: str = "positive") -> None:
        self._name = name
        self.fixed_pred = fixed_pred

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "1.0.0-test"

    def predict(self, texts: list[str]) -> list[Prediction]:
        return [
            Prediction(
                label=self.fixed_pred,  # type: ignore[arg-type]
                score=0.75,
                probabilities={"positive": 0.75, "neutral": 0.15, "negative": 0.10},
            )
            for _ in texts
        ]


# ---------------------------------------------------------------------------
# Contamination Checks
# ---------------------------------------------------------------------------


def test_contamination_detection() -> None:
    """Verify that FinBERT is flagged on Financial PhraseBank, while other models are not."""
    # FinBERT should be flagged
    status_finbert = check_contamination("finbert", "financial_phrasebank")
    assert status_finbert.is_contaminated is True
    assert status_finbert.reason is not None
    assert "fine-tuned directly" in status_finbert.reason

    # VADER should not be contaminated
    status_vader = check_contamination("vader", "financial_phrasebank")
    assert status_vader.is_contaminated is False
    assert status_vader.reason is None

    # RoBERTa should not be contaminated on Financial PhraseBank
    status_roberta = check_contamination("roberta", "financial_phrasebank")
    assert status_roberta.is_contaminated is False

    # In-domain dataset has no model contamination
    status_indomain = check_contamination("finbert", "in_domain")
    assert status_indomain.is_contaminated is False


# ---------------------------------------------------------------------------
# Metrics & Bootstrap Confidence Intervals
# ---------------------------------------------------------------------------


def test_classification_metrics_empty() -> None:
    """Verify empty input handling in classification metrics."""
    res = compute_classification_metrics([], [])
    assert res.sample_size == 0
    assert res.accuracy == 0.0
    assert res.macro_f1 == 0.0
    assert res.bootstrap_ci_macro_f1 == (0.0, 0.0)


def test_classification_metrics_perfect() -> None:
    """Verify metrics on perfect 100% agreement predictions."""
    y = ["positive", "neutral", "negative"] * 10
    res = compute_classification_metrics(y, y, n_bootstrap=200, seed=42)

    assert res.sample_size == 30
    assert res.accuracy == 1.0
    assert res.macro_f1 == 1.0
    assert res.per_class["positive"].precision == 1.0
    assert res.per_class["positive"].recall == 1.0
    assert res.per_class["positive"].f1 == 1.0
    assert res.bootstrap_ci_macro_f1 == (1.0, 1.0)


def test_classification_metrics_partial() -> None:
    """Verify accuracy, macro-F1, and confusion matrix calculation."""
    y_true = ["positive", "neutral", "negative", "neutral"]
    y_pred = ["positive", "positive", "negative", "neutral"]

    res = compute_classification_metrics(y_true, y_pred, n_bootstrap=100, seed=42)
    # 3 correct out of 4 = 75% accuracy
    assert res.accuracy == 0.75
    assert 0.0 < res.macro_f1 < 1.0

    # Check confusion matrix
    cm = res.confusion_matrix
    assert cm["positive"]["positive"] == 1
    assert cm["neutral"]["positive"] == 1
    assert cm["neutral"]["neutral"] == 1
    assert cm["negative"]["negative"] == 1


def test_bootstrap_macro_f1_ci_ordering() -> None:
    """Verify that bootstrap confidence intervals satisfy low <= high."""
    y_true = ["positive", "neutral", "negative"] * 10
    y_pred = ["positive", "negative", "neutral"] * 10

    low, high = compute_bootstrap_macro_f1_ci(
        y_true=y_true,
        y_pred=y_pred,
        classes=["positive", "neutral", "negative"],
        n_bootstrap=100,
        seed=42,
    )
    assert 0.0 <= low <= high <= 1.0


def test_confusion_matrix_structure() -> None:
    """Verify confusion matrix counts."""
    matrix = compute_confusion_matrix(
        y_true=["positive", "neutral"],
        y_pred=["negative", "neutral"],
    )
    assert matrix["positive"]["negative"] == 1
    assert matrix["neutral"]["neutral"] == 1
    assert matrix["positive"]["positive"] == 0


# ---------------------------------------------------------------------------
# Error Analysis & Taxonomy Categorization
# ---------------------------------------------------------------------------


def test_error_taxonomy_categorization() -> None:
    """Verify categorization of misclassifications into the 5 failure modes."""
    # 1. Neutral reporting of negative event
    cat1 = categorize_misclassification(
        text="Earthquake of magnitude 5.8 recorded off coast; police investigate reports",
        true_label="neutral",
        pred_label="negative",
    )
    assert cat1 == "neutral_reporting_of_negative_events"

    # 2. Negation
    cat2 = categorize_misclassification(
        text="Company fails to achieve revenue targets despite strong sales",
        true_label="negative",
        pred_label="positive",
    )
    assert cat2 == "negation"

    # 3. Mixed sentiment
    cat3 = categorize_misclassification(
        text="Quarterly revenue jumps 25% but operating margins compress sharply",
        true_label="negative",
        pred_label="positive",
    )
    assert cat3 == "mixed_sentiment"

    # 4. Domain terms
    cat4 = categorize_misclassification(
        text="Automaker announces global recall of 400,000 hybrid vehicles",
        true_label="negative",
        pred_label="positive",
    )
    assert cat4 == "domain_terms"

    # 5. Sarcasm / scare quotes
    cat5 = categorize_misclassification(
        text="Investors celebrate 'historic' deal that yields minimal gains",
        true_label="negative",
        pred_label="positive",
    )
    assert cat5 == "sarcasm"

    # 6. Other
    cat6 = categorize_misclassification(
        text="A brief sentence with standard vocabulary.",
        true_label="neutral",
        pred_label="positive",
    )
    assert cat6 == "other"


def test_analyze_model_errors_aggregation() -> None:
    """Verify error aggregation and representative sampling."""
    texts = [
        "Company fails to deliver quarterly guidance",
        "Automaker announces recall of vehicles",
        "Routine meeting concludes as expected",
    ]
    y_true = ["negative", "negative", "neutral"]
    y_pred = ["positive", "positive", "neutral"]  # 2 errors, 1 correct
    scores = [0.8, 0.7, 0.0]

    result = analyze_model_errors(texts, y_true, y_pred, scores, model_name="test_model")
    assert result.total_samples == 3
    assert result.total_errors == 2
    assert result.category_counts["negation"] == 1
    assert result.category_counts["domain_terms"] == 1

    # Check sampled headline
    samples = result.samples_by_category["negation"]
    assert len(samples) == 1
    assert samples[0].text == texts[0]
    assert samples[0].true_label == "negative"
    assert samples[0].pred_label == "positive"


# ---------------------------------------------------------------------------
# Benchmark Runner & Datasets
# ---------------------------------------------------------------------------


def test_benchmark_runner_flow() -> None:
    """Verify BenchmarkRunner execution, report saving, and markdown generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        runner = BenchmarkRunner(output_dir=Path(tmp_dir))
        model = MockEvalModel("mock_eval", fixed_pred="positive")

        test_items = [
            BenchmarkItem(id=1, text="Great growth and surging profits", label="positive"),
            BenchmarkItem(id=2, text="Terrible bankruptcy and massive losses", label="negative"),
        ]

        # Evaluate on test items
        output = runner.evaluate_model_on_dataset(
            model=model,
            dataset_name="custom_dataset",
            items=test_items,
        )

        assert output.model_name == "mock_eval"
        assert output.metrics.sample_size == 2
        assert output.metrics.accuracy == 0.5  # 1 out of 2 matched
        assert output.error_analysis.total_errors == 1

        # Test report saving
        results = {"custom_dataset": [output]}
        json_file, md_file = runner.save_reports(results)
        assert json_file.exists()
        assert md_file.exists()
        md_text = md_file.read_text(encoding="utf-8")
        assert "Model Evaluation and Benchmark Report" in md_text
        assert "mock_eval" in md_text


def test_financial_phrasebank_loader_splits() -> None:
    """Verify deterministic splits and loading of Financial PhraseBank."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        splits = ensure_financial_phrasebank(dest_dir=Path(tmp_dir), seed=42)
        assert splits["train"].exists()
        assert splits["val"].exists()
        assert splits["test"].exists()

        train_items = load_benchmark_split(splits["train"])
        val_items = load_benchmark_split(splits["val"])
        test_items = load_benchmark_split(splits["test"])

        assert len(train_items) + len(val_items) + len(test_items) == 2264

        # Verify no overlapping IDs across splits
        train_ids = {it.id for it in train_items}
        val_ids = {it.id for it in val_items}
        test_ids = {it.id for it in test_items}

        assert train_ids.isdisjoint(val_ids)
        assert train_ids.isdisjoint(test_ids)
        assert val_ids.isdisjoint(test_ids)
