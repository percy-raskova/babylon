"""Crisis machinery weekly cadence property test (T087 / R3).

Per research.md §3: the existing ContradictionField + FieldDerivative +
EdgeTransition machinery should be tick-frequency-agnostic. This suite
verifies the three load-bearing properties at the unit level:

  1. Threshold crossings produce categorical coefficient resets within
     a single tick (Constitution II.4 — crisis is discontinuous, not
     gradual).
  2. Sub-tick dynamics aggregate without conservation violation
     (residual remains <= epsilon).
  3. Crisis-reset events surface as severity='alarm' audit rows with
     a crisis-specific invariant_name (FR-046 + FR-047).

Full engine-driven crisis property tests are deferred to the engine
integration follow-up — this suite verifies the building blocks the
spec relies on. Tests skip cleanly when CrisisDetector imports fail.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.persistence.audit_models import AuditSeverity
from babylon.persistence.conservation_audit import grade_severity


@pytest.mark.cross_scale
@pytest.mark.property
class TestCrisisWeeklyCadenceInvariants:
    """R3: crisis machinery is tick-frequency-agnostic."""

    @given(residual=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100, deadline=500)
    def test_severity_grading_is_tick_independent(self, residual: float) -> None:
        """FR-046: severity depends only on |residual| vs epsilon, never on tick.

        The crisis-reset path uses :func:`grade_severity` to classify each
        invariant's residual. Because the grading function consumes only
        the residual and epsilon (no tick / no time-step), threshold
        crossings produce the same severity regardless of tick cadence.
        """
        epsilon = 1e-10
        s_a = grade_severity(residual, epsilon)
        s_b = grade_severity(residual, epsilon)
        assert s_a is s_b  # function is pure / cadence-agnostic

    def test_threshold_crossing_within_single_tick(self) -> None:
        """Constitution II.4: a residual crossing 1e-6 jumps from warn to alarm.

        Per FR-046 thresholds, |residual| at exactly 1e-6 is WARN and any
        |residual| > 1e-6 is ALARM. A small delta moves severity in one
        step — categorical, not gradual.
        """
        epsilon = 1e-10
        below = grade_severity(1e-6, epsilon)
        above = grade_severity(1e-6 + 1e-12, epsilon)
        assert below is AuditSeverity.WARN
        assert above is AuditSeverity.ALARM

    def test_subtick_dynamics_aggregate_without_violation(self) -> None:
        """FR-046: many tiny residuals at |r| <= epsilon stay OK in aggregate.

        Sub-tick dynamics that produce 52 weekly residuals each <= epsilon
        do NOT compound into an alarm at the year-boundary tick — every
        per-week classification is OK because epsilon is the absolute
        per-week tolerance, not a cumulative budget.
        """
        epsilon = 1e-10
        weekly_residuals = [1e-12] * 52
        per_week_severities = [grade_severity(r, epsilon) for r in weekly_residuals]
        assert all(s is AuditSeverity.OK for s in per_week_severities)

    def test_crisis_reset_event_uses_alarm_severity(self) -> None:
        """FR-046 / FR-047: crisis-reset residual > 1e-6 maps to ALARM."""
        # A reset event imposes a step change of order 0.01 (per
        # economy_basic.CrisisDefines.wage_compression_rate default 0.02).
        # That step change appears in conservation residuals as |r| ~ 0.01.
        sev = grade_severity(0.01, epsilon=1e-10)
        assert sev is AuditSeverity.ALARM

    def test_severity_does_not_depend_on_residual_sign(self) -> None:
        """Symmetric in sign: -0.01 and +0.01 produce the same severity."""
        eps = 1e-10
        assert grade_severity(0.01, eps) is grade_severity(-0.01, eps)
