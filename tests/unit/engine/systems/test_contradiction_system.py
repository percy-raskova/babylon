"""Unit tests for the Lawverian ContradictionSystem rewire (Phase C1.3).

The rewrite replaces the saturating, add-only edge-``tension`` accumulator
with **fresh-per-tick** scale-free wealth-asymmetry gaps computed off the
:class:`~babylon.dialectics.core.opposition.OppositionRegistry`. These tests
pin the new contract:

- per-edge ``tension`` is the current wealth-asymmetry gap, recomputed each
  tick (idempotent under a static graph — NOT accumulated);
- the registry snapshot is stashed on the graph attribute
  ``opposition_states`` (the cross-tick + consumer handoff channel — the
  bridged runner recreates ``TickContext`` each tick so ``persistent_data``
  is not a cross-tick channel there);
- ``contradiction_frames`` is derived from the registry (intensity ← gap,
  aspect_balance ← rate, principal_aspect ← leading_pole);
- RUPTURE fires on principal-gap > threshold AND rising (rate > 0), never on
  hitting a ceiling, never on a static or falling gap.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.dialectics.core.coupling import StanceIntervention
from babylon.engine.graph import BabylonGraph
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import (
    OPPOSITION_INTERVENTIONS_ATTR,
    ContradictionSystem,
)
from babylon.models.enums import EdgeType, EventType

pytestmark = pytest.mark.unit


def _rupture_events(services: ServiceContainer) -> list[object]:
    return [e for e in services.event_bus.get_history() if e.type == EventType.RUPTURE]


class TestFreshEdgeTension:
    """Per-edge tension is the current wealth-asymmetry gap, not accumulated."""

    def test_exploitation_tension_equals_wealth_asymmetry_gap(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION, tension=0.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        # |30 - 10| / (10 + 30) = 0.5, fresh (not the 0.0 it started at).
        assert graph["worker"]["owner"]["tension"] == pytest.approx(0.5)

    def test_tension_is_not_accumulated_across_ticks(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION, tension=0.0)
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})
        first = graph["worker"]["owner"]["tension"]
        system.step(graph, services, {"tick": 2})
        second = graph["worker"]["owner"]["tension"]

        # Static graph -> identical gap both ticks (no add-only accumulation).
        assert first == pytest.approx(0.5)
        assert second == pytest.approx(0.5)

    def test_tenancy_rent_free_guard_gives_zero_tension(self) -> None:
        graph = BabylonGraph()
        graph.add_node("tenant", wealth=10.0)
        graph.add_node("land", node_type="territory", rent_level=0.0)
        graph.add_edge("tenant", "land", edge_type=EdgeType.TENANCY, tension=0.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph["tenant"]["land"]["tension"] == pytest.approx(0.0)


class TestRegistryStash:
    """The registry snapshot lands on the graph attribute ``opposition_states``."""

    def test_opposition_states_written_to_graph_attr(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 3})

        states = graph.graph["opposition_states"]
        assert set(states) == {"capital_labor", "wage", "tenancy", "atomization", "imperial"}
        assert states["capital_labor"]["gap"] == pytest.approx(0.5)
        assert states["capital_labor"]["tick"] == 3
        # capital_labor is the only non-zero gap -> it is the principal.
        assert states["capital_labor"]["is_principal"] is True

    def test_rate_carried_across_ticks_via_graph_attr(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        services = ServiceContainer.create()
        system = ContradictionSystem()

        system.step(graph, services, {"tick": 1})
        assert graph.graph["opposition_states"]["capital_labor"]["rate"] == pytest.approx(0.0)

        # Widen the gap: owner richer -> gap rises -> rate > 0.
        graph.nodes["owner"]["wealth"] = 90.0
        system.step(graph, services, {"tick": 2})
        cap = graph.graph["opposition_states"]["capital_labor"]
        assert cap["gap"] == pytest.approx(80.0 / 100.0)  # |90-10|/100 = 0.8
        assert cap["rate"] == pytest.approx(0.8 - 0.5)  # rose by 0.3


class TestContradictionFrames:
    """``contradiction_frames`` is derived from the registry states."""

    def test_frame_principal_maps_gap_rate_pole(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        frame = graph.graph["contradiction_frames"]["global"]
        principal = frame["principal"]
        assert principal["id"] == "capital_labor"
        assert principal["intensity"] == pytest.approx(0.5)  # intensity <- gap
        assert principal["aspect_balance"] == pytest.approx(0.0)  # aspect_balance <- rate (tick 1)
        assert principal["principal_aspect"] in ("a", "b")  # principal_aspect <- leading_pole


class TestRuptureGate:
    """RUPTURE = condition AND level: gap > threshold AND rate > 0."""

    def _extreme_graph(self, owner_wealth: float) -> nx.DiGraph[str]:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=1.0)
        graph.add_node("owner", wealth=owner_wealth)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        return graph

    def test_no_rupture_on_static_extreme_gap(self) -> None:
        # gap = 99/101 ~ 0.98 > 0.9 threshold, but rate = 0 (static) -> no rupture.
        graph = self._extreme_graph(100.0)
        services = ServiceContainer.create()
        system = ContradictionSystem()
        system.step(graph, services, {"tick": 1})
        system.step(graph, services, {"tick": 2})
        assert _rupture_events(services) == []

    def test_rupture_fires_when_gap_high_and_rising(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._extreme_graph(50.0)  # gap = 49/51 ~ 0.96 (rate 0 on tick 1)
        system.step(graph, services, {"tick": 1})
        assert _rupture_events(services) == []  # rising gate not yet satisfied

        graph.nodes["owner"]["wealth"] = 200.0  # gap = 199/201 ~ 0.99, rate > 0
        system.step(graph, services, {"tick": 2})
        ruptures = _rupture_events(services)
        assert len(ruptures) == 1
        assert ruptures[0].payload["opposition"] == "capital_labor"
        assert ruptures[0].payload["gap"] > 0.9
        assert ruptures[0].payload["rate"] > 0.0

    def test_no_rupture_when_gap_high_but_falling(self) -> None:
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = self._extreme_graph(200.0)  # gap ~ 0.99
        system.step(graph, services, {"tick": 1})
        graph.nodes["owner"]["wealth"] = 100.0  # gap ~ 0.98, falling -> rate < 0
        system.step(graph, services, {"tick": 2})
        assert _rupture_events(services) == []

    def test_no_rupture_when_gap_low_but_rising(self) -> None:
        # The LEVEL half of the gate: rate > 0 alone must never fire —
        # quantity has not yet accumulated to the threshold (I.7).
        # Kills the mutant that deletes `gap > threshold` from _maybe_rupture.
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=12.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        system.step(graph, services, {"tick": 1})
        graph.nodes["owner"]["wealth"] = 14.0  # gap 0.09 -> 0.17: rising, far below 0.9
        system.step(graph, services, {"tick": 2})
        cap = graph.graph["opposition_states"]["capital_labor"]
        assert cap["rate"] > 0.0  # the rising precondition really holds
        assert cap["gap"] < float(services.defines.tension.rupture_gap_threshold)
        assert _rupture_events(services) == []


class TestStanceInterventions:
    """``opposition_interventions`` attr: applied post-step, consumed once."""

    def _labor_dominant_graph(self) -> nx.DiGraph[str]:
        # Worker richer than owner -> capital_labor balance < 0 -> leading_pole "a".
        graph = BabylonGraph()
        graph.add_node("worker", wealth=30.0)
        graph.add_node("owner", wealth=10.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        return graph

    def _dump(self, delta: float) -> dict[str, object]:
        return StanceIntervention(
            target_key="capital_labor", delta_balance=delta, source="test"
        ).model_dump()

    def test_no_intervention_leaves_the_natural_measure(self) -> None:
        graph = self._labor_dominant_graph()
        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "a"

    def test_intervention_flips_leading_pole_through_the_system(self) -> None:
        graph = self._labor_dominant_graph()
        graph.graph[OPPOSITION_INTERVENTIONS_ATTR] = [self._dump(1.0)]

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        cap = graph.graph["opposition_states"]["capital_labor"]
        assert cap["leading_pole"] == "b"  # flipped from "a" by the +1.0 shove
        assert cap["balance"] == pytest.approx(0.5)  # clamp(-0.5 + 1.0)

    def test_interventions_are_consumed_once(self) -> None:
        graph = self._labor_dominant_graph()
        services = ServiceContainer.create()
        system = ContradictionSystem()
        graph.graph[OPPOSITION_INTERVENTIONS_ATTR] = [self._dump(1.0)]

        system.step(graph, services, {"tick": 1})
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "b"
        assert graph.graph[OPPOSITION_INTERVENTIONS_ATTR] == []  # cleared after use

        # Tick 2 with no fresh interventions: fresh measure only, NOT re-applied.
        system.step(graph, services, {"tick": 2})
        assert graph.graph["opposition_states"]["capital_labor"]["leading_pole"] == "a"


class TestWageValuePairsExtraction:
    """`_build_graph_inputs` lifts (w_paid, v_produced) off paid class nodes (D4)."""

    @staticmethod
    def _inputs(graph: nx.DiGraph[str]):  # type: ignore[no-untyped-def]

        return ContradictionSystem()._build_graph_inputs(graph)

    def test_pairs_extracted_from_nodes_carrying_both_attrs(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0, v_produced=5.0)
        graph.add_node("c2", w_paid=3.0, v_produced=4.0)
        pairs = self._inputs(graph).wage_value_pairs
        assert set(pairs) == {(6.0, 5.0), (3.0, 4.0)}

    def test_node_missing_v_produced_is_skipped(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0)  # no v_produced
        assert self._inputs(graph).wage_value_pairs == ()

    def test_inactive_node_skipped(self) -> None:
        graph = BabylonGraph()
        graph.add_node("c1", w_paid=6.0, v_produced=5.0, active=False)
        assert self._inputs(graph).wage_value_pairs == ()

    def test_no_pairs_when_no_accounting_attrs(self) -> None:
        graph = BabylonGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION)
        assert self._inputs(graph).wage_value_pairs == ()
