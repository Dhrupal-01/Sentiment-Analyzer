"""Model registry providing discovery and instantiation of sentiment models."""

import os
from collections.abc import Callable
from pathlib import Path

from news_sentiment.models.base import SentimentModel
from news_sentiment.models.transformer import MODEL_TRAINING_DOMAINS, HFTransformerModel
from news_sentiment.models.vader import VaderModel

FINE_TUNED_LABEL_MAPPING = {
    "LABEL_0": "negative",
    "LABEL_1": "neutral",
    "LABEL_2": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "positive": "positive",
}


def _load_fine_tuned_model() -> SentimentModel:
    """Load the fine-tuned sequence classification model from local disk or hub."""
    local_path = Path("models/fine_tuned/best")
    if local_path.exists():
        return HFTransformerModel(
            model_id=str(local_path),
            name="fine_tuned",
            revision="local",
            label_mapping=FINE_TUNED_LABEL_MAPPING,  # type: ignore[arg-type]
        )

    env_path = os.getenv("FINE_TUNED_MODEL_PATH")
    if env_path:
        return HFTransformerModel(
            model_id=env_path,
            name="fine_tuned",
            revision="main",
            label_mapping=FINE_TUNED_LABEL_MAPPING,  # type: ignore[arg-type]
        )

    raise RuntimeError(
        "Fine-tuned model checkpoint not found at 'models/fine_tuned/best'. "
        "Train the model using 'python scripts/train.py' or set FINE_TUNED_MODEL_PATH."
    )


# Registry storing factory callables for lazy instantiation
_REGISTRY: dict[str, Callable[[], SentimentModel]] = {
    "vader": lambda: VaderModel(),
    "roberta": lambda: HFTransformerModel(
        model_id="cardiffnlp/twitter-roberta-base-sentiment-latest",
        name="roberta",
        revision="main",
    ),
    "finbert": lambda: HFTransformerModel(
        model_id="ProsusAI/finbert",
        name="finbert",
        revision="main",
    ),
    "fine_tuned": _load_fine_tuned_model,
}

# Cache instantiated model singletons
_INSTANCES: dict[str, SentimentModel] = {}


def register_model(name: str, factory: Callable[[], SentimentModel]) -> None:
    """Register a new sentiment model factory under a key name."""
    clean_name = name.lower().strip()
    _REGISTRY[clean_name] = factory
    _INSTANCES.pop(clean_name, None)


def list_models() -> list[str]:
    """List all registered sentiment model names."""
    return sorted(_REGISTRY.keys())


def get_model(name: str) -> SentimentModel:
    """Retrieve an initialized sentiment model by name.

    Args:
        name: Registered name (e.g. 'vader', 'roberta', 'finbert').

    Returns:
        SentimentModel instance.

    Raises:
        KeyError if model is not registered.
    """
    clean_name = name.lower().strip()
    if clean_name not in _REGISTRY:
        raise KeyError(f"Unknown model '{name}'. Available models: {list_models()}")

    if clean_name not in _INSTANCES:
        _INSTANCES[clean_name] = _REGISTRY[clean_name]()

    return _INSTANCES[clean_name]


def get_model_domain(name: str) -> str:
    """Retrieve documentation of a model's pre-training or fine-tuning domain."""
    clean_name = name.lower().strip()
    if clean_name == "vader":
        return (
            "VADER Lexicon: Rule-based lexicon curated from social media (tweets) and "
            "product reviews. Incorporates punctuation, capitalization, emoticons, "
            "and contrastive conjunctions."
        )
    if clean_name == "roberta":
        return MODEL_TRAINING_DOMAINS["cardiffnlp/twitter-roberta-base-sentiment-latest"]
    if clean_name == "finbert":
        return MODEL_TRAINING_DOMAINS["ProsusAI/finbert"]
    if clean_name in ("fine_tuned", "fine-tuned"):
        return (
            "Fine-tuned DistilRoBERTa sequence classification model trained on the "
            "Financial PhraseBank 100% agreement train split (1,584 sentences). "
            "Checkpoint selected on validation split; evaluated for domain gap on news headlines."
        )
    return "Custom sentiment model domain."
