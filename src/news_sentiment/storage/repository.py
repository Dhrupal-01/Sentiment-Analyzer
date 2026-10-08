"""Repository for database CRUD operations, deduplication tracking, and audit logging."""

import random
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from news_sentiment.storage.dedup import normalize_title, normalize_url
from news_sentiment.storage.models import (
    Article,
    ArticleAnnotation,
    ArticleDuplicate,
    IngestionRun,
    Topic,
)


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


class AnnotationRepository:
    """Operations on ground-truth human annotations."""

    @staticmethod
    def save_annotation(
        session: Session,
        article_id: int,
        annotator_id: str,
        label: str,
        notes: str | None = None,
    ) -> ArticleAnnotation:
        """Create or update a human annotation for an article."""
        existing = session.scalar(
            select(ArticleAnnotation).where(
                (ArticleAnnotation.article_id == article_id)
                & (ArticleAnnotation.annotator_id == annotator_id)
            )
        )
        if existing:
            existing.label = label
            existing.notes = notes
            existing.updated_at = datetime.now(UTC)
            session.flush()
            return existing

        annotation = ArticleAnnotation(
            article_id=article_id,
            annotator_id=annotator_id,
            label=label,
            notes=notes,
        )
        session.add(annotation)
        session.flush()
        return annotation

    @staticmethod
    def get_annotations(
        session: Session,
        annotator_id: str | None = None,
        exclude_skipped: bool = False,
    ) -> list[ArticleAnnotation]:
        """Fetch annotations, optionally filtered by annotator."""
        stmt = select(ArticleAnnotation).order_by(ArticleAnnotation.id.asc())
        if annotator_id:
            stmt = stmt.where(ArticleAnnotation.annotator_id == annotator_id)
        if exclude_skipped:
            stmt = stmt.where(ArticleAnnotation.label != "skip")
        return list(session.scalars(stmt).all())

    @staticmethod
    def get_stratified_sample(
        session: Session,
        annotator_id: str,
        sample_size: int = 300,
        seed: int = 42,
    ) -> list[Article]:
        """Sample unannotated articles stratified across topics and news providers."""
        annotated_subq = (
            select(ArticleAnnotation.article_id)
            .where(ArticleAnnotation.annotator_id == annotator_id)
            .scalar_subquery()
        )

        unannotated = list(
            session.scalars(
                select(Article).where(Article.id.not_in(annotated_subq)).order_by(Article.id.asc())
            ).all()
        )

        if len(unannotated) <= sample_size:
            return unannotated

        # Group by stratum: (topic, provider)
        strata: dict[tuple[str, str], list[Article]] = {}
        for art in unannotated:
            key = (art.topic, art.provider)
            strata.setdefault(key, []).append(art)

        # Shuffle each stratum with fixed seed
        rng = random.Random(seed)
        for items in strata.values():
            rng.shuffle(items)

        # Round-robin sampling across strata until sample_size is reached
        sampled: list[Article] = []
        strata_lists = list(strata.values())
        strata_lists.sort(key=lambda s: (s[0].topic, s[0].provider) if s else ("", ""))

        while len(sampled) < sample_size and any(strata_lists):
            for items in strata_lists:
                if items and len(sampled) < sample_size:
                    sampled.append(items.pop(0))

        return sampled

    @staticmethod
    def get_overlapping_annotations(
        session: Session,
        annotator_1: str,
        annotator_2: str,
        exclude_skipped: bool = True,
    ) -> list[tuple[ArticleAnnotation, ArticleAnnotation]]:
        """Find paired annotations across two annotators on the exact same articles."""
        stmt_1 = select(ArticleAnnotation).where(ArticleAnnotation.annotator_id == annotator_1)
        if exclude_skipped:
            stmt_1 = stmt_1.where(ArticleAnnotation.label != "skip")
        annos_1 = {a.article_id: a for a in session.scalars(stmt_1).all()}

        stmt_2 = select(ArticleAnnotation).where(ArticleAnnotation.annotator_id == annotator_2)
        if exclude_skipped:
            stmt_2 = stmt_2.where(ArticleAnnotation.label != "skip")
        annos_2 = {a.article_id: a for a in session.scalars(stmt_2).all()}

        common_ids = sorted(set(annos_1.keys()) & set(annos_2.keys()))
        return [(annos_1[cid], annos_2[cid]) for cid in common_ids]
