"""Offline tests for news ingestion sources with mocked HTTP responses."""

import pytest
import respx

from news_sentiment.config.settings import Settings
from news_sentiment.sources import (
    GdeltSource,
    NewsApiSource,
    RssFeedSource,
    SourceAuthenticationError,
    SourceConfigurationError,
    SourceParseError,
    SourceRateLimitError,
    get_source,
    list_sources,
)

SAMPLE_GDELT_RESPONSE = {
    "articles": [
        {
            "url": "https://www.reuters.com/markets/asia/stocks-rally-2026",
            "title": "Asian Stocks Surge After Central Bank Cuts Rates - Reuters",
            "seendate": "20261008T080000Z",
            "domain": "reuters.com",
            "language": "English",
            "sourcecountry": "United States",
        },
        {
            "url": "https://www.bloomberg.com/news/articles/2026/chip-boom",
            "title": "Semiconductor Demand Surpasses Global Projections",
            "seendate": "20261008T093000Z",
            "domain": "bloomberg.com",
            "language": "English",
        },
    ]
}

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>BBC News - World</title>
    <link>https://www.bbc.com/news</link>
    <description>BBC World News Feed</description>
    <item>
      <title>Global Climate Summit Reaches Historic Clean Energy Agreement - BBC News</title>
      <link>https://www.bbc.com/news/world-energy-100</link>
      <description>Delegates from over 100 nations agreed on renewable benchmarks.</description>
      <pubDate>Thu, 08 Oct 2026 09:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Autonomous Flight Regulations Unveiled by Aviation Authority</title>
      <link>https://www.bbc.com/news/technology-flight-200</link>
      <description>New frameworks for drone logistics and aerial transit systems.</description>
      <pubDate>Thu, 08 Oct 2026 10:15:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_NEWSAPI_RESPONSE = {
    "status": "ok",
    "totalResults": 2,
    "articles": [
        {
            "source": {"id": "wired", "name": "Wired"},
            "author": "Tech Staff",
            "title": "Quantum Computing Breakthrough Unlocks New Encryption Paradigms",
            "description": "Researchers demonstrate coherence threshold stability.",
            "url": "https://www.wired.com/story/quantum-cryptography-2026",
            "publishedAt": "2026-10-08T11:00:00Z",
        }
    ],
}


# ==========================================
# 1. GDELT Tests (Mocked Offline)
# ==========================================


@respx.mock
def test_gdelt_source_success() -> None:
    """Verify GDELT source parses valid articles from mocked DOC 2.0 API."""
    respx.get("https://api.gdeltproject.org/api/v2/doc/doc").respond(
        status_code=200,
        json=SAMPLE_GDELT_RESPONSE,
    )

    settings = Settings(rate_limit_gdelt=0.0)
    source = GdeltSource(settings=settings)
    articles = source.fetch_headlines(topic="markets", limit=10)

    assert len(articles) == 2
    assert articles[0].title == "Asian Stocks Surge After Central Bank Cuts Rates - Reuters"
    assert articles[0].outlet == "reuters.com"
    assert articles[0].provider == "gdelt"
    assert articles[0].topic == "markets"
    assert articles[0].published_at is not None
    assert articles[0].published_at.year == 2026


@respx.mock
def test_gdelt_source_empty() -> None:
    """Verify GDELT handles empty or whitespace results gracefully."""
    respx.get("https://api.gdeltproject.org/api/v2/doc/doc").respond(
        status_code=200,
        text="",
    )

    settings = Settings(rate_limit_gdelt=0.0)
    source = GdeltSource(settings=settings)
    articles = source.fetch_headlines(topic="unknown_niche_topic")
    assert articles == []


@respx.mock
def test_gdelt_source_malformed_json() -> None:
    """Verify GDELT raises SourceParseError when response is invalid HTML/text."""
    respx.get("https://api.gdeltproject.org/api/v2/doc/doc").respond(
        status_code=200,
        text="<html><body>Server Busy</body></html>",
    )

    settings = Settings(rate_limit_gdelt=0.0)
    source = GdeltSource(settings=settings)
    with pytest.raises(SourceParseError) as exc_info:
        source.fetch_headlines(topic="markets")
    assert "Invalid JSON" in str(exc_info.value)


@respx.mock
def test_gdelt_source_rate_limited() -> None:
    """Verify GDELT raises SourceRateLimitError on HTTP 429."""
    respx.get("https://api.gdeltproject.org/api/v2/doc/doc").respond(
        status_code=429,
        text="Rate limit exceeded",
    )

    settings = Settings(rate_limit_gdelt=0.0)
    source = GdeltSource(settings=settings)
    with pytest.raises(SourceRateLimitError):
        source.fetch_headlines(topic="markets")


# ==========================================
# 2. RSS Feed Tests (Mocked Offline)
# ==========================================


@respx.mock
def test_rss_source_success() -> None:
    """Verify RSS source parses valid feed XML and filters by topic."""
    feed_url = "https://feeds.bbci.co.uk/news/world/rss.xml"
    respx.get(feed_url).respond(
        status_code=200,
        text=SAMPLE_RSS_XML,
    )

    settings = Settings(rate_limit_rss=0.0)
    source = RssFeedSource(feed_urls=[feed_url], settings=settings)

    # Fetch with no filter
    articles = source.fetch_headlines(topic="world", query=None)
    assert len(articles) == 2
    assert "Global Climate Summit" in articles[0].title
    assert articles[0].outlet == "BBC News - World"
    assert articles[0].provider == "rss"
    assert articles[0].published_at is not None

    # Fetch with keyword filter
    drone_articles = source.fetch_headlines(topic="tech", query="flight drone")
    assert len(drone_articles) == 1
    assert "Autonomous Flight" in drone_articles[0].title


@respx.mock
def test_rss_source_all_failed() -> None:
    """Verify RSS source raises SourceParseError if all configured feeds fail."""
    feed_url = "https://example.com/bad-feed.xml"
    respx.get(feed_url).respond(status_code=500, text="Internal Server Error")

    settings = Settings(rate_limit_rss=0.0)
    source = RssFeedSource(feed_urls=[feed_url], settings=settings)
    with pytest.raises(SourceParseError):
        source.fetch_headlines(topic="general")


# ==========================================
# 3. NewsAPI Tests (Mocked Offline)
# ==========================================


def test_newsapi_missing_key() -> None:
    """Verify NewsAPI raises SourceConfigurationError when no key is set."""
    settings = Settings(newsapi_key=None, rate_limit_newsapi=0.0)
    source = NewsApiSource(settings=settings)
    with pytest.raises(SourceConfigurationError) as exc_info:
        source.fetch_headlines(topic="tech")
    assert "NewsAPI requires an API key" in str(exc_info.value)


@respx.mock
def test_newsapi_success() -> None:
    """Verify NewsAPI parses articles when key is provided."""
    respx.get("https://newsapi.org/v2/everything").respond(
        status_code=200,
        json=SAMPLE_NEWSAPI_RESPONSE,
    )

    settings = Settings(newsapi_key="test_key_123", rate_limit_newsapi=0.0)
    source = NewsApiSource(settings=settings)
    articles = source.fetch_headlines(topic="quantum", query="quantum computing")

    assert len(articles) == 1
    assert "Quantum Computing" in articles[0].title
    assert articles[0].outlet == "Wired"
    assert articles[0].provider == "newsapi"


@respx.mock
def test_newsapi_auth_failure() -> None:
    """Verify NewsAPI maps apiKeyInvalid to SourceAuthenticationError."""
    respx.get("https://newsapi.org/v2/everything").respond(
        status_code=200,
        json={"status": "error", "code": "apiKeyInvalid", "message": "Invalid key"},
    )

    source = NewsApiSource(api_key="invalid_key", settings=Settings(rate_limit_newsapi=0.0))
    with pytest.raises(SourceAuthenticationError):
        source.fetch_headlines(topic="markets")


@respx.mock
def test_newsapi_rate_limit() -> None:
    """Verify NewsAPI maps rateLimited to SourceRateLimitError."""
    respx.get("https://newsapi.org/v2/everything").respond(
        status_code=200,
        json={"status": "error", "code": "rateLimited", "message": "Too many requests"},
    )

    source = NewsApiSource(api_key="valid_key", settings=Settings(rate_limit_newsapi=0.0))
    with pytest.raises(SourceRateLimitError):
        source.fetch_headlines(topic="markets")


# ==========================================
# 4. Factory & Registry Tests
# ==========================================


def test_sources_factory() -> None:
    """Verify list_sources and get_source return appropriate providers."""
    providers = list_sources()
    assert "gdelt" in providers
    assert "rss" in providers
    assert "newsapi" in providers

    assert isinstance(get_source("gdelt"), GdeltSource)
    assert isinstance(get_source("rss"), RssFeedSource)
    assert isinstance(get_source("newsapi"), NewsApiSource)

    with pytest.raises(SourceConfigurationError):
        get_source("unsupported_provider")
