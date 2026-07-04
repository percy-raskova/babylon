"""Read source abstraction for the Observatory (spec-099).

Every Observatory read runs against one of two backends, chosen by the
``source`` query param:

* ``live`` — the runner Postgres, through the read-only ``sim`` alias (spec-096;
  ``default_transaction_read_only=on`` + migration-refusing router).
* ``archive`` — a session's exported Parquet under ``BABYLON_ARCHIVE_ROOT``,
  read via an in-memory DuckDB (the same pattern as
  :func:`babylon.persistence.archival.query_archived_session`), read-only. No
  new dependency — ``duckdb`` already ships in the project.

Both readers expose the same ``execute(sql, params) -> list[dict]`` +
``table_available(table) -> bool`` interface. Raw-table SQL (``tick_commit``,
``boundary_flow_register``, ``conservation_audit_log``) is IDENTICAL across
backends (same schema); it is authored with ``?`` placeholders and translated
to ``%s`` for Postgres. Only the value-aggregate *views* differ (live has the
Postgres views; archive reconstructs over the raw hex Parquet).
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any


class Source(StrEnum):
    """Which backend an Observatory read targets."""

    LIVE = "live"
    ARCHIVE = "archive"


def parse_source(raw: str | None) -> Source:
    """Parse the ``source`` query param (default ``live``).

    Raises:
        ValueError: If ``raw`` is not a known source.
    """
    if raw is None or raw == "":
        return Source.LIVE
    try:
        return Source(raw)
    except ValueError as exc:
        raise ValueError(f"unknown source: {raw!r} (expected live|archive)") from exc


#: Default archive root (spec-088 local-only ruling; ``mise run sim:archived``).
_DEFAULT_ARCHIVE_ROOT = "/media/user/data/babylon-archives"


def archive_root() -> Path:
    """Return the archive root, honouring ``BABYLON_ARCHIVE_ROOT`` if set."""
    return Path(os.environ.get("BABYLON_ARCHIVE_ROOT", _DEFAULT_ARCHIVE_ROOT))


def archive_dir(session_id: str) -> Path:
    """Return the per-session archive directory ``<root>/<session_id>/``."""
    return archive_root() / session_id


def translate_placeholders(sql: str) -> str:
    """Translate DuckDB-style ``?`` placeholders to psycopg ``%s``.

    Our raw-table SQL is authored with ``?`` (DuckDB native) and contains no
    literal ``?`` elsewhere, so a plain substitution is safe.
    """
    return sql.replace("?", "%s")


class LiveReader:
    """Read the runner Postgres via a ``sim``-alias cursor (read-only)."""

    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def table_available(self, table: str) -> bool:  # noqa: ARG002
        """Live Postgres always has the runner tables."""
        return True

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Run ``sql`` (``?`` placeholders) and return rows as dicts."""
        self._cursor.execute(translate_placeholders(sql), params)
        columns = [d[0] for d in self._cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in self._cursor.fetchall()]


class ArchiveReader:
    """Read a session's exported Parquet via in-memory DuckDB (read-only).

    Mirrors :func:`babylon.persistence.archival.query_archived_session`: each
    ``<table>.parquet`` under the session dir becomes a DuckDB view named after
    the table. Only tables whose Parquet exists are registered (a zero-row table
    has no file, per the archive manifest).
    """

    def __init__(self, session_dir: Path) -> None:
        self._dir = session_dir

    def table_available(self, table: str) -> bool:
        """True iff ``<table>.parquet`` exists in the session archive dir."""
        return (self._dir / f"{table}.parquet").is_file()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Register the session's Parquet as views and run ``sql`` (``?`` params)."""
        import duckdb  # type: ignore[import-untyped, import-not-found, unused-ignore]

        con = duckdb.connect()
        try:
            for parquet in sorted(self._dir.glob("*.parquet")):
                path_literal = str(parquet).replace("'", "''")
                con.execute(
                    f'CREATE VIEW "{parquet.stem}" AS '
                    f"SELECT * FROM read_parquet('{path_literal}')"
                )
            result = con.execute(sql, list(params))
            columns = [d[0] for d in result.description]
            return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        finally:
            con.close()


__all__ = [
    "Source",
    "parse_source",
    "archive_root",
    "archive_dir",
    "translate_placeholders",
    "LiveReader",
    "ArchiveReader",
]
