"""GDELT DOC 2.0 API source implementation."""

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.sources.base import ArticleData, BaseNewsSource
from news_sentiment.sources.client import ProviderRateLimiter, execute_request_with_retry
from news_sentiment.sources.exceptions import SourceParseError


class GdeltSource(BaseNewsSource):
    """News source client for the GDELT DOC 2.0 API."""

    GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or httpx.Client(
            timeout=self.settings.request_timeout,
            headers={"User-Agent": "NewsSentimentAnalyzer/0.1.0"},
        )
        self.rate_limiter = ProviderRateLimiter(min_interval_seconds=self.settings.rate_limit_gdelt)

    @property
    def name(self) -> str:
        return "gdelt"

    def _parse_gdelt_date(self, date_str: str | None) -> datetime | None:
        """Parse GDELT date format (e.g. '20261008T123000Z' or '20261008123000')."""
        if not date_str:
            return None
        cleaned = date_str.replace("Z", "").replace("T", "")
        try:
            return datetime.strptime(cleaned[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        except ValueError:
            return None

    def fetch_headlines(
        self,
        topic: str,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ArticleData]:
        """Fetch headlines matching topic/query from GDELT DOC 2.0."""
        search_query = query.strip() if query and query.strip() else topic.strip()
        max_records = max(1, min(limit, 250))

        params = {
            "query": search_query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": str(max_records),
            "sort": "datedesc",
        }

        response = execute_request_with_retry(
            client=self.client,
            method="GET",
            url=self.GDELT_URL,
            provider=self.name,
            rate_limiter=self.rate_limiter,
            params=params,
        )

        try:
            # GDELT may return empty text or whitespace if no articles found
            text = response.text.strip()
            if not text:
                return []
            payload: dict[str, Any] = json.loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            # GDELT occasionally returns plain HTML or error text
            if "articles" not in response.text:
                raise SourceParseError(
                    f"Invalid JSON returned from GDELT: {response.text[:150]}",
                    provider=self.name,
                ) from exc
            payload = {}

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

            outlet = item.get("domain") or item.get("sourcecountry") or None
            published_at = self._parse_gdelt_date(item.get("seendate"))

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
