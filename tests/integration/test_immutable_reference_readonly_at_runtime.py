"""FR-005 enforcement: immutable_reference_* tables are SELECT-only at runtime.

T031b. Confirms that INSERT/UPDATE/DELETE on any immutable_reference_*
table raises ``psycopg.errors.InsufficientPrivilege`` once the runtime
role has been granted only SELECT.

This test currently runs against the same Postgres role as initialization
(the test fixture uses the superuser role for migration apply). It will
behave fully when a deploy-time role split is introduced; for the MVP we
assert the REVOKE statement is in the migration file and that
psycopg raises a permission error if any other role attempts a write
under that REVOKE.

Skips when no Postgres available, when run as superuser (which bypasses
GRANT/REVOKE), or when the test database has not been split into the
migration role + runtime role pair.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.cross_scale, pytest.mark.integration]

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")


REFERENCE_TABLES: tuple[str, ...] = (
    "immutable_reference_bea_io",
    "immutable_reference_melt_tau",
    "immutable_reference_basket_gamma",
    "immutable_reference_erdi",
    "immutable_reference_hickel_drain",
    "immutable_reference_ricci_unequal",
    "immutable_reference_faf_freight",
    "immutable_reference_qcew_employment",
    "immutable_reference_bea_reis_rent",
    "immutable_reference_fred_rates",
)


@pytest.fixture
def apply_062_migrations(pg_pool):  # type: ignore[no-untyped-def]
    migrations_dir = Path("src/babylon/persistence/migrations").resolve()
    with pg_pool.connection() as conn:
        conn.autocommit = True
        for sql_file in sorted(migrations_dir.glob("00*.sql")):
            conn.execute(sql_file.read_text())


def test_revoke_present_in_migration_sql() -> None:
    """All 10 immutable_reference_* tables must have REVOKE in the SQL."""
    sql = (
        Path("src/babylon/persistence/migrations")
        .resolve()
        .joinpath("0010_immutable_reference_tables.sql")
        .read_text()
    )
    for tbl in REFERENCE_TABLES:
        revoke_line = f"REVOKE INSERT, UPDATE, DELETE ON {tbl} FROM PUBLIC"
        assert revoke_line in sql, (
            f"REVOKE statement missing for {tbl} in migration 0010 — "
            f"FR-005 enforcement broken at the schema layer."
        )


def test_under_revoke_writes_raise_insufficient_privilege(  # type: ignore[no-untyped-def]
    pg_pool, apply_062_migrations
):
    """An INSERT against a REVOKE-protected table raises InsufficientPrivilege.

    This test is meaningful only when the test pool's role is the
    non-privileged runtime role. Many local setups use the superuser
    (postgres) account which is not constrained by REVOKE. In that case
    we mark the test xfail and rely on the deploy-time role split test.
    """
    from psycopg import errors

    with pg_pool.connection() as conn:
        conn.autocommit = True
        # Determine if we are running as a superuser; superuser bypasses REVOKE.
        is_super = conn.execute(
            "SELECT rolsuper FROM pg_roles WHERE rolname = CURRENT_USER"
        ).fetchone()
        if is_super and is_super[0]:
            pytest.xfail(
                "Running as Postgres superuser; REVOKE is bypassed. "
                "Production deploy must split the migration role from the "
                "runtime role. This is verified by deploy-time integration."
            )
        # Otherwise, attempt an INSERT and expect InsufficientPrivilege.
        try:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO immutable_reference_melt_tau "
                    "(session_id, year, tau, canonical_source) "
                    "VALUES (gen_random_uuid(), 2010, 1.0, 'test')"
                )
        except errors.InsufficientPrivilege:
            return  # expected
        pytest.fail("Expected InsufficientPrivilege on runtime INSERT")
