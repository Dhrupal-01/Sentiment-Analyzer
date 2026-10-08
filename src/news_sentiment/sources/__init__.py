"""News sources package: interfaces, client implementations, and provider registry."""

from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.sources.base import ArticleData, BaseNewsSource
from news_sentiment.sources.exceptions import (
    NewsSourceError,
    SourceAuthenticationError,
    SourceConfigurationError,
    SourceNetworkError,
    SourceParseError,
    SourceRateLimitError,
    SourceTimeoutError,
)
from news_sentiment.sources.gdelt import GdeltSource
from news_sentiment.sources.newsapi import NewsApiSource
from news_sentiment.sources.rss import RssFeedSource

__all__ = [
    "ArticleData",
    "BaseNewsSource",
    "GdeltSource",
    "NewsApiSource",
    "NewsSourceError",
    "RssFeedSource",
    "SourceAuthenticationError",
    "SourceConfigurationError",
    "SourceNetworkError",
    "SourceParseError",
    "SourceRateLimitError",
    "SourceTimeoutError",
    "get_source",
    "list_sources",
]


def list_sources() -> list[str]:
    """List supported source provider identifiers."""
    return ["gdelt", "rss", "newsapi"]


def get_source(name: str, settings: Settings | None = None) -> BaseNewsSource:
    """Retrieve an initialized news source provider by name.

    Args:
        name: Provider name ('gdelt', 'rss', or 'newsapi').
        settings: Optional Settings override.

    Returns:
        Configured BaseNewsSource instance.

    Raises:
        SourceConfigurationError if provider name is unrecognized.
    """
    app_settings = settings or get_settings()
    provider_name = name.lower().strip()

    if provider_name == "gdelt":
        return GdeltSource(settings=app_settings)
    if provider_name == "rss":
        return RssFeedSource(settings=app_settings)
    if provider_name == "newsapi":
        return NewsApiSource(settings=app_settings)

    raise SourceConfigurationError(
        f"Unsupported news source provider: '{name}'. Supported providers: {list_sources()}",
        provider=name,
    )
