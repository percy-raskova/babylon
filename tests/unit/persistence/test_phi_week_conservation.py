"""Unit tests for the spec-101 Φ-week conservation evaluator.

Pins the relative-residual identity ``Σ DRAIN_EDGE / Φ_week ≡ 1.0`` per bloc
(D4) and its severity grading through the auditor, without any DB.
"""

from __future__ import annotations

import uuid

import pytest

from babylon.economics.boundary_flow_register import BoundaryFlowRegisterRow
from babylon.economics.node_kinds import BoundaryEdgeKind, NodeKind
from babylon.persistence.audit_models import AuditSeverity
from babylon.persistence.conservation_audit import (
    ConservationAuditor,
    phi_week_conservation_evaluator,
)

pytestmark = [pytest.mark.unit]

_SID = uuid.uuid4()


def _drain(node: str, county: str, magnitude: float) -> BoundaryFlowRegisterRow:
    return BoundaryFlowRegisterRow(
        session_id=_SID,
        tick=1,
        source_node_id=node,
        source_kind=NodeKind.EXTERNAL,
        dest_node_id=county,
        dest_kind=NodeKind.COUNTY,
        flow_type=BoundaryEdgeKind.DRAIN_EDGE,
        magnitude=magnitude,
    )


def test_balanced_drain_gives_unit_ratio() -> None:
    phi_year = 52_000.0  # → phi_week = 1000.0
    rows = [_drain("canada", "26163", 600.0), _drain("canada", "26125", 400.0)]
    ctx = {"boundary_rows": rows, "external_nodes_phi": {"canada": phi_year}}
    (result,) = phi_week_conservation_evaluator(None, None, ctx)
    assert result.scale == "external:canada"
    assert result.computed_value == pytest.approx(1.0)
    assert result.expected_value == 1.0


def test_zero_phi_bloc_skipped() -> None:
    ctx = {"boundary_rows": [], "external_nodes_phi": {"india": 0.0, "canada": 52.0}}
    results = phi_week_conservation_evaluator(None, None, ctx)
    scales = {r.scale for r in results}
    assert "external:india" not in scales
    assert "external:canada" in scales


def test_non_drain_and_wrong_kind_ignored() -> None:
    phi_year = 52.0  # phi_week = 1.0
    trade = BoundaryFlowRegisterRow(
        session_id=_SID,
        tick=1,
        source_node_id="canada",
        source_kind=NodeKind.EXTERNAL,
        dest_node_id="26163",
        dest_kind=NodeKind.HEX,
        flow_type=BoundaryEdgeKind.TRADE_EDGE,
        magnitude=999.0,
    )
    ctx = {
        "boundary_rows": [trade, _drain("canada", "26163", 1.0)],
        "external_nodes_phi": {"canada": phi_year},
    }
    (result,) = phi_week_conservation_evaluator(None, None, ctx)
    assert result.computed_value == pytest.approx(1.0)  # only the DRAIN row counted


def test_none_context_yields_no_results() -> None:
    assert phi_week_conservation_evaluator(None, None, None) == []


def test_balanced_is_ok_underdrain_is_alarm_via_auditor() -> None:
    auditor = ConservationAuditor(epsilon=1e-9, rng_seed=0)
    auditor.register_invariant(
        "imperial_rent_phi_week_distribution", phi_week_conservation_evaluator
    )
    phi_year = 52.0  # phi_week = 1.0
    # canada balanced (1.0), china under-drained (0.5 → residual -0.5 → ALARM)
    rows = [_drain("canada", "26163", 1.0), _drain("china", "26163", 0.5)]
    ctx = {"boundary_rows": rows, "external_nodes_phi": {"canada": phi_year, "china": phi_year}}
    audit_rows, alarms = auditor.evaluate(session_id=_SID, tick=1, hex_rows=[], context=ctx)
    by_scale = {r.scale: r for r in audit_rows}
    assert by_scale["external:canada"].severity is AuditSeverity.OK
    assert by_scale["external:china"].severity is AuditSeverity.ALARM
    assert any(a.scale == "external:china" for a in alarms)
