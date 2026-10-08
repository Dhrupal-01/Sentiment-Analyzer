"""Add article_annotations table for human ground-truth labeling

Revision ID: 0003_add_annotations_table
Revises: 0002_add_predictions_table
Create Date: 2026-10-09 00:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_annotations_table"
down_revision: str | None = "0002_add_predictions_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "article_annotations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("annotator_id", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["article_id"],
            ["articles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "article_id",
            "annotator_id",
            name="uq_article_annotator",
        ),
    )
    op.create_index(
        op.f("ix_article_annotations_article_id"),
        "article_annotations",
        ["article_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_article_annotations_annotator_id"),
        "article_annotations",
        ["annotator_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_article_annotations_label"),
        "article_annotations",
        ["label"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_article_annotations_label"), table_name="article_annotations")
    op.drop_index(op.f("ix_article_annotations_annotator_id"), table_name="article_annotations")
    op.drop_index(op.f("ix_article_annotations_article_id"), table_name="article_annotations")
    op.drop_table("article_annotations")
