"""Pytest configuration and common fixtures."""

import pytest
from fastapi.testclient import TestClient

from news_sentiment.api.main import create_app
from news_sentiment.config.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing dedicated test settings."""
    return Settings(
        environment="testing",
        debug=True,
        log_level="DEBUG",
        log_format="console",
        database_url="sqlite:///:memory:",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """Fixture providing a FastAPI TestClient configured for testing."""
    test_app = create_app(settings=test_settings)
    return TestClient(test_app)
