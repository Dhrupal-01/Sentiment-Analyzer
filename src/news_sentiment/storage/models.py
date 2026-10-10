"""SQLAlchemy declarative database models for news sentiment storage."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""


class Topic(Base):
    """News topic or tracking theme configured for ingestion."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    query: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name='{self.name}', is_active={self.is_active})>"


class Article(Base):
    """Canonical ingested news article headline and provenance metadata."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    url: Mapped[str] = mapped_column(String(1024), unique=True, index=True, nullable=False)
    outlet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    duplicates: Mapped[list["ArticleDuplicate"]] = relationship(
        back_populates="canonical_article",
        cascade="all, delete-orphan",
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )
    annotations: Mapped[list["ArticleAnnotation"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )
    explanations: Mapped[list["ArticleExplanation"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title='{self.title[:30]}...', outlet='{self.outlet}')>"


class ArticleDuplicate(Base):
    """Audit log recording detected duplicate occurrences rather than silently dropping them."""

    __tablename__ = "article_duplicates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_article_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duplicate_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    duplicate_title: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)  # exact_url or normalized_title
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    canonical_article: Mapped["Article"] = relationship(back_populates="duplicates")

    def __repr__(self) -> str:
        return (
            f"<ArticleDuplicate(canonical_id={self.canonical_article_id}, reason='{self.reason}')>"
        )


class IngestionRun(Base):
    """Audit metadata tracking every execution of the ingestion pipeline."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    articles_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    articles_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="in_progress", nullable=False)

    def __repr__(self) -> str:
        return (
            f"<IngestionRun(id={self.id}, provider='{self.provider}', "
            f"inserted={self.articles_inserted}, status='{self.status}')>"
        )


class Prediction(Base):
    """Model inference prediction record tied to an article and specific model version."""

    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "model_name",
            "model_version",
            name="uq_article_model_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    probabilities: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    article: Mapped["Article"] = relationship(back_populates="predictions")

    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id}, model='{self.model_name}:{self.model_version}', "
            f"label='{self.label}', score={self.score:.3f})>"
        )


class ArticleAnnotation(Base):
    """Human ground-truth annotation for an article headline."""

    __tablename__ = "article_annotations"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "annotator_id",
            name="uq_article_annotator",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    annotator_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    label: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # positive, neutral, negative, skip
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale_tokens: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    article: Mapped["Article"] = relationship(back_populates="annotations")

    def __repr__(self) -> str:
        return (
            f"<ArticleAnnotation(id={self.id}, article_id={self.article_id}, "
            f"annotator='{self.annotator_id}', label='{self.label}')>"
        )


class ArticleExplanation(Base):
    """Cached feature attribution explanation for an article headline."""

    __tablename__ = "article_explanations"
    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "model_name",
            "model_version",
            "method",
            name="uq_article_model_method_explanation",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    prediction_label: Mapped[str] = mapped_column(String(20), nullable=False)
    prediction_score: Mapped[float] = mapped_column(Float, nullable=False)
    attributions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    article: Mapped["Article"] = relationship(back_populates="explanations")

    def __repr__(self) -> str:
        return (
            f"<ArticleExplanation(id={self.id}, article_id={self.article_id}, "
            f"model='{self.model_name}:{self.model_version}', method='{self.method}')>"
        )
