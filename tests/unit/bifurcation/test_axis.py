"""Tests for per-axis contradiction analysis (US2, Feature 033).

Tests cover:
- ``crosses_contradiction_axis``: Detects edges spanning hegemonic/marginalized divide.
- ``classify_edge_antagonism``: Classifies edge direction (lateral/upward/downward/none).
- ``compute_axis_tendency``: Computes solidarity vs antagonism balance along an axis.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.config.defines import BifurcationDefines
from babylon.domain.bifurcation.axis import (
    classify_edge_antagonism,
    compute_axis_tendency,
    crosses_contradiction_axis,
)
from babylon.models.entities.community import (
    CommunityState,
)
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType, ContradictionType, EdgeMode, EdgeType
from babylon.topology.graph import BabylonGraph

from .factories import (
    assign_communities_to_graph,
    build_test_hypergraph,
    make_community_state,
)

# Dummy contradictions for testing
colonial_contradiction = Contradiction(
    id="colonial",
    type=ContradictionType.IMPERIAL,
    aspect_a=CommunityType.SETTLER,
    aspect_b=CommunityType.NEW_AFRIKAN,
    intensity=0.5,
    principal_aspect="a",
    identity=0.1,
    form_of_struggle=EdgeMode.EXTRACTIVE,
)

patriarchal_contradiction = Contradiction(
    id="patriarchal",
    type=ContradictionType.GENDER,
    aspect_a=CommunityType.PATRIARCHAL,
    aspect_b=CommunityType.WOMEN,
    intensity=0.5,
    principal_aspect="a",
    identity=0.1,
    form_of_struggle=EdgeMode.EXTRACTIVE,
)

# =============================================================================
# Helper: build directed graph with typed edges
# =============================================================================


def _build_typed_graph(
    agents: dict[str, dict[str, float]],
    edges: list[tuple[str, str, EdgeType, dict[str, float]]],
) -> BabylonGraph:
    """Build a DiGraph with typed edges.

    Args:
        agents: Node ID to attribute dict.
        edges: (source, target, edge_type, extra_attrs) tuples.

    Returns:
        DiGraph with configured nodes and edges.
    """
    G: BabylonGraph = BabylonGraph()
    for node_id, attrs in agents.items():
        G.add_node(node_id, _node_type="social_class", **attrs)
    for src, tgt, etype, extra in edges:
        G.add_edge(src, tgt, edge_type=etype, **extra)
    return G


# =============================================================================
# crosses_contradiction_axis
# =============================================================================


class TestCrossesContradictionAxis:
    """Tests for crosses_contradiction_axis function."""

    @pytest.mark.topology
    def test_settler_to_new_afrikan_on_colonial_axis(self) -> None:
        """SETTLER member -> NEW_AFRIKAN member on COLONIAL axis = True."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_settler": {CommunityType.SETTLER},
            "agent_na": {CommunityType.NEW_AFRIKAN},
        }
        result = crosses_contradiction_axis(
            source_id="agent_settler",
            target_id="agent_na",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is True

    @pytest.mark.topology
    def test_settler_to_women_on_colonial_axis_false(self) -> None:
        """SETTLER -> WOMEN on COLONIAL axis = False (WOMEN is patriarchal, not colonial)."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_settler": {CommunityType.SETTLER},
            "agent_women": {CommunityType.WOMEN},
        }
        result = crosses_contradiction_axis(
            source_id="agent_settler",
            target_id="agent_women",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is False

    @pytest.mark.topology
    def test_two_settlers_on_colonial_axis_false(self) -> None:
        """Two SETTLER members on COLONIAL axis = False (same side)."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_a": {CommunityType.SETTLER},
            "agent_b": {CommunityType.SETTLER},
        }
        result = crosses_contradiction_axis(
            source_id="agent_a",
            target_id="agent_b",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is False

    @pytest.mark.topology
    def test_patriarchal_to_women_on_patriarchal_axis(self) -> None:
        """PATRIARCHAL -> WOMEN on PATRIARCHAL axis = True."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_p": {CommunityType.PATRIARCHAL},
            "agent_w": {CommunityType.WOMEN},
        }
        result = crosses_contradiction_axis(
            source_id="agent_p",
            target_id="agent_w",
            contradiction=patriarchal_contradiction,
            agent_memberships=memberships,
        )
        assert result is True

    @pytest.mark.topology
    def test_no_memberships_for_either_agent(self) -> None:
        """Both agents with no memberships = False."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_a": set(),
            "agent_b": set(),
        }
        result = crosses_contradiction_axis(
            source_id="agent_a",
            target_id="agent_b",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is False

    @pytest.mark.topology
    def test_one_agent_missing_from_memberships(self) -> None:
        """Agent not in memberships dict at all = False."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_a": {CommunityType.SETTLER},
        }
        result = crosses_contradiction_axis(
            source_id="agent_a",
            target_id="agent_missing",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is False

    @pytest.mark.topology
    def test_agent_with_multiple_communities_crosses(self) -> None:
        """Agent with multiple communities including hegemonic crosses with marginalized agent."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_multi": {CommunityType.SETTLER, CommunityType.WOMEN},
            "agent_na": {CommunityType.NEW_AFRIKAN},
        }
        result = crosses_contradiction_axis(
            source_id="agent_multi",
            target_id="agent_na",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is True

    @pytest.mark.topology
    def test_reverse_direction_also_crosses(self) -> None:
        """NEW_AFRIKAN -> SETTLER on COLONIAL axis = True (reversed direction)."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_na": {CommunityType.NEW_AFRIKAN},
            "agent_settler": {CommunityType.SETTLER},
        }
        result = crosses_contradiction_axis(
            source_id="agent_na",
            target_id="agent_settler",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is True

    @pytest.mark.topology
    def test_two_marginalized_same_axis_false(self) -> None:
        """Two marginalized agents on same axis = False (no hegemonic endpoint)."""
        memberships: dict[str, set[CommunityType]] = {
            "agent_na": {CommunityType.NEW_AFRIKAN},
            "agent_fn": {CommunityType.FIRST_NATIONS},
        }
        result = crosses_contradiction_axis(
            source_id="agent_na",
            target_id="agent_fn",
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result is False


# =============================================================================
# classify_edge_antagonism
# =============================================================================

# Antagonistic edge types for reference:
# EXPLOITATION, REPRESSION, COMPETITION


class TestClassifyEdgeAntagonism:
    """Tests for classify_edge_antagonism function."""

    @pytest.mark.topology
    def test_exploitation_from_hegemonic_to_marginalized_downward(self) -> None:
        """EXPLOITATION from SETTLER to NEW_AFRIKAN on colonial axis = 'downward'."""
        agents = {"bourgeois": {"wealth": 500.0}, "worker": {"wealth": 20.0}}
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("bourgeois", "worker", EdgeType.EXPLOITATION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "bourgeois": {CommunityType.SETTLER},
            "worker": {CommunityType.NEW_AFRIKAN},
        }

        result = classify_edge_antagonism(
            source_id="bourgeois",
            target_id="worker",
            graph=graph,
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result == "downward"

    @pytest.mark.topology
    def test_repression_from_marginalized_to_hegemonic_upward(self) -> None:
        """REPRESSION from NEW_AFRIKAN to SETTLER on colonial axis = 'upward'."""
        agents = {"agent_na": {"wealth": 20.0}, "agent_settler": {"wealth": 100.0}}
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("agent_na", "agent_settler", EdgeType.REPRESSION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "agent_na": {CommunityType.NEW_AFRIKAN},
            "agent_settler": {CommunityType.SETTLER},
        }

        result = classify_edge_antagonism(
            source_id="agent_na",
            target_id="agent_settler",
            graph=graph,
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result == "upward"

    @pytest.mark.topology
    def test_competition_both_marginalized_lateral(self) -> None:
        """COMPETITION between two marginalized agents = 'lateral'."""
        agents = {"agent_na": {"wealth": 20.0}, "agent_na2": {"wealth": 25.0}}
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("agent_na", "agent_na2", EdgeType.COMPETITION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "agent_na": {CommunityType.NEW_AFRIKAN},
            "agent_na2": {CommunityType.NEW_AFRIKAN},
        }

        result = classify_edge_antagonism(
            source_id="agent_na",
            target_id="agent_na2",
            graph=graph,
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result == "lateral"

    @pytest.mark.topology
    def test_both_hegemonic_lateral(self) -> None:
        """EXPLOITATION between two hegemonic agents on patriarchal axis = 'lateral'."""
        agents = {"agent_pa": {"wealth": 300.0}, "agent_pb": {"wealth": 200.0}}
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("agent_pa", "agent_pb", EdgeType.EXPLOITATION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        # Both agents are on the hegemonic side of the patriarchal axis
        memberships: dict[str, set[CommunityType]] = {
            "agent_pa": {CommunityType.PATRIARCHAL},
            "agent_pb": {CommunityType.PATRIARCHAL},
        }

        result = classify_edge_antagonism(
            source_id="agent_pa",
            target_id="agent_pb",
            graph=graph,
            contradiction=patriarchal_contradiction,
            agent_memberships=memberships,
        )
        assert result == "lateral"

    @pytest.mark.topology
    def test_neither_on_axis_returns_none(self) -> None:
        """Agents not on this axis at all = 'none'."""
        agents = {"agent_w": {"wealth": 30.0}, "agent_t": {"wealth": 30.0}}
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("agent_w", "agent_t", EdgeType.EXPLOITATION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        # Both are on patriarchal axis but we query colonial axis
        memberships: dict[str, set[CommunityType]] = {
            "agent_w": {CommunityType.WOMEN},
            "agent_t": {CommunityType.TRANS},
        }

        result = classify_edge_antagonism(
            source_id="agent_w",
            target_id="agent_t",
            graph=graph,
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result == "none"

    @pytest.mark.topology
    def test_only_one_on_axis_returns_none(self) -> None:
        """Only one endpoint on this axis = 'none'."""
        agents = {"agent_s": {"wealth": 100.0}, "agent_w": {"wealth": 30.0}}
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("agent_s", "agent_w", EdgeType.EXPLOITATION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        # SETTLER is on colonial axis, WOMEN is NOT on colonial axis
        memberships: dict[str, set[CommunityType]] = {
            "agent_s": {CommunityType.SETTLER},
            "agent_w": {CommunityType.WOMEN},
        }

        result = classify_edge_antagonism(
            source_id="agent_s",
            target_id="agent_w",
            graph=graph,
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result == "none"

    @pytest.mark.topology
    def test_solidarity_edge_not_antagonistic_returns_none(self) -> None:
        """SOLIDARITY edge is not antagonistic, so classify returns 'none'."""
        agents = {"agent_s": {"wealth": 100.0}, "agent_na": {"wealth": 20.0}}
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("agent_s", "agent_na", EdgeType.SOLIDARITY, {"solidarity_strength": 0.8}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "agent_s": {CommunityType.SETTLER},
            "agent_na": {CommunityType.NEW_AFRIKAN},
        }

        result = classify_edge_antagonism(
            source_id="agent_s",
            target_id="agent_na",
            graph=graph,
            contradiction=colonial_contradiction,
            agent_memberships=memberships,
        )
        assert result == "none"


# =============================================================================
# compute_axis_tendency
# =============================================================================


class TestComputeAxisTendency:
    """Tests for compute_axis_tendency function."""

    @pytest.mark.topology
    def test_all_solidarity_no_antagonism_high_ratio(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """All cross-axis solidarity, no antagonism -> high tendency_ratio (>> 1.0)."""
        # SETTLER agent with solidarity to NEW_AFRIKAN agent (crosses colonial axis)
        agents = {
            "settler_1": {"wealth": 100.0},
            "na_1": {"wealth": 20.0},
            "na_2": {"wealth": 20.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, {"solidarity_strength": 0.8}),
            ("settler_1", "na_2", EdgeType.SOLIDARITY, {"solidarity_strength": 0.7}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
            "na_2": {CommunityType.NEW_AFRIKAN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.3),
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.8),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.axis_id == "colonial"
        assert result.cross_solidarity_weighted > 0.0
        assert result.lateral_antagonism_weighted == 0.0
        # With zero antagonism, ratio should be very high
        assert result.tendency_ratio > 1.0
        assert result.cross_edge_count == 2
        assert result.lateral_edge_count == 0

    @pytest.mark.topology
    def test_all_antagonism_no_solidarity_low_ratio(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """All antagonism, no solidarity -> tendency_ratio near 0.0."""
        agents = {
            "na_1": {"wealth": 20.0},
            "na_2": {"wealth": 25.0},
            "fn_1": {"wealth": 15.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("na_1", "na_2", EdgeType.COMPETITION, {"weight": 1.0}),
            ("na_1", "fn_1", EdgeType.COMPETITION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "na_1": {CommunityType.NEW_AFRIKAN},
            "na_2": {CommunityType.NEW_AFRIKAN},
            "fn_1": {CommunityType.FIRST_NATIONS},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.FIRST_NATIONS: make_community_state(CommunityType.FIRST_NATIONS, ci=0.5),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.axis_id == "colonial"
        assert result.cross_solidarity_weighted == 0.0
        assert result.lateral_antagonism_weighted > 0.0
        # 0 / (positive + epsilon) -> near 0
        assert result.tendency_ratio < 0.01
        assert result.cross_edge_count == 0
        assert result.lateral_edge_count > 0

    @pytest.mark.topology
    def test_mixed_edges_intermediate_ratio(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Mix of cross solidarity and lateral antagonism -> intermediate ratio."""
        agents = {
            "settler_1": {"wealth": 100.0},
            "na_1": {"wealth": 20.0},
            "na_2": {"wealth": 25.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            # Cross-axis solidarity
            ("settler_1", "na_1", EdgeType.SOLIDARITY, {"solidarity_strength": 0.8}),
            # Lateral antagonism (both marginalized on colonial axis)
            ("na_1", "na_2", EdgeType.COMPETITION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
            "na_2": {CommunityType.NEW_AFRIKAN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.3),
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.7),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.axis_id == "colonial"
        assert result.cross_solidarity_weighted > 0.0
        assert result.lateral_antagonism_weighted > 0.0
        assert result.cross_edge_count == 1
        assert result.lateral_edge_count == 1
        # Ratio should be finite and positive
        assert result.tendency_ratio > 0.0
        assert result.tendency_ratio < 100.0

    @pytest.mark.topology
    def test_no_edges_on_axis_zero_ratio(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """No edges on this axis -> tendency_ratio near 0 (0 / epsilon)."""
        # Agents on patriarchal axis, query colonial axis
        agents = {
            "agent_p": {"wealth": 100.0},
            "agent_w": {"wealth": 30.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("agent_p", "agent_w", EdgeType.SOLIDARITY, {"solidarity_strength": 0.9}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "agent_p": {CommunityType.PATRIARCHAL},
            "agent_w": {CommunityType.WOMEN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.PATRIARCHAL: make_community_state(CommunityType.PATRIARCHAL, ci=0.3),
            CommunityType.WOMEN: make_community_state(CommunityType.WOMEN, ci=0.7),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.axis_id == "colonial"
        assert result.cross_solidarity_weighted == 0.0
        assert result.lateral_antagonism_weighted == 0.0
        # 0 / epsilon -> near 0
        assert result.tendency_ratio < 1.0
        assert result.cross_edge_count == 0
        assert result.lateral_edge_count == 0

    @pytest.mark.topology
    def test_pure_hegemonic_source_collapses_weight_despite_high_target_ci(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """A pure-hegemonic source stays near-zero even with a high-CI target.

        settler_1 has no marginalized community membership, so its own
        marginalized CI is 0 regardless of the SETTLER community-level
        CI=0.3 set below. na_1's NEW_AFRIKAN CI=0.9 doesn't help either:
        consciousness_weighted_solidarity takes min(source_ci, target_ci)
        across each agent's MARGINALIZED memberships, so
        min(0.0, 0.9) = 0.0 and the edge weight collapses to
        1.0 * sigmoid(0.0) ~= 0.018 -- not "near full".
        """
        agents = {
            "settler_1": {"wealth": 100.0},
            "na_1": {"wealth": 20.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, {"solidarity_strength": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.3),
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.9),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.cross_edge_count == 1
        # weight = solidarity_strength(1.0) * sigmoid(min(0.0, 0.9)=0.0, mid=0.4, k=10.0)
        assert result.cross_solidarity_weighted == pytest.approx(0.017986, abs=1e-5)

    @pytest.mark.topology
    def test_low_ci_communities_near_zero_cross_weight(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Low-CI communities -> cross solidarity weighted near zero (assimilation trap)."""
        agents = {
            "settler_1": {"wealth": 100.0},
            "na_1": {"wealth": 20.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, {"solidarity_strength": 0.9}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.1),
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.1),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        # Low CI (0.1) -> sigmoid near 0 -> weighted near 0
        assert result.cross_solidarity_weighted < 0.05
        assert result.cross_edge_count == 1

    @pytest.mark.topology
    def test_upward_edge_count_tracked(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Upward antagonism edges are counted separately."""
        agents = {
            "na_1": {"wealth": 20.0},
            "settler_1": {"wealth": 100.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            # Upward: marginalized -> hegemonic
            ("na_1", "settler_1", EdgeType.REPRESSION, {"weight": 1.0}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "na_1": {CommunityType.NEW_AFRIKAN},
            "settler_1": {CommunityType.SETTLER},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.3),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.upward_edge_count == 1
        assert result.lateral_edge_count == 0

    @pytest.mark.topology
    def test_axis_tendency_returns_frozen_model(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """AxisTendency result is a frozen Pydantic model."""
        graph: BabylonGraph = BabylonGraph()
        graph.add_node("a", _node_type="social_class", wealth=50.0)

        memberships: dict[str, set[CommunityType]] = {"a": {CommunityType.SETTLER}}
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.3),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=colonial_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        # Verify it's an AxisTendency
        from babylon.domain.bifurcation.types import AxisTendency

        assert isinstance(result, AxisTendency)

        # Verify frozen (Pydantic should raise ValidationError on mutation)
        with pytest.raises(ValidationError):
            result.tendency_ratio = 999.0  # type: ignore[misc]

    @pytest.mark.topology
    def test_patriarchal_axis_tendency(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Verify compute_axis_tendency works with patriarchal axis."""
        agents = {
            "agent_p": {"wealth": 100.0},
            "agent_w": {"wealth": 30.0},
            "agent_w2": {"wealth": 25.0},
        }
        edges: list[tuple[str, str, EdgeType, dict[str, float]]] = [
            # Cross-axis solidarity on patriarchal axis
            ("agent_p", "agent_w", EdgeType.SOLIDARITY, {"solidarity_strength": 0.7}),
            # Lateral antagonism (both marginalized on patriarchal axis)
            ("agent_w", "agent_w2", EdgeType.COMPETITION, {"weight": 0.5}),
        ]
        graph = _build_typed_graph(agents, edges)

        memberships: dict[str, set[CommunityType]] = {
            "agent_p": {CommunityType.PATRIARCHAL},
            "agent_w": {CommunityType.WOMEN},
            "agent_w2": {CommunityType.WOMEN},
        }
        assign_communities_to_graph(graph, memberships)

        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.PATRIARCHAL: make_community_state(CommunityType.PATRIARCHAL, ci=0.3),
            CommunityType.WOMEN: make_community_state(CommunityType.WOMEN, ci=0.7),
        }

        H = build_test_hypergraph(memberships, community_states)

        result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=patriarchal_contradiction,
            community_states=community_states,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.axis_id == "patriarchal"
        assert result.cross_edge_count == 1
        assert result.lateral_edge_count == 1
        assert result.cross_solidarity_weighted >= 0.0
        assert result.lateral_antagonism_weighted > 0.0
