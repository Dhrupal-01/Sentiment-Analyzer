"""Common interface and data transfer objects for news source providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ArticleData:
    """Standardized representation of a fetched headline across all providers."""

    title: str
    url: str
    outlet: str | None
    published_at: datetime | None
    provider: str
    topic: str
    raw_data: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


class BaseNewsSource(ABC):
    """Abstract base class for all news headline ingestion providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for this source provider (e.g. 'gdelt', 'rss')."""

    @abstractmethod
    def fetch_headlines(
        self,
        topic: str,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ArticleData]:
        """Fetch headlines for a given topic or query from this provider.

        Args:
            topic: Canonical topic label (e.g. 'technology', 'markets').
            query: Optional search keyword expression (defaults to topic if None).
            limit: Maximum number of articles to retrieve.

        Returns:
            A list of standardized ArticleData records.

        Raises:
            NewsSourceError or one of its typed subclasses on failure.
        """
