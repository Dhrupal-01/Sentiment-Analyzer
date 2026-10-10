"""Add article_explanations table and rationale_tokens to annotations

Revision ID: 0004_add_explanations_table
Revises: 0003_add_annotations_table
Create Date: 2026-10-10 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_add_explanations_table"
down_revision: str | None = "0003_add_annotations_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add rationale_tokens column to article_annotations
    op.add_column(
        "article_annotations",
        sa.Column("rationale_tokens", sa.JSON(), nullable=True),
    )

    # 2. Create article_explanations table
    op.create_table(
        "article_explanations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("prediction_label", sa.String(length=20), nullable=False),
        sa.Column("prediction_score", sa.Float(), nullable=False),
        sa.Column("attributions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "article_id",
            "model_name",
            "model_version",
            "method",
            name="uq_article_model_method_explanation",
        ),
    )
    op.create_index(
        op.f("ix_article_explanations_article_id"),
        "article_explanations",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_article_explanations_model_name"),
        "article_explanations",
        ["model_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_article_explanations_model_version"),
        "article_explanations",
        ["model_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_article_explanations_method"),
        "article_explanations",
        ["method"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_article_explanations_method"), table_name="article_explanations")
    op.drop_index(op.f("ix_article_explanations_model_version"), table_name="article_explanations")
    op.drop_index(op.f("ix_article_explanations_model_name"), table_name="article_explanations")
    op.drop_index(op.f("ix_article_explanations_article_id"), table_name="article_explanations")
    op.drop_table("article_explanations")
    op.drop_column("article_annotations", "rationale_tokens")
