"""Property-based tests for the Material Base ordering causal invariant
(INV-013 / spec-056 US1).

See ``specs/056-causal-invariants/contracts/material_base_ordering.md`` for
the full predicate specification. Encodes ADR032 Materialist Causality
(Material Base before Action Phase) and Constitution I.18
(Material-Ideological Distinction) — organizations must observe a
fully-resolved material state before deliberating.

Four predicates:

  AS1 — Every Material Base System runs before any Action Phase System (T014)
  AS2 — Permuted system list catches inversion (T015)
  AS3 — OODASystem invoked exactly once per tick (T016)
  FR-012 — Spy non-interference: spied tick == unspied tick (T017)
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.engine.simulation_engine import (
    _DEFAULT_SYSTEMS,
    ACTION_PHASE_SYSTEMS,
    MATERIAL_BASE_SYSTEMS,
    SimulationEngine,
)
from babylon.engine.systems.ooda import OODASystem
from babylon.engine.systems.vitality import VitalitySystem
from babylon.models.world_state import (
    SOCIAL_CLASS_COMPUTED_FIELDS,
    TERRITORY_EXCLUDED_FIELDS,
    WorldState,
)
from tests.property.harness.causal_harness import SystemCallSpy
from tests.property.strategies.worldstate import worldstate_strategy


def _build_default_engine() -> SimulationEngine:
    """Construct a SimulationEngine with the canonical default System list
    (from ``_DEFAULT_SYSTEMS`` — preserves the materialist causality
    ordering, unlike ``all_systems()`` which returns filesystem-discovery
    order)."""
    return SimulationEngine(systems=[type(s)() for s in _DEFAULT_SYSTEMS])


def _build_exclude_paths() -> dict:
    """Spec 055 exclude rules for FR-012 spy non-interference comparison."""
    return {
        "tick": True,
        "entities": {"__all__": set(SOCIAL_CLASS_COMPUTED_FIELDS)},
        "territories": {"__all__": set(TERRITORY_EXCLUDED_FIELDS)},
    }


@pytest.mark.unit
class TestMaterialBaseOrdering:
    """INV-013: every Material Base System call_index < every Action Phase call_index."""

    @given(state=worldstate_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_material_base_runs_before_action_phase(
        self,
        state: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """AS1: every Material Base System invoked this tick precedes every
        Action Phase System invoked this tick."""
        engine = _build_default_engine()
        with SystemCallSpy(engine) as spy:
            engine.run_tick(state.to_graph(), service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]

        material_names = {cls.__name__ for cls in MATERIAL_BASE_SYSTEMS}
        action_names = {cls.__name__ for cls in ACTION_PHASE_SYSTEMS}
        material_indices = [
            event.call_index for event in spy.events if event.system_class_name in material_names
        ]
        action_indices = [
            event.call_index for event in spy.events if event.system_class_name in action_names
        ]

        if material_indices and action_indices:
            assert max(material_indices) < min(action_indices), (
                f"Material Base System ran AFTER Action Phase System. "
                f"Material max={max(material_indices)}, Action min={min(action_indices)}. "
                f"Material indices: {material_indices}; Action indices: {action_indices}."
            )

    def test_permuted_system_list_catches_inversion(
        self,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """AS2: an engine with OODA moved BEFORE Material Base Systems
        is detected by the spy. Negative test."""
        # Hand-build a system list with OODA at position 0
        permuted_systems = [OODASystem(), VitalitySystem()]
        engine = SimulationEngine(systems=permuted_systems)

        state = WorldState(tick=0)
        with SystemCallSpy(engine) as spy:
            engine.run_tick(state.to_graph(), service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]

        material_names = {cls.__name__ for cls in MATERIAL_BASE_SYSTEMS}
        action_names = {cls.__name__ for cls in ACTION_PHASE_SYSTEMS}
        material_indices = [
            event.call_index for event in spy.events if event.system_class_name in material_names
        ]
        action_indices = [
            event.call_index for event in spy.events if event.system_class_name in action_names
        ]

        # Confirm the spy observed the inversion: action precedes material
        assert action_indices and material_indices
        assert max(material_indices) > min(action_indices), (
            "Spy failed to detect deliberate inversion — the negative test "
            "is broken, which means real inversions might also slip through."
        )

    @given(state=worldstate_strategy())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_ooda_invoked_exactly_once_per_tick(
        self,
        state: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """AS3: OODASystem invoked exactly once per tick."""
        engine = _build_default_engine()
        with SystemCallSpy(engine) as spy:
            engine.run_tick(state.to_graph(), service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]

        ooda_count = sum(1 for event in spy.events if event.system_class_name == "OODASystem")
        assert ooda_count == 1, (
            f"OODASystem invoked {ooda_count} times this tick; expected exactly 1"
        )

    @given(state=worldstate_strategy())
    @settings(
        max_examples=20,
        deadline=2000,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_spy_does_not_alter_post_state(
        self,
        state: WorldState,
    ) -> None:
        """FR-012: spied tick produces identical post-state as unspied tick.

        Runs the same starting state through ``run_tick`` twice — once
        with ``SystemCallSpy`` active, once without — and asserts both
        post-tick WorldStates ``model_dump``-equal under Spec 055 exclude
        rules. Without this guarantee, the spy itself could be the bug
        it's trying to catch.

        Each run uses a FRESH ``ServiceContainer`` + ``TickContext`` to
        avoid cross-run state contamination via mutated event bus,
        metrics dict, or persistent_data — those mutations are real
        engine behavior, not spy interference.
        """
        from babylon.engine.context import TickContext
        from babylon.engine.services import ServiceContainer

        # Run 1: unspied baseline
        engine_a = _build_default_engine()
        services_a = ServiceContainer.create()
        ctx_a = TickContext(tick=state.tick)
        graph_a = state.to_graph()
        engine_a.run_tick(graph_a, services_a, ctx_a)
        baseline_state = WorldState.from_graph(graph_a, tick=state.tick)

        # Run 2: spied — fresh services + context for clean comparison
        engine_b = _build_default_engine()
        services_b = ServiceContainer.create()
        ctx_b = TickContext(tick=state.tick)
        graph_b = state.to_graph()
        with SystemCallSpy(engine_b):
            engine_b.run_tick(graph_b, services_b, ctx_b)
        spied_state = WorldState.from_graph(graph_b, tick=state.tick)

        exclude = _build_exclude_paths()
        baseline_dump = baseline_state.model_dump(exclude=exclude)
        spied_dump = spied_state.model_dump(exclude=exclude)

        # Normalize relationships ordering (per Spec 055 round-trip pattern)
        for dump in (baseline_dump, spied_dump):
            if "relationships" in dump and isinstance(dump["relationships"], list):
                dump["relationships"] = sorted(
                    dump["relationships"],
                    key=lambda r: (
                        r.get("source_id", ""),
                        r.get("target_id", ""),
                        str(r.get("edge_type", "")),
                    ),
                )

        assert spied_dump == baseline_dump, (
            "SystemCallSpy altered the post-tick state — non-interference violated (FR-012)"
        )
