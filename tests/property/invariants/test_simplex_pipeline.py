"""Property-based tests for the ternary consciousness simplex bound invariant
(INV-008 / spec-054 US3).

See ``specs/054-bound-invariants/contracts/simplex_pipeline.md`` for the
full predicate specification.

Three predicates:

  Predicate A — single-tick simplex preservation across the full pipeline (T023)
  Predicate B — multi-tick (5) simplex stability — catches incremental drift (T024)
  Predicate C — route_agitation_to_ternary preserves the simplex (T025)

NOTE on US3 Predicate A/B vacuity: ``WorldState`` collections do not directly
carry ``TernaryConsciousness`` instances; the ternary simplex lives on
``Community`` hyperedges inside the graph during tick processing. The
``SimplexPreserved`` invariant walks every entity looking for a
``consciousness`` attribute that IS a ``TernaryConsciousness`` instance and
returns success vacuously when none are present — which is the correct
semantics: "no entity holds an off-simplex consciousness" is trivially
satisfied when no entity holds ANY ternary consciousness. The harness still
exercises the round-trip and pipeline machinery, so a future change that
adds ``TernaryConsciousness`` to a ``WorldState`` collection extends
coverage automatically.

Predicate C directly exercises the routing formula and is the load-bearing
test for the simplex math.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.config.defines import ConsciousnessDefines
from babylon.engine.context import TickContext
from babylon.engine.invariants import SimplexPreserved
from babylon.engine.simulation_engine import SimulationEngine
from babylon.formulas.consciousness_routing import route_agitation_to_ternary
from babylon.models.world_state import WorldState
from tests.property.harness.system_registry import all_systems
from tests.property.strategies.consciousness_simplex import simplex_points
from tests.property.strategies.worldstate import (
    worldstate_with_consecutive_ticks_strategy,
    worldstate_with_simplex_consciousness_strategy,
)

# Tolerance per spec acceptance scenario US3.1.
_SIMPLEX_TOL = 1e-4

# Multi-tick depth per spec acceptance scenario US3.2.
_TICK_COUNT = 5


def _run_one_tick(pre: WorldState, services: object, tick: int) -> WorldState:
    """Helper: build a SimulationEngine with all 21 Systems and run one tick."""
    systems = [cls() for cls in all_systems()]
    engine = SimulationEngine(systems=systems)
    graph = pre.to_graph()
    ctx = TickContext(tick=tick)
    engine.run_tick(graph, services, ctx)  # type: ignore[arg-type]
    return WorldState.from_graph(graph, tick=pre.tick + 1)


@pytest.mark.unit
class TestSimplexPipeline:
    """INV-008: every TernaryConsciousness on every entity stays on the simplex."""

    @given(state=worldstate_with_simplex_consciousness_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_simplex_preserved_single_tick(
        self,
        state: WorldState,
        service_container_fixture: object,
    ) -> None:
        """Predicate A: after one tick of the full pipeline, every
        TernaryConsciousness still lies on the simplex."""
        post = _run_one_tick(state, service_container_fixture, tick=state.tick)
        invariant = SimplexPreserved(tolerance=_SIMPLEX_TOL)
        result = invariant.check(state, post)
        assert result.ok, result.msg

    @given(state=worldstate_with_consecutive_ticks_strategy(n_ticks=_TICK_COUNT))
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_simplex_preserved_five_ticks(
        self,
        state: WorldState,
        service_container_fixture: object,
    ) -> None:
        """Predicate B: simplex preserved across 5 consecutive ticks.

        Each tick threads its post-state into the next tick's pre-state.
        Catches incremental drift that escapes the single-tick check.
        """
        invariant = SimplexPreserved(tolerance=_SIMPLEX_TOL)
        current = state
        for tick_idx in range(_TICK_COUNT):
            post = _run_one_tick(current, service_container_fixture, tick=current.tick)
            result = invariant.check(current, post)
            assert result.ok, f"Tick {tick_idx}: {result.msg}"
            current = post

    @given(
        agitation=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
        solidarity=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        edu_pressure=st.floats(min_value=0.0, max_value=0.8, allow_nan=False, allow_infinity=False),
        starting_point=simplex_points(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_route_agitation_preserves_simplex_sum(
        self,
        agitation: float,
        solidarity: float,
        edu_pressure: float,
        starting_point: tuple[float, float, float],
    ) -> None:
        """Predicate C: ``route_agitation_to_ternary`` preserves r + l + f = 1.

        The routing formula sets ``Δl = -(Δr + Δf)`` so the deltas sum to 0
        by construction. Applied to a valid simplex starting point, the
        result still sums to 1 (within float64 tolerance).

        NOTE on per-component bounds: the routing formula CAN drive
        components below 0 (e.g., when Δl is large-negative and l0 is small)
        because the routing is the *generator* of the new simplex point,
        not the *normalizer*. ``normalize_to_simplex`` is the downstream
        clamp. So this test asserts only the sum-preservation invariant.
        """
        defines = ConsciousnessDefines()
        r0, l0, f0 = starting_point
        delta_r, delta_l, delta_f = route_agitation_to_ternary(
            agitation, solidarity, edu_pressure, defines
        )
        # The deltas sum to 0 by formula construction.
        delta_sum = delta_r + delta_l + delta_f
        assert math.isclose(delta_sum, 0.0, abs_tol=_SIMPLEX_TOL), (
            f"Routing deltas sum to {delta_sum:.6e}, expected 0 within {_SIMPLEX_TOL}"
        )
        # Applied to a simplex point, sum is preserved.
        r1, l1, f1 = r0 + delta_r, l0 + delta_l, f0 + delta_f
        total = r1 + l1 + f1
        assert math.isclose(total, 1.0, abs_tol=_SIMPLEX_TOL), (
            f"Post-routing simplex sum = {total:.6e} (start={r0 + l0 + f0:.6e}, "
            f"deltas=({delta_r:.6e}, {delta_l:.6e}, {delta_f:.6e}))"
        )
