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

from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.models.enums import EdgeType, EventType

pytestmark = pytest.mark.unit


def _rupture_events(services: ServiceContainer) -> list[object]:
    return [e for e in services.event_bus.get_history() if e.type == EventType.RUPTURE]


class TestFreshEdgeTension:
    """Per-edge tension is the current wealth-asymmetry gap, not accumulated."""

    def test_exploitation_tension_equals_wealth_asymmetry_gap(self) -> None:
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("worker", wealth=10.0)
        graph.add_node("owner", wealth=30.0)
        graph.add_edge("worker", "owner", edge_type=EdgeType.EXPLOITATION, tension=0.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        # |30 - 10| / (10 + 30) = 0.5, fresh (not the 0.0 it started at).
        assert graph["worker"]["owner"]["tension"] == pytest.approx(0.5)

    def test_tension_is_not_accumulated_across_ticks(self) -> None:
        graph: nx.DiGraph[str] = nx.DiGraph()
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
        graph: nx.DiGraph[str] = nx.DiGraph()
        graph.add_node("tenant", wealth=10.0)
        graph.add_node("land", node_type="territory", rent_level=0.0)
        graph.add_edge("tenant", "land", edge_type=EdgeType.TENANCY, tension=0.0)

        ContradictionSystem().step(graph, ServiceContainer.create(), {"tick": 1})

        assert graph["tenant"]["land"]["tension"] == pytest.approx(0.0)


class TestRegistryStash:
    """The registry snapshot lands on the graph attribute ``opposition_states``."""

    def test_opposition_states_written_to_graph_attr(self) -> None:
        graph: nx.DiGraph[str] = nx.DiGraph()
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
        graph: nx.DiGraph[str] = nx.DiGraph()
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
        graph: nx.DiGraph[str] = nx.DiGraph()
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
        graph: nx.DiGraph[str] = nx.DiGraph()
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
        graph: nx.DiGraph[str] = nx.DiGraph()
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
