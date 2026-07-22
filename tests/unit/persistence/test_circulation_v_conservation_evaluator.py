"""Unit tests for the spec-063/Vol II Circulation U4 FR-010 conservation evaluator.

Pins: ``CirculationVConservationEvaluator`` reads
``context["vol2_circulation_result"]`` (a
:class:`~babylon.engine.systems.vol2_circulation.CirculationStepResult`) and
reports one ``per_stage``-scale result comparing
``post_total_v_in_area + boundary_out_total_v`` against ``pre_total_v``;
quiet no-op when the key/context is absent (the sub-stage didn't run).
"""

from __future__ import annotations

import uuid

import pytest

from babylon.engine.systems.vol2_circulation import CirculationStepResult
from babylon.persistence.audit_models import AuditSeverity
from babylon.persistence.conservation_audit import (
    CirculationVConservationEvaluator,
    ConservationAuditor,
)

pytestmark = [pytest.mark.unit]

_SID = uuid.uuid4()


def _result(
    *,
    pre_total_v: float,
    post_total_v_in_area: float,
    boundary_out_total_v: float,
) -> CirculationStepResult:
    return CirculationStepResult(
        tick=1,
        pre_total_v=pre_total_v,
        post_total_v_in_area=post_total_v_in_area,
        boundary_out_total_v=boundary_out_total_v,
        rows_emitted=0,
        od_year_used=2010,
        conservation_residual=abs(pre_total_v - (post_total_v_in_area + boundary_out_total_v)),
    )


def test_none_context_is_quiet_no_op() -> None:
    """The sub-stage never ran (context None) -- no results, not an alarm."""
    evaluator = CirculationVConservationEvaluator()
    assert evaluator(None, None, None) == []


def test_missing_key_is_quiet_no_op() -> None:
    """Context present but the gate is still closed for this tick -- no results."""
    evaluator = CirculationVConservationEvaluator()
    assert evaluator(None, None, {}) == []


def test_conserved_result_yields_one_ok_row() -> None:
    """A conserved CirculationStepResult grades OK through the auditor."""
    evaluator = CirculationVConservationEvaluator()
    result = _result(pre_total_v=1000.0, post_total_v_in_area=700.0, boundary_out_total_v=300.0)
    results = evaluator(None, None, {"vol2_circulation_result": result})
    assert len(results) == 1
    assert results[0].scale == "per_stage"
    assert results[0].invariant_name == "circulation_preserves_sum_v"
    assert results[0].computed_value == pytest.approx(1000.0)
    assert results[0].expected_value == pytest.approx(1000.0)

    auditor = ConservationAuditor(epsilon=1e-9, rng_seed=42)
    auditor.register_invariant("circulation_preserves_sum_v", evaluator)
    rows, alarms = auditor.evaluate(
        session_id=_SID,
        tick=1,
        hex_rows=[],
        context={"vol2_circulation_result": result},
    )
    assert len(rows) == 1
    assert rows[0].severity is AuditSeverity.OK
    assert rows[0].residual == pytest.approx(0.0)
    assert alarms == []


def test_broken_conservation_grades_alarm() -> None:
    """A residual beyond 1e-6 grades ALARM (FR-046) -- proves the wiring, not

    just the vacuous-pass path (the honest counterpart to
    ``test_paired_cross_border_evaluator.py``'s missing-pair alarm test).
    """
    evaluator = CirculationVConservationEvaluator()
    # pre=1000, post_in_area + boundary_out = 900 -- residual 100, way past 1e-6.
    result = _result(pre_total_v=1000.0, post_total_v_in_area=700.0, boundary_out_total_v=200.0)

    auditor = ConservationAuditor(epsilon=1e-9, rng_seed=42)
    auditor.register_invariant("circulation_preserves_sum_v", evaluator)
    rows, alarms = auditor.evaluate(
        session_id=_SID,
        tick=1,
        hex_rows=[],
        context={"vol2_circulation_result": result},
    )
    assert len(rows) == 1
    assert rows[0].severity is AuditSeverity.ALARM
    assert rows[0].residual == pytest.approx(-100.0)
    assert len(alarms) == 1
    assert alarms[0].invariant_name == "circulation_preserves_sum_v"
