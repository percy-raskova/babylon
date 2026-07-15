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


# hex_cell as it shipped BEFORE county_name/bea_ea_code/msa_code/state_fips were
# added to HEX_CELL_DDL. Reproduces the drift observed on the live web DB
# (2026-07-12): ``CREATE TABLE IF NOT EXISTS`` no-ops on the stale table, so the
# newer columns never appear and ``CREATE INDEX ... ON hex_cell(bea_ea_code)``
# fails with UndefinedColumn — which init_schema's caller swallowed as a
# "non-fatal" warning, silently aborting every DDL statement after it.
_STALE_HEX_CELL_DDL = """
CREATE TABLE hex_cell (
    h3_index        VARCHAR(15) PRIMARY KEY,
    county_fips     VARCHAR(5) NOT NULL,
    res6_parent     VARCHAR(15) NOT NULL,
    res5_parent     VARCHAR(15) NOT NULL,
    geometry        geometry(Polygon, 4326) NOT NULL,
    centroid        geometry(Point, 4326) NOT NULL
)
"""


def test_bootstrap_heals_drifted_hex_cell(fresh_db_pool: Any) -> None:
    """A pre-existing ``hex_cell`` missing the newer columns must be healed.

    Regression for the 2026-07-12 live-DB drift. ``CREATE TABLE IF NOT EXISTS``
    cannot add columns to an existing table, so the idempotent ``ALTER TABLE
    ... ADD COLUMN IF NOT EXISTS`` statements in ``POSTGRES_SCHEMA_DDL`` must add
    them before ``idx_hex_cell_bea_ea`` runs. The full bootstrap must then
    complete without error and the healed columns + index must exist.
    """
    with fresh_db_pool.connection() as conn:
        conn.autocommit = True
        conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        conn.execute(_STALE_HEX_CELL_DDL)

    # Must complete cleanly on the drifted table (RED before the ALTER heal:
    # raises psycopg UndefinedColumn at the bea_ea_code index).
    _bootstrap_spec_037_schema(fresh_db_pool)

    with fresh_db_pool.connection() as conn:
        cols = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'hex_cell'"
            ).fetchall()
        }
        assert {"county_name", "bea_ea_code", "msa_code", "state_fips"} <= cols, (
            f"stale hex_cell was not healed; columns present: {sorted(cols)}"
        )
        index_row = conn.execute(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_hex_cell_bea_ea'"
        ).fetchone()
        assert index_row is not None, "idx_hex_cell_bea_ea must exist after healing"


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
