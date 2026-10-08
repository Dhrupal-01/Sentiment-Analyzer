"""Tests for IngestionService end-to-end ingestion and idempotency."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from news_sentiment.config.settings import Settings
from news_sentiment.sources.base import ArticleData, BaseNewsSource
from news_sentiment.sources.exceptions import SourceNetworkError
from news_sentiment.sources.service import IngestionService
from news_sentiment.storage.database import init_db
from news_sentiment.storage.models import Article, ArticleDuplicate, IngestionRun
from news_sentiment.storage.repository import TopicRepository


class DummyMockSource(BaseNewsSource):
    """Predictable mock news source returning canned articles."""

    def __init__(self, name: str = "mock_source", should_fail: bool = False) -> None:
        self._name = name
        self.should_fail = should_fail

    @property
    def name(self) -> str:
        return self._name

    def fetch_headlines(
        self,
        topic: str,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ArticleData]:
        if self.should_fail:
            raise SourceNetworkError("Simulated connection failure", provider=self.name)

        return [
            ArticleData(
                title=f"Breaking Story 1 for {topic} - Reuters",
                url=f"https://news.org/{topic}/story-1?utm_source=rss",
                outlet="Reuters",
                published_at=datetime.now(UTC),
                provider=self.name,
                topic=topic,
            ),
            ArticleData(
                title=f"Analysis of Policy on {topic} | BBC News",
                url=f"https://news.org/{topic}/story-2",
                outlet="BBC",
                published_at=datetime.now(UTC),
                provider=self.name,
                topic=topic,
            ),
        ]


def test_ingestion_service_idempotency() -> None:
    """Verify that running ingestion multiple times on identical input is strictly idempotent."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    settings = Settings()
    service = IngestionService(settings=settings)
    mock_source = DummyMockSource(name="test_provider")

    with Session(engine) as session:
        # Pass 1: Initial Ingestion
        summary1 = service.ingest_topic(
            topic="markets",
            source=mock_source,
            limit=10,
            session=session,
        )
        session.commit()

        assert summary1.articles_fetched == 2
        assert summary1.articles_inserted == 2
        assert summary1.duplicates_found == 0
        assert summary1.errors is None

        # Verify DB state after pass 1
        articles_pass1 = session.scalars(select(Article)).all()
        assert len(list(articles_pass1)) == 2

        duplicates_pass1 = session.scalars(select(ArticleDuplicate)).all()
        assert len(list(duplicates_pass1)) == 0

        # Pass 2: Re-run the exact same ingestion
        summary2 = service.ingest_topic(
            topic="markets",
            source=mock_source,
            limit=10,
            session=session,
        )
        session.commit()

        # Idempotency assertions:
        # Zero new articles inserted, all 2 detected as duplicates
        assert summary2.articles_fetched == 2
        assert summary2.articles_inserted == 0
        assert summary2.duplicates_found == 2
        assert summary2.errors is None

        # Verify DB state after pass 2: canonical articles remain strictly 2!
        articles_pass2 = session.scalars(select(Article)).all()
        assert len(list(articles_pass2)) == 2

        # 2 duplicates recorded in audit table
        duplicates_pass2 = session.scalars(select(ArticleDuplicate)).all()
        assert len(list(duplicates_pass2)) == 2


def test_ingestion_service_collect_all() -> None:
    """Verify collect_all ingests every active configured topic."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    settings = Settings()
    service = IngestionService(settings=settings)
    mock_source = DummyMockSource(name="collect_provider")

    with Session(engine) as session:
        TopicRepository.add_topic(session, name="macro", query="interest rates central banks")
        TopicRepository.add_topic(session, name="energy", query="crude oil natural gas")
        session.commit()

        summaries = service.collect_all(source=mock_source, limit=10, session=session)
        session.commit()

        assert len(summaries) == 2
        assert {s.topic for s in summaries} == {"macro", "energy"}
        assert sum(s.articles_inserted for s in summaries) == 4

        # Verify IngestionRun audit logs were persisted for each topic
        runs = session.scalars(select(IngestionRun)).all()
        assert len(list(runs)) == 2


def test_ingestion_service_error_handling() -> None:
    """Verify IngestionService handles provider errors gracefully and logs failed run."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    service = IngestionService(settings=Settings())
    failing_source = DummyMockSource(name="failing_provider", should_fail=True)

    with Session(engine) as session:
        summary = service.ingest_topic(
            topic="ai",
            source=failing_source,
            session=session,
        )
        session.commit()

        assert summary.errors is not None
        assert "Simulated connection failure" in summary.errors
        assert summary.articles_inserted == 0

        # Verify run status is failed
        run = session.scalar(select(IngestionRun).where(IngestionRun.topic == "ai"))
        assert run is not None
        assert run.status == "failed"
