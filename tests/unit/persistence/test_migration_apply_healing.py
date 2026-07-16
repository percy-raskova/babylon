"""TDD proof for task #77: self-healing migration apply.

Root cause: ``test_trace_view_columns.py``'s ``view_applied`` fixture (and
``test_trace_view_columns_v2.py``'s ``_apply_spec_065_migrations`` helper)
re-applied every migration file via a bare ``conn.execute(...)`` loop with no
error handling. When a KILLED background pytest run left the shared
``babylon_test`` DB in a mid-migration/leftover state, the first psycopg
error raised straight out of fixture setup (a pytest ERROR, observed twice
2026-07-15) — even though the same test passes cleanly in isolation (a clean
process re-applies the whole idempotent sequence in ~63s).

Both fixtures now delegate to ``conftest.apply_migrations_healing``. This
file proves its contract two ways:

1. Fast, deterministic mock-based tests (no real Postgres) — the retry-and-
   log-loudly behavior itself, RED before the conftest fix existed (a bare
   first-attempt failure would have propagated), GREEN now.
2. A real, disposable-Postgres reproduction of the actual leftover shape
   found while investigating this task: migration 0026
   (``0026_partition_dynamic_tables.sql``) DROPs ``view_runtime_trace_emission``
   as part of its one-time partition-conversion pass and defers recreation to
   migration 0030 "later in the same pass" (see 0026's own docstring) — a
   background run killed between files 0026 and 0030 leaves the view
   missing entirely. Building this against a throwaway DB (never the shared
   ``babylon_test``) confirmed the healer copes with it.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest

from tests.unit.persistence.conftest import MIGRATIONS_DIR, apply_migrations_healing


class _FakeResult:
    """Cursor-result double for ``ensure_ddl_applied``'s stamp SELECTs.

    ``fetchone() -> None`` models a database with no stamp table, so the
    applier always takes the slow (full-apply) path — exactly the healing
    scenario under test.
    """

    def fetchone(self) -> None:
        return None


class _FlakyStubPool:
    """A fake pool that fails every statement for its first N attempts.

    Each ``.connection()`` entry models one full apply-pass — the same
    shape ``apply_migrations_healing`` drives (one connection per attempt).
    ``executed_on_success`` records EVERY statement (advisory lock, stamp
    bookkeeping, migration texts); :meth:`migration_chunks_applied` filters
    to just the migration-file texts, which all open with a ``-- 0NNN``
    header comment.
    """

    def __init__(self, fail_attempts: int) -> None:
        self._fail_attempts = fail_attempts
        self.attempts = 0
        self.executed_on_success: list[str] = []

    def migration_chunks_applied(self) -> list[str]:
        return [sql for sql in self.executed_on_success if sql.lstrip().startswith("-- 0")]

    @contextmanager
    def connection(self) -> Iterator[Any]:
        self.attempts += 1
        attempt = self.attempts

        def _execute(sql_text: str, params: Any = None) -> _FakeResult:  # noqa: ARG001 — protocol shape
            if attempt <= self._fail_attempts:
                raise psycopg.errors.UndefinedColumn("simulated dirty/mid-migration leftover state")
            self.executed_on_success.append(sql_text)
            return _FakeResult()

        yield SimpleNamespace(autocommit=False, execute=_execute)


def test_heals_on_one_retry(caplog: pytest.LogCaptureFixture) -> None:
    """First attempt fails (dirty state); the retry heals -- no exception.

    This is the task #77 behavioral contract: before the conftest fix, a
    first-attempt ``psycopg.Error`` propagated straight out of fixture setup.
    """
    pool = _FlakyStubPool(fail_attempts=1)
    with caplog.at_level(logging.WARNING):
        apply_migrations_healing(pool)

    assert pool.attempts == 2, "must retry exactly once, not loop unboundedly"
    sql_files = sorted(MIGRATIONS_DIR.glob("00*.sql"))
    assert len(pool.migration_chunks_applied()) == len(sql_files), (
        "the healed retry must apply every migration file"
    )
    assert any(
        "dirty/mid-migration leftover state" in record.message and record.levelno == logging.WARNING
        for record in caplog.records
    ), "heal must be logged LOUDLY (Constitution III.11), not silently"


def test_persistent_failure_raises_loudly(caplog: pytest.LogCaptureFixture) -> None:
    """A failure that persists through the retry is a real bug -- must raise.

    Constitution III.11: heal loudly once, never silently mask a genuine,
    reproducible error as a transient dirty-state hiccup.
    """
    pool = _FlakyStubPool(fail_attempts=99)
    with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError, match="failed twice"):
        apply_migrations_healing(pool)

    assert pool.attempts == 2, "must stop after MAX_ATTEMPTS, never retry unboundedly"
    assert any(record.levelno == logging.ERROR for record in caplog.records), (
        "a persistent failure must log at ERROR, not just WARNING"
    )


@pytest.fixture
def dirty_db_pool(pg_dsn: str) -> Iterator[Any]:
    """A throwaway DB manually driven into task #77's exact leftover shape.

    Bootstraps the spec-037 schema, then applies migrations only through
    0026 (inclusive): 0026's partition-conversion pass DROPs
    ``view_runtime_trace_emission`` (and 4 aggregate views), deferring
    recreation to 0030 "later in the same pass" per 0026's own docstring.
    Stopping right there mirrors a background run killed between files 0026
    and 0030 -- the actual mechanism found while investigating this task.

    Uses a disposable per-test database (never the shared ``babylon_test``)
    so this reproduction cannot itself leave the real shared DB dirty for
    other tests -- mirrors ``test_migration_idempotency.py``'s
    ``fresh_db_pool`` pattern.
    """
    from psycopg import sql
    from psycopg_pool import ConnectionPool

    db_name = f"heal_probe_{uuid.uuid4().hex[:12]}"
    try:
        admin = psycopg.connect(pg_dsn, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL not available (set BABYLON_TEST_PG_DSN)")
    with admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

    fresh_dsn = re.sub(r"dbname=\S+", f"dbname={db_name}", pg_dsn)
    pool = ConnectionPool(conninfo=fresh_dsn, min_size=1, max_size=2, open=True)

    from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL

    with pool.connection() as conn:
        conn.autocommit = True
        for ddl in POSTGRES_SCHEMA_DDL:
            conn.execute(ddl)
        for sql_file in sorted(MIGRATIONS_DIR.glob("00*.sql")):
            if int(sql_file.name[:4]) > 26:
                break
            conn.execute(sql_file.read_text())

    try:
        yield pool
    finally:
        pool.close()
        with psycopg.connect(pg_dsn, autocommit=True) as admin2:
            admin2.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(db_name)))


@pytest.mark.integration
def test_heals_real_kill_mid_migration_leftover_state(dirty_db_pool: Any) -> None:
    """Reproduces task #77's leftover shape against a REAL disposable DB.

    Confirms ``apply_migrations_healing`` copes with a DB where a killed run
    left ``view_runtime_trace_emission`` dropped (0026 ran; 0027-0032,
    including the recreating 0030, did not). Whichever attempt heals it, the
    end state must be: no exception, and the view exists.
    """
    with dirty_db_pool.connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_views WHERE viewname = 'view_runtime_trace_emission'"
        ).fetchone()
    assert row is None, "fixture must reproduce the view-missing leftover state"

    apply_migrations_healing(dirty_db_pool)

    with dirty_db_pool.connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM pg_views WHERE viewname = 'view_runtime_trace_emission'"
        ).fetchone()
    assert row is not None, "the view must exist after healing"
