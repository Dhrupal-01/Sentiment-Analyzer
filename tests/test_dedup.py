"""Tests for URL and headline title normalization and deduplication logic."""

import pytest

from news_sentiment.storage.dedup import normalize_title, normalize_url


@pytest.mark.parametrize(
    ("input_url", "expected_url"),
    [
        (
            "https://www.Reuters.com/markets/stocks?utm_source=twitter&utm_medium=social#breaking",
            "https://www.reuters.com/markets/stocks",
        ),
        (
            "HTTP://EXAMPLE.COM/news/article/?ref=homepage&fbclid=12345&gclid=67890",
            "http://example.com/news/article",
        ),
        (
            "https://bbc.com/news/world-12345?topic=tech&utm_campaign=daily",
            "https://bbc.com/news/world-12345?topic=tech",
        ),
        (
            "https://ft.com/content/abc-123/",
            "https://ft.com/content/abc-123",
        ),
        (
            "",
            "",
        ),
    ],
)
def test_normalize_url(input_url: str, expected_url: str) -> None:
    """Verify URL canonicalization and stripping of tracking parameters."""
    assert normalize_url(input_url) == expected_url


@pytest.mark.parametrize(
    ("input_title", "expected_title"),
    [
        (
            "Federal Reserve holds interest rates steady - Reuters",
            "federal reserve holds interest rates steady",
        ),
        (
            "Tech Giants Face New Antitrust Scrutiny | BBC News",
            "tech giants face new antitrust scrutiny",
        ),
        (
            "Oil prices tumble amid unexpected inventory build — Wall Street Journal",
            "oil prices tumble amid unexpected inventory build",
        ),
        (
            "Markets Rally! S&P 500 Hits All-Time High, Nasdaq Soars -- AP News",
            "markets rally s p 500 hits all time high nasdaq soars",
        ),
        (
            "   Inflation Cools: What it Means for Your Wallet - The Guardian   ",
            "inflation cools what it means for your wallet",
        ),
        (
            "",
            "",
        ),
    ],
)
def test_normalize_title(input_title: str, expected_title: str) -> None:
    """Verify headline title canonicalization, punctuation removal, and suffix stripping."""
    assert normalize_title(input_title) == expected_title


def test_near_duplicate_cross_outlet_matching() -> None:
    """Verify that the same headline syndicated across outlets normalizes to the same string."""
    title_reuters = "US Inflation Drops to 2.5% in August - Reuters"
    title_bbc = "US inflation drops to 2.5% in August | BBC"
    title_ap = "US Inflation Drops to 2.5% in August -- AP"

    assert normalize_title(title_reuters) == normalize_title(title_bbc)
    assert normalize_title(title_bbc) == normalize_title(title_ap)
