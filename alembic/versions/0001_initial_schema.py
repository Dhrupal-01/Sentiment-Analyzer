"""Initial schema: topics, articles, article_duplicates, and ingestion_runs

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-08 15:45:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Topics table
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("query", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topics_name"), "topics", ["name"], unique=True)

    # 2. Articles table
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("outlet", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_articles_normalized_title"), "articles", ["normalized_title"], unique=False)
    op.create_index(op.f("ix_articles_url"), "articles", ["url"], unique=True)
    op.create_index(op.f("ix_articles_provider"), "articles", ["provider"], unique=False)
    op.create_index(op.f("ix_articles_topic"), "articles", ["topic"], unique=False)

    # 3. Article Duplicates table
    op.create_table(
        "article_duplicates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("canonical_article_id", sa.Integer(), nullable=False),
        sa.Column("duplicate_url", sa.String(length=1024), nullable=False),
        sa.Column("duplicate_title", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["canonical_article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_article_duplicates_canonical_article_id"),
        "article_duplicates",
        ["canonical_article_id"],
        unique=False,
    )

    # 4. Ingestion Runs table
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=True),
        sa.Column("articles_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("articles_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicates_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="in_progress"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_index(op.f("ix_article_duplicates_canonical_article_id"), table_name="article_duplicates")
    op.drop_table("article_duplicates")
    op.drop_index(op.f("ix_articles_topic"), table_name="articles")
    op.drop_index(op.f("ix_articles_provider"), table_name="articles")
    op.drop_index(op.f("ix_articles_url"), table_name="articles")
    op.drop_index(op.f("ix_articles_normalized_title"), table_name="articles")
    op.drop_table("articles")
    op.drop_index(op.f("ix_topics_name"), table_name="topics")
    op.drop_table("topics")
