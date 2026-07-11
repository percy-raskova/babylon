"""Unit tests for the spec-063 FR-030c paired cross-border emission evaluator.

Pins: every COMMUTE_OUT with dest_kind='external' must have a same-tick
paired TRADE_EDGE with swapped source/dest and equal magnitude; each
external dest with missing pairs yields one alarm-grade result.
"""

from __future__ import annotations

import uuid

import pytest

from babylon.domain.economics.boundary_flow_register import BoundaryFlowRegisterRow
from babylon.domain.economics.node_kinds import BoundaryEdgeKind, NodeKind
from babylon.persistence.audit_models import AuditSeverity
from babylon.persistence.conservation_audit import (
    ConservationAuditor,
    PairedCrossBorderEmissionEvaluator,
)

pytestmark = [pytest.mark.unit]

_SID = uuid.uuid4()
_HEX = "872ab2c58ffffff"


def _commute_out(hex_id: str, dest: str, magnitude: float) -> BoundaryFlowRegisterRow:
    return BoundaryFlowRegisterRow(
        session_id=_SID,
        tick=1,
        source_node_id=hex_id,
        source_kind=NodeKind.HEX,
        dest_node_id=dest,
        dest_kind=NodeKind.EXTERNAL,
        flow_type=BoundaryEdgeKind.COMMUTE_OUT,
        magnitude=magnitude,
    )


def _trade_pair(hex_id: str, ext: str, magnitude: float) -> BoundaryFlowRegisterRow:
    return BoundaryFlowRegisterRow(
        session_id=_SID,
        tick=1,
        source_node_id=ext,
        source_kind=NodeKind.EXTERNAL,
        dest_node_id=hex_id,
        dest_kind=NodeKind.HEX,
        flow_type=BoundaryEdgeKind.TRADE_EDGE,
        magnitude=magnitude,
    )


def test_fully_paired_rows_yield_no_results() -> None:
    """A COMMUTE_OUT with its swapped/equal-magnitude TRADE_EDGE is clean."""
    evaluator = PairedCrossBorderEmissionEvaluator()
    ctx = {
        "boundary_rows": [
            _commute_out(_HEX, "canada", 42.5),
            _trade_pair(_HEX, "canada", 42.5),
        ]
    }
    assert evaluator(None, None, ctx) == []


def test_missing_pair_yields_one_alarm_result() -> None:
    """One unpaired COMMUTE_OUT → one result graded ALARM through the auditor."""
    evaluator = PairedCrossBorderEmissionEvaluator()
    ctx = {"boundary_rows": [_commute_out(_HEX, "canada", 42.5)]}
    results = evaluator(None, None, ctx)
    assert len(results) == 1
    assert results[0].scale == "external:canada"[:32]
    assert results[0].computed_value == 1.0
    assert results[0].expected_value == 0.0

    auditor = ConservationAuditor(epsilon=1e-9, rng_seed=42)
    auditor.register_invariant("paired_cross_border_emission", evaluator)
    rows, alarms = auditor.evaluate(session_id=_SID, tick=1, hex_rows=[], context=ctx)
    assert len(rows) == 1
    assert rows[0].severity is AuditSeverity.ALARM
    assert len(alarms) == 1
    assert alarms[0].invariant_name == "paired_cross_border_emission"


def test_magnitude_mismatch_counts_as_missing() -> None:
    """A TRADE_EDGE whose magnitude drifts from its COMMUTE_OUT is not a pair."""
    evaluator = PairedCrossBorderEmissionEvaluator()
    ctx = {
        "boundary_rows": [
            _commute_out(_HEX, "canada", 42.5),
            _trade_pair(_HEX, "canada", 43.5),  # off by 1.0 → broken pairing
        ]
    }
    results = evaluator(None, None, ctx)
    assert len(results) == 1
    assert results[0].computed_value == 1.0


def test_two_missing_pairs_same_dest_aggregate_to_count_two() -> None:
    """PK-safety design pin: same external dest aggregates to ONE result row.

    conservation_audit_log PK is (session_id, tick, scale, invariant_name)
    (migration 0014), so two per-pair rows for one dest would collide.
    """
    evaluator = PairedCrossBorderEmissionEvaluator()
    ctx = {
        "boundary_rows": [
            _commute_out(_HEX, "canada", 10.0),
            _commute_out("872ab2c59ffffff", "canada", 20.0),
        ]
    }
    results = evaluator(None, None, ctx)
    assert len(results) == 1
    assert results[0].scale == "external:canada"
    assert results[0].computed_value == 2.0


def test_missing_pairs_different_dests_yield_one_result_each() -> None:
    """Distinct external dests produce distinct (scale-separated) results."""
    evaluator = PairedCrossBorderEmissionEvaluator()
    ctx = {
        "boundary_rows": [
            _commute_out(_HEX, "canada", 10.0),
            _commute_out(_HEX, "rest_of_usa", 20.0),
        ]
    }
    results = evaluator(None, None, ctx)
    assert len(results) == 2
    scales = {r.scale for r in results}
    assert scales == {"external:canada", "external:rest_of_usa"}


def test_non_external_and_other_flow_types_ignored() -> None:
    """DRAIN_EDGE rows and non-external COMMUTE_OUT rows are out of scope."""
    evaluator = PairedCrossBorderEmissionEvaluator()
    drain = BoundaryFlowRegisterRow(
        session_id=_SID,
        tick=1,
        source_node_id="canada",
        source_kind=NodeKind.EXTERNAL,
        dest_node_id="26163",
        dest_kind=NodeKind.COUNTY,
        flow_type=BoundaryEdgeKind.DRAIN_EDGE,
        magnitude=99.0,
    )
    county_commute = BoundaryFlowRegisterRow(
        session_id=_SID,
        tick=1,
        source_node_id=_HEX,
        source_kind=NodeKind.HEX,
        dest_node_id="26163",
        dest_kind=NodeKind.COUNTY,
        flow_type=BoundaryEdgeKind.COMMUTE_OUT,
        magnitude=7.0,
    )
    ctx = {"boundary_rows": [drain, county_commute]}
    assert evaluator(None, None, ctx) == []


def test_none_and_empty_context_yield_empty() -> None:
    """None context and empty boundary_rows are both quiet no-ops."""
    evaluator = PairedCrossBorderEmissionEvaluator()
    assert evaluator(None, None, None) == []
    assert evaluator(None, None, {"boundary_rows": []}) == []


def test_duplicate_pairs_consume_one_to_one() -> None:
    """Matching is a one-to-one multiset consume: 2 commutes need 2 pairs."""
    evaluator = PairedCrossBorderEmissionEvaluator()
    ctx = {
        "boundary_rows": [
            _commute_out(_HEX, "canada", 10.0),
            _commute_out(_HEX, "canada", 10.0),
            _trade_pair(_HEX, "canada", 10.0),  # only ONE pair available
        ]
    }
    results = evaluator(None, None, ctx)
    assert len(results) == 1
    assert results[0].computed_value == 1.0
