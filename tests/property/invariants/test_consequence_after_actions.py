"""Property-based tests for the Consequence-after-OODA-actions causal
invariant (INV-014 / spec-056 US2).

See ``specs/056-causal-invariants/contracts/consequence_after_actions.md``
for the full predicate specification. Encodes Constitution I.17 OODA
(organizations deliberate against a fixed material snapshot, not against
mid-loop consequences) and III.7 Determinism (replay requires
order-independence over the organization set).

Three predicates:

  AS1 — Every Consequence System call timestamp > max OODA action timestamp (T018)
  AS2 — Deliberate interleaving (Consequence fires mid-OODA-loop) is caught (T019)
  AS3 — Reversed per-org iteration order produces equivalent post-state (T020)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import (
    _DEFAULT_SYSTEMS,
    CONSEQUENCE_SYSTEMS,
    SimulationEngine,
)
from babylon.engine.systems import ooda as ooda_module
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.ooda import OODASystem
from babylon.models.world_state import (
    SOCIAL_CLASS_COMPUTED_FIELDS,
    TERRITORY_EXCLUDED_FIELDS,
    WorldState,
)
from babylon.topology.graph import BabylonGraph
from tests.property.harness.causal_harness import (
    OrganizationActionSpy,
    SystemCallSpy,
)
from tests.property.strategies.worldstate import worldstate_strategy


def _build_default_engine() -> SimulationEngine:
    """Engine with the canonical _DEFAULT_SYSTEMS (causality order)."""
    return SimulationEngine(systems=[type(s)() for s in _DEFAULT_SYSTEMS])


def _build_exclude_paths() -> dict:
    """Spec 055 exclude rules for AS3 model_dump comparison."""
    return {
        "tick": True,
        "entities": {"__all__": set(SOCIAL_CLASS_COMPUTED_FIELDS)},
        "territories": {"__all__": set(TERRITORY_EXCLUDED_FIELDS)},
    }


@pytest.mark.unit
class TestConsequenceAfterActions:
    """INV-014: every Consequence System call_index > max OODA action timestamp."""

    @given(state=worldstate_strategy(min_entities=2))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_consequences_after_all_org_actions(
        self,
        state: WorldState,
    ) -> None:
        """AS1: every Consequence System invocation postdates every
        per-organization action resolved this tick.

        Note: with no organization nodes in the random WorldState,
        the per-org spy may record zero events — in that case the
        predicate is vacuously satisfied.
        """
        services = ServiceContainer.create()
        ctx = TickContext(tick=state.tick)
        engine = _build_default_engine()

        with SystemCallSpy(engine) as sys_spy, OrganizationActionSpy() as org_spy:
            engine.run_tick(state.to_graph(), services, ctx)

        consequence_names = {cls.__name__ for cls in CONSEQUENCE_SYSTEMS}
        consequence_events = [e for e in sys_spy.events if e.system_class_name in consequence_names]

        if not org_spy.events:
            return  # vacuous — no organizations resolved this tick

        max_org_ts = max(e.monotonic_timestamp_ns for e in org_spy.events)
        for cs_event in consequence_events:
            assert cs_event.monotonic_timestamp_ns > max_org_ts, (
                f"Consequence System {cs_event.system_class_name} fired at "
                f"timestamp {cs_event.monotonic_timestamp_ns} but the latest "
                f"per-org action completed at {max_org_ts} — interleaving "
                f"detected (INV-014)"
            )

    def test_deliberate_interleaving_caught(self) -> None:
        """AS2: monkey-patch _resolve_for_organization to fire
        ContradictionSystem.step in the middle of the per-org loop.
        Confirm the predicate from AS1 catches the interleaving.

        Hand-built scenario: graph with 2 organization nodes (added
        directly per the existing OODA test pattern), the patched
        method invokes ContradictionSystem.step() AFTER the first
        per-org call only (so the second per-org timestamp postdates
        the Consequence-System timestamp — exactly the AS1 violation
        pattern). Negative test, no Hypothesis.
        """

        from babylon.models.enums import OrgType

        services = ServiceContainer.create()
        ctx = TickContext(tick=0)
        engine = _build_default_engine()

        # Build a 2-org graph directly (mirrors tests/unit/ooda/test_ooda_system.py
        # pattern — organization nodes are added to the graph with attributes,
        # not constructed via the Organization Pydantic model).
        graph = BabylonGraph()
        for i in range(2):
            graph.add_node(
                f"org_{i}",
                _node_type="organization",
                org_type=OrgType.POLITICAL_FACTION.value,
                territory_ids=[],
                consciousness_tendency="revolutionary",
                ooda_profile={"action_points": 2, "decision_mode": "autocratic"},
            )

        # Find the engine's existing ContradictionSystem instance (so the
        # SystemCallSpy sees the injected mid-loop call — a freshly-
        # constructed ContradictionSystem() would be invisible to the
        # spy because the spy wraps engine._systems, not arbitrary
        # System instances).
        contradiction_instance = next(
            s for s in engine._systems if isinstance(s, ContradictionSystem)
        )

        # For this AS2 negative test, instrument the per-org calls
        # inline (rather than via OrganizationActionSpy) so we control
        # the patch ordering precisely. We capture per-org timestamps
        # AND inject the mid-loop Consequence call from the same wrapper.
        import time

        original = OODASystem._resolve_for_organization
        per_org_timestamps: list[int] = []
        call_count = {"n": 0}

        def interleaving_wrapper(self_, *args, **kwargs):
            per_org_timestamps.append(time.monotonic_ns())
            result = original(self_, *args, **kwargs)
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Fire the engine's own ContradictionSystem mid-loop
                # (the bug being simulated). The SystemCallSpy IS wrapping
                # this instance's step method, so the call is recorded
                # in sys_spy.events with a mid-loop timestamp.
                contradiction_instance.step(graph, services, ctx)
            return result

        with (
            SystemCallSpy(engine) as sys_spy,
            patch.object(OODASystem, "_resolve_for_organization", interleaving_wrapper),
        ):
            engine.run_tick(graph, services, ctx)

        # The bug: ContradictionSystem fired between first and second
        # per-org calls — confirm the spy timestamps capture this.
        consequence_names = {cls.__name__ for cls in CONSEQUENCE_SYSTEMS}
        contradiction_events = [
            e for e in sys_spy.events if e.system_class_name == "ContradictionSystem"
        ]
        # ContradictionSystem fires twice: once mid-OODA-loop (the bug),
        # once at its natural position (post-OODA, late in pipeline).
        assert len(contradiction_events) >= 2, (
            f"Expected ContradictionSystem to fire at least twice (mid-loop "
            f"injection + natural pipeline position); got "
            f"{len(contradiction_events)} events"
        )
        assert len(per_org_timestamps) >= 2, (
            f"Expected at least 2 per-org calls, got {len(per_org_timestamps)} — "
            f"check the graph construction"
        )

        min_org_ts = min(per_org_timestamps)
        max_org_ts = max(per_org_timestamps)
        interleaved = [
            e for e in contradiction_events if min_org_ts < e.monotonic_timestamp_ns < max_org_ts
        ]
        assert interleaved, (
            "Deliberate interleaving wrapper failed to inject a "
            "Consequence-System call between per-org timestamps — the "
            "negative test is broken (assert that the AS1 predicate is "
            "machine-falsifiable)"
        )

        # Sanity: at least one consequence System (besides the mid-loop
        # injection) fires AFTER all per-org calls — that's the canonical
        # post-OODA pipeline position.
        post_loop_consequences = [
            e
            for e in sys_spy.events
            if e.system_class_name in consequence_names and e.monotonic_timestamp_ns > max_org_ts
        ]
        assert post_loop_consequences, (
            "Pipeline did not produce any Consequence-System calls after "
            "the OODA loop completed — pipeline broken?"
        )

    @given(state=worldstate_strategy(min_entities=2))
    @settings(
        max_examples=20,
        deadline=3000,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_org_iteration_order_does_not_affect_post_state(
        self,
        state: WorldState,
    ) -> None:
        """AS3: post-tick state is independent of per-organization
        iteration order inside OODASystem.

        Two runs of the same starting state with opposite per-org
        orderings (via patching ``_collect_org_nodes`` to reverse the
        list). If the post-states differ, OODA's per-org work has a
        non-commutative side effect that breaks replay.
        """
        # Run 1: natural OODA order
        engine_a = _build_default_engine()
        services_a = ServiceContainer.create()
        ctx_a = TickContext(tick=state.tick)
        graph_a = state.to_graph()
        engine_a.run_tick(graph_a, services_a, ctx_a)
        post_a = WorldState.from_graph(graph_a, tick=state.tick)

        # Run 2: reversed OODA order via patching _collect_org_nodes
        original_collect = ooda_module._collect_org_nodes

        def reversed_collect(graph):
            return list(reversed(original_collect(graph)))

        engine_b = _build_default_engine()
        services_b = ServiceContainer.create()
        ctx_b = TickContext(tick=state.tick)
        graph_b = state.to_graph()
        with patch.object(ooda_module, "_collect_org_nodes", reversed_collect):
            engine_b.run_tick(graph_b, services_b, ctx_b)
        post_b = WorldState.from_graph(graph_b, tick=state.tick)

        exclude = _build_exclude_paths()
        dump_a = post_a.model_dump(exclude=exclude)
        dump_b = post_b.model_dump(exclude=exclude)

        for dump in (dump_a, dump_b):
            if "relationships" in dump and isinstance(dump["relationships"], list):
                dump["relationships"] = sorted(
                    dump["relationships"],
                    key=lambda r: (
                        r.get("source_id", ""),
                        r.get("target_id", ""),
                        str(r.get("edge_type", "")),
                    ),
                )

        assert dump_a == dump_b, (
            "Per-organization iteration order affects post-tick state — "
            "OODA has a non-commutative side effect over the org set "
            "(INV-014 AS3 violation)"
        )
