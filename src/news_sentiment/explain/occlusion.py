"""Leave-one-out occlusion explainer for lexicon and transformer sentiment models."""

from news_sentiment.explain.base import BaseExplainer, Explanation, TokenAttribution
from news_sentiment.explain.tokenizer import remove_token_by_span, tokenize_with_spans
from news_sentiment.models.base import SentimentModel


class OcclusionExplainer(BaseExplainer):
    """Leave-one-out occlusion explainer.

    Measures attribution as:
        weight_i = score(full text) - score(text without token i)

    Faithfully attributes negated phrases (e.g. 'not good') by measuring the score
    shift when the negation particle or modified adjective is occluded.
    """

    def explain(self, text: str, model: SentimentModel) -> Explanation:
        """Generate leave-one-out occlusion attributions for the input text."""
        clean_text = text.strip()
        if not clean_text:
            return Explanation(
                text=text,
                model_name=model.name,
                model_version=model.version,
                method="occlusion",
                prediction_label="neutral",
                prediction_score=0.0,
                attributions=[],
            )

        full_pred = model.predict_one(clean_text)
        full_score = full_pred.score
        spans = tokenize_with_spans(clean_text)

        if not spans:
            return Explanation(
                text=text,
                model_name=model.name,
                model_version=model.version,
                method="occlusion",
                prediction_label=full_pred.label,
                prediction_score=full_score,
                attributions=[],
            )

        # Batch-predict occluded texts for efficiency
        occluded_texts: list[str] = []
        for span in spans:
            sub = remove_token_by_span(clean_text, span)
            occluded_texts.append(sub)

        # Predict occluded scores in batches
        non_empty_indices = [i for i, t in enumerate(occluded_texts) if t]
        non_empty_texts = [occluded_texts[i] for i in non_empty_indices]

        scores_by_index: dict[int, float] = {}
        if non_empty_texts:
            preds = model.predict(non_empty_texts)
            for idx, pred in zip(non_empty_indices, preds, strict=False):
                scores_by_index[idx] = pred.score

        attributions: list[TokenAttribution] = []
        for i, span in enumerate(spans):
            # If omitting the token leaves empty text, score baseline is neutral (0.0)
            sub_score = scores_by_index.get(i, 0.0)
            weight = round(full_score - sub_score, 4)
            attributions.append(TokenAttribution(token=span.token, weight=weight))

        return Explanation(
            text=text,
            model_name=model.name,
            model_version=model.version,
            method="occlusion",
            prediction_label=full_pred.label,
            prediction_score=full_score,
            attributions=attributions,
        )
