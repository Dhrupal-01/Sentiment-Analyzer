"""Robust HTTP client with rate limiting, timeouts, and exponential backoff retries."""

import threading
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from news_sentiment.config.logging import get_logger
from news_sentiment.sources.exceptions import (
    NewsSourceError,
    SourceAuthenticationError,
    SourceNetworkError,
    SourceRateLimitError,
    SourceTimeoutError,
)

logger = get_logger(__name__)


class ProviderRateLimiter:
    """Thread-safe rate limiter enforcing minimum time spacing between requests per provider."""

    def __init__(self, min_interval_seconds: float = 1.0) -> None:
        self.min_interval = min_interval_seconds
        self._last_request_time = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until the minimum interval since the last request has elapsed."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
            self._last_request_time = time.monotonic()


def execute_request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    provider: str,
    rate_limiter: ProviderRateLimiter | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Execute an HTTP request with provider rate limiting and exponential backoff retries."""
    if rate_limiter:
        rate_limiter.acquire()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5.0),
        retry=retry_if_exception_type((SourceNetworkError, SourceTimeoutError)),
        reraise=True,
    )
    def _do_request() -> httpx.Response:
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            logger.warning("Timeout during %s request to %s: %s", provider, url, exc)
            raise SourceTimeoutError(f"Request timed out: {exc}", provider=provider) from exc
        except httpx.NetworkError as exc:
            logger.warning("Network failure during %s request to %s: %s", provider, url, exc)
            raise SourceNetworkError(f"Network error: {exc}", provider=provider) from exc
        except httpx.HTTPError as exc:
            raise NewsSourceError(f"HTTP error: {exc}", provider=provider) from exc

        # Handle specific HTTP error status codes
        if response.status_code == 429:
            raise SourceRateLimitError(
                f"Rate limit exceeded (HTTP 429): {response.text[:200]}",
                provider=provider,
            )
        if response.status_code in (401, 403):
            raise SourceAuthenticationError(
                f"Authentication failed (HTTP {response.status_code}): {response.text[:200]}",
                provider=provider,
            )
        if response.is_error:
            raise NewsSourceError(
                f"HTTP {response.status_code} error: {response.text[:200]}",
                provider=provider,
            )

        return response

    return _do_request()
