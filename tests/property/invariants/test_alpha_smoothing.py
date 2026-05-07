"""Property-based tests for the alpha-smoothing EMA inequality bound invariant
(INV-009 / spec-054 US4).

See ``specs/054-bound-invariants/contracts/alpha_smoothing.md`` for the
full predicate specification.

Three predicates implementing the hybrid strategy from Q3 clarification:

  Predicate A — synthesized formula sweep across every discovered coefficient (T026)
  Predicate B — observed end-to-end smoothing via CoefficientSmoother (T027)
  Predicate C — crisis suspension is honored by CrisisStateInspector (T028)

US4 contract:

    Between non-crisis ticks t -> t+1, for every smoothed coefficient c:
        |c[t+1] - c[t]| <= alpha * |raw[t+1] - c[t]| + epsilon

    where epsilon = 1e-12 (float64 round-off floor).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.economics.tick.smoothing import CoefficientSmoother
from babylon.economics.tick.types import CrisisPhase
from tests.property.harness import tol
from tests.property.harness.alpha_discovery import (
    AlphaCoefficient,
    discover_alpha_coefficients,
)
from tests.property.harness.crisis_inspector import CrisisStateInspector
from tests.property.strategies.alpha_coefficient import alpha_coefficient_triple_strategy


def _ema_bound(alpha: float, raw: float, prev: float) -> float:
    """EMA inequality bound with magnitude-aware float64 tolerance.

    The EMA update ``new = prev + alpha * (raw - prev)`` produces a drift
    ``|new - prev| = alpha * |raw - prev|`` exactly in real arithmetic. In
    float64, accumulating fma round-off at magnitudes ~1e7 reaches ~1e-9
    absolute drift over the equality. The magnitude-aware ``tol()`` helper
    (from spec-053) accounts for this with a ``1e-13 * |magnitude|`` term.
    """
    return alpha * abs(raw - prev) + tol(n=1, magnitude=max(abs(prev), abs(raw)))


@dataclass(frozen=True)
class _MockCrisisState:
    """Minimal stand-in for a state object carrying a CrisisPhase value.

    Used by Predicate C to drive the inspector across all enum values.
    """

    crisis_phase: CrisisPhase | None


@pytest.mark.unit
class TestAlphaSmoothing:
    """INV-009: alpha-smoothed coefficients respect the EMA inequality
    in steady state; suspended in crisis ticks."""

    @pytest.mark.parametrize(
        "coeff",
        discover_alpha_coefficients(),
        ids=lambda c: f"{c.containing_class.__name__}.{c.field_name}",
    )
    @given(triple=alpha_coefficient_triple_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_alpha_inequality_synthesized(
        self,
        coeff: AlphaCoefficient,
        triple: tuple[float, float, float | None],
    ) -> None:
        """Predicate A: synthesized EMA sweep across every discovered coefficient.

        For each ``AlphaCoefficient`` discovered in ``defines.py``, draws random
        ``(prev, raw, override_alpha)`` triples and asserts the EMA
        inequality on ``CoefficientSmoother.smooth``. Falsifies the
        formula across the full coefficient set.
        """
        prev, raw, override_alpha = triple
        alpha = override_alpha if override_alpha is not None else coeff.default_alpha
        smoother = CoefficientSmoother(alpha=alpha)
        new = smoother.smooth(raw=raw, previous=prev, is_initialized=True)
        drift = abs(new - prev)
        bound = _ema_bound(alpha, raw, prev)
        assert drift <= bound, (
            f"INV-009 (synth) {coeff.containing_class.__name__}.{coeff.field_name}: "
            f"drift={drift:.6e}, bound={bound:.6e}, alpha={alpha}, "
            f"prev={prev}, raw={raw}, new={new}"
        )

    @given(
        prev=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        alpha=st.floats(min_value=1e-3, max_value=1.0, allow_nan=False, allow_infinity=False),
        raws=st.lists(
            st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
            min_size=5,
            max_size=10,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_ema_observed_multitick_trajectory(
        self,
        prev: float,
        alpha: float,
        raws: list[float],
    ) -> None:
        """Predicate B: observed multi-tick smoother trajectory.

        Threads ``CoefficientSmoother.smooth`` across a sequence of raw inputs,
        asserting the EMA inequality on every (prev, raw, post) step. This
        is the "observed" layer of the Q3 hybrid strategy: it falsifies the
        wiring of the smoother under realistic multi-tick usage rather than
        single-step formula correctness.

        A regression that bypasses ``CoefficientSmoother`` (e.g., a System
        that writes raw values directly to the coefficient slot) would not
        be caught by this test directly, but would show up in any future
        observed-pipeline extension that reads the same coefficient through
        two paths.
        """
        smoother = CoefficientSmoother(alpha=alpha)
        current = prev
        is_initialized = True
        for tick_idx, raw in enumerate(raws):
            new = smoother.smooth(raw=raw, previous=current, is_initialized=is_initialized)
            drift = abs(new - current)
            bound = _ema_bound(alpha, raw, current)
            assert drift <= bound, (
                f"INV-009 (observed) tick {tick_idx}: drift={drift:.6e}, "
                f"bound={bound:.6e}, alpha={alpha}, prev={current}, "
                f"raw={raw}, new={new}"
            )
            current = new

    def test_inequality_suspended_in_crisis(self) -> None:
        """Predicate C: ``CrisisStateInspector.is_steady_state`` correctly
        suspends the inequality in crisis phases (US4.3).

        Sanity-checks the suspension precondition is honored before any
        inequality assertion fires. ``NORMAL`` and ``None`` are steady
        state; every other ``CrisisPhase`` value is crisis (NOT steady).
        """
        inspector = CrisisStateInspector()

        # NORMAL and None are steady state.
        assert inspector.is_steady_state(_MockCrisisState(crisis_phase=None))
        assert inspector.is_steady_state(_MockCrisisState(crisis_phase=CrisisPhase.NORMAL))

        # All other phases are crisis (NOT steady state).
        crisis_phases = (
            CrisisPhase.ONSET,
            CrisisPhase.EARLY,
            CrisisPhase.DEEP,
            CrisisPhase.RECOVERY,
        )
        for phase in crisis_phases:
            state = _MockCrisisState(crisis_phase=phase)
            assert not inspector.is_steady_state(state), (
                f"is_steady_state should be False for {phase!r}; "
                f"the inequality must not be asserted in crisis ticks per US4"
            )

        # Missing attribute defaults to steady state per spec edge case.
        empty: Any = object()
        assert inspector.is_steady_state(empty)
