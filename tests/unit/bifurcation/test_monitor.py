"""Tests for BifurcationMonitor (T032, Phase 10, Feature 033).

Validates that BifurcationMonitor:
- Records bifurcation snapshots per tick
- Emits BifurcationTendencyEvent on tendency change
- Integrates with CommunityStateStore protocol
"""

from __future__ import annotations

import pytest
import xgi
from tests.unit.bifurcation.conftest import (
    build_test_hypergraph,
    make_community_state,
)

from babylon.bifurcation.types import BifurcationSnapshot
from babylon.config.defines import BifurcationDefines
from babylon.engine.bifurcation_monitor import BifurcationMonitor
from babylon.engine.community_state_store import InMemoryCommunityStateStore
from babylon.models.entities.community import CommunityState
from babylon.models.enums import CommunityType, ConsciousnessTendency, EdgeType, EventType
from babylon.models.events import BifurcationTendencyEvent

pytestmark = pytest.mark.topology


def _build_monitor_graph(
    agent_communities: dict[str, set[CommunityType]],
    edges: list[tuple[str, str, EdgeType, float]],
) -> dict[str, object]:
    """Build graph data dict for monitor tests.

    Returns:
        Dict with 'agents', 'edges' keys suitable for building a test graph.
    """
    import networkx as nx
    from tests.unit.bifurcation.conftest import assign_communities_to_graph

    graph: nx.DiGraph = nx.DiGraph()  # type: ignore[type-arg]
    for agent_id in agent_communities:
        graph.add_node(agent_id, _node_type="social_class", wealth=50.0)
    for src, tgt, edge_type, strength in edges:
        graph.add_edge(src, tgt, edge_type=edge_type, solidarity_strength=strength, weight=1.0)
    assign_communities_to_graph(graph, agent_communities)
    return {"graph": graph, "agent_communities": agent_communities}


class TestBifurcationMonitorRecording:
    """BifurcationMonitor records BifurcationSnapshot per analysis."""

    def test_record_produces_snapshot(self) -> None:
        """Single analysis call produces one BifurcationSnapshot."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.5),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.5),
        ]

        store = InMemoryCommunityStateStore(states)
        monitor = BifurcationMonitor(community_state_store=store)

        data = _build_monitor_graph(agents, edges)
        H = build_test_hypergraph(agents, states)

        monitor.record_bifurcation(
            graph=data["graph"],
            H=H,
            agent_memberships=agents,
            tick=0,
        )

        assert len(monitor.bifurcation_history) == 1
        snapshot = monitor.bifurcation_history[0]
        assert isinstance(snapshot, BifurcationSnapshot)
        assert snapshot.tick == 0

    def test_multiple_recordings(self) -> None:
        """Multiple calls accumulate snapshots."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.5),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.5),
        ]

        store = InMemoryCommunityStateStore(states)
        monitor = BifurcationMonitor(community_state_store=store)

        data = _build_monitor_graph(agents, edges)
        H = build_test_hypergraph(agents, states)

        for tick in range(3):
            monitor.record_bifurcation(
                graph=data["graph"],
                H=H,
                agent_memberships=agents,
                tick=tick,
            )

        assert len(monitor.bifurcation_history) == 3
        assert monitor.bifurcation_history[0].tick == 0
        assert monitor.bifurcation_history[2].tick == 2


class TestBifurcationMonitorEvents:
    """BifurcationMonitor emits events on tendency change."""

    def test_no_event_on_first_recording(self) -> None:
        """First recording has no previous tendency — no event."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.5),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.5),
        ]

        store = InMemoryCommunityStateStore(states)
        monitor = BifurcationMonitor(community_state_store=store)

        data = _build_monitor_graph(agents, edges)
        H = build_test_hypergraph(agents, states)

        monitor.record_bifurcation(
            graph=data["graph"],
            H=H,
            agent_memberships=agents,
            tick=0,
        )

        events = monitor.get_pending_events()
        assert len(events) == 0

    def test_no_event_when_tendency_unchanged(self) -> None:
        """Same tendency across ticks → no event."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        # Low CI → fascist both ticks
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.1),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.1),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        store = InMemoryCommunityStateStore(states)
        monitor = BifurcationMonitor(community_state_store=store)

        data = _build_monitor_graph(agents, edges)
        H = build_test_hypergraph(agents, states)

        for tick in range(3):
            monitor.record_bifurcation(
                graph=data["graph"],
                H=H,
                agent_memberships=agents,
                tick=tick,
            )

        events = monitor.get_pending_events()
        assert len(events) == 0

    def test_event_emitted_on_tendency_change(self) -> None:
        """Tendency change emits BifurcationTendencyEvent."""
        agents_fascist = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        # First tick: fascist (low CI + solidarity edges)
        states_low = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.1),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.1),
        }
        edges_solidarity: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        store = InMemoryCommunityStateStore(states_low)
        monitor = BifurcationMonitor(community_state_store=store)

        data = _build_monitor_graph(agents_fascist, edges_solidarity)
        H_low = build_test_hypergraph(agents_fascist, states_low)

        # Tick 0: fascist
        monitor.record_bifurcation(
            graph=data["graph"],
            H=H_low,
            agent_memberships=agents_fascist,
            tick=0,
        )

        # Now change to revolutionary scenario: high CI + intersectional
        agents_rev = {
            "settler_1": {CommunityType.SETTLER, CommunityType.DISABLED},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states_high = {
            CommunityType.NEW_AFRIKAN: make_community_state(
                CommunityType.NEW_AFRIKAN,
                ci=0.8,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
            CommunityType.SETTLER: make_community_state(
                CommunityType.SETTLER,
                ci=0.8,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
            CommunityType.DISABLED: make_community_state(
                CommunityType.DISABLED,
                ci=0.8,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
        }
        # Update store
        store._states.clear()
        store._states.update(states_high)

        data_rev = _build_monitor_graph(agents_rev, edges_solidarity)
        H_high = build_test_hypergraph(agents_rev, states_high)

        # Tick 1: revolutionary (high CI + intersectional marginalized)
        monitor.record_bifurcation(
            graph=data_rev["graph"],
            H=H_high,
            agent_memberships=agents_rev,
            tick=1,
        )

        events = monitor.get_pending_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, BifurcationTendencyEvent)
        assert event.event_type == EventType.BIFURCATION_TENDENCY_CHANGE
        assert event.previous_tendency == "fascist"
        assert event.new_tendency == "revolutionary"

    def test_get_pending_events_clears(self) -> None:
        """get_pending_events clears the list after return."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.1),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.1),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        store = InMemoryCommunityStateStore(states)
        monitor = BifurcationMonitor(community_state_store=store)

        data = _build_monitor_graph(agents, edges)
        H = build_test_hypergraph(agents, states)

        monitor.record_bifurcation(
            graph=data["graph"],
            H=H,
            agent_memberships=agents,
            tick=0,
        )

        # Now change to indeterminate
        store._states.clear()

        import networkx as nx

        empty_graph: nx.DiGraph = nx.DiGraph()  # type: ignore[type-arg]
        empty_H: xgi.Hypergraph = xgi.Hypergraph()
        empty_memberships: dict[str, set[CommunityType]] = {}

        monitor.record_bifurcation(
            graph=empty_graph,
            H=empty_H,
            agent_memberships=empty_memberships,
            tick=1,
        )

        # First call gets events (and clears internal list)
        monitor.get_pending_events()
        # Second call should be empty
        events2 = monitor.get_pending_events()
        assert len(events2) == 0


class TestBifurcationMonitorDefinesInjection:
    """BifurcationMonitor accepts optional BifurcationDefines."""

    def test_custom_defines(self) -> None:
        """Monitor uses provided BifurcationDefines."""
        defines = BifurcationDefines(indeterminate_dead_zone=0.5)
        states: dict[CommunityType, CommunityState] = {}
        store = InMemoryCommunityStateStore(states)
        monitor = BifurcationMonitor(
            community_state_store=store,
            defines=defines,
        )
        assert monitor._defines.indeterminate_dead_zone == 0.5
