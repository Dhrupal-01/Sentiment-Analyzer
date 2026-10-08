"""Tests for application settings and configuration loading."""

import os
from unittest.mock import patch

from news_sentiment.config.settings import Settings, get_settings


def test_default_settings() -> None:
    """Verify default settings values."""
    settings = Settings()
    assert settings.app_name == "News Sentiment Analyzer"
    assert settings.app_version == "0.1.0"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.log_format == "console"
    assert "sqlite" in settings.database_url
    assert settings.api_port == 8000
    assert len(settings.cors_origins) >= 1


def test_settings_env_override() -> None:
    """Verify settings can be overridden via environment variables."""
    with patch.dict(
        os.environ,
        {
            "APP_NAME": "Custom Sentiment Service",
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "WARNING",
            "LOG_FORMAT": "json",
            "API_PORT": "9000",
        },
    ):
        settings = Settings()
        assert settings.app_name == "Custom Sentiment Service"
        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.log_level == "WARNING"
        assert settings.log_format == "json"
        assert settings.api_port == 9000


def test_get_settings_cached() -> None:
    """Verify that get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
