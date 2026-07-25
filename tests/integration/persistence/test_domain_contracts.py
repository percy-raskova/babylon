"""PG-live proof that migration 0039's CREATE DOMAINs enforce the contract.

Applies ``0039_domain_contracts.sql`` (via the real
:func:`babylon.persistence.postgres_schema.ensure_ddl_applied` helper) against a
throwaway database, then proves each domain REJECTS an out-of-range / malformed
value and ACCEPTS an in-range one — the enforce-not-compute contract exercised
end to end. A domain violation surfaces as PostgreSQL SQLSTATE 23514
(``CheckViolation``).

Marked ``integration`` so it is skipped when PostgreSQL is absent (the fast unit
gate never needs a database); when the canonical ``babylon_test`` server is
reachable it runs against a fresh disposable DB, so it never pollutes shared
state with the new domains.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Generator
from typing import Any

import psycopg
import pytest
from psycopg import errors, sql

from babylon.persistence.postgres_schema import ensure_ddl_applied
from babylon.sentinels.domain_sync.registry import MIGRATION_PATH

pytestmark = pytest.mark.integration


@pytest.fixture()
def domain_conn(pg_dsn: str) -> Generator[Any, None, None]:
    """A fresh disposable DB with only migration 0039's domains applied.

    Mirrors ``test_migration_idempotency.fresh_db_pool``: a brand-new database
    on the local test server so the domains never touch shared ``babylon_test``
    state. Applied through the production ``ensure_ddl_applied`` path.
    """
    try:
        admin = psycopg.connect(pg_dsn, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL not available (set BABYLON_TEST_PG_DSN)")
    db_name = f"dom_ct_{uuid.uuid4().hex[:12]}"
    with admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))

    fresh_dsn = re.sub(r"dbname=\S+", f"dbname={db_name}", pg_dsn)
    migration_text = MIGRATION_PATH.read_text(encoding="utf-8")
    conn = psycopg.connect(fresh_dsn, autocommit=True)
    try:
        ensure_ddl_applied(conn, [migration_text])
        yield conn
    finally:
        conn.close()
        with psycopg.connect(pg_dsn, autocommit=True) as admin2:
            admin2.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(db_name)))


def _rejects(conn: Any, domain: str, value: object) -> bool:
    """Whether casting ``value`` to ``domain`` raises the domain's CHECK.

    Casting to a domain applies its CHECK, so ``CAST(<value> AS probability)``
    with an out-of-range value raises ``CheckViolation`` (autocommit => the
    failed statement rolls back on its own, leaving the connection usable). The
    ``CAST(... AS ...)`` form is used rather than ``value::domain`` because the
    ``::`` cast binds tighter than unary minus (``-0.1::probability`` would cast
    ``0.1`` and negate the result, testing the wrong value).

    :param conn: An autocommit connection to the domain-bearing DB.
    :param domain: The domain name to cast to.
    :param value: The value to validate.
    :returns: ``True`` if the domain rejected the value, ``False`` if accepted.
    """
    try:
        conn.execute(
            sql.SQL("SELECT CAST({} AS {})").format(sql.Literal(value), sql.Identifier(domain))
        )
    except errors.CheckViolation:
        return True
    return False


def test_numeric_domains_enforce_their_range(domain_conn: Any) -> None:
    """probability [0,1], currency [0,inf), ratio (0,inf) reject out-of-range."""
    # probability [0, 1]
    assert _rejects(domain_conn, "probability", 1.5)
    assert _rejects(domain_conn, "probability", -0.1)
    assert not _rejects(domain_conn, "probability", 0.5)
    assert not _rejects(domain_conn, "probability", 0.0)
    assert not _rejects(domain_conn, "probability", 1.0)
    # currency [0, inf)
    assert _rejects(domain_conn, "currency", -1.0)
    assert not _rejects(domain_conn, "currency", 0.0)
    assert not _rejects(domain_conn, "currency", 12345.678)
    # ratio (0, inf) — zero is excluded
    assert _rejects(domain_conn, "ratio", 0.0)
    assert _rejects(domain_conn, "ratio", -1.0)
    assert not _rejects(domain_conn, "ratio", 0.5)
    # labor_hours [0, inf)
    assert _rejects(domain_conn, "labor_hours", -0.001)
    assert not _rejects(domain_conn, "labor_hours", 0.0)


def test_fips5_rejects_a_four_digit_string(domain_conn: Any) -> None:
    """fips5 rejects a 4-digit string and accepts a 5-digit one."""
    assert _rejects(domain_conn, "fips5", "1234")
    assert _rejects(domain_conn, "fips5", "123456")
    assert _rejects(domain_conn, "fips5", "abcde")
    assert not _rejects(domain_conn, "fips5", "12345")


def test_fips2_and_h3index_enforce_format(domain_conn: Any) -> None:
    """fips2 is exactly 2 digits; h3index is exactly 15 characters."""
    assert _rejects(domain_conn, "fips2", "5")
    assert not _rejects(domain_conn, "fips2", "06")
    assert _rejects(domain_conn, "h3index", "12345678901234")  # 14 chars
    assert not _rejects(domain_conn, "h3index", "123456789012345")  # 15 chars


def test_domains_are_nullable(domain_conn: Any) -> None:
    """A SQL CHECK is not-false on NULL — nullability stays a column decision."""
    row = domain_conn.execute("SELECT NULL::probability").fetchone()
    assert row is not None and row[0] is None


def test_migration_is_idempotent_at_the_db_level(domain_conn: Any) -> None:
    """Re-executing the raw migration text is a clean no-op (the DO guards)."""
    migration_text = MIGRATION_PATH.read_text(encoding="utf-8")
    # Direct re-exec (bypassing the stamp fast-path) must not raise on the
    # already-created domains — the pg_type guards make each CREATE a no-op.
    domain_conn.execute(migration_text)
    domain_conn.execute(migration_text)
    count = domain_conn.execute(
        "SELECT count(*) FROM pg_type WHERE typtype = 'd' "
        "AND typname IN ('probability','currency','ratio','labor_hours','fips5','fips2','h3index')"
    ).fetchone()
    assert count is not None and count[0] == 7
