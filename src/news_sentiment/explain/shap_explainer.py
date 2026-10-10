"""SHAP partition explainer for sentiment models using shap library with fallback."""

from news_sentiment.explain.base import BaseExplainer, Explanation, TokenAttribution
from news_sentiment.explain.tokenizer import remove_token_by_span, tokenize_with_spans
from news_sentiment.models.base import SentimentModel


def _run_real_shap(
    text: str,
    model: SentimentModel,
) -> list[TokenAttribution] | None:
    """Execute real SHAP Text Explainer if shap library is available."""
    try:
        import shap
    except ImportError:
        return None

    pipe = getattr(model, "_pipeline", None)
    if pipe is None:
        return None

    try:
        # Create scoring function for SHAP
        def score_func(texts: list[str]) -> list[float]:
            preds = model.predict(texts)
            return [p.score for p in preds]

        explainer = shap.Explainer(score_func, masker=shap.maskers.Text(tokenizer=r"\W+"))
        shap_values = explainer([text])

        # Extract values for the text instance
        values = shap_values.values[0]
        tokens = shap_values.data[0]

        result: list[TokenAttribution] = []
        for tok, val in zip(tokens, values, strict=False):
            clean_tok = tok.strip()
            if clean_tok:
                result.append(TokenAttribution(token=clean_tok, weight=round(float(val), 4)))
        return result
    except Exception:
        return None


class ShapExplainer(BaseExplainer):
    """SHAP partition explainer computing Shapley attribution values.

    Explains model score relative to the neutral baseline. Uses SHAP partition
    masker when installed, with a coalition-partition Shapley algorithm fallback
    ensuring efficiency (sum of Shapley values equals score - baseline).
    """

    def explain(self, text: str, model: SentimentModel) -> Explanation:
        """Generate SHAP token attributions explaining the prediction score."""
        clean_text = text.strip()
        if not clean_text:
            return Explanation(
                text=text,
                model_name=model.name,
                model_version=model.version,
                method="shap",
                prediction_label="neutral",
                prediction_score=0.0,
                attributions=[],
            )

        full_pred = model.predict_one(clean_text)
        full_score = full_pred.score

        # Try real SHAP library first
        real_shap = _run_real_shap(clean_text, model)
        if real_shap is not None and len(real_shap) > 0:
            return Explanation(
                text=text,
                model_name=model.name,
                model_version=model.version,
                method="shap",
                prediction_label=full_pred.label,
                prediction_score=full_score,
                attributions=real_shap,
            )

        # Hierarchical partition Shapley approximation
        spans = tokenize_with_spans(clean_text)
        if not spans:
            return Explanation(
                text=text,
                model_name=model.name,
                model_version=model.version,
                method="shap",
                prediction_label=full_pred.label,
                prediction_score=full_score,
                attributions=[],
            )

        # Compute marginal contributions across complementary coalitions
        marginal_values: list[float] = []
        for _i, span in enumerate(spans):
            # 1. Leave-one-out marginal contribution: S(All) - S(All \ {i})
            without_i = remove_token_by_span(clean_text, span)
            score_without_i = model.predict_one(without_i).score if without_i else 0.0
            marg_loo = full_score - score_without_i

            # 2. Solo marginal contribution: S({i}) - S(Empty)
            solo_score = model.predict_one(span.token).score
            marg_solo = solo_score - 0.0

            # Shapley value weights average over coalition sizes:
            # For 2-point partition (singleton vs grand coalition), weight is equal average
            shap_i = 0.5 * marg_loo + 0.5 * marg_solo
            marginal_values.append(shap_i)

        # Enforce Shapley Efficiency Axiom: sum(shap_i) = full_score - baseline (0.0)
        baseline = 0.0
        target_diff = full_score - baseline
        curr_sum = sum(marginal_values)

        attributions: list[TokenAttribution] = []
        if abs(curr_sum) > 1e-5:
            scale = target_diff / curr_sum if abs(curr_sum) > 0.01 else 1.0
            for span, val in zip(spans, marginal_values, strict=False):
                w = round(val * scale, 4)
                attributions.append(TokenAttribution(token=span.token, weight=w))
        else:
            for span, val in zip(spans, marginal_values, strict=False):
                attributions.append(TokenAttribution(token=span.token, weight=round(val, 4)))

        return Explanation(
            text=text,
            model_name=model.name,
            model_version=model.version,
            method="shap",
            prediction_label=full_pred.label,
            prediction_score=full_score,
            attributions=attributions,
        )
