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


def test_cli_explain_success() -> None:
    """Verify that 'newsent explain' outputs token attributions."""
    result = runner.invoke(
        app,
        [
            "explain",
            "Markets rally strongly as inflation cools",
            "--model",
            "vader",
            "--method",
            "occlusion",
        ],
    )
    assert result.exit_code == 0
    assert "Headline:" in result.output
    assert "Model:" in result.output
    assert "Prediction:" in result.output
    assert "Token" in result.output
    assert "Attribution Weight" in result.output


def test_cli_explain_invalid_model() -> None:
    """Verify that 'newsent explain' errors gracefully on unknown model."""
    result = runner.invoke(
        app,
        ["explain", "Markets rally", "--model", "unknown_model"],
    )
    assert result.exit_code != 0
    assert "Error loading model" in result.output


def test_cli_explain_invalid_method() -> None:
    """Verify that 'newsent explain' errors gracefully on unknown explainer method."""
    result = runner.invoke(
        app,
        ["explain", "Markets rally", "--model", "vader", "--method", "unknown_method"],
    )
    assert result.exit_code != 0
    assert "Error generating explanation" in result.output
