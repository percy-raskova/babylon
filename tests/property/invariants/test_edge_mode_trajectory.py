"""Property-based tests for the edge-mode trajectory legality bound invariant
(INV-009 / spec-055 US1).

See ``specs/055-topology-invariants/contracts/edge_mode_trajectory.md`` for
the full predicate specification.

Three predicates implemented across two test methods + four file-local
helpers (T013):

  Predicate A — synthesized trajectory across N evidence events (T014)
  Predicate B — observed end-to-end trajectory via SimulationEngine (T015)
  Predicate C — final mode is a legal ``EdgeMode`` enum value
                (operationalized inside every read helper via
                ``EdgeMode(value)`` construction, T013)
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.engine.simulation_engine import SimulationEngine
from babylon.engine.systems.edge_transition import (
    _VALID_TRANSITIONS,
    EdgeTransitionSystem,
)
from babylon.models.enums import EdgeMode
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph
from tests.property.harness.system_registry import all_systems
from tests.property.strategies.edge_mode_evidence import edge_mode_trajectory_strategy
from tests.property.strategies.worldstate import worldstate_strategy

# --------------------------------------------------------------------------- #
# T013 — file-local helpers                                                   #
# --------------------------------------------------------------------------- #
# All four helpers construct ``EdgeMode(value)`` so Predicate C (final mode is
# a legal enum value) is operationalized at every read site rather than as a
# separate test. Malformed string values raise ``ValueError`` immediately.


def _build_two_node_graph(starting_mode: EdgeMode) -> BabylonGraph:
    """Build a 2-node graph with one edge carrying the starting edge_mode."""
    graph = BabylonGraph()
    graph.add_node(
        "src",
        _node_type="social_class",
        contradiction_fields={},
        field_derivatives={},
        wealth=100.0,
    )
    graph.add_node(
        "tgt",
        _node_type="social_class",
        contradiction_fields={},
        field_derivatives={},
        wealth=100.0,
    )
    graph.add_edge(
        "src",
        "tgt",
        edge_type="exploitation",
        edge_mode=starting_mode.value,
    )
    return graph


def _apply_event_to_graph(graph: BabylonGraph, event: dict[str, Any]) -> None:
    """Write the event into the appropriate node's contradiction_fields/field_derivatives."""
    node_id = "src" if event["scope"] == "source" else "tgt"
    field = event["field"]
    metric = event["metric"]
    value = event["value"]
    node_attrs = graph.nodes[node_id]
    if metric == "value":
        cf = dict(node_attrs.get("contradiction_fields", {}))
        cf[field] = value
        node_attrs["contradiction_fields"] = cf
    else:
        fd = dict(node_attrs.get("field_derivatives", {}))
        fd_field = dict(fd.get(field, {}))
        fd_field[metric] = value
        fd[field] = fd_field
        node_attrs["field_derivatives"] = fd


def _read_edge_mode(graph: BabylonGraph) -> EdgeMode:
    """Read the single edge's edge_mode attribute and construct EdgeMode(value)."""
    edges = list(graph.edges(data=True))
    if not edges:
        raise AssertionError("Test graph has no edges")
    _src, _tgt, data = edges[0]
    raw = data["edge_mode"]
    return EdgeMode(raw)  # raises ValueError on malformed input — Predicate C


def _capture_edge_modes(
    graph: BabylonGraph,
) -> dict[tuple[str, str, str], EdgeMode]:
    """Return {(source, target, edge_type): EdgeMode} for every edge with edge_mode."""
    out: dict[tuple[str, str, str], EdgeMode] = {}
    for src, tgt, data in graph.edges(data=True):
        raw = data.get("edge_mode")
        if raw is None:
            continue
        edge_type = str(data.get("edge_type", "unknown"))
        out[(src, tgt, edge_type)] = EdgeMode(raw)  # Predicate C check
    return out


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestEdgeModeTrajectory:
    """INV-009: every edge-mode arc along a trajectory is legal."""

    @given(trajectory_input=edge_mode_trajectory_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_synthesized_trajectory_is_legal(
        self,
        trajectory_input: tuple[EdgeMode, list[dict[str, Any]]],
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate A: synthesized trajectory through EdgeTransitionSystem.

        For each ``(starting_mode, events)`` tuple, builds a 2-node graph,
        applies each event via direct attribute write, runs
        ``EdgeTransitionSystem.step`` once per event, and asserts every
        consecutive ``(prev, cur)`` pair is in ``_VALID_TRANSITIONS`` or
        equal (trivial no-transition).
        """
        starting_mode, events = trajectory_input
        graph = _build_two_node_graph(starting_mode)
        system = EdgeTransitionSystem()

        modes_observed: list[EdgeMode] = [starting_mode]
        for event in events:
            _apply_event_to_graph(graph, event)
            system.step(graph, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]
            modes_observed.append(_read_edge_mode(graph))

        trivial_count = 0
        persistence_count = 0
        for i, (prev, cur) in enumerate(zip(modes_observed[:-1], modes_observed[1:], strict=True)):
            if prev == cur:
                if prev == EdgeMode.ANTAGONISTIC:
                    persistence_count += 1
                else:
                    trivial_count += 1
                continue
            assert (prev, cur) in _VALID_TRANSITIONS, (
                f"Illegal arc at step {i}: ({prev} -> {cur}). "
                f"Trajectory: {[m.value for m in modes_observed]}"
            )

        assert modes_observed[-1] in EdgeMode  # Predicate C — final mode legal

    @given(state=worldstate_strategy(min_entities=2, max_relationships=4))
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_observed_trajectory_is_legal(
        self,
        state: WorldState,
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate B: observed end-to-end trajectory via SimulationEngine.

        Runs 5 consecutive ticks via real ``SimulationEngine.run_tick`` with
        all 21 Systems. For every edge present in both pre and post (matched
        by ``(source, target, edge_type)``), asserts arc legality.
        """
        systems = [cls() for cls in all_systems()]
        engine = SimulationEngine(systems=systems)

        current_state = state
        pre_modes = _capture_edge_modes(current_state.to_graph())

        for tick_idx in range(5):
            graph = current_state.to_graph()
            engine.run_tick(graph, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]
            post_modes = _capture_edge_modes(graph)

            for edge_id in pre_modes.keys() & post_modes.keys():
                prev = pre_modes[edge_id]
                cur = post_modes[edge_id]
                if prev == cur:
                    continue
                assert (prev, cur) in _VALID_TRANSITIONS, (
                    f"Tick {tick_idx} edge {edge_id}: illegal arc ({prev} -> {cur})"
                )

            current_state = WorldState.from_graph(graph, tick=current_state.tick + 1)
            pre_modes = post_modes
