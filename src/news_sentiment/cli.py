"""Command-line interface for the News Sentiment Analyzer."""

from typing import Annotated

import typer

from news_sentiment import __version__
from news_sentiment.evaluation.metrics import compute_confusion_matrix
from news_sentiment.models.metrics import compute_agreement_rate, compute_cohen_kappa
from news_sentiment.models.pipeline import InferencePipeline
from news_sentiment.models.registry import get_model
from news_sentiment.sources.service import IngestionService
from news_sentiment.storage.database import get_db_session, init_db
from news_sentiment.storage.repository import AnnotationRepository, TopicRepository

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


@app.command("analyze")
def analyze_cmd(
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="Sentiment model identifier ('vader', 'roberta', 'finbert').",
        ),
    ] = "vader",
    topic: Annotated[
        str | None,
        typer.Option(
            "--topic",
            "-t",
            help="Optional topic filter to score.",
        ),
    ] = None,
    batch_size: Annotated[
        int,
        typer.Option(
            "--batch-size",
            "-b",
            help="Batch size for model scoring.",
        ),
    ] = 32,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of articles to score.",
        ),
    ] = None,
) -> None:
    """Batch-score unanalyzed headlines using a registered sentiment model."""
    init_db()
    try:
        sentiment_model = get_model(model)
    except (KeyError, RuntimeError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Analyzing headlines with model '{sentiment_model.name}' "
        f"(version: {sentiment_model.version})..."
    )
    pipeline = InferencePipeline()
    summary = pipeline.score_unprocessed(
        model=sentiment_model,
        topic=topic,
        batch_size=batch_size,
        limit=limit,
    )
    typer.echo(
        f"Analysis complete: {summary.articles_scored} article(s) scored "
        f"in {summary.elapsed_seconds:.2f}s."
    )


@app.command("compare")
def compare_cmd(
    topic: Annotated[
        str,
        typer.Option(
            "--topic",
            "-t",
            help="Topic name on which to evaluate and compare models.",
        ),
    ],
    models: Annotated[
        str,
        typer.Option(
            "--models",
            "-m",
            help="Comma-separated model names (e.g. 'vader,roberta,finbert').",
        ),
    ] = "vader,roberta,finbert",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of headlines to compare.",
        ),
    ] = 100,
) -> None:
    """Compare predictions, agreement rates, and Cohen's kappa across models for a topic."""
    init_db()
    model_names = [m.strip().lower() for m in models.split(",") if m.strip()]
    if len(model_names) < 2:
        typer.secho(
            "Please provide at least 2 models to compare (e.g. --models vader,roberta).",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    loaded_models = []
    for m_name in model_names:
        try:
            loaded_models.append(get_model(m_name))
        except (KeyError, RuntimeError) as exc:
            typer.secho(f"Error loading model '{m_name}': {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc

    typer.echo(
        f"Comparing models ({', '.join(model_names)}) on topic '{topic}' (limit: {limit})..."
    )
    pipeline = InferencePipeline()
    report = pipeline.compare_models(topic=topic, models=loaded_models, limit=limit)

    if report.sample_size == 0:
        typer.echo(
            f"No headlines found for topic '{topic}'. Run 'newsent ingest --topic {topic}' first."
        )
        return

    typer.echo(
        f"\nModel Comparison Report — Topic: '{topic}' ({report.sample_size} headlines evaluated)"
    )
    typer.echo("=" * 72)
    typer.echo(f"{'Model Pair':<28} | {'Agreement Rate':^16} | {'Cohen’s Kappa (κ)':^18}")
    typer.echo("-" * 72)
    for pair in report.pairwise_metrics:
        pair_str = f"{pair.model_a} vs {pair.model_b}"
        agree_str = f"{pair.agreement_rate * 100:.1f}%"
        kappa_str = f"{pair.cohen_kappa:.3f}"
        typer.echo(f"{pair_str:<28} | {agree_str:^16} | {kappa_str:^18}")
    typer.echo("=" * 72)

    disagree_count = len(report.disagreements)
    typer.echo(f"\nDisagreements ({disagree_count} of {report.sample_size} headlines disagreed):")
    if not report.disagreements:
        typer.echo("  All models achieved 100% unanimous agreement across all headlines.")
    else:
        for idx, item in enumerate(report.disagreements[:20], 1):
            typer.echo(f'\n{idx}. "{item.title}"')
            for m_name, pred_info in item.predictions.items():
                lbl = pred_info["label"]
                sc = pred_info["score"]
                typer.echo(f"     • {m_name:<10}: {lbl:<8} (score: {sc:+.2f})")
        if len(report.disagreements) > 20:
            typer.echo(
                f"\n... and {len(report.disagreements) - 20} additional disagreements truncated."
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


@app.command("label")
def label_cmd(
    annotator: Annotated[
        str,
        typer.Option(
            "--annotator",
            "-a",
            help="Unique annotator username or identifier.",
        ),
    ] = "annotator_1",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of headlines to present in this session.",
        ),
    ] = 300,
    stratified: Annotated[
        bool,
        typer.Option(
            "--stratified/--no-stratified",
            help="Whether to sample headlines stratified across topics and sources.",
        ),
    ] = True,
    seed: Annotated[
        int,
        typer.Option(
            "--seed",
            help="Random seed for deterministic sampling.",
        ),
    ] = 42,
) -> None:
    """Interactively label stored headlines with human ground-truth sentiment."""
    init_db()
    with get_db_session() as session:
        candidates = AnnotationRepository.get_stratified_sample(
            session=session,
            annotator_id=annotator,
            sample_size=limit,
            seed=seed,
        )

        if not candidates:
            typer.echo(
                f"No unannotated headlines available for '{annotator}'. "
                "Ingest more headlines with 'newsent ingest' or 'newsent collect'."
            )
            return

        typer.echo(f"\nLoaded {len(candidates)} candidate headline(s) for annotator '{annotator}'.")
        typer.echo("Options: [p]ositive | [n]eutral | [e]gative | [s]kip | [q]uit")
        typer.echo("-" * 72)

        labeled_count = 0
        for idx, art in enumerate(candidates, 1):
            src_str = art.outlet or art.provider
            typer.echo(f"\n[{idx}/{len(candidates)}] Topic: {art.topic} | Source: {src_str}")
            typer.echo(f'Title: "{art.title}"')
            if art.url:
                typer.echo(f"URL:   {art.url}")

            # Prompt strictly without suggestions or pre-fills
            choice = ""
            while choice not in ("p", "n", "e", "s", "q", "1", "2", "3", "4"):
                choice = (
                    typer.prompt("Sentiment ([p]os / [n]eu / n[e]g / [s]kip / [q]uit)")
                    .strip()
                    .lower()
                )

            if choice == "q":
                typer.echo(f"\nLabeling session ended. {labeled_count} headline(s) annotated.")
                break

            label_map = {
                "p": "positive",
                "1": "positive",
                "n": "neutral",
                "2": "neutral",
                "e": "negative",
                "3": "negative",
                "s": "skip",
                "4": "skip",
            }
            assigned_label = label_map[choice]

            notes_input = typer.prompt("Notes (optional, press Enter to skip)", default="").strip()
            notes = notes_input if notes_input else None

            AnnotationRepository.save_annotation(
                session=session,
                article_id=art.id,
                annotator_id=annotator,
                label=assigned_label,
                notes=notes,
            )
            session.commit()
            labeled_count += 1
            typer.echo(f"Saved: '{assigned_label}'")

        typer.echo(f"\nCompleted session! Total labeled: {labeled_count}.")


@app.command("label-agreement")
def label_agreement_cmd(
    annotator1: Annotated[
        str,
        typer.Option(
            "--annotator1",
            "-1",
            help="Username/ID of the first annotator.",
        ),
    ] = "annotator_1",
    annotator2: Annotated[
        str,
        typer.Option(
            "--annotator2",
            "-2",
            help="Username/ID of the second annotator.",
        ),
    ] = "annotator_2",
) -> None:
    """Compute Cohen's kappa and inter-annotator agreement between two annotators."""
    init_db()
    with get_db_session() as session:
        pairs = AnnotationRepository.get_overlapping_annotations(
            session=session,
            annotator_1=annotator1,
            annotator_2=annotator2,
            exclude_skipped=True,
        )

        if not pairs:
            typer.secho(
                f"No overlapping non-skipped annotations found between "
                f"'{annotator1}' and '{annotator2}'.",
                fg=typer.colors.YELLOW,
            )
            return

        labels_1 = [p[0].label for p in pairs]
        labels_2 = [p[1].label for p in pairs]

        agreement_rate = compute_agreement_rate(labels_1, labels_2)
        kappa = compute_cohen_kappa(labels_1, labels_2)

        typer.echo(f"\nInter-Annotator Agreement Report: '{annotator1}' vs '{annotator2}'")
        typer.echo("=" * 72)
        typer.echo(f"Overlapping Annotations: {len(pairs)}")
        typer.echo(f"Raw Agreement Rate:      {agreement_rate * 100:.1f}%")
        typer.echo(f"Cohen’s Kappa (κ):       {kappa:.3f}")

        # Confusion matrix
        matrix = compute_confusion_matrix(labels_1, labels_2)
        typer.echo(f"\nConfusion Matrix (Rows: {annotator1}, Columns: {annotator2}):")
        typer.echo(f"{'':<12} | {'Positive':^10} | {'Neutral':^10} | {'Negative':^10}")
        typer.echo("-" * 48)
        for c1 in ("positive", "neutral", "negative"):
            row = [str(matrix[c1][c2]) for c2 in ("positive", "neutral", "negative")]
            typer.echo(f"{c1.capitalize():<12} | {row[0]:^10} | {row[1]:^10} | {row[2]:^10}")

        # Disagreements
        disagreements = [p for p in pairs if p[0].label != p[1].label]
        typer.echo(f"\nDisagreements ({len(disagreements)} of {len(pairs)} disagreed):")
        if not disagreements:
            typer.echo("  Unanimous 100% agreement between annotators!")
        else:
            for idx, (a1, a2) in enumerate(disagreements[:15], 1):
                title = a1.article.title if a1.article else f"Article {a1.article_id}"
                typer.echo(f'  {idx}. "{title}"')
                typer.echo(f"     • {annotator1}: {a1.label} | {annotator2}: {a2.label}")


def main() -> None:
    """CLI execution entrypoint."""
    app()


if __name__ == "__main__":
    main()
