"""Ingestion service coordinating fetching, deduplication, and persistence."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from news_sentiment.config.logging import get_logger
from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.sources import BaseNewsSource, get_source
from news_sentiment.sources.exceptions import NewsSourceError
from news_sentiment.storage.database import get_db_session
from news_sentiment.storage.repository import (
    ArticleRepository,
    IngestionRunRepository,
    TopicRepository,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class IngestionSummary:
    """Summary metrics of an ingestion run."""

    topic: str
    provider: str
    articles_fetched: int
    articles_inserted: int
    duplicates_found: int
    errors: str | None = None


class IngestionService:
    """Service orchestrating news headline collection, deduplication, and auditing."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def ingest_topic(
        self,
        topic: str,
        source: BaseNewsSource | str = "gdelt",
        query: str | None = None,
        limit: int = 100,
        session: Session | None = None,
    ) -> IngestionSummary:
        """Fetch headlines for a single topic and ingest with deduplication."""
        provider_client = (
            get_source(source, settings=self.settings) if isinstance(source, str) else source
        )
        provider_name = provider_client.name

        def _do_ingest(s: Session) -> IngestionSummary:
            run = IngestionRunRepository.start_run(s, provider=provider_name, topic=topic)
            run_id = run.id

            fetched_count = 0
            inserted_count = 0
            duplicates_count = 0
            error_msg: str | None = None

            try:
                articles = provider_client.fetch_headlines(topic=topic, query=query, limit=limit)
                fetched_count = len(articles)

                for item in articles:
                    _, is_inserted, _ = ArticleRepository.ingest_article(
                        session=s,
                        title=item.title,
                        url=item.url,
                        provider=item.provider,
                        topic=item.topic,
                        outlet=item.outlet,
                        published_at=item.published_at,
                    )
                    if is_inserted:
                        inserted_count += 1
                    else:
                        duplicates_count += 1

                IngestionRunRepository.finish_run(
                    session=s,
                    run_id=run_id,
                    fetched=fetched_count,
                    inserted=inserted_count,
                    duplicates=duplicates_count,
                    status="completed",
                )

            except NewsSourceError as exc:
                error_msg = str(exc)
                logger.error("Ingestion error for %s (%s): %s", topic, provider_name, exc)
                IngestionRunRepository.finish_run(
                    session=s,
                    run_id=run_id,
                    fetched=fetched_count,
                    inserted=inserted_count,
                    duplicates=duplicates_count,
                    errors=error_msg,
                    status="failed",
                )
            except Exception as exc:
                error_msg = f"Unexpected failure: {exc}"
                logger.exception("Unexpected error during ingestion: %s", exc)
                IngestionRunRepository.finish_run(
                    session=s,
                    run_id=run_id,
                    fetched=fetched_count,
                    inserted=inserted_count,
                    duplicates=duplicates_count,
                    errors=error_msg,
                    status="failed",
                )

            return IngestionSummary(
                topic=topic,
                provider=provider_name,
                articles_fetched=fetched_count,
                articles_inserted=inserted_count,
                duplicates_found=duplicates_count,
                errors=error_msg,
            )

        if session is not None:
            return _do_ingest(session)

        with get_db_session() as new_session:
            return _do_ingest(new_session)

    def collect_all(
        self,
        source: BaseNewsSource | str = "gdelt",
        limit: int = 100,
        session: Session | None = None,
    ) -> list[IngestionSummary]:
        """Ingest headlines for every configured active topic."""

        def _do_collect(s: Session) -> list[IngestionSummary]:
            topics = TopicRepository.list_topics(s, active_only=True)
            summaries: list[IngestionSummary] = []
            for t in topics:
                summary = self.ingest_topic(
                    topic=t.name,
                    source=source,
                    query=t.query,
                    limit=limit,
                    session=s,
                )
                summaries.append(summary)
            return summaries

        if session is not None:
            return _do_collect(session)

        with get_db_session() as new_session:
            return _do_collect(new_session)
