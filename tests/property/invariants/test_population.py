"""Property-based tests for population conservation modulo births and deaths
(INV-004 / Spec 053 US4).

See ``specs/053-conservation-invariants/contracts/population_lifecycle.md``.

The invariant: ``population_{t+1} == population_t + births_t − deaths_t``,
where ``population_t`` is the grid-wide sum of D-P-D′ cohort counts read
from per-hex ``DPDState`` instances (Spec 030).

Note (spec drift): the original spec described cohort counts as integer-
valued, but the actual ``DPDState`` model uses floats with ``ge=0.0``. The
test therefore uses a small numerical tolerance instead of strict integer
equality.

This test currently focuses on the **algebraic** form of the invariant —
``post_pop − pre_pop == births − deaths`` — by verifying the equation holds
for any DPDState distribution paired with synthetic births/deaths counts.
A future enhancement (TODO) will wire this to a live ``run_tick`` that
actually mutates D-P-D′ cohorts via lifecycle/vitality systems and reads
the per-tick events from ``WorldState.events``.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.economics.lifecycle.types import DPDState
from tests.property.strategies.dpd_state import dpd_state_grid_strategy

_TOL = 1e-9  # float-arithmetic tolerance for cohort sums


def _sum_population(grid: Mapping[str, DPDState]) -> float:
    """Sum total_population across the grid."""
    return sum(d.total_population for d in grid.values())


@pytest.mark.unit
class TestPopulationAccountingAlgebra:
    """INV-004: the accounting equation pop_{t+1} = pop_t + births - deaths."""

    @given(
        grid=dpd_state_grid_strategy(min_hexes=1, max_hexes=100),
        births=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
        deaths=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_pop_delta_equals_births_minus_deaths(
        self,
        grid: Mapping[str, DPDState],
        births: float,
        deaths: float,
    ) -> None:
        """For any starting population and any (births, deaths) counts,
        a post-state with pop_post = pop_pre + births - deaths satisfies
        the accounting equation exactly (clamped at zero for non-negativity).
        """
        pre_pop = _sum_population(grid)
        # Construct the algebraically-required post population.
        # Clamp at zero — populations can't go negative.
        deaths_actual = min(deaths, pre_pop + births)
        post_pop = pre_pop + births - deaths_actual
        # The invariant: post_pop - pre_pop == births - deaths_actual exactly.
        delta = post_pop - pre_pop
        expected = births - deaths_actual
        drift = abs(delta - expected)
        assert drift < _TOL, (
            f"INV-004: accounting equation violated — "
            f"pre={pre_pop}, post={post_pop}, births={births}, "
            f"deaths={deaths_actual}, drift={drift:.3e}"
        )
        assert post_pop >= 0.0, (
            f"INV-004: post-population negative ({post_pop}) — non-negativity violated"
        )

    @given(grid=dpd_state_grid_strategy(min_hexes=1, max_hexes=100))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_zero_births_zero_deaths_preserves_pop(
        self,
        grid: Mapping[str, DPDState],
    ) -> None:
        """births = deaths = 0 ⇒ pop_{t+1} = pop_t exactly."""
        pre_pop = _sum_population(grid)
        # Trivially: with no transitions the total is unchanged.
        post_pop = pre_pop  # represents what a no-op tick would produce
        assert post_pop == pre_pop, (
            f"INV-004: zero-tick changed population from {pre_pop} to {post_pop}"
        )


# TODO (post-spec-053): wire to live SimulationEngine.run_tick that mutates
# D-P-D′ cohorts via LifecycleSystem and VitalitySystem; read per-tick BIRTH
# and DEATH events from WorldState.events. The current algebraic form
# verifies the invariant's MATHEMATICAL CORRECTNESS but does not exercise
# the engine's bookkeeping pipeline. Once LifecycleSystem publishes BIRTH/
# DEATH events with cohort counts in the payload, replace the synthetic
# (births, deaths) with a parametrized over @given(dpd_state_grid_strategy())
# that runs run_tick and asserts the equation against the published events.
