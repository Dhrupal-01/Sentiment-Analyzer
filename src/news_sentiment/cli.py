"""Command-line interface for the News Sentiment Analyzer."""

from typing import Annotated

import typer

from news_sentiment import __version__

app = typer.Typer(
    name="newsent",
    help="News Sentiment Analyzer CLI: ingest headlines, classify, explain, and track sentiment.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit when --version flag is provided."""
    if value:
        typer.echo(f"newsent version {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show application version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """News Sentiment Analyzer CLI entrypoint."""


@app.command("version")
def version_cmd() -> None:
    """Show the current application version."""
    typer.echo(f"newsent version {__version__}")


def main() -> None:
    """CLI execution entrypoint."""
    app()


if __name__ == "__main__":
    main()
