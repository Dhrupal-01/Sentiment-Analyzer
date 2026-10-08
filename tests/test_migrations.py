"""Tests for Alembic schema migrations on a clean database."""

import os
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migrations_clean_database_lifecycle() -> None:
    """Verify that Alembic migrations apply cleanly to a clean database, downgrade, and re-apply."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db_url = f"sqlite:///{db_path}"
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")

        engine = create_engine(db_url)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        expected_tables = {
            "topics",
            "articles",
            "article_duplicates",
            "ingestion_runs",
            "predictions",
            "alembic_version",
        }
        assert expected_tables.issubset(table_names)

        # Verify columns on predictions table
        pred_cols = {col["name"] for col in inspector.get_columns("predictions")}
        expected_pred_cols = {
            "id",
            "article_id",
            "model_name",
            "model_version",
            "label",
            "score",
            "probabilities",
            "created_at",
        }
        assert expected_pred_cols.issubset(pred_cols)

        # Verify columns on articles table
        article_cols = {col["name"] for col in inspector.get_columns("articles")}
        expected_article_cols = {
            "id",
            "title",
            "normalized_title",
            "url",
            "outlet",
            "published_at",
            "fetched_at",
            "provider",
            "topic",
        }
        assert expected_article_cols.issubset(article_cols)

        # 2. Downgrade to base
        command.downgrade(alembic_cfg, "base")
        inspector_post_down = inspect(engine)
        tables_post_down = set(inspector_post_down.get_table_names())
        assert "articles" not in tables_post_down
        assert "topics" not in tables_post_down

        # 3. Re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        inspector_reup = inspect(engine)
        assert "articles" in set(inspector_reup.get_table_names())

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
