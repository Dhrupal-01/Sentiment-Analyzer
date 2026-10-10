"""Tests for 'newsent label' and 'newsent label-agreement' CLI commands."""

import tempfile

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from news_sentiment.cli import app
from news_sentiment.config.settings import get_settings
from news_sentiment.storage.database import init_db
from news_sentiment.storage.models import Article, ArticleAnnotation
from news_sentiment.storage.repository import AnnotationRepository

runner = CliRunner()


def test_cli_label_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify interactive 'newsent label' workflow without pre-filled suggestions."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        test_db = f"sqlite:///{tmp.name}"
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()

        engine = create_engine(test_db)
        init_db(engine)

        with Session(engine) as session:
            session.add(
                Article(
                    title="Clean energy investments jump 40% globally",
                    normalized_title="clean energy investments jump 40% globally",
                    url="https://example.org/green-energy",
                    topic="climate",
                    provider="rss",
                )
            )
            session.commit()

        # Simulate user inputs:
        # 1. 'p' (positive sentiment)
        # 2. 'jump' (rationale words)
        # 3. 'Strong expansion note' (notes)
        # 4. 'q' (quit)
        result = runner.invoke(
            app,
            ["label", "--annotator", "test_user", "--limit", "10"],
            input="p\njump\nStrong expansion note\nq\n",
        )
        assert result.exit_code == 0
        assert "Loaded 1 candidate headline(s)" in result.output
        assert "Clean energy investments jump 40% globally" in result.output
        assert "Saved: 'positive'" in result.output

        # Verify record in database
        with Session(engine) as session:
            anno = session.scalar(
                select(ArticleAnnotation).where(ArticleAnnotation.annotator_id == "test_user")
            )
            assert anno is not None
            assert anno.label == "positive"
            assert anno.notes == "Strong expansion note"
            assert anno.rationale_tokens == ["jump"]

        # Running again shows no unannotated headlines
        result_empty = runner.invoke(app, ["label", "--annotator", "test_user"])
        assert result_empty.exit_code == 0
        assert "No unannotated headlines available for 'test_user'" in result_empty.output


def test_cli_label_agreement(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 'newsent label-agreement' outputs agreement rate, kappa, and confusion matrix."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        test_db = f"sqlite:///{tmp.name}"
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()

        engine = create_engine(test_db)
        init_db(engine)

        with Session(engine) as session:
            # 2 articles
            a1 = Article(
                title="Economic output surges to record levels",
                normalized_title="economic output surges to record levels",
                url="https://example.org/surge",
                topic="economy",
                provider="gdelt",
            )
            a2 = Article(
                title="Central bank leaves benchmark rate unchanged",
                normalized_title="central bank leaves benchmark rate unchanged",
                url="https://example.org/rate",
                topic="economy",
                provider="gdelt",
            )
            session.add_all([a1, a2])
            session.flush()

            # Annotator 1
            session.add(ArticleAnnotation(article_id=a1.id, annotator_id="u1", label="positive"))
            session.add(ArticleAnnotation(article_id=a2.id, annotator_id="u1", label="neutral"))

            # Annotator 2 agrees on a1, disagrees on a2
            session.add(ArticleAnnotation(article_id=a1.id, annotator_id="u2", label="positive"))
            session.add(ArticleAnnotation(article_id=a2.id, annotator_id="u2", label="positive"))
            session.commit()

        result = runner.invoke(app, ["label-agreement", "--annotator1", "u1", "--annotator2", "u2"])
        assert result.exit_code == 0
        assert "Inter-Annotator Agreement Report: 'u1' vs 'u2'" in result.output
        assert "Overlapping Annotations: 2" in result.output
        assert "Raw Agreement Rate:      50.0%" in result.output
        assert "Disagreements (1 of 2 disagreed):" in result.output
        assert "Central bank leaves benchmark rate unchanged" in result.output


def test_cli_label_agreement_no_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify label-agreement gracefully reports when no overlapping annotations exist."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        test_db = f"sqlite:///{tmp.name}"
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()

        engine = create_engine(test_db)
        init_db(engine)

        result = runner.invoke(app, ["label-agreement", "--annotator1", "u1", "--annotator2", "u2"])
        assert result.exit_code == 0
        assert "No overlapping non-skipped annotations found" in result.output


def test_annotation_repository_stratified_sample() -> None:
    """Verify AnnotationRepository stratified sampling across topics and providers."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    with Session(engine) as session:
        # Add articles across two topics and two providers
        for i in range(10):
            session.add(
                Article(
                    title=f"Article {i}",
                    normalized_title=f"article {i}",
                    url=f"https://example.org/art/{i}",
                    topic="markets" if i < 5 else "tech",
                    provider="gdelt" if i % 2 == 0 else "rss",
                )
            )
        session.commit()

        sample = AnnotationRepository.get_stratified_sample(
            session=session,
            annotator_id="test_user",
            sample_size=4,
            seed=42,
        )
        assert len(sample) == 4
        topics = {a.topic for a in sample}
        assert "markets" in topics
        assert "tech" in topics
