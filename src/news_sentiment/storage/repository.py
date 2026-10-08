"""Repository for database CRUD operations, deduplication tracking, and audit logging."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from news_sentiment.storage.dedup import normalize_title, normalize_url
from news_sentiment.storage.models import Article, ArticleDuplicate, IngestionRun, Topic


class TopicRepository:
    """Operations on news tracking topics."""

    @staticmethod
    def add_topic(session: Session, name: str, query: str) -> Topic:
        """Create and persist a new tracking topic."""
        existing = session.scalar(select(Topic).where(Topic.name == name))
        if existing:
            existing.query = query
            existing.is_active = True
            session.flush()
            return existing

        topic = Topic(name=name, query=query, is_active=True)
        session.add(topic)
        session.flush()
        return topic

    @staticmethod
    def list_topics(session: Session, active_only: bool = False) -> list[Topic]:
        """Retrieve topics ordered by creation date."""
        stmt = select(Topic)
        if active_only:
            stmt = stmt.where(Topic.is_active.is_(True))
        stmt = stmt.order_by(Topic.name.asc())
        return list(session.scalars(stmt).all())

    @staticmethod
    def get_topic(session: Session, name: str) -> Topic | None:
        """Retrieve a topic by name."""
        return session.scalar(select(Topic).where(Topic.name == name))


class ArticleRepository:
    """Operations on news articles with deduplication auditing."""

    @staticmethod
    def ingest_article(
        session: Session,
        title: str,
        url: str,
        provider: str,
        topic: str,
        outlet: str | None = None,
        published_at: datetime | None = None,
    ) -> tuple[Article, bool, str | None]:
        """Ingest an article with exact-URL and normalized-title deduplication.

        Returns:
            (article, is_inserted, duplicate_reason)
            - If new: returns (article, True, None)
            - If duplicate: returns (canonical_article, False, reason) and audits the duplicate.
        """
        canonical_url = normalize_url(url)
        canonical_title = normalize_title(title)

        # Check 1: Exact URL match
        existing_by_url = session.scalar(select(Article).where(Article.url == canonical_url))
        if existing_by_url:
            dup = ArticleDuplicate(
                canonical_article_id=existing_by_url.id,
                duplicate_url=canonical_url,
                duplicate_title=title,
                provider=provider,
                topic=topic,
                reason="exact_url",
            )
            session.add(dup)
            session.flush()
            return existing_by_url, False, "exact_url"

        # Check 2: Near-duplicate title match
        existing_by_title = session.scalar(
            select(Article).where(Article.normalized_title == canonical_title)
        )
        if existing_by_title:
            dup = ArticleDuplicate(
                canonical_article_id=existing_by_title.id,
                duplicate_url=canonical_url,
                duplicate_title=title,
                provider=provider,
                topic=topic,
                reason="normalized_title",
            )
            session.add(dup)
            session.flush()
            return existing_by_title, False, "normalized_title"

        # Insert canonical article
        article = Article(
            title=title.strip(),
            normalized_title=canonical_title,
            url=canonical_url,
            outlet=outlet.strip() if outlet else None,
            published_at=published_at,
            provider=provider,
            topic=topic,
        )
        session.add(article)
        session.flush()
        return article, True, None


class IngestionRunRepository:
    """Audit tracker for pipeline ingestion executions."""

    @staticmethod
    def start_run(
        session: Session,
        provider: str,
        topic: str | None = None,
    ) -> IngestionRun:
        """Create and persist a new IngestionRun record."""
        run = IngestionRun(
            provider=provider,
            topic=topic,
            status="in_progress",
        )
        session.add(run)
        session.flush()
        return run

    @staticmethod
    def finish_run(
        session: Session,
        run_id: int,
        fetched: int,
        inserted: int,
        duplicates: int,
        errors: str | None = None,
        status: str = "completed",
    ) -> IngestionRun | None:
        """Update and finalize an IngestionRun record."""
        run = session.get(IngestionRun, run_id)
        if run:
            run.ended_at = datetime.now(UTC)
            run.articles_fetched = fetched
            run.articles_inserted = inserted
            run.duplicates_found = duplicates
            run.errors = errors
            run.status = status
            session.flush()
        return run
