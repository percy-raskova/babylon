"""Schema migration helper for spec-068 vintage tracking.

Adds the ``vintage_published_date`` column to ``fact_bea_national_industry``
and ``fact_bea_io_coefficient`` if absent. The operation is idempotent:
re-running against a DB that already has the column is a no-op.

Per research.md R10, this runs as a single transactional block at the
start of the ingest CLI. SQLite supports ``ALTER TABLE ADD COLUMN`` as a
constant-time operation that preserves both the WAL state and existing
primary-key constraints.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import Engine, text

log = logging.getLogger(__name__)

_TABLES_WITH_VINTAGE_COLUMN: tuple[str, ...] = (
    "fact_bea_national_industry",
    "fact_bea_io_coefficient",
)
_VINTAGE_COLUMN_NAME = "vintage_published_date"
_VINTAGE_COLUMN_DDL = f"ALTER TABLE {{table}} ADD COLUMN {_VINTAGE_COLUMN_NAME} DATE"


def _existing_columns(engine: Engine, table_name: str) -> Iterator[str]:
    """Yield column names already declared on ``table_name`` in the SQLite DB."""
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        for row in result:
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            yield str(row[1])


def ensure_vintage_columns(engine: Engine) -> dict[str, bool]:
    """Add ``vintage_published_date`` to the two BEA fact tables if absent.

    Idempotent: returns whether each table was modified by this call.

    Args:
        engine: SQLAlchemy engine bound to the reference SQLite DB.

    Returns:
        Mapping of ``table_name -> column_added`` (True if this call added
        the column; False if it was already present).
    """
    results: dict[str, bool] = {}
    with engine.begin() as conn:  # BEGIN IMMEDIATE via SQLAlchemy autobegin
        for table_name in _TABLES_WITH_VINTAGE_COLUMN:
            existing = set(_existing_columns(engine, table_name))
            if _VINTAGE_COLUMN_NAME in existing:
                log.info(
                    "schema migration: %s.%s already present — no-op",
                    table_name,
                    _VINTAGE_COLUMN_NAME,
                )
                results[table_name] = False
                continue

            ddl = _VINTAGE_COLUMN_DDL.format(table=table_name)
            log.info("schema migration: adding %s.%s", table_name, _VINTAGE_COLUMN_NAME)
            conn.execute(text(ddl))
            results[table_name] = True

    return results
