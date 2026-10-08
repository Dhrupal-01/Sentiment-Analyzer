"""Tests for the FastAPI endpoints and application lifecycle."""

from fastapi.testclient import TestClient

from news_sentiment.api.main import create_app
from news_sentiment.config.settings import Settings


def test_health_endpoint(client: TestClient) -> None:
    """Verify that the /health endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "testing"
    assert "version" in data


def test_root_endpoint(client: TestClient) -> None:
    """Verify that the / root endpoint returns welcome information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["docs_url"] == "/docs"


def test_app_lifespan() -> None:
    """Verify that app startup and shutdown lifespan context functions cleanly."""
    settings = Settings(environment="testing", log_level="INFO", log_format="console")
    app = create_app(settings=settings)
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
