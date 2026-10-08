"""Command-line interface for the News Sentiment Analyzer."""

from typing import Annotated

import typer

from news_sentiment import __version__
from news_sentiment.sources.service import IngestionService
from news_sentiment.storage.database import get_db_session, init_db
from news_sentiment.storage.repository import TopicRepository

app = typer.Typer(
    name="newsent",
    help="News Sentiment Analyzer CLI: ingest headlines, classify, explain, and track sentiment.",
    no_args_is_help=True,
)

topics_app = typer.Typer(
    name="topics",
    help="Manage news tracking topics.",
    no_args_is_help=True,
)
app.add_typer(topics_app, name="topics")


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


@app.command("ingest")
def ingest_cmd(
    topic: Annotated[
        str,
        typer.Option(
            "--topic",
            "-t",
            help="Topic name or category to ingest.",
        ),
    ],
    source: Annotated[
        str,
        typer.Option(
            "--source",
            "-s",
            help="News provider source ('gdelt', 'rss', or 'newsapi').",
        ),
    ] = "gdelt",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of articles to ingest.",
        ),
    ] = 100,
) -> None:
    """Ingest headlines for a specified topic from a news provider."""
    init_db()
    service = IngestionService()
    typer.echo(
        f"Ingesting headlines for topic '{topic}' using source '{source}' (limit: {limit})..."
    )

    summary = service.ingest_topic(topic=topic, source=source, limit=limit)
    if summary.errors:
        typer.secho(f"Ingestion warning/error: {summary.errors}", fg=typer.colors.RED)

    typer.echo(
        f"Ingestion completed: {summary.articles_fetched} fetched, "
        f"{summary.articles_inserted} inserted, "
        f"{summary.duplicates_found} duplicates recorded."
    )


@app.command("collect")
def collect_cmd(
    source: Annotated[
        str,
        typer.Option(
            "--source",
            "-s",
            help="News provider source ('gdelt', 'rss', or 'newsapi').",
        ),
    ] = "gdelt",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of articles per topic.",
        ),
    ] = 100,
) -> None:
    """Ingest headlines for every configured active topic."""
    init_db()
    with get_db_session() as session:
        topics = TopicRepository.list_topics(session, active_only=True)

    if not topics:
        typer.echo(
            "No active topics found. Add topics using 'newsent topics add <name> --query <query>'."
        )
        return

    typer.echo(
        f"Collecting headlines across {len(topics)} active topic(s) using source '{source}'..."
    )
    service = IngestionService()
    summaries = service.collect_all(source=source, limit=limit)

    total_fetched = sum(s.articles_fetched for s in summaries)
    total_inserted = sum(s.articles_inserted for s in summaries)
    total_duplicates = sum(s.duplicates_found for s in summaries)

    typer.echo(
        f"Collection complete across {len(summaries)} topic(s): "
        f"{total_fetched} total fetched, "
        f"{total_inserted} inserted, "
        f"{total_duplicates} duplicates recorded."
    )


@topics_app.command("add")
def topics_add_cmd(
    name: Annotated[
        str,
        typer.Argument(
            help="Unique name identifier for the topic (e.g. 'markets', 'tech').",
        ),
    ],
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Search keywords query expression for news providers.",
        ),
    ],
) -> None:
    """Add or update a news tracking topic."""
    init_db()
    with get_db_session() as session:
        topic = TopicRepository.add_topic(session, name=name, query=query)
        typer.echo(f"Topic '{topic.name}' configured with query: '{topic.query}'")


@topics_app.command("list")
def topics_list_cmd() -> None:
    """List all configured news tracking topics."""
    init_db()
    with get_db_session() as session:
        topics = TopicRepository.list_topics(session, active_only=False)
        if not topics:
            typer.echo(
                "No topics configured. Add one with 'newsent topics add <name> --query <query>'."
            )
            return

        typer.echo(f"Configured topics ({len(topics)} total):")
        for t in topics:
            status_str = "active" if t.is_active else "inactive"
            typer.echo(f"  • {t.name:<15} [{status_str:^8}] query: '{t.query}'")


def main() -> None:
    """CLI execution entrypoint."""
    app()


if __name__ == "__main__":
    main()
