"""Tests for the Typer CLI entrypoint."""

from typer.testing import CliRunner

from news_sentiment import __version__
from news_sentiment.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    """Verify that 'newsent version' outputs the expected package version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"newsent version {__version__}" in result.output.strip()


def test_cli_version_flag() -> None:
    """Verify that 'newsent --version' and '-v' output the expected package version."""
    for flag in ["--version", "-v"]:
        result = runner.invoke(app, [flag])
        assert result.exit_code == 0
        assert f"newsent version {__version__}" in result.output.strip()


def test_cli_help() -> None:
    """Verify that running without arguments displays help message."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "News Sentiment Analyzer CLI" in result.output
    assert "version" in result.output


def test_cli_main_callable() -> None:
    """Verify that cli.main executes cleanly."""
    from unittest.mock import patch

    from news_sentiment.cli import main

    with patch("news_sentiment.cli.app") as mock_app:
        main()
        mock_app.assert_called_once()
