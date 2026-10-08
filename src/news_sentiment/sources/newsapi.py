"""NewsAPI source implementation for developer and staging ingestion."""

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.sources.base import ArticleData, BaseNewsSource
from news_sentiment.sources.client import ProviderRateLimiter, execute_request_with_retry
from news_sentiment.sources.exceptions import (
    NewsSourceError,
    SourceAuthenticationError,
    SourceConfigurationError,
    SourceParseError,
    SourceRateLimitError,
)


class NewsApiSource(BaseNewsSource):
    """News source client for the NewsAPI.org service (Developer / Free plan)."""

    NEWSAPI_URL = "https://newsapi.org/v2/everything"

    def __init__(
        self,
        api_key: str | None = None,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.api_key = api_key or self.settings.newsapi_key
        self.client = client or httpx.Client(
            timeout=self.settings.request_timeout,
            headers={"User-Agent": "NewsSentimentAnalyzer/0.1.0"},
        )
        self.rate_limiter = ProviderRateLimiter(
            min_interval_seconds=self.settings.rate_limit_newsapi
        )

    @property
    def name(self) -> str:
        return "newsapi"

    def _parse_iso_date(self, date_str: str | None) -> datetime | None:
        """Parse ISO-8601 date string to UTC datetime."""
        if not date_str:
            return None
        try:
            # Handle standard 'Z' or offset formats
            cleaned = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            return None

    def fetch_headlines(
        self,
        topic: str,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ArticleData]:
        """Fetch headlines from NewsAPI.

        Raises:
            SourceConfigurationError if no API key is provided.
            SourceAuthenticationError, SourceRateLimitError, or NewsSourceError on failure.
        """
        if not self.api_key or not self.api_key.strip():
            raise SourceConfigurationError(
                "NewsAPI requires an API key. Please configure NEWSAPI_KEY in your environment.",
                provider=self.name,
            )

        search_query = query.strip() if query and query.strip() else topic.strip()
        page_size = max(1, min(limit, 100))

        params = {
            "q": search_query,
            "pageSize": str(page_size),
            "language": "en",
            "sortBy": "publishedAt",
        }
        headers = {
            "X-Api-Key": self.api_key,
        }

        response = execute_request_with_retry(
            client=self.client,
            method="GET",
            url=self.NEWSAPI_URL,
            provider=self.name,
            rate_limiter=self.rate_limiter,
            params=params,
            headers=headers,
        )

        try:
            payload: dict[str, Any] = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise SourceParseError(
                f"Invalid JSON received from NewsAPI: {response.text[:150]}",
                provider=self.name,
            ) from exc

        status = payload.get("status")
        if status != "ok":
            code = payload.get("code", "")
            message = payload.get("message", "Unknown NewsAPI error")
            if code in ("apiKeyMissing", "apiKeyInvalid", "apiKeyDisabled"):
                raise SourceAuthenticationError(message, provider=self.name)
            if code in ("rateLimited", "maximumResultsReached"):
                raise SourceRateLimitError(message, provider=self.name)
            raise NewsSourceError(f"NewsAPI error ({code}): {message}", provider=self.name)

        raw_articles = payload.get("articles", [])
        if not isinstance(raw_articles, list):
            return []

        results: list[ArticleData] = []
        for item in raw_articles:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue

            source_info = item.get("source")
            outlet = source_info.get("name") if isinstance(source_info, dict) else None
            published_at = self._parse_iso_date(item.get("publishedAt"))

            results.append(
                ArticleData(
                    title=title,
                    url=url,
                    outlet=outlet,
                    published_at=published_at,
                    provider=self.name,
                    topic=topic,
                    raw_data=item,
                )
            )

        return results[:limit]
