"""Add predictions table for model inference tracking

Revision ID: 0002_add_predictions_table
Revises: 0001_initial_schema
Create Date: 2026-10-08 22:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_predictions_table"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("probabilities", sa.JSON(), nullable=False),
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
            name="uq_article_model_version",
        ),
    )
    op.create_index(op.f("ix_predictions_article_id"), "predictions", ["article_id"], unique=False)
    op.create_index(op.f("ix_predictions_model_name"), "predictions", ["model_name"], unique=False)
    op.create_index(
        op.f("ix_predictions_model_version"),
        "predictions",
        ["model_version"],
        unique=False,
    )
    op.create_index(op.f("ix_predictions_label"), "predictions", ["label"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_predictions_label"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_model_version"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_model_name"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_article_id"), table_name="predictions")
    op.drop_table("predictions")
