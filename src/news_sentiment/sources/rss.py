"""Publisher RSS feed source implementation using feedparser."""

import time
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from news_sentiment.config.logging import get_logger
from news_sentiment.config.settings import Settings, get_settings
from news_sentiment.sources.base import ArticleData, BaseNewsSource
from news_sentiment.sources.client import ProviderRateLimiter, execute_request_with_retry
from news_sentiment.sources.exceptions import SourceParseError

logger = get_logger(__name__)


class RssFeedSource(BaseNewsSource):
    """News source client ingesting publisher RSS syndication feeds."""

    def __init__(
        self,
        feed_urls: list[str] | None = None,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.feed_urls = feed_urls or list(self.settings.default_rss_feeds)
        self.client = client or httpx.Client(
            timeout=self.settings.request_timeout,
            headers={"User-Agent": "NewsSentimentAnalyzer/0.1.0"},
            follow_redirects=True,
        )
        self.rate_limiter = ProviderRateLimiter(min_interval_seconds=self.settings.rate_limit_rss)

    @property
    def name(self) -> str:
        return "rss"

    def _parse_time_struct(self, time_struct: time.struct_time | None) -> datetime | None:
        """Convert a time.struct_time tuple to a UTC timezone-aware datetime."""
        if not time_struct:
            return None
        try:
            timestamp = time.mktime(time_struct)
            return datetime.fromtimestamp(timestamp, tz=UTC)
        except (ValueError, OverflowError):
            return None

    def _matches_query(self, entry: Any, query: str | None) -> bool:
        """Check whether entry matches search keywords in title or summary."""
        if not query or not query.strip():
            return True

        keywords = [k.lower() for k in query.split() if k]
        title = str(getattr(entry, "title", "")).lower()
        summary = str(getattr(entry, "summary", "")).lower()

        return any(k in title or k in summary for k in keywords)

    def fetch_headlines(
        self,
        topic: str,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ArticleData]:
        """Fetch headlines from configured RSS feeds, optionally filtering by topic/query."""
        if not self.feed_urls:
            return []

        articles: list[ArticleData] = []
        errors: list[str] = []

        for feed_url in self.feed_urls:
            if len(articles) >= limit:
                break

            try:
                response = execute_request_with_retry(
                    client=self.client,
                    method="GET",
                    url=feed_url,
                    provider=self.name,
                    rate_limiter=self.rate_limiter,
                )
                feed_data = feedparser.parse(response.text)
            except Exception as exc:
                logger.warning("Error fetching RSS feed %s: %s", feed_url, exc)
                errors.append(f"{feed_url}: {exc}")
                continue

            if feed_data.bozo and not feed_data.entries:
                logger.warning(
                    "Bozo exception parsing RSS feed %s: %s",
                    feed_url,
                    feed_data.bozo_exception,
                )
                continue

            feed_title = feed_data.feed.get("title", "")
            feed_domain = urllib.parse.urlparse(feed_url).netloc

            for entry in feed_data.entries:
                if len(articles) >= limit:
                    break

                title = str(getattr(entry, "title", "")).strip()
                url = str(getattr(entry, "link", "")).strip()

                if not title or not url:
                    continue

                if query and not self._matches_query(entry, query):
                    continue

                outlet = getattr(entry, "source", {}).get("title") or feed_title or feed_domain
                published_time = getattr(
                    entry, "published_parsed", getattr(entry, "updated_parsed", None)
                )
                published_at = self._parse_time_struct(published_time)

                articles.append(
                    ArticleData(
                        title=title,
                        url=url,
                        outlet=outlet,
                        published_at=published_at,
                        provider=self.name,
                        topic=topic,
                        raw_data={"feed_url": feed_url, "id": getattr(entry, "id", None)},
                    )
                )

        if not articles and errors and len(errors) == len(self.feed_urls):
            raise SourceParseError(
                f"Failed to fetch any RSS feeds: {'; '.join(errors)}",
                provider=self.name,
            )

        return articles[:limit]
