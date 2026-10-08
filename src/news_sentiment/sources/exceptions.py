"""Typed exception hierarchy for news ingestion sources."""


class NewsSourceError(Exception):
    """Base exception for all news source ingestion errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider

    def __str__(self) -> str:
        prefix = f"[{self.provider}] " if self.provider else ""
        return f"{prefix}{self.message}"


class SourceNetworkError(NewsSourceError):
    """Network connection, transport, or DNS failure."""


class SourceTimeoutError(SourceNetworkError):
    """HTTP request timed out."""


class SourceRateLimitError(NewsSourceError):
    """Provider rate limit or quota exceeded (e.g. HTTP 429)."""


class SourceAuthenticationError(NewsSourceError):
    """Missing or invalid API key/credentials (HTTP 401/403)."""


class SourceParseError(NewsSourceError):
    """Failed to parse API response payload (malformed JSON or XML)."""


class SourceConfigurationError(NewsSourceError):
    """Required source configuration is absent or invalid."""
