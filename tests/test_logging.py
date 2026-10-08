"""Tests for structured logging configuration and formatters."""

import json
import logging

from news_sentiment.config.logging import (
    ConsoleFormatter,
    JSONFormatter,
    configure_logging,
    get_logger,
)


def test_json_formatter() -> None:
    """Verify JSONFormatter produces valid JSON with standard and extra attributes."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test message with extra metadata",
        args=(),
        exc_info=None,
    )
    record.__dict__["topic"] = "markets"
    record.__dict__["score"] = 0.95

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test message with extra metadata"
    assert "timestamp" in parsed
    assert parsed["extra"]["topic"] == "markets"
    assert parsed["extra"]["score"] == 0.95


def test_json_formatter_with_exception() -> None:
    """Verify JSONFormatter includes serialized exception info."""
    formatter = JSONFormatter()
    try:
        raise ValueError("Simulated failure")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname=__file__,
            lineno=25,
            msg="Exception occurred",
            args=(),
            exc_info=sys.exc_info(),
        )

    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "ERROR"
    assert "exception" in parsed
    assert "ValueError: Simulated failure" in parsed["exception"]


def test_console_formatter() -> None:
    """Verify ConsoleFormatter produces structured human-readable text."""
    formatter = ConsoleFormatter()
    record = logging.LogRecord(
        name="cli_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=40,
        msg="Human readable headline logged",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    assert "[INFO    ]" in output
    assert "[cli_logger]" in output
    assert "Human readable headline logged" in output


def test_console_formatter_with_exception() -> None:
    """Verify ConsoleFormatter appends serialized exception info."""
    formatter = ConsoleFormatter()
    try:
        raise RuntimeError("Console error trace")
    except RuntimeError:
        import sys

        record = logging.LogRecord(
            name="cli_logger",
            level=logging.ERROR,
            pathname=__file__,
            lineno=50,
            msg="Failure in processing",
            args=(),
            exc_info=sys.exc_info(),
        )

    output = formatter.format(record)
    assert "[ERROR   ]" in output
    assert "Failure in processing" in output
    assert "RuntimeError: Console error trace" in output


def test_configure_logging() -> None:
    """Verify configure_logging properly updates root logger handlers and levels."""
    configure_logging(log_level="DEBUG", log_format="json")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JSONFormatter)

    configure_logging(log_level="WARNING", log_format="console")
    assert root.level == logging.WARNING
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, ConsoleFormatter)


def test_get_logger() -> None:
    """Verify get_logger returns an instance of logging.Logger."""
    logger = get_logger("custom_namespace")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "custom_namespace"
