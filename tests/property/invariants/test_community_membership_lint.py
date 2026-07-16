"""Property-based tests for the hyperedges-not-pairwise structural linter
(INV-010 / spec-055 US2).

See ``specs/055-topology-invariants/contracts/community_membership_lint.md``
for the full predicate specification. Encodes Constitution II.7 (Edges vs
Hyperedges) and Anti-Pattern VIII.9 (Community as Pairwise Edge).

Three predicates:

  Predicate A — full-pipeline post-state linter (T016)
  Predicate B — MEMBERSHIP edge count delta is legitimate-only (T017)
  Predicate C — seeded violation is detected (negative test, T018)
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.engine.invariants import NoCommunityFanOut
from babylon.engine.simulation_engine import SimulationEngine
from babylon.models.enums import EdgeType
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph
from tests.property.harness.system_registry import all_systems
from tests.property.harness.topology_harness import (
    _inject_community_markers,
    is_community_node,
)
from tests.property.strategies.worldstate import (
    worldstate_with_community_node_strategy,
)


def _count_membership_edges(graph: BabylonGraph, *, exclude_community_sources: bool) -> int:
    """Count MEMBERSHIP edges in ``graph``.

    If ``exclude_community_sources`` is True, only counts edges whose
    source is NOT a community node (i.e., the legitimate
    organization-to-SocialClass MEMBERSHIP edges).
    """
    count = 0
    for src, _tgt, data in graph.edges(data=True):
        edge_type_raw = data.get("edge_type")
        if edge_type_raw is None:
            continue
        try:
            edge_type = (
                edge_type_raw if isinstance(edge_type_raw, EdgeType) else EdgeType(edge_type_raw)
            )
        except ValueError:
            continue
        if edge_type != EdgeType.MEMBERSHIP:
            continue
        if exclude_community_sources and is_community_node(graph, src):
            continue
        count += 1
    return count


@pytest.mark.unit
class TestCommunityMembershipLint:
    """INV-010: no MEMBERSHIP edge has a community-node source."""

    @given(strategy_output=worldstate_with_community_node_strategy())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_no_community_fan_out_post_pipeline(
        self,
        strategy_output: tuple[WorldState, frozenset[str]],
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate A: full-pipeline post-state has no community fan-outs."""
        state, community_node_ids = strategy_output
        systems = [cls() for cls in all_systems()]
        engine = SimulationEngine(systems=systems)

        graph = state.to_graph()
        _inject_community_markers(graph, community_node_ids)
        engine.run_tick(graph, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]

        invariant = NoCommunityFanOut()
        result = invariant.check_graph(graph)
        assert result.ok, result.msg

    @given(strategy_output=worldstate_with_community_node_strategy())
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_membership_count_delta_is_legitimate_only(
        self,
        strategy_output: tuple[WorldState, frozenset[str]],
        service_container_fixture: object,
        tick_context_fixture: object,
    ) -> None:
        """Predicate B: zero illegitimate community-fan-out MEMBERSHIP edges in post-graph."""
        state, community_node_ids = strategy_output
        systems = [cls() for cls in all_systems()]
        engine = SimulationEngine(systems=systems)

        graph = state.to_graph()
        _inject_community_markers(graph, community_node_ids)
        engine.run_tick(graph, service_container_fixture, tick_context_fixture)  # type: ignore[arg-type]

        post_membership_count = _count_membership_edges(graph, exclude_community_sources=False)
        post_legitimate_count = _count_membership_edges(graph, exclude_community_sources=True)

        illegitimate_post = post_membership_count - post_legitimate_count
        assert illegitimate_post == 0, (
            f"Found {illegitimate_post} community-fan-out MEMBERSHIP edges in post-graph"
        )

    def test_seeded_community_fan_out_is_detected(self) -> None:
        """Predicate C: deliberately-seeded community-fan-out edge IS caught."""
        # Hand-build a minimal 2-entity state and seed a violation.
        # IDs must match SocialClass.id pattern ^C[0-9]{3}$ — use C999 as the
        # community-tagged source and C001 as the member target.
        from babylon.models.entities.social_class import SocialClass
        from babylon.models.enums import SocialRole

        comm = SocialClass(
            id="C999", name="Comm", role=SocialRole.PERIPHERY_PROLETARIAT, wealth=10.0
        )
        member = SocialClass(
            id="C001", name="Member", role=SocialRole.PERIPHERY_PROLETARIAT, wealth=10.0
        )
        state = WorldState(tick=0, entities={"C999": comm, "C001": member})

        graph = state.to_graph()
        _inject_community_markers(graph, frozenset(["C999"]))
        # Deliberately seed the violation
        graph.add_edge("C999", "C001", edge_type=EdgeType.MEMBERSHIP.value)

        invariant = NoCommunityFanOut()
        result = invariant.check_graph(graph)

        assert not result.ok
        assert "C999" in result.msg
        assert "MEMBERSHIP" in result.msg
