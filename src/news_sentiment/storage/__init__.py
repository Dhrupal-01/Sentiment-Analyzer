"""Storage layer: SQLAlchemy models, database engine, migrations, and repositories."""

from news_sentiment.storage.database import (
    get_db_session,
    get_engine,
    get_session_factory,
    init_db,
)
from news_sentiment.storage.dedup import normalize_title, normalize_url
from news_sentiment.storage.models import (
    Article,
    ArticleAnnotation,
    ArticleDuplicate,
    Base,
    IngestionRun,
    Prediction,
    Topic,
)
from news_sentiment.storage.repository import (
    AnnotationRepository,
    ArticleRepository,
    IngestionRunRepository,
    TopicRepository,
)

__all__ = [
    "AnnotationRepository",
    "Article",
    "ArticleAnnotation",
    "ArticleDuplicate",
    "ArticleRepository",
    "Base",
    "IngestionRun",
    "IngestionRunRepository",
    "Prediction",
    "Topic",
    "TopicRepository",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "init_db",
    "normalize_title",
    "normalize_url",
]
