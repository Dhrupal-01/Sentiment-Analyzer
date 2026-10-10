"""Business logic and data access services for the FastAPI API layer."""

import json
import math
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from news_sentiment.api.errors import BadRequestError, NotFoundError
from news_sentiment.api.schemas import (
    AnalyzeResponse,
    DailyTrendItem,
    DateRange,
    ExplainResponse,
    HeadlineItem,
    HeadlinePredictionItem,
    ModelEvaluationMetrics,
    ModelExplainabilityMetrics,
    ModelMetadataItem,
    ModelPredictionItem,
    ModelsRegistryResponse,
    PaginatedHeadlinesResponse,
    SentimentDistribution,
    SentimentPercentages,
    TextAnalysisResult,
    TokenAttributionItem,
    TopicResponse,
    TopicsListResponse,
    TopicSummaryResponse,
    TopicTrendResponse,
)
from news_sentiment.evaluation.contamination import check_contamination
from news_sentiment.explain import explain_detailed
from news_sentiment.models.base import SentimentModel
from news_sentiment.models.registry import get_model, get_model_domain, list_models
from news_sentiment.storage.models import Article, Prediction, Topic
from news_sentiment.storage.repository import TopicRepository

# In-memory LRU cache for explanation requests without article_id
_MAX_MEM_CACHE_ENTRIES = 500
_IN_MEMORY_EXPLAIN_CACHE: OrderedDict[tuple[str, str, str], ExplainResponse] = OrderedDict()


def analyze_texts(
    texts: list[str],
    model_names: list[str] | None = None,
) -> AnalyzeResponse:
    """Classify sentiment across one or more texts using selected models.

    Args:
        texts: Non-empty list of headline text strings.
        model_names: Optional model names to execute (defaults to all available).

    Returns:
        AnalyzeResponse containing per-text predictions across models.
    """
    available = list_models()
    selected_names = [m.lower().strip() for m in model_names] if model_names else ["vader"]

    # Validate that all requested models exist
    for name in selected_names:
        if name not in available:
            raise BadRequestError(
                f"Unknown model '{name}'. Available registered models: {available}",
                details={"requested_model": name, "available_models": available},
            )

    loaded_models: dict[str, SentimentModel] = {}
    for name in selected_names:
        try:
            loaded_models[name] = get_model(name)
        except Exception as exc:
            raise BadRequestError(
                f"Failed to load model '{name}': {exc}",
                details={"model": name, "error": str(exc)},
            ) from exc

    results: list[TextAnalysisResult] = []
    # Pre-predict across batch for efficiency
    batch_preds: dict[str, list[Any]] = {}
    for m_name, model in loaded_models.items():
        batch_preds[m_name] = model.predict(texts)

    for i, text in enumerate(texts):
        text_preds: dict[str, ModelPredictionItem] = {}
        for m_name, model in loaded_models.items():
            pred = batch_preds[m_name][i]
            text_preds[m_name] = ModelPredictionItem(
                label=pred.label,
                score=round(pred.score, 4),
                probabilities={k: round(v, 4) for k, v in pred.probabilities.items()},
                model_version=model.version,
            )
        results.append(TextAnalysisResult(text=text, predictions=text_preds))

    return AnalyzeResponse(
        texts_count=len(texts),
        models=selected_names,
        results=results,
    )


def explain_text(
    text: str,
    model_name: str = "vader",
    method: str = "occlusion",
    article_id: int | None = None,
    session: Session | None = None,
) -> ExplainResponse:
    """Explain a prediction score on a headline, utilizing DB or memory caching.

    Args:
        text: Input headline string.
        model_name: Registered model name.
        method: Saliency method ('occlusion', 'integrated_gradients', 'shap').
        article_id: Optional database article ID for persistent caching.
        session: Database session.

    Returns:
        ExplainResponse containing token attributions.
    """
    clean_model = model_name.lower().strip()
    clean_method = method.lower().strip()
    valid_methods = ["occlusion", "integrated_gradients", "shap"]

    if clean_method not in valid_methods:
        raise BadRequestError(
            f"Invalid method '{method}'. Valid explanation methods: {valid_methods}",
            details={"requested_method": method, "valid_methods": valid_methods},
        )

    try:
        model = get_model(clean_model)
    except KeyError as exc:
        raise BadRequestError(
            f"Unknown model '{model_name}'. Available: {list_models()}",
            details={"requested_model": model_name, "available_models": list_models()},
        ) from exc

    # Check memory cache if no article_id was specified
    cache_key = (text.strip(), clean_model, clean_method)
    if article_id is None and cache_key in _IN_MEMORY_EXPLAIN_CACHE:
        # Move to end (LRU)
        _IN_MEMORY_EXPLAIN_CACHE.move_to_end(cache_key)
        return _IN_MEMORY_EXPLAIN_CACHE[cache_key]

    # Compute explanation (explain_detailed checks DB cache automatically when article_id is set)
    detailed = explain_detailed(
        text=text,
        model=model,
        method=clean_method,
        article_id=article_id,
        session=session,
        use_cache=True,
    )

    token_items = [
        TokenAttributionItem(token=a.token, weight=round(a.weight, 4))
        for a in detailed.attributions
    ]

    response = ExplainResponse(
        text=detailed.text,
        model_name=detailed.model_name,
        model_version=detailed.model_version,
        method=detailed.method,
        prediction_label=detailed.prediction_label,
        prediction_score=round(detailed.prediction_score, 4),
        attributions=token_items,
    )

    # Store in memory cache if not tied to an article_id
    if article_id is None:
        if len(_IN_MEMORY_EXPLAIN_CACHE) >= _MAX_MEM_CACHE_ENTRIES:
            _IN_MEMORY_EXPLAIN_CACHE.popitem(last=False)
        _IN_MEMORY_EXPLAIN_CACHE[cache_key] = response

    return response


def list_topics_service(
    session: Session,
    active_only: bool = False,
) -> TopicsListResponse:
    """Retrieve all configured topics alongside their current article counts."""
    topics = TopicRepository.list_topics(session, active_only=active_only)

    counts_stmt = select(Article.topic, func.count(Article.id)).group_by(Article.topic)
    counts_map = dict(session.execute(counts_stmt).all())

    topic_items: list[TopicResponse] = [
        TopicResponse(
            id=t.id,
            name=t.name,
            query=t.query,
            is_active=t.is_active,
            created_at=t.created_at,
            article_count=counts_map.get(t.name, 0),
        )
        for t in topics
    ]

    return TopicsListResponse(topics=topic_items, total=len(topic_items))


def create_topic_service(
    session: Session,
    name: str,
    query: str,
    is_active: bool = True,
) -> TopicResponse:
    """Add or update a news tracking topic."""
    topic = TopicRepository.add_topic(session, name=name, query=query)
    topic.is_active = is_active
    session.commit()
    session.refresh(topic)

    art_count = (
        session.scalar(select(func.count(Article.id)).where(Article.topic == topic.name)) or 0
    )

    return TopicResponse(
        id=topic.id,
        name=topic.name,
        query=topic.query,
        is_active=topic.is_active,
        created_at=topic.created_at,
        article_count=art_count,
    )


def get_topic_headlines_service(
    session: Session,
    topic_id: int,
    page: int = 1,
    page_size: int = 20,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    source: str | None = None,
    label: str | None = None,
    model: str | None = None,
) -> PaginatedHeadlinesResponse:
    """Fetch paginated, filtered news headlines for a topic."""
    topic = session.get(Topic, topic_id)
    if not topic:
        raise NotFoundError(
            f"Topic with ID {topic_id} not found.",
            details={"topic_id": topic_id},
        )

    stmt = select(Article).where(Article.topic == topic.name)

    if start_date:
        stmt = stmt.where(Article.published_at >= start_date)
    if end_date:
        stmt = stmt.where(Article.published_at <= end_date)
    if source:
        clean_src = source.strip()
        stmt = stmt.where(
            (Article.outlet.ilike(f"%{clean_src}%")) | (Article.provider == clean_src)
        )

    pred_filters = []
    if model:
        pred_filters.append(Prediction.model_name == model.strip().lower())
    if label:
        pred_filters.append(Prediction.label == label.strip().lower())

    if pred_filters:
        pred_subq = select(Prediction.article_id).where(*pred_filters).scalar_subquery()
        stmt = stmt.where(Article.id.in_(pred_subq))

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    offset = (page - 1) * page_size
    stmt = (
        stmt.order_by(Article.published_at.desc().nullslast(), Article.id.desc())
        .offset(offset)
        .limit(page_size)
    )

    articles = list(session.scalars(stmt).all())
    items: list[HeadlineItem] = []

    for art in articles:
        preds: list[HeadlinePredictionItem] = []
        for p in art.predictions:
            if model and p.model_name != model.strip().lower():
                continue
            if label and p.label != label.strip().lower():
                continue
            preds.append(
                HeadlinePredictionItem(
                    model_name=p.model_name,
                    model_version=p.model_version,
                    label=p.label,
                    score=round(p.score, 4),
                    probabilities={k: round(v, 4) for k, v in p.probabilities.items()},
                    created_at=p.created_at,
                )
            )

        items.append(
            HeadlineItem(
                id=art.id,
                title=art.title,
                url=art.url,
                outlet=art.outlet,
                published_at=art.published_at,
                topic=art.topic,
                provider=art.provider,
                predictions=preds,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedHeadlinesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_topic_summary_service(
    session: Session,
    topic_id: int,
    model_name: str = "vader",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> TopicSummaryResponse:
    """Compute overall sentiment distribution and average score for a topic."""
    topic = session.get(Topic, topic_id)
    if not topic:
        raise NotFoundError(
            f"Topic with ID {topic_id} not found.",
            details={"topic_id": topic_id},
        )

    clean_model = model_name.strip().lower()
    stmt = (
        select(Prediction)
        .join(Article, Article.id == Prediction.article_id)
        .where(
            Article.topic == topic.name,
            Prediction.model_name == clean_model,
        )
    )

    if start_date:
        stmt = stmt.where(Article.published_at >= start_date)
    if end_date:
        stmt = stmt.where(Article.published_at <= end_date)

    predictions = list(session.scalars(stmt).all())
    total = len(predictions)

    pos = sum(1 for p in predictions if p.label == "positive")
    neu = sum(1 for p in predictions if p.label == "neutral")
    neg = sum(1 for p in predictions if p.label == "negative")

    pos_pct = round((pos / total) * 100, 2) if total > 0 else 0.0
    neu_pct = round((neu / total) * 100, 2) if total > 0 else 0.0
    neg_pct = round((neg / total) * 100, 2) if total > 0 else 0.0
    avg_score = round(sum(p.score for p in predictions) / total, 4) if total > 0 else 0.0

    return TopicSummaryResponse(
        topic_id=topic.id,
        topic_name=topic.name,
        model_name=clean_model,
        total_headlines=total,
        sentiment_distribution=SentimentDistribution(positive=pos, neutral=neu, negative=neg),
        sentiment_percentages=SentimentPercentages(
            positive=pos_pct, neutral=neu_pct, negative=neg_pct
        ),
        average_score=avg_score,
        date_range=DateRange(start=start_date, end=end_date),
    )


def get_topic_trend_service(
    session: Session,
    topic_id: int,
    model_name: str = "vader",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> TopicTrendResponse:
    """Generate daily time-series sentiment and volume trends for a topic."""
    topic = session.get(Topic, topic_id)
    if not topic:
        raise NotFoundError(
            f"Topic with ID {topic_id} not found.",
            details={"topic_id": topic_id},
        )

    clean_model = model_name.strip().lower()
    stmt = (
        select(Article.published_at, Article.fetched_at, Prediction.score, Prediction.label)
        .join(Prediction, Prediction.article_id == Article.id)
        .where(
            Article.topic == topic.name,
            Prediction.model_name == clean_model,
        )
    )

    if start_date:
        stmt = stmt.where(Article.published_at >= start_date)
    if end_date:
        stmt = stmt.where(Article.published_at <= end_date)

    rows = session.execute(stmt).all()

    # Aggregate by calendar date
    day_groups: dict[str, list[tuple[float, str]]] = {}
    for r in rows:
        ts = r[0] or r[1]
        date_str = ts.strftime("%Y-%m-%d")
        day_groups.setdefault(date_str, []).append((r[2], r[3]))

    time_series: list[DailyTrendItem] = []
    for d_str in sorted(day_groups.keys()):
        points = day_groups[d_str]
        scores = [p[0] for p in points]
        labels = [p[1] for p in points]
        vol = len(points)
        avg_s = round(sum(scores) / vol, 4) if vol > 0 else 0.0
        pos = sum(1 for lbl in labels if lbl == "positive")
        neu = sum(1 for lbl in labels if lbl == "neutral")
        neg = sum(1 for lbl in labels if lbl == "negative")

        time_series.append(
            DailyTrendItem(
                date=d_str,
                average_score=avg_s,
                headline_volume=vol,
                positive_count=pos,
                neutral_count=neu,
                negative_count=neg,
            )
        )

    return TopicTrendResponse(
        topic_id=topic.id,
        topic_name=topic.name,
        model_name=clean_model,
        time_series=time_series,
    )


def get_models_registry_service() -> ModelsRegistryResponse:
    """Retrieve all models from the registry with metadata and benchmark metrics."""
    available_names = list_models()
    items: list[ModelMetadataItem] = []

    # Attempt to load empirical benchmark results
    bench_data: dict[str, Any] = {}
    bench_file = Path("reports/eval/benchmark_results.json")
    if bench_file.exists():
        try:
            with bench_file.open("r", encoding="utf-8") as f:
                bench_data = json.load(f)
        except Exception:
            bench_data = {}

    # Attempt to load explainability results
    faith_data: dict[str, Any] = {}
    faith_file = Path("reports/explainability/faithfulness_results.json")
    if faith_file.exists():
        try:
            with faith_file.open("r", encoding="utf-8") as f:
                faith_data = json.load(f)
        except Exception:
            faith_data = {}

    plaus_data: dict[str, Any] = {}
    plaus_file = Path("reports/explainability/plausibility_results.json")
    if plaus_file.exists():
        try:
            with plaus_file.open("r", encoding="utf-8") as f:
                plaus_data = json.load(f)
        except Exception:
            plaus_data = {}

    for name in available_names:
        try:
            model = get_model(name)
            version = model.version
        except Exception:
            version = "1.0.0"

        domain = get_model_domain(name)
        contam = check_contamination(name, "financial_phrasebank")

        # Parse evaluation metrics from benchmark results
        eval_metrics: ModelEvaluationMetrics | None = None
        for _ds, records in bench_data.items():
            if isinstance(records, list):
                for rec in records:
                    if rec.get("model_name") == name and "metrics" in rec:
                        m = rec["metrics"]
                        eval_metrics = ModelEvaluationMetrics(
                            accuracy=m.get("accuracy", 0.0),
                            macro_f1=m.get("macro_f1", 0.0),
                            bootstrap_ci_macro_f1=m.get("bootstrap_ci_macro_f1"),
                            sample_size=m.get("sample_size", 0),
                        )
                        break
            if eval_metrics:
                break

        # Parse explainability metrics
        explain_metrics: ModelExplainabilityMetrics | None = None
        m_faith = faith_data.get("models", {}).get(name, {}).get("occlusion")
        m_plaus = plaus_data.get("models", {}).get(name, {}).get("occlusion", {}).get("top_3")
        if m_faith and m_plaus:
            explain_metrics = ModelExplainabilityMetrics(
                deletion_aopc_gain=m_faith.get("deletion_aopc_gain", 0.0),
                pct_faithful=m_faith.get("pct_faithful", 0.0),
                plausibility_top3_f1=m_plaus.get("f1", 0.0),
            )

        items.append(
            ModelMetadataItem(
                name=name,
                version=version,
                domain=domain,
                is_contaminated=contam.is_contaminated,
                contamination_reason=contam.reason,
                evaluation_metrics=eval_metrics,
                explainability_metrics=explain_metrics,
            )
        )

    return ModelsRegistryResponse(models=items, total=len(items))
