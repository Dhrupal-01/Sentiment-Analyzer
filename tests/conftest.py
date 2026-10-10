"""Pytest configuration and common fixtures."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from news_sentiment.api.dependencies import get_db
from news_sentiment.api.main import create_app
from news_sentiment.config.settings import Settings
from news_sentiment.storage.database import init_db


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing dedicated test settings."""
    return Settings(
        environment="testing",
        debug=True,
        log_level="DEBUG",
        log_format="console",
        database_url="sqlite:///:memory:",
        api_rate_limit_per_minute=1000,
    )


@pytest.fixture
def test_engine() -> Engine:
    """Fixture providing an in-memory SQLite engine with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine


@pytest.fixture
def client(test_settings: Settings, test_engine: Engine) -> Generator[TestClient, None, None]:
    """Fixture providing a FastAPI TestClient with database session override."""
    test_app = create_app(settings=test_settings)

    def override_get_db() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session
            session.commit()

    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app) as test_client:
        yield test_client
    test_app.dependency_overrides.clear()
