"""Batch inference pipeline and multi-model comparative evaluation."""

import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from news_sentiment.config.logging import get_logger
from news_sentiment.models.base import SentimentModel
from news_sentiment.models.metrics import (
    DisagreementItem,
    PairwiseMetric,
    compare_model_predictions,
)
from news_sentiment.storage.database import get_db_session
from news_sentiment.storage.models import Article, Prediction

logger = get_logger(__name__)


@dataclass(frozen=True)
class InferenceSummary:
    """Summary metrics of a batch inference execution."""

    model_name: str
    model_version: str
    articles_scored: int
    elapsed_seconds: float


@dataclass(frozen=True)
class ModelComparisonReport:
    """Consolidated comparative report evaluating multiple models on a topic."""

    topic: str
    sample_size: int
    models: list[str]
    pairwise_metrics: list[PairwiseMetric]
    disagreements: list[DisagreementItem]


class InferencePipeline:
    """Service executing batch inference, model persistence, and comparative analysis."""

    def score_unprocessed(
        self,
        model: SentimentModel,
        topic: str | None = None,
        batch_size: int = 32,
        limit: int | None = None,
        session: Session | None = None,
    ) -> InferenceSummary:
        """Batch-score articles that do not have predictions for this model and version yet.

        Never overwrites existing records; new model versions store new rows.
        """
        start_time = time.monotonic()

        def _do_score(s: Session) -> InferenceSummary:
            # Query articles lacking predictions for this specific model and version
            stmt = (
                select(Article)
                .outerjoin(
                    Prediction,
                    (Prediction.article_id == Article.id)
                    & (Prediction.model_name == model.name)
                    & (Prediction.model_version == model.version),
                )
                .where(Prediction.id.is_(None))
            )

            if topic:
                stmt = stmt.where(Article.topic == topic)

            stmt = stmt.order_by(Article.id.asc())
            if limit:
                stmt = stmt.limit(limit)

            articles = list(s.scalars(stmt).all())
            total_scored = 0

            # Process in configurable batches
            for i in range(0, len(articles), batch_size):
                batch = articles[i : i + batch_size]
                titles = [a.title for a in batch]
                preds = model.predict(titles)

                for art, pred in zip(batch, preds, strict=True):
                    record = Prediction(
                        article_id=art.id,
                        model_name=model.name,
                        model_version=model.version,
                        label=pred.label,
                        score=pred.score,
                        probabilities=pred.probabilities,
                    )
                    s.add(record)
                    total_scored += 1

                s.flush()

            elapsed = time.monotonic() - start_time
            logger.info(
                "Inference complete for %s (v%s): scored %d articles in %.2fs",
                model.name,
                model.version,
                total_scored,
                elapsed,
            )
            return InferenceSummary(
                model_name=model.name,
                model_version=model.version,
                articles_scored=total_scored,
                elapsed_seconds=elapsed,
            )

        if session is not None:
            return _do_score(session)

        with get_db_session() as new_session:
            return _do_score(new_session)

    def compare_models(
        self,
        topic: str,
        models: list[SentimentModel],
        limit: int = 100,
        session: Session | None = None,
    ) -> ModelComparisonReport:
        """Compare predictions of multiple models on a given topic.

        Computes pairwise agreement rates, Cohen's kappa, and isolates
        headlines where models disagree.
        """

        def _do_compare(s: Session) -> ModelComparisonReport:
            # First, ensure all articles for this topic have predictions from all models
            for m in models:
                self.score_unprocessed(model=m, topic=topic, limit=limit, session=s)

            # Query all articles for this topic up to limit
            stmt = select(Article).where(Article.topic == topic).order_by(Article.id.asc())
            if limit:
                stmt = stmt.limit(limit)
            articles = list(s.scalars(stmt).all())

            if not articles:
                return ModelComparisonReport(
                    topic=topic,
                    sample_size=0,
                    models=[m.name for m in models],
                    pairwise_metrics=[],
                    disagreements=[],
                )

            # Collect predictions for each article per model
            model_labels: dict[str, list[str]] = {m.name: [] for m in models}
            article_model_preds: list[tuple[Article, dict[str, Prediction]]] = []

            for art in articles:
                preds_for_art: dict[str, Prediction] = {}
                for m in models:
                    pred = s.scalar(
                        select(Prediction).where(
                            (Prediction.article_id == art.id)
                            & (Prediction.model_name == m.name)
                            & (Prediction.model_version == m.version)
                        )
                    )
                    if pred:
                        preds_for_art[m.name] = pred

                # Only evaluate articles scored by all compared models
                if len(preds_for_art) == len(models):
                    article_model_preds.append((art, preds_for_art))
                    for m in models:
                        model_labels[m.name].append(preds_for_art[m.name].label)

            pairwise_metrics = compare_model_predictions(model_labels)

            # Find disagreements where not all models agree on the label
            disagreements: list[DisagreementItem] = []
            for art, p_dict in article_model_preds:
                labels = {p.label for p in p_dict.values()}
                if len(labels) > 1:
                    disagreements.append(
                        DisagreementItem(
                            title=art.title,
                            predictions={
                                m_name: {
                                    "label": pred.label,
                                    "score": pred.score,
                                    "probabilities": pred.probabilities,
                                }
                                for m_name, pred in p_dict.items()
                            },
                        )
                    )

            return ModelComparisonReport(
                topic=topic,
                sample_size=len(article_model_preds),
                models=[m.name for m in models],
                pairwise_metrics=pairwise_metrics,
                disagreements=disagreements,
            )

        if session is not None:
            return _do_compare(session)

        with get_db_session() as new_session:
            return _do_compare(new_session)
