"""Tests for CLI 'newsent analyze' and 'newsent compare' commands."""

import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from news_sentiment.cli import app
from news_sentiment.config.settings import get_settings
from news_sentiment.models.base import Prediction, SentimentModel
from news_sentiment.models.registry import register_model
from news_sentiment.storage.database import init_db
from news_sentiment.storage.models import Article

runner = CliRunner()


class CliTestModel(SentimentModel):
    """Deterministic test model for CLI tests."""

    def __init__(self, name: str, fixed_label: str, score: float) -> None:
        self._name = name
        self.fixed_label = fixed_label
        self.fixed_score = score

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "cli-test-1.0"

    def predict(self, texts: list[str]) -> list[Prediction]:
        return [
            Prediction(
                label=self.fixed_label,  # type: ignore[arg-type]
                score=self.fixed_score,
                probabilities={"positive": 0.5, "neutral": 0.3, "negative": 0.2},
            )
            for _ in texts
        ]


@pytest.fixture(autouse=True)
def register_cli_mock_models() -> None:
    """Register deterministic models for CLI comparison tests."""
    register_model("model_pos", lambda: CliTestModel("model_pos", "positive", 0.85))
    register_model("model_neg", lambda: CliTestModel("model_neg", "negative", -0.85))


def test_cli_analyze_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 'newsent analyze --model vader' scores unanalyzed articles."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        test_db = f"sqlite:///{tmp.name}"
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()

        engine = create_engine(test_db)
        init_db(engine)

        # Seed an article
        with Session(engine) as session:
            session.add(
                Article(
                    title="Tech stocks surge on strong AI quarterly revenue",
                    normalized_title="tech stocks surge on strong ai quarterly revenue",
                    url="https://example.org/ai-surge",
                    topic="tech",
                    provider="rss",
                )
            )
            session.commit()

        # Run analyze command
        result = runner.invoke(app, ["analyze", "--model", "vader"])
        assert result.exit_code == 0
        assert "Analyzing headlines with model 'vader'" in result.output
        assert "1 article(s) scored" in result.output

        # Run analyze again; should score 0 articles
        result_again = runner.invoke(app, ["analyze", "--model", "vader"])
        assert result_again.exit_code == 0
        assert "0 article(s) scored" in result_again.output


def test_cli_analyze_invalid_model() -> None:
    """Verify 'newsent analyze --model unknown' displays error and exit code 1."""
    result = runner.invoke(app, ["analyze", "--model", "unknown_model_name"])
    assert result.exit_code == 1
    assert "Unknown model 'unknown_model_name'" in result.output


def test_cli_compare_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 'newsent compare' calculates agreement table and reports disagreements."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        test_db = f"sqlite:///{tmp.name}"
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()

        engine = create_engine(test_db)
        init_db(engine)

        with Session(engine) as session:
            session.add(
                Article(
                    title="Economic growth accelerates amid fiscal expansion",
                    normalized_title="economic growth accelerates amid fiscal expansion",
                    url="https://example.org/econ-growth",
                    topic="economy",
                    provider="gdelt",
                )
            )
            session.commit()

        result = runner.invoke(
            app,
            ["compare", "--topic", "economy", "--models", "model_pos,model_neg"],
        )
        assert result.exit_code == 0
        assert "Model Comparison Report" in result.output
        assert "model_pos vs model_neg" in result.output
        assert "0.0%" in result.output  # 0% agreement
        assert "Disagreements (1 of 1 headlines disagreed):" in result.output
        assert "Economic growth accelerates amid fiscal expansion" in result.output


def test_cli_compare_validation_errors() -> None:
    """Verify error checking for minimum 2 models and empty topic handling."""
    # Fewer than 2 models
    result_too_few = runner.invoke(app, ["compare", "--topic", "tech", "--models", "vader"])
    assert result_too_few.exit_code == 1
    assert "Please provide at least 2 models" in result_too_few.output

    # Nonexistent model
    result_bad_model = runner.invoke(
        app, ["compare", "--topic", "tech", "--models", "vader,fake_model"]
    )
    assert result_bad_model.exit_code == 1
    assert "Error loading model 'fake_model'" in result_bad_model.output
