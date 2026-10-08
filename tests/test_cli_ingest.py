"""Tests for the newsent CLI ingestion and topic commands."""

import tempfile

import pytest
from typer.testing import CliRunner

from news_sentiment.cli import app
from news_sentiment.config.settings import get_settings
from news_sentiment.sources.base import ArticleData, BaseNewsSource

runner = CliRunner()


class MockCliSource(BaseNewsSource):
    """Mock source for CLI command tests."""

    @property
    def name(self) -> str:
        return "gdelt"

    def fetch_headlines(
        self,
        topic: str,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ArticleData]:
        return [
            ArticleData(
                title=f"Sample Headline for {topic} - Reuters",
                url=f"https://example.org/{topic}/1",
                outlet="Reuters",
                published_at=None,
                provider="gdelt",
                topic=topic,
            )
        ]


def test_cli_topics_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 'newsent topics add' and 'newsent topics list' work end-to-end."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        test_db = f"sqlite:///{tmp.name}"
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()

        # 1. List topics when empty
        result_empty = runner.invoke(app, ["topics", "list"])
        assert result_empty.exit_code == 0
        assert "No topics configured" in result_empty.output

        # 2. Add topic
        result_add = runner.invoke(
            app,
            ["topics", "add", "markets", "--query", "stocks inflation interest rates"],
        )
        assert result_add.exit_code == 0
        assert "Topic 'markets' configured with query" in result_add.output

        # 3. List topics after adding
        result_list = runner.invoke(app, ["topics", "list"])
        assert result_list.exit_code == 0
        assert "markets" in result_list.output
        assert "active" in result_list.output


def test_cli_ingest_and_collect(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify 'newsent ingest' and 'newsent collect' execute cleanly with mocked source."""
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        test_db = f"sqlite:///{tmp.name}"
        monkeypatch.setenv("DATABASE_URL", test_db)
        get_settings.cache_clear()
        monkeypatch.setattr(
            "news_sentiment.sources.service.get_source",
            lambda name, settings=None: MockCliSource(),
        )

        # 1. Ingest single topic
        res_ingest = runner.invoke(
            app,
            ["ingest", "--topic", "technology", "--source", "gdelt", "--limit", "10"],
        )
        assert res_ingest.exit_code == 0
        assert "Ingestion completed" in res_ingest.output
        assert "1 fetched, 1 inserted, 0 duplicates" in res_ingest.output

        # 2. Re-ingest single topic to verify idempotency in CLI output
        res_reingest = runner.invoke(
            app,
            ["ingest", "--topic", "technology", "--source", "gdelt", "--limit", "10"],
        )
        assert res_reingest.exit_code == 0
        assert "1 fetched, 0 inserted, 1 duplicates" in res_reingest.output

        # 3. Test collect with configured topic
        runner.invoke(app, ["topics", "add", "technology", "--query", "tech AI"])
        res_collect = runner.invoke(app, ["collect", "--source", "gdelt", "--limit", "5"])
        assert res_collect.exit_code == 0
        assert "Collection complete" in res_collect.output
