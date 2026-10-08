"""Model registry providing discovery and instantiation of sentiment models."""

from collections.abc import Callable

from news_sentiment.models.base import SentimentModel
from news_sentiment.models.transformer import MODEL_TRAINING_DOMAINS, HFTransformerModel
from news_sentiment.models.vader import VaderModel

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
    return "Custom sentiment model domain."
