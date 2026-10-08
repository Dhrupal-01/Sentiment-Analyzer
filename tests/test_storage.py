"""Tests for storage layer, repository operations, deduplication, and audit trails."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from news_sentiment.storage.database import init_db
from news_sentiment.storage.models import Article, ArticleDuplicate
from news_sentiment.storage.repository import (
    ArticleRepository,
    IngestionRunRepository,
    TopicRepository,
)


def test_topic_repository() -> None:
    """Verify Topic CRUD and uniqueness operations."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    with Session(engine) as session:
        # Add topics
        t1 = TopicRepository.add_topic(session, name="markets", query="stocks inflation economy")
        session.commit()
        assert t1.id is not None
        assert t1.name == "markets"

        # Update existing topic query idempotently
        t1_updated = TopicRepository.add_topic(session, name="markets", query="updated query")
        session.commit()
        assert t1_updated.id == t1.id
        assert t1_updated.query == "updated query"

        # Add second topic
        TopicRepository.add_topic(session, name="tech", query="semiconductors AI software")
        session.commit()

        # List topics
        topics = TopicRepository.list_topics(session)
        assert len(topics) == 2
        assert [t.name for t in topics] == ["markets", "tech"]

        # Get single topic
        fetched = TopicRepository.get_topic(session, "tech")
        assert fetched is not None
        assert fetched.name == "tech"


def test_article_repository_deduplication_exact_url() -> None:
    """Verify that duplicate URL is recorded in article_duplicates rather than inserted."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    with Session(engine) as session:
        # 1. Ingest original article
        art1, is_inserted, reason = ArticleRepository.ingest_article(
            session=session,
            title="Markets Rally on Tech Surge - Reuters",
            url="https://reuters.com/markets/123?utm_source=twitter",
            provider="gdelt",
            topic="markets",
            outlet="Reuters",
            published_at=datetime.now(UTC),
        )
        session.commit()
        assert is_inserted is True
        assert reason is None
        assert art1.id is not None

        # 2. Ingest duplicate with same canonical URL (differing only in tracking param)
        art2, is_inserted2, reason2 = ArticleRepository.ingest_article(
            session=session,
            title="Markets Rally on Tech Surge - Reuters",
            url="https://reuters.com/markets/123?utm_medium=email",
            provider="gdelt",
            topic="markets",
            outlet="Reuters",
        )
        session.commit()
        assert is_inserted2 is False
        assert reason2 == "exact_url"
        assert art2.id == art1.id

        # Verify only 1 canonical article exists
        articles = session.scalars(select(Article)).all()
        assert len(list(articles)) == 1

        # Verify duplicate was audited
        duplicates = session.scalars(select(ArticleDuplicate)).all()
        assert len(list(duplicates)) == 1
        assert duplicates[0].canonical_article_id == art1.id
        assert duplicates[0].reason == "exact_url"


def test_article_repository_deduplication_normalized_title() -> None:
    """Verify that near-duplicate headline titles across URLs are audited as duplicates."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    with Session(engine) as session:
        # 1. Ingest initial syndicated article
        art1, is_ins1, _ = ArticleRepository.ingest_article(
            session=session,
            title="Oil Prices Slump Amid Rising Supply - Reuters",
            url="https://reuters.com/oil-slump",
            provider="gdelt",
            topic="commodities",
            outlet="Reuters",
        )
        session.commit()
        assert is_ins1 is True

        # 2. Ingest syndicated article from another outlet with identical core title
        art2, is_ins2, reason2 = ArticleRepository.ingest_article(
            session=session,
            title="Oil prices slump amid rising supply | Yahoo Finance",
            url="https://finance.yahoo.com/news/oil-slump-supply",
            provider="rss",
            topic="commodities",
            outlet="Yahoo Finance",
        )
        session.commit()
        assert is_ins2 is False
        assert reason2 == "normalized_title"
        assert art2.id == art1.id

        # Verify article count is still 1
        articles = session.scalars(select(Article)).all()
        assert len(list(articles)) == 1

        # Verify duplicate recorded
        dup = session.scalar(select(ArticleDuplicate))
        assert dup is not None
        assert dup.canonical_article_id == art1.id
        assert dup.reason == "normalized_title"
        assert dup.provider == "rss"


def test_ingestion_run_lifecycle() -> None:
    """Verify IngestionRun status and metric transitions."""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    with Session(engine) as session:
        run = IngestionRunRepository.start_run(session, provider="gdelt", topic="markets")
        session.commit()
        run_id = run.id
        assert run.status == "in_progress"
        assert run.ended_at is None

        finished = IngestionRunRepository.finish_run(
            session=session,
            run_id=run_id,
            fetched=50,
            inserted=45,
            duplicates=5,
            status="completed",
        )
        session.commit()
        assert finished is not None
        assert finished.status == "completed"
        assert finished.articles_fetched == 50
        assert finished.articles_inserted == 45
        assert finished.duplicates_found == 5
        assert finished.ended_at is not None
