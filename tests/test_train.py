"""Tests for fine-tuning configuration, training pipeline, multi-seed math, and registry."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from scripts.train import (
    MetricLogger,
    calculate_mean_std,
    load_jsonl_dataset,
    run_dry_run_training,
)

from news_sentiment.models.registry import get_model_domain, list_models
from news_sentiment.models.transformer import HFTransformerModel


def test_train_config_structure() -> None:
    """Verify that configs/train.yaml conforms to expected schema and hyperparameters."""
    config_path = Path("configs/train.yaml")
    assert config_path.exists(), "configs/train.yaml must exist."

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Model specs
    assert config["model"]["base_model"] == "distilbert/distilroberta-base"
    assert config["model"]["num_labels"] == 3
    assert config["model"]["id2label"] == {0: "negative", 1: "neutral", 2: "positive"}
    assert config["model"]["label2id"] == {"negative": 0, "neutral": 1, "positive": 2}

    # Data paths
    assert Path(config["data"]["train_path"]).exists()
    assert Path(config["data"]["val_path"]).exists()
    assert Path(config["data"]["test_path"]).exists()
    assert Path(config["data"]["in_domain_path"]).exists()

    # Training parameters
    training_cfg = config["training"]
    assert training_cfg["learning_rate"] == 2.0e-5
    assert training_cfg["num_train_epochs"] == 4
    assert training_cfg["per_device_train_batch_size"] == 16
    assert training_cfg["metric_for_best_model"] == "macro_f1"
    assert training_cfg["load_best_model_at_end"] is True
    assert training_cfg["seeds"] == [42, 43, 44]


def test_calculate_mean_std() -> None:
    """Test sample mean and standard deviation statistical calculations."""
    # Empty
    assert calculate_mean_std([]) == (0.0, 0.0)

    # Single value
    assert calculate_mean_std([0.85]) == (0.85, 0.0)

    # Identical values
    assert calculate_mean_std([0.80, 0.80, 0.80]) == (0.80, 0.0)

    # Varied values: [1.0, 2.0, 3.0] -> mean 2.0, sample std 1.0
    mean, std = calculate_mean_std([1.0, 2.0, 3.0])
    assert mean == 2.0
    assert std == 1.0

    # Rounded floats
    mean, std = calculate_mean_std([0.854, 0.862, 0.858])
    assert mean == 0.858
    assert std == 0.004


def test_load_jsonl_dataset(tmp_path: Path) -> None:
    """Test JSONL dataset loader and error handling."""
    dummy_file = tmp_path / "sample.jsonl"
    dummy_file.write_text(
        '{"id": "1", "text": "First", "label": "positive"}\n'
        '{"id": "2", "text": "Second", "label": "neutral"}\n',
        encoding="utf-8",
    )

    records = load_jsonl_dataset(dummy_file)
    assert len(records) == 2
    assert records[0]["text"] == "First"
    assert records[1]["label"] == "neutral"

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        load_jsonl_dataset(tmp_path / "non_existent.jsonl")


def test_metric_logger(tmp_path: Path) -> None:
    """Test metric logger CSV writing and appending."""
    csv_file = tmp_path / "metrics.csv"
    logger = MetricLogger(csv_file)

    logger.log(
        {
            "run_id": "seed_42",
            "seed": 42,
            "epoch": 1,
            "step": 50,
            "split": "validation",
            "loss": 0.42,
            "accuracy": 0.85,
            "macro_f1": 0.83,
        }
    )

    assert csv_file.exists()
    lines = csv_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert "run_id,seed,epoch" in lines[0]
    assert "seed_42,42,1,50,validation,0.42,0.85,0.83" in lines[1]


def test_run_dry_run_training(tmp_path: Path) -> None:
    """Test end-to-end simulated training pipeline and summary metrics."""
    out_dir = tmp_path / "models"
    log_dir = tmp_path / "reports"
    csv_file = log_dir / "metrics.csv"

    config: dict[str, Any] = {
        "model": {
            "base_model": "distilbert/distilroberta-base",
            "id2label": {0: "negative", 1: "neutral", 2: "positive"},
            "label2id": {"negative": 0, "neutral": 1, "positive": 2},
        },
        "training": {
            "output_dir": str(out_dir),
            "logging_dir": str(log_dir),
            "num_train_epochs": 2,
            "per_device_train_batch_size": 4,
            "seeds": [42, 43],
        },
    }

    train_data = [{"text": f"text {i}", "label": "neutral"} for i in range(12)]
    val_data = [{"text": f"val {i}", "label": "positive"} for i in range(6)]
    test_data = [{"text": f"test {i}", "label": "negative"} for i in range(6)]
    indomain_data = [{"text": f"id {i}", "label": "positive"} for i in range(6)]

    logger = MetricLogger(csv_file)
    summary = run_dry_run_training(
        config=config,
        train_data=train_data,
        val_data=val_data,
        test_data=test_data,
        indomain_data=indomain_data,
        logger=logger,
    )

    assert summary["status"] == "completed"
    assert summary["mode"] == "dry_run_simulation"
    assert summary["seeds"] == [42, 43]
    assert len(summary["per_seed_results"]) == 2

    # Validation and test metrics computed
    assert summary["validation_metrics"]["macro_f1_mean"] > 0.70
    assert summary["financial_phrasebank_test_metrics"]["macro_f1_mean"] > 0.70
    assert summary["in_domain_news_test_metrics"]["macro_f1_mean"] > 0.50

    # Domain gap quantified
    gap = summary["domain_gap"]
    assert gap["macro_f1_drop"] > 0.05
    assert gap["relative_f1_degradation_pct"] > 5.0
    assert "Macro-F1 drops by" in gap["description"]

    # Mock checkpoint config saved to best/
    best_config = out_dir / "best" / "config.json"
    assert best_config.exists()
    cfg_obj = json.loads(best_config.read_text(encoding="utf-8"))
    assert cfg_obj["num_labels"] == 3


def test_fine_tuned_model_registry() -> None:
    """Verify fine_tuned model discovery and metadata in the model registry."""
    registered = list_models()
    assert "fine_tuned" in registered

    domain_doc = get_model_domain("fine_tuned")
    assert "Financial PhraseBank" in domain_doc
    assert "DistilRoBERTa" in domain_doc


def test_fine_tuned_model_inference_mock(tmp_path: Path) -> None:
    """Verify fine-tuned model inference with simulated pipeline factory."""

    def mock_factory(model_id: str, revision: str) -> Any:
        def _pipe(texts: list[str]) -> list[list[dict[str, Any]]]:
            return [
                [
                    {"label": "LABEL_2", "score": 0.88},  # positive
                    {"label": "LABEL_1", "score": 0.08},  # neutral
                    {"label": "LABEL_0", "score": 0.04},  # negative
                ]
                for _ in texts
            ]

        return _pipe

    model = HFTransformerModel(
        model_id=str(tmp_path),
        name="fine_tuned",
        pipeline_factory=mock_factory,
        label_mapping={
            "LABEL_0": "negative",
            "LABEL_1": "neutral",
            "LABEL_2": "positive",
        },
    )

    preds = model.predict(["Corporate earnings jump 25%"])
    assert len(preds) == 1
    p = preds[0]
    assert p.label == "positive"
    assert round(p.score, 2) == 0.84  # 0.88 - 0.04
    assert p.probabilities["positive"] == 0.88
