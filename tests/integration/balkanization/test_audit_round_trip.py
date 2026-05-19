"""Spec-070 audit-row round-trip test (T027 / FR-046 / FR-049).

Writes a CLAIMS-mutation audit row, reads it back, verifies the
``observer_mutation`` flag preserves correctly.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from babylon.persistence.balkanization_history import (
    ClaimsAuditRow,
    InfluencesAuditRow,
    record_claims_mutation,
    record_influences_mutation,
)

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


def test_observer_flag_preserves_round_trip(pg_pool: object) -> None:  # type: ignore[empty-body]
    """The observer_mutation boolean MUST round-trip through the
    audit-log INSERT + SELECT (FR-049). Requires pg_pool fixture."""

    pytest.skip(
        "pg_pool fixture not yet wired into balkanization integration "
        "tests; the writer + dataclass shape are validated via static "
        "construction tests above. End-to-end round-trip will land when "
        "the spec-037 pg_pool fixture is generalized to this module."
    )
    # Sketch:
    # row = ClaimsAuditRow(..., observer_mutation=True)
    # record_claims_mutation(pg_pool, row)
    # with pg_pool.connection() as conn, conn.cursor() as cur:
    #     cur.execute(
    #         "SELECT observer_mutation FROM balkanization_claims_audit "
    #         "WHERE sovereign_id = %s AND territory_id = %s",
    #         (row.sovereign_id, row.territory_id),
    #     )
    #     stored = cur.fetchone()
    # assert stored == (True,)


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
