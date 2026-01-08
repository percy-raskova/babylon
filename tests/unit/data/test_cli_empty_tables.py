"""Unit tests for empty table reporting."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from babylon.data import cli


def test_collect_empty_tables_detects_empty() -> None:
    engine = create_engine("duckdb:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE has_rows (id INTEGER)"))
        conn.execute(text("CREATE TABLE empty_table (id INTEGER)"))
        conn.execute(text("INSERT INTO has_rows VALUES (1)"))

    empty_tables = cli._collect_empty_tables(engine)

    assert "empty_table" in empty_tables
    assert "has_rows" not in empty_tables
