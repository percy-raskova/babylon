"""Spec-070 audit-row round-trip test (T027 / FR-046 / FR-049).

Writes a CLAIMS-mutation audit row, reads it back, verifies the
``observer_mutation`` flag preserves correctly.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from babylon.persistence.balkanization_history import (
    ClaimsAuditRow,
    InfluencesAuditRow,
    record_claims_mutation,
    record_influences_mutation,
)

PG_DSN_ENV = "BABYLON_TEST_PG_DSN"
DEFAULT_DSN = "dbname=babylon_test host=localhost port=5433 user=test password=test"


def _postgres_reachable() -> bool:
    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    try:
        import psycopg

        psycopg.connect(dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = [pytest.mark.integration, pytest.mark.requires_postgres]


def test_claims_audit_dataclass_construction() -> None:
    """Static construction sanity (does not require Postgres)."""

    row = ClaimsAuditRow(
        session_id=uuid4(),
        tick=0,
        sovereign_id="SOV_USA_FED",
        territory_id="HEX_000",
        operation="CREATE",
        control_level=1.0,
        fiscal_status="taxed",
        legal_status="de_jure",
        recognition_level=1.0,
        observer_mutation=False,
    )
    assert row.observer_mutation is False


def test_influences_audit_dataclass_construction() -> None:
    """Static construction sanity (does not require Postgres)."""

    row = InfluencesAuditRow(
        session_id=uuid4(),
        tick=5,
        faction_id="FAC_DECOLONIAL",
        territory_id="HEX_002",
        operation="UPDATE",
        influence_level=0.7,
        support_type="ideological",
        cadre_count=100,
        sympathizer_count=10_000,
        observer_mutation=True,
    )
    assert row.observer_mutation is True


@pytest.fixture(scope="module")
def apply_balkanization_migrations(pg_pool):  # type: ignore[no-untyped-def]
    """Apply the full migration set so the spec-070 audit tables exist.

    Routes through the runner's canonical applier — digest-stamped +
    advisory-locked (``ensure_ddl_applied``), package-relative paths — a
    raw ``conn.execute`` loop here would be a fifth unprotected DDL entry
    point re-opening the 2026-07-16 xdist race/deadlock family.
    """
    from babylon.engine.headless_runner.runner import _apply_migrations

    _apply_migrations(pg_pool)


@pytest.mark.skipif(not _postgres_reachable(), reason="Postgres test DB not reachable")
def test_observer_flag_preserves_round_trip(  # type: ignore[no-untyped-def]
    pg_pool, apply_balkanization_migrations
) -> None:
    """The observer_mutation boolean MUST round-trip through the
    audit-log INSERT + SELECT (FR-049)."""

    session_id = uuid4()
    observer_row = ClaimsAuditRow(
        session_id=session_id,
        tick=0,
        sovereign_id="SOV_TEST_ROUNDTRIP",
        territory_id="HEX_RT_OBSERVER",
        operation="CREATE",
        control_level=1.0,
        fiscal_status="taxed",
        legal_status="de_jure",
        recognition_level=1.0,
        observer_mutation=True,
    )
    system_row = ClaimsAuditRow(
        session_id=session_id,
        tick=0,
        sovereign_id="SOV_TEST_ROUNDTRIP",
        territory_id="HEX_RT_SYSTEM",
        operation="CREATE",
        control_level=1.0,
        fiscal_status="taxed",
        legal_status="de_jure",
        recognition_level=1.0,
        observer_mutation=False,
    )
    record_claims_mutation(pg_pool, observer_row)
    record_claims_mutation(pg_pool, system_row)

    with pg_pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT territory_id, observer_mutation "
            "FROM balkanization_claims_audit "
            "WHERE session_id = %s AND sovereign_id = %s "
            "ORDER BY territory_id",
            (session_id, observer_row.sovereign_id),
        )
        rows = cur.fetchall()

    # Both directions must round-trip: a writer bug that always forces
    # True (or always defaults to the column's FALSE default) would
    # surface as a mismatch on one of these two rows.
    assert rows == [
        (observer_row.territory_id, True),
        (system_row.territory_id, False),
    ]


def test_writer_module_exports() -> None:
    """The :mod:`balkanization_history` module exports both writers
    plus their input dataclasses."""

    import babylon.persistence.balkanization_history as bh

    assert {
        "ClaimsAuditRow",
        "InfluencesAuditRow",
        "Operation",
        "record_claims_mutation",
        "record_influences_mutation",
    } <= set(bh.__all__)
    # Re-assert callable shape.
    assert callable(record_claims_mutation)
    assert callable(record_influences_mutation)
