"""Unified explainability service routing explanation methods and caching database results."""

from sqlalchemy.orm import Session

from news_sentiment.explain.base import BaseExplainer, Explanation, TokenAttribution
from news_sentiment.explain.integrated_gradients import IntegratedGradientsExplainer
from news_sentiment.explain.occlusion import OcclusionExplainer
from news_sentiment.explain.shap_explainer import ShapExplainer
from news_sentiment.models.base import SentimentModel
from news_sentiment.storage.database import get_db_session
from news_sentiment.storage.repository import ExplanationRepository

_EXPLAINERS: dict[str, BaseExplainer] = {
    "occlusion": OcclusionExplainer(),
    "integrated_gradients": IntegratedGradientsExplainer(),
    "shap": ShapExplainer(),
}


def get_explainer(method: str) -> BaseExplainer:
    """Retrieve an explainer instance by method name.

    Args:
        method: One of 'occlusion', 'integrated_gradients', 'shap'.

    Raises:
        ValueError if method is unrecognized.
    """
    clean_method = method.lower().strip()
    if clean_method not in _EXPLAINERS:
        valid_methods = sorted(_EXPLAINERS.keys())
        raise ValueError(f"Unknown explanation method '{method}'. Valid methods: {valid_methods}")
    return _EXPLAINERS[clean_method]


def explain_detailed(
    text: str,
    model: SentimentModel,
    method: str = "occlusion",
    article_id: int | None = None,
    session: Session | None = None,
    use_cache: bool = True,
) -> Explanation:
    """Generate and optionally cache a detailed explanation for an article headline.

    Args:
        text: Input headline text to explain.
        model: SentimentModel instance providing predictions.
        method: 'occlusion', 'integrated_gradients', or 'shap'.
        article_id: Optional database article ID for caching.
        session: Optional active SQLAlchemy session.
        use_cache: Whether to query and write to the database explanation cache.

    Returns:
        Explanation containing metadata, predicted score, and list[TokenAttribution].
    """
    clean_method = method.lower().strip()
    explainer = get_explainer(clean_method)

    # 1. Try reading from database cache if article_id is provided
    if article_id is not None and use_cache:

        def _check_cache(s: Session) -> Explanation | None:
            cached = ExplanationRepository.get_explanation(
                session=s,
                article_id=article_id,
                model_name=model.name,
                model_version=model.version,
                method=clean_method,
            )
            if cached:
                attrs = [
                    TokenAttribution(token=item["token"], weight=item["weight"])
                    for item in cached.attributions
                ]
                return Explanation(
                    text=text,
                    model_name=cached.model_name,
                    model_version=cached.model_version,
                    method=cached.method,
                    prediction_label=cached.prediction_label,
                    prediction_score=cached.prediction_score,
                    attributions=attrs,
                )
            return None

        if session is not None:
            cached_exp = _check_cache(session)
            if cached_exp is not None:
                return cached_exp
        else:
            with get_db_session() as s:
                cached_exp = _check_cache(s)
                if cached_exp is not None:
                    return cached_exp

    # 2. Compute explanation using the requested method
    explanation = explainer.explain(text=text, model=model)

    # 3. Cache computed explanation in the database if article_id is provided
    if article_id is not None and use_cache:

        def _save_cache(s: Session) -> None:
            attr_dicts = [a.to_dict() for a in explanation.attributions]
            ExplanationRepository.save_explanation(
                session=s,
                article_id=article_id,
                model_name=model.name,
                model_version=model.version,
                method=clean_method,
                prediction_label=explanation.prediction_label,
                prediction_score=explanation.prediction_score,
                attributions=attr_dicts,
            )

        if session is not None:
            _save_cache(session)
        else:
            with get_db_session() as s:
                _save_cache(s)

    return explanation


def explain(
    text: str,
    model: SentimentModel,
    method: str = "occlusion",
    article_id: int | None = None,
    session: Session | None = None,
    use_cache: bool = True,
) -> list[TokenAttribution]:
    """Explain a model's prediction score on a headline, returning token attributions.

    Args:
        text: Input text headline.
        model: SentimentModel instance.
        method: Explanation method ('occlusion', 'integrated_gradients', or 'shap').
        article_id: Optional article ID to enable database caching.
        session: Optional database session.
        use_cache: Whether to use database caching.

    Returns:
        list[TokenAttribution] where weights explain that model's own score.
    """
    detailed = explain_detailed(
        text=text,
        model=model,
        method=method,
        article_id=article_id,
        session=session,
        use_cache=use_cache,
    )
    return detailed.attributions
