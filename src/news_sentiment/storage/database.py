"""Database engine, connection pooling, and session management."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from news_sentiment.config.settings import get_settings
from news_sentiment.storage.models import Base


def get_engine(database_url: str | None = None) -> Engine:
    """Create a configured SQLAlchemy Engine instance."""
    url = database_url or get_settings().database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(url, connect_args=connect_args, echo=False)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Create a scoped sessionmaker factory bound to the engine."""
    eng = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


@contextmanager
def get_db_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Provide a transactional database session scope."""
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine | None = None) -> None:
    """Initialize database schema tables directly."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
