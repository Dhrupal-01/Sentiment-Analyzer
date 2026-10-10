"""Simple in-memory sliding window rate limiter for API requests."""

import time
from collections import defaultdict

from fastapi import Request

from news_sentiment.api.errors import RateLimitExceededError
from news_sentiment.config.logging import get_logger

logger = get_logger(__name__)


class SimpleRateLimiter:
    """In-memory sliding-window rate limiter per client IP address."""

    def __init__(
        self,
        requests_per_minute: int = 120,
        enabled: bool = True,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.enabled = enabled
        self._history: dict[str, list[float]] = defaultdict(list)

    def reset(self) -> None:
        """Clear all rate limiting state (useful in test teardown)."""
        self._history.clear()

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address, respecting X-Forwarded-For if available."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def check(self, request: Request) -> None:
        """Evaluate whether the incoming request exceeds rate limits.

        Raises:
            RateLimitExceededError: If the client IP has exceeded requests_per_minute.
        """
        if not self.enabled or self.requests_per_minute <= 0:
            return

        client_ip = self.get_client_ip(request)
        now = time.time()
        window_start = now - 60.0

        # Prune timestamps older than 60 seconds
        timestamps = [ts for ts in self._history[client_ip] if ts > window_start]
        self._history[client_ip] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            oldest = timestamps[0]
            retry_after = max(1, int(60.0 - (now - oldest)))
            logger.warning(
                "Rate limit exceeded for %s (%d requests in last 60s)",
                client_ip,
                len(timestamps),
                extra={"client_ip": client_ip, "limit": self.requests_per_minute},
            )
            raise RateLimitExceededError(
                message=f"Rate limit exceeded: max {self.requests_per_minute} requests per minute.",
                retry_after=retry_after,
            )

        self._history[client_ip].append(now)


# Module-level default instance
_default_rate_limiter = SimpleRateLimiter()


def get_rate_limiter() -> SimpleRateLimiter:
    """Retrieve the application rate limiter instance."""
    return _default_rate_limiter
