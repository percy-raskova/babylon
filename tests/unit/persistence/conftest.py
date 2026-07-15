"""Shared self-healing migration applier for the persistence unit tests.

Task #77: ``test_trace_view_columns.py`` (and its sibling
``test_trace_view_columns_v2.py``) each re-apply the ``migrations/`` folder
directly against the shared ``babylon_test`` Postgres DB via a bare
``conn.execute(sql_file.read_text())`` loop, with no error handling. Observed
twice on 2026-07-15: when a KILLED background pytest run leaves that shared
DB in a mid-migration/leftover state, the raw loop raises a bare
``psycopg.Error`` straight out of fixture setup — pytest reports a setup
ERROR (not a test failure), and the same test passes cleanly in isolation
(a clean process re-applies the whole idempotent sequence in ~63s).

This follows the schema-heal precedent set by commit ``e7804cd7`` (Program 17
seam, ``src/babylon/persistence/postgres_schema.py`` /
``postgres_runtime/_legacy.py``): heal LOUDLY (Constitution III.11 — never
silently), attribute the failure to a cause, and only swallow the FIRST
failure — a second, persistent failure is a real bug and must still surface.

Every migration file is independently idempotent by contract
(``tests/integration/persistence/test_migration_idempotency.py`` proves the
full sequence applies twice cleanly against a fresh DB), so a full-sequence
retry is a safe, non-destructive self-heal: it costs time, never data, and
needs no destructive ``DROP SCHEMA`` against a DB other concurrent test runs
may be touching.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import psycopg

logger = logging.getLogger(__name__)

#: Resolved relative to this file (package-relative), NOT the process CWD —
#: mirrors the fix already applied to
#: ``babylon.engine.headless_runner.runner._apply_migrations``.
MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3] / "src" / "babylon" / "persistence" / "migrations"
)

#: One retry only. A bounded, statically-provable 2 attempts: the first
#: failure is presumed dirty leftover state (heal and retry); a second,
#: identical failure is a real bug and must propagate loudly.
MAX_ATTEMPTS = 2


def _apply_all(pool: Any, sql_files: list[Path]) -> None:
    """Apply every file in ``sql_files`` in order, in one connection."""
    with pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sql_files:
            conn.execute(sql_file.read_text())


def apply_migrations_healing(pool: Any, glob_pattern: str = "00*.sql") -> None:
    """Apply migration files matching ``glob_pattern``, self-healing once.

    :param pool: A ``psycopg_pool.ConnectionPool``-like object exposing
        ``.connection()`` as a context manager.
    :param glob_pattern: Glob for migration filenames (sorted before apply).
        ``test_trace_view_columns.py`` passes the default (every migration);
        ``test_trace_view_columns_v2.py`` passes ``"002[0-3]_*.sql"``.
    :raises RuntimeError: if the healed retry ALSO fails — a persistent
        error is a real bug, not dirty leftover state, and must not be
        hidden (Constitution III.11).
    """
    sql_files = sorted(MIGRATIONS_DIR.glob(glob_pattern))
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            _apply_all(pool, sql_files)
        except psycopg.Error as exc:
            if attempt < MAX_ATTEMPTS:
                logger.warning(
                    "Migration apply failed against the shared test DB "
                    "(dirty/mid-migration leftover state suspected — "
                    "Constitution III.11 heal loudly, never silently): "
                    "%s: %s — retrying the full migration sequence once "
                    "to self-heal",
                    type(exc).__name__,
                    exc,
                )
                continue
            logger.error(
                "Migration self-heal FAILED after retry — the shared "
                "babylon_test DB may be genuinely broken (not just dirty); "
                "investigate immediately: %s: %s",
                type(exc).__name__,
                exc,
            )
            raise RuntimeError(
                f"Migration sequence failed twice against the shared test DB "
                f"(not a transient dirty-state issue): {type(exc).__name__}: {exc}"
            ) from exc
        else:
            return
