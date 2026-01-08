"""Export DuckDB tables into a SQLite database."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_DUCKDB_PATH = Path("data/duckdb/marxist-data-3NF.duckdb")
DEFAULT_SQLITE_PATH = Path("data/sqlite/marxist-data-3NF.sqlite")
EXCLUDED_TABLES = {"alembic_version"}


def build_export_plan(
    tables: list[str],
    source_schema: str = "main",
    target_schema: str = "sqlite_db",
) -> list[str]:
    """Build CREATE TABLE AS statements for SQLite export."""
    selected = sorted(table for table in tables if table not in EXCLUDED_TABLES)
    return [
        f"CREATE TABLE {target_schema}.{table} AS SELECT * FROM {source_schema}.{table};"
        for table in selected
    ]


def _ensure_sqlite_extension(con: duckdb.DuckDBPyConnection) -> None:
    try:
        con.execute("LOAD sqlite;")
    except Exception:
        con.execute("INSTALL sqlite;")
        con.execute("LOAD sqlite;")


def export_duckdb_to_sqlite(
    duckdb_path: Path | None = None,
    sqlite_path: Path | None = None,
    overwrite: bool = False,
) -> int:
    """Export DuckDB base tables into a SQLite file.

    Returns:
        Number of tables exported.
    """
    source_path = duckdb_path or DEFAULT_DUCKDB_PATH
    target_path = sqlite_path or DEFAULT_SQLITE_PATH

    if not source_path.exists():
        raise FileNotFoundError(f"DuckDB file not found: {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        if overwrite:
            target_path.unlink()
        else:
            raise FileExistsError(f"SQLite file already exists: {target_path} (use overwrite=True)")

    con = duckdb.connect(str(source_path))
    try:
        _ensure_sqlite_extension(con)
        con.execute("ATTACH ? AS sqlite_db (TYPE sqlite)", [str(target_path)])

        tables = [
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            ).fetchall()
        ]

        plan = build_export_plan(tables)
        for statement in plan:
            con.execute(statement)

        logger.info("Exported %s tables to %s", len(plan), target_path)
        return len(plan)
    finally:
        con.close()
