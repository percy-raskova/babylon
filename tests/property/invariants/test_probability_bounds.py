"""Property-based tests for the Probability ∈ [0, 1] bound invariant
(INV-006 / spec-054 US1).

See ``specs/054-bound-invariants/contracts/probability_bounds.md`` for the
full predicate specification.

Four predicates implemented as separate test methods on
``TestProbabilityBounds``:

  Predicate A — full-pipeline post-state preservation (T016)
  Predicate B — per-formula domain via type-driven discovery (T017)
  Predicate C — SOLIDARITY edge strength after SolidaritySystem.step (T018)
  Predicate D — graph round-trip preservation (T019, FR-012)
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from babylon.engine.invariants import ProbabilityInRange
from babylon.engine.simulation_engine import SimulationEngine
from babylon.engine.systems.solidarity import SolidaritySystem
from babylon.models.entities.relationship import Relationship
from babylon.models.world_state import WorldState
from tests.property.harness.bound_harness import BoundInvariantHarness
from tests.property.harness.probability_discovery import (
    discover_probability_fields,
    discover_probability_formulas,
)
from tests.property.harness.system_registry import all_systems
from tests.property.strategies.probability_field import (
    worldstate_with_probability_fields_strategy,
)
from tests.property.strategies.worldstate import (
    worldstate_with_solidarity_edges_strategy,
)

# --------------------------------------------------------------------------- #
# Predicate B — per-formula input strategies                                  #
# --------------------------------------------------------------------------- #
#
# Hand-written per-formula input strategies. The discovery walker
# (``discover_probability_formulas``) uses type-driven introspection — adding
# a new ``-> Probability`` formula extends the parametrize set automatically.
# This map provides the input generators each formula needs.
#
# **Drift safety**: when discovery surfaces a formula with no entry here, the
# test fails loudly rather than skipping silently. Adding a new formula
# without registering its inputs is a CI failure, not a coverage gap.

_FORMULA_INPUT_STRATEGIES: dict[str, st.SearchStrategy[dict[str, float]]] = {
    "calculate_acquiescence_probability": st.fixed_dictionaries(
        {
            "wealth": st.floats(
                min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False
            ),
            "subsistence_threshold": st.floats(
                min_value=1e-3, max_value=1e6, allow_nan=False, allow_infinity=False
            ),
            "steepness_k": st.floats(
                min_value=1e-3, max_value=10.0, allow_nan=False, allow_infinity=False
            ),
        }
    ),
    "calculate_revolution_probability": st.fixed_dictionaries(
        {
            "cohesion": st.floats(
                min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
            ),
            "repression": st.floats(
                min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
            ),
        }
    ),
}


def _full_pipeline_runner(graph: object, services: object, ctx: object) -> None:
    """Build a SimulationEngine with all 21 Systems and run one tick.

    Used by Predicate A as the ``BoundInvariantHarness.system`` argument so
    the harness exercises the full materialist-causality pipeline rather
    than any single System.
    """
    systems = [cls() for cls in all_systems()]
    engine = SimulationEngine(systems=systems)
    engine.run_tick(graph, services, ctx)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestProbabilityBounds:
    """INV-006: every Probability-typed value in the post-state stays in [0, 1].

    Default-deny: this test asserts the bound for EVERY discovered field
    pair across the full pipeline. Genuine bugs cause Hypothesis to surface
    a shrunk minimal example naming the offending field, entity, and value.
    """

    @given(state=worldstate_with_probability_fields_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_probability_post_runtick_in_range(
        self,
        state: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate A: after run_tick, every Probability field is in [0, 1].

        Uses the full 21-System pipeline so any System that introduces a
        silent escape from [0, 1] is caught. The discovered field set
        (~71 pairs) is checked exhaustively in a single sweep of the
        post-state.
        """
        invariant = ProbabilityInRange(field_pairs=discover_probability_fields())
        harness = BoundInvariantHarness(
            system=_full_pipeline_runner,
            invariants=[invariant],
        )
        result = harness.run(state, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]
        outcome = result.outcomes[invariant.name]
        assert outcome != "SKIPPED", "Pipeline runner cannot opt out of probability bounds"
        assert outcome.ok, outcome.msg

    @pytest.mark.parametrize(
        "formula",
        discover_probability_formulas(),
        ids=lambda f: f.__name__,
    )
    def test_probability_formula_in_range(self, formula: Callable[..., float]) -> None:
        """Predicate B: every Probability-returning formula stays in [0, 1].

        Type-driven via ``discover_probability_formulas``. Per-formula input
        strategies live in ``_FORMULA_INPUT_STRATEGIES``. Failing loudly on
        a missing-strategy entry is intentional: registering inputs is part
        of narrowing a return type to ``Probability``.
        """
        strategy = _FORMULA_INPUT_STRATEGIES.get(formula.__name__)
        if strategy is None:
            pytest.fail(
                f"Formula {formula.__name__} discovered as Probability-returning "
                f"but no input strategy registered in _FORMULA_INPUT_STRATEGIES. "
                f"Add an entry mapping the formula name to a Hypothesis strategy "
                f"that draws valid inputs."
            )

        @given(args=strategy)
        @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
        def _check(args: dict[str, float]) -> None:
            result = formula(**args)
            assert 0.0 <= result <= 1.0, f"{formula.__name__}({args}) = {result}"

        _check()

    @given(state=worldstate_with_solidarity_edges_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_solidarity_strength_in_range(
        self,
        state: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate C: SOLIDARITY edge strength stays in [0, 1] after step.

        Runs SolidaritySystem in isolation and asserts the
        ``Relationship.solidarity_strength`` field is bounded after the
        consciousness propagation pass.
        """
        invariant = ProbabilityInRange(field_pairs=[(Relationship, "solidarity_strength")])
        harness = BoundInvariantHarness(
            system=SolidaritySystem,
            invariants=[invariant],
        )
        result = harness.run(state, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]
        outcome = result.outcomes[invariant.name]
        if outcome == "SKIPPED":
            pytest.skip(
                f"SolidaritySystem opted out of probability_in_range: "
                f"{result.skip_reasons.get(invariant.name, '<no reason>')}"
            )
        assert outcome.ok, outcome.msg

    @given(state=worldstate_with_probability_fields_strategy())
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_probability_round_trip_preserves_bound(self, state: WorldState) -> None:
        """Predicate D (FR-012): graph round-trip preserves [0, 1] on every
        Probability field.

        Tests that ``WorldState.from_graph(state.to_graph())`` does not
        silently produce out-of-range values via the in-place mutation
        path. ``from_graph`` is expected to either raise ``ValidationError``
        on construction (Pydantic enforces the constraint at the field
        boundary) OR yield a state that satisfies the invariant.
        """
        graph = state.to_graph()
        rehydrated = WorldState.from_graph(graph, tick=state.tick)
        invariant = ProbabilityInRange(field_pairs=discover_probability_fields())
        result = invariant.check(state, rehydrated)
        assert result.ok, result.msg
