"""D4 (ADR096): the babylon_intel least-privilege role migration.

Applies the full migration set on a fresh database (mirroring the runner's
real contract) and asserts the role exists with exactly the intended grants:
SELECT on the projection views, SELECT+INSERT on document_chunk, and NO
UPDATE/DELETE. Skips when PostgreSQL is unavailable.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Generator
from typing import Any

import psycopg
import pytest
from psycopg import sql

from babylon.engine.headless_runner.runner import _apply_migrations

pytestmark = pytest.mark.integration


@pytest.fixture()
def fresh_db_pool(pg_dsn: str) -> Generator[Any, None, None]:
    from psycopg_pool import ConnectionPool

    db_name = f"intel_role_{uuid.uuid4().hex[:12]}"
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
            # DROP OWNED cleans grants so the shared role can be dropped, then
            # drop the DB. The role is cluster-global; leave it if other DBs use it.
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(db_name)))


def _bootstrap(pool: Any) -> None:
    from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL

    with pool.connection() as conn:
        conn.autocommit = True
        for ddl in POSTGRES_SCHEMA_DDL:
            conn.execute(ddl)


def test_role_created_with_expected_grants(fresh_db_pool: Any) -> None:
    _bootstrap(fresh_db_pool)
    _apply_migrations(fresh_db_pool)
    with fresh_db_pool.connection() as conn:
        conn.autocommit = True
        role = conn.execute(
            "SELECT rolcanlogin, rolsuper FROM pg_roles WHERE rolname = 'babylon_intel'"
        ).fetchone()
        assert role is not None, "babylon_intel role must exist"
        assert role[0] is True, "babylon_intel must be a LOGIN (connection) role"
        assert role[1] is False, "babylon_intel must NOT be superuser"

        # SELECT on a composition view; NO write on it.
        assert (
            conn.execute(
                "SELECT has_table_privilege('babylon_intel', 'v_hex_intel', 'SELECT')"
            ).fetchone()[0]
            is True
        )
        assert (
            conn.execute(
                "SELECT has_table_privilege('babylon_intel', 'v_hex_intel', 'INSERT')"
            ).fetchone()[0]
            is False
        )

        # INSERT + SELECT on document_chunk; NO UPDATE/DELETE.
        assert (
            conn.execute(
                "SELECT has_table_privilege('babylon_intel', 'document_chunk', 'INSERT')"
            ).fetchone()[0]
            is True
        )
        assert (
            conn.execute(
                "SELECT has_table_privilege('babylon_intel', 'document_chunk', 'SELECT')"
            ).fetchone()[0]
            is True
        )
        assert (
            conn.execute(
                "SELECT has_table_privilege('babylon_intel', 'document_chunk', 'UPDATE')"
            ).fetchone()[0]
            is False
        )
        assert (
            conn.execute(
                "SELECT has_table_privilege('babylon_intel', 'document_chunk', 'DELETE')"
            ).fetchone()[0]
            is False
        )


def test_migration_reapplies_idempotently(fresh_db_pool: Any) -> None:
    from babylon.persistence.postgres_schema import SCHEMA_STAMP_TABLE

    _bootstrap(fresh_db_pool)
    _apply_migrations(fresh_db_pool)
    with fresh_db_pool.connection() as conn:
        conn.autocommit = True
        conn.execute(f"DROP TABLE {SCHEMA_STAMP_TABLE}")  # force full re-run
    _apply_migrations(fresh_db_pool)  # guarded CREATE ROLE must not error
    with fresh_db_pool.connection() as conn:
        conn.autocommit = True
        assert (
            conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'babylon_intel'").fetchone()
            is not None
        )
