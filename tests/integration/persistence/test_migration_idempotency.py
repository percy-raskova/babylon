"""Migration hygiene gate (Loud Machine C.3).

The headless runner re-applies EVERY file in
``src/babylon/persistence/migrations/`` on every start (sorted glob, no
version table — see :func:`babylon.engine.headless_runner.runner._apply_migrations`).
Per-file idempotency is therefore the contract, and it must hold across the
whole sequence: a later migration may change schema that an earlier one's
re-run touches.

This gate would have caught the 0027/0028 self-conflict that turned the unit
suite red on 2026-07-07: 0027's backfill named ``ON CONFLICT (h3_index)``
while 0028 had already replaced that PK with ``(session_id, h3_index)``, so
every re-run failed with InvalidColumnReference on any database where 0028
had been applied.

Two checks:

1. Numeric prefixes are unique (two ``0031_*.sql`` files shipped in spec-092;
   sorted-glob ordering between them was a lexical accident).
2. The full sequence applies cleanly TWICE against a fresh database that has
   the spec-037 bootstrap schema (mirrors the runner's real contract: the
   test DB is created by ``mise run db:up`` + schema bootstrap, then
   migrations re-run on every runner start).
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from collections.abc import Generator
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql

from babylon.engine.headless_runner.runner import _apply_migrations

pytestmark = pytest.mark.integration

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[3] / "src" / "babylon" / "persistence" / "migrations"
)


def test_migration_numeric_prefixes_are_unique() -> None:
    """Sorted-glob ordering between same-prefix files is a lexical accident."""
    prefixes = [
        match.group(1)
        for sql_file in sorted(MIGRATIONS_DIR.glob("00*.sql"))
        if (match := re.match(r"^(\d{4})_", sql_file.name)) is not None
    ]
    duplicates = [prefix for prefix, count in Counter(prefixes).items() if count > 1]
    assert not duplicates, (
        f"Duplicate migration prefixes {duplicates}: ordering between same-prefix "
        f"files is undefined by design intent (sorted-glob is lexical). Renumber."
    )


@pytest.fixture()
def fresh_db_pool(pg_dsn: str) -> Generator[Any, None, None]:
    """A pool against a brand-new database on the local test server.

    The shared ``babylon_test`` DB carries prior migration state, which is
    exactly what this gate must NOT depend on: the contract is fresh-DB
    bootstrap + repeated migration application.
    """
    from psycopg_pool import ConnectionPool

    db_name = f"mig_idem_{uuid.uuid4().hex[:12]}"
    try:
        admin = psycopg.connect(pg_dsn, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL not available (set BABYLON_TEST_PG_DSN)")
    with admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

    fresh_dsn = re.sub(r"dbname=\S+", f"dbname={db_name}", pg_dsn)
    pool = ConnectionPool(conninfo=fresh_dsn, min_size=1, max_size=2, open=True)
    try:
        yield pool
    finally:
        pool.close()
        with psycopg.connect(pg_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(db_name)))


def _bootstrap_spec_037_schema(pool: Any) -> None:
    from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL

    with pool.connection() as conn:
        conn.autocommit = True
        for ddl in POSTGRES_SCHEMA_DDL:
            conn.execute(ddl)


def test_migrations_apply_twice_on_fresh_db(fresh_db_pool: Any) -> None:
    """Fresh DB + bootstrap, then the runner's applier twice — no error.

    The second pass is the load-bearing one: it exercises every migration
    against the schema as later migrations have already reshaped it.
    """
    _bootstrap_spec_037_schema(fresh_db_pool)
    _apply_migrations(fresh_db_pool)
    _apply_migrations(fresh_db_pool)


def test_migrations_dir_resolution_is_cwd_independent(tmp_path: Path, monkeypatch: Any) -> None:
    """The applier must find migrations regardless of the process CWD.

    Pre-fix behaviour: ``Path("src/...")`` resolved relative to whatever
    directory the runner was launched from, so a foreign CWD silently
    applied ZERO migrations. Post-fix, resolution is package-relative and
    an empty result raises RunnerError.
    """
    from contextlib import contextmanager
    from types import SimpleNamespace

    monkeypatch.chdir(tmp_path)

    executed: list[str] = []

    class _CountingPool:
        @contextmanager
        def connection(self) -> Any:
            yield SimpleNamespace(autocommit=False, execute=executed.append)

    _apply_migrations(_CountingPool())
    assert len(executed) >= 20, (
        "silently applied zero migrations from a foreign CWD — the applier "
        "must resolve the migrations dir relative to the package, not the CWD"
    )
