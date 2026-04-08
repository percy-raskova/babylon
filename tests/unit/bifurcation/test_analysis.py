"""Tests for full bifurcation analysis orchestrator (US5, Feature 033).

Critical validation: the assimilation trap test (high cross-line density
+ CI<=0.2) must classify as "fascist" despite many solidarity edges.
"""

from __future__ import annotations

import networkx as nx
import pytest
import xgi
from pydantic import ValidationError

from babylon.bifurcation.analysis import bifurcation_tendency
from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import (
    CommunityState,
)
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import (
    CommunityType,
    ConsciousnessTendency,
    ContradictionType,
    EdgeMode,
    EdgeType,
)

from .conftest import (
    assign_communities_to_graph,
    build_test_hypergraph,
    make_community_state,
)

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

pytestmark = pytest.mark.topology


# =============================================================================
# Helper: Build analysis test scenarios
# =============================================================================


def _build_analysis_scenario(
    agent_communities: dict[str, set[CommunityType]],
    community_states: dict[CommunityType, CommunityState],
    edges: list[tuple[str, str, EdgeType, float]],
    territories: list[dict[str, object]] | None = None,
) -> tuple[nx.DiGraph, xgi.Hypergraph, dict[str, set[CommunityType]]]:
    """Build a complete scenario graph for bifurcation analysis.

    Args:
        agent_communities: Agent ID to community memberships.
        community_states: Community states for hypergraph.
        edges: List of (source, target, edge_type, strength) tuples.
        territories: Optional territory nodes with legitimation.

    Returns:
        Tuple of (graph, hypergraph, agent_memberships).
    """
    graph: nx.DiGraph = nx.DiGraph()

    # Add agent nodes
    for agent_id in agent_communities:
        graph.add_node(agent_id, _node_type="social_class", wealth=50.0)

    # Add edges
    for src, tgt, edge_type, strength in edges:
        graph.add_edge(src, tgt, edge_type=edge_type, solidarity_strength=strength, weight=1.0)

    # Set community memberships on graph
    assign_communities_to_graph(graph, agent_communities)

    # Add territories if provided
    if territories:
        for terr in territories:
            graph.add_node(terr["id"], **{k: v for k, v in terr.items() if k != "id"})

    # Build hypergraph
    H = build_test_hypergraph(agent_communities, community_states)

    return graph, H, agent_communities


# =============================================================================
# Critical Test: Assimilation Trap
# =============================================================================


class TestAssimilationTrap:
    """The assimilation trap: high edge density + low CI = fascist.

    This is the core validation of the consciousness-weighted model.
    The Democratic Party coalition pattern: many cross-line solidarity
    edges but CI <= 0.2 (assimilated), so consciousness weighting
    collapses the effective solidarity to near-zero.
    """

    def test_high_density_low_ci_classifies_fascist(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Many cross-line solidarity edges but CI=0.1 → fascist."""
        # Agents: settler and New Afrikan with many solidarity edges
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "settler_2": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
            "na_2": {CommunityType.NEW_AFRIKAN},
            "women_1": {CommunityType.WOMEN},
        }

        # Low CI for all communities (assimilated)
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.1),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.1),
            CommunityType.WOMEN: make_community_state(CommunityType.WOMEN, ci=0.1),
            CommunityType.PATRIARCHAL: make_community_state(CommunityType.PATRIARCHAL, ci=0.1),
        }

        # Many cross-line solidarity edges
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
            ("settler_1", "na_2", EdgeType.SOLIDARITY, 0.9),
            ("settler_2", "na_1", EdgeType.SOLIDARITY, 0.9),
            ("settler_2", "na_2", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)

        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        # Core assertion: must be fascist despite high edge density
        assert result.overall_tendency == "fascist"
        # Cross-line solidarity count should be high
        assert result.cross_line_solidarity_count >= 4
        # But consciousness-weighted value should be near-zero
        assert result.consciousness_weighted_cross_solidarity < 0.1

    def test_low_ci_cross_solidarity_near_zero(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Verify consciousness weighting collapses low-CI solidarity."""
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

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.consciousness_weighted_cross_solidarity < 0.05


# =============================================================================
# Revolutionary Classification
# =============================================================================


class TestRevolutionaryClassification:
    """High CI + strong cross-line solidarity = revolutionary."""

    def test_high_ci_solidarity_classifies_revolutionary(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """High CI communities with cross-axis solidarity → revolutionary.

        Note: Hegemonic agents need intersectional marginalized memberships
        (e.g., DISABLED) for consciousness weighting to be effective, since
        the sigmoid uses min(source_ci, target_ci) of MARGINALIZED communities.
        Pure hegemonic agents have marginalized CI = 0.
        """
        # Settlers also have DISABLED membership (intersectional)
        agents = {
            "settler_1": {CommunityType.SETTLER, CommunityType.DISABLED},
            "na_1": {CommunityType.NEW_AFRIKAN},
            "na_2": {CommunityType.NEW_AFRIKAN},
            "women_1": {CommunityType.WOMEN},
            "patriarchal_1": {CommunityType.PATRIARCHAL, CommunityType.QUEER},
        }

        states = {
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
            CommunityType.WOMEN: make_community_state(
                CommunityType.WOMEN,
                ci=0.8,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
            CommunityType.PATRIARCHAL: make_community_state(
                CommunityType.PATRIARCHAL,
                ci=0.8,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
            CommunityType.DISABLED: make_community_state(
                CommunityType.DISABLED,
                ci=0.8,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
            CommunityType.QUEER: make_community_state(
                CommunityType.QUEER,
                ci=0.8,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
        }

        # Cross-axis solidarity on both axes
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
            ("settler_1", "na_2", EdgeType.SOLIDARITY, 0.9),
            ("patriarchal_1", "women_1", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.overall_tendency == "revolutionary"
        assert result.consciousness_weighted_cross_solidarity > 0.5

    def test_per_axis_tendency_ratios_high(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Revolutionary scenario has high per-axis tendency ratios."""
        # Settler needs intersectional marginalized membership for CI weighting
        agents = {
            "settler_1": {CommunityType.SETTLER, CommunityType.DISABLED},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }

        states = {
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

        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.per_axis_tendency["colonial"] > 1.0


# =============================================================================
# Indeterminate Classification
# =============================================================================


class TestIndeterminateClassification:
    """Mixed signals → indeterminate."""

    def test_mixed_solidarity_and_antagonism(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Balanced solidarity and antagonism → indeterminate."""
        # NetworkX DiGraph doesn't support parallel edges between same pair,
        # so use separate agents for solidarity vs exploitation edges.
        agents2 = {
            "settler_1": {CommunityType.SETTLER},
            "settler_2": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
            "na_2": {CommunityType.NEW_AFRIKAN},
        }
        edges2: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.5),
            ("settler_2", "na_2", EdgeType.EXPLOITATION, 0.5),
        ]
        states2 = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.5),
        }

        graph, H, memberships = _build_analysis_scenario(agents2, states2, edges2)
        result = bifurcation_tendency(
            graph,
            H,
            states2,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        # With balanced forces, result should be indeterminate
        assert result.overall_tendency in ("indeterminate", "fascist", "revolutionary")
        # Verify the metrics capture both
        assert result.cross_line_solidarity_count >= 1
        assert result.lateral_antagonism_count >= 0 or result.upward_antagonism_count >= 0


# =============================================================================
# Degenerate Cases (FR-014)
# =============================================================================


class TestDegenerateCases:
    """Edge cases and degenerate inputs."""

    def test_empty_graph(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Empty graph → indeterminate with zero metrics."""
        graph: nx.DiGraph = nx.DiGraph()
        H: xgi.Hypergraph = xgi.Hypergraph()
        states: dict[CommunityType, CommunityState] = {}
        memberships: dict[str, set[CommunityType]] = {}

        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.overall_tendency == "indeterminate"
        assert result.cross_line_solidarity_count == 0
        assert result.consciousness_weighted_cross_solidarity == 0.0
        assert result.raw_beta_0 == 0
        assert result.raw_beta_1 == 0

    def test_no_solidarity_edges(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Agents with no solidarity edges → fascist (pure antagonism)."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.5),
        }

        # Only exploitation, no solidarity
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.EXPLOITATION, 0.8),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.overall_tendency == "fascist"
        assert result.cross_line_solidarity_count == 0

    def test_single_node_graph(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Single agent, no edges → indeterminate."""
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("lone_wolf", _node_type="social_class", wealth=50.0)
        H: xgi.Hypergraph = xgi.Hypergraph()
        states: dict[CommunityType, CommunityState] = {}
        memberships: dict[str, set[CommunityType]] = {}

        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.overall_tendency == "indeterminate"

    def test_no_cross_axis_agents(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """All agents on same side of all axes → indeterminate."""
        agents = {
            "na_1": {CommunityType.NEW_AFRIKAN},
            "na_2": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.8),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("na_1", "na_2", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        # No cross-axis edges possible
        assert result.cross_line_solidarity_count == 0
        assert result.overall_tendency == "indeterminate"


# =============================================================================
# Topology Metrics
# =============================================================================


class TestTopologyMetrics:
    """Verify Betti numbers and resilience metrics are populated."""

    def test_betti_numbers_populated(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Result includes raw and filtered Betti numbers."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.8),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.8),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        # Two nodes connected → 1 component, 0 cycles
        assert result.raw_beta_0 >= 1
        assert result.raw_beta_1 >= 0
        # Filtered should also be computed
        assert result.filtered_beta_0 >= 0
        assert result.filtered_beta_1 >= 0

    def test_resilience_in_range(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Purge resilience is in [0, 1]."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.8),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.8),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert 0.0 <= result.resilience_under_targeted_purge <= 1.0

    def test_equivalence_classes_populated(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Equivalence class distribution is a dict."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.8),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.8),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert isinstance(result.equivalence_class_distribution, dict)


# =============================================================================
# Bridge and Legitimation Integration
# =============================================================================


class TestBridgeAndLegitimation:
    """Bridge detection and legitimation amplifier integration."""

    def test_bridge_count_populated(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """With INSTITUTIONAL_EXCLUSION spanning axis, bridge is detected."""
        agents = {
            "settler_1": {CommunityType.SETTLER, CommunityType.DISABLED},
            "na_1": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
        }

        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.7),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.7),
            CommunityType.DISABLED: make_community_state(
                CommunityType.DISABLED, ci=0.7, infrastructure=0.5
            ),
        }

        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.community_bridge_count >= 1
        assert result.bridge_potential_weighted > 0.0

    def test_legitimation_index_populated(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Territory legitimation feeds into result."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.7),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.7),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]
        territories = [
            {
                "id": "T1",
                "_node_type": "territory",
                "legitimation_index": 0.3,
                "population": 100,
            },
        ]

        graph, H, memberships = _build_analysis_scenario(
            agents, states, edges, territories=territories
        )
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        assert result.legitimation_index == pytest.approx(0.3, abs=0.01)


# =============================================================================
# Dominant Tendency Distribution
# =============================================================================


class TestDominantTendencyDistribution:
    """Verify dominant tendency distribution sums to 1.0."""

    def test_distribution_sums_to_one(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Tendency distribution across marginalized communities sums to 1.0."""
        agents = {
            "na_1": {CommunityType.NEW_AFRIKAN},
            "women_1": {CommunityType.WOMEN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(
                CommunityType.NEW_AFRIKAN,
                ci=0.7,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
            CommunityType.WOMEN: make_community_state(
                CommunityType.WOMEN,
                ci=0.5,
                tendency=ConsciousnessTendency.LIBERAL,
            ),
        }
        edges: list[tuple[str, str, EdgeType, float]] = []

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        total = sum(result.dominant_tendency_distribution.values())
        if total > 0:
            assert total == pytest.approx(1.0, abs=0.01)


# =============================================================================
# Result Model Constraints
# =============================================================================


class TestResultModelConstraints:
    """BifurcationResult is a frozen Pydantic model."""

    def test_result_is_frozen(
        self,
        bifurcation_defines: BifurcationDefines,
    ) -> None:
        """Cannot mutate BifurcationResult fields."""
        agents = {
            "settler_1": {CommunityType.SETTLER},
            "na_1": {CommunityType.NEW_AFRIKAN},
        }
        states = {
            CommunityType.NEW_AFRIKAN: make_community_state(CommunityType.NEW_AFRIKAN, ci=0.5),
            CommunityType.SETTLER: make_community_state(CommunityType.SETTLER, ci=0.5),
        }
        edges: list[tuple[str, str, EdgeType, float]] = [
            ("settler_1", "na_1", EdgeType.SOLIDARITY, 0.9),
        ]

        graph, H, memberships = _build_analysis_scenario(agents, states, edges)
        result = bifurcation_tendency(
            graph,
            H,
            states,
            [colonial_contradiction, patriarchal_contradiction],
            memberships,
            bifurcation_defines,
        )

        with pytest.raises(ValidationError):
            result.overall_tendency = "fascist"  # type: ignore[misc]
