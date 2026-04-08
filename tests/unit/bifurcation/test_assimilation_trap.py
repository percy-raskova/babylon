"""Tests for assimilation trap detection (Feature 034, US5).

Verifies that bifurcation analysis correctly distinguishes between
revolutionary solidarity (high r + cross-line edges) and assimilated
solidarity (low r + cross-line edges = crisis-fragile).

TDD red phase: tests written BEFORE implementation.
"""

from __future__ import annotations

import networkx as nx
import pytest
import xgi  # type: ignore[import-untyped]

from babylon.bifurcation.consciousness import consciousness_weighted_solidarity
from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import CommunityState
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType, ConsciousnessTendency, ContradictionAxis, EdgeType
from babylon.models.types import Probability

from .conftest import build_test_hypergraph, make_community_state

colonial_contradiction = Contradiction(
    id="colonial",
    axis=ContradictionAxis.IMPERIAL,
    aspect_a=CommunityType.SETTLER,
    aspect_b=CommunityType.NEW_AFRIKAN,
    intensity=0.5,
)


def _build_solidarity_scenario(
    ci_marginalized: float,
    tendency: ConsciousnessTendency = ConsciousnessTendency.LIBERAL,
) -> tuple[
    nx.DiGraph, xgi.Hypergraph, dict[CommunityType, CommunityState], dict[str, set[CommunityType]]
]:
    """Build a graph with cross-line solidarity at given CI level.

    Creates 4 agents: A1, A2 (NEW_AFRIKAN), A3, A4 (WOMEN).
    Both communities are marginalized so consciousness weighting applies.
    Cross-line SOLIDARITY edges: A1-A3, A2-A4.

    Args:
        ci_marginalized: CI for both marginalized communities.
        tendency: Dominant tendency for marginalized communities.

    Returns:
        Tuple of (graph, hypergraph, community_states, agent_memberships).
    """
    graph: nx.DiGraph = nx.DiGraph()

    # Add agents
    for agent_id in ("A1", "A2", "A3", "A4"):
        graph.add_node(agent_id, _node_type="social_class", wealth=30.0)

    # Cross-line solidarity edges
    graph.add_edge("A1", "A3", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)
    graph.add_edge("A2", "A4", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)

    # Community states — both marginalized communities at same CI
    community_states: dict[CommunityType, CommunityState] = {
        CommunityType.NEW_AFRIKAN: make_community_state(
            CommunityType.NEW_AFRIKAN,
            ci=ci_marginalized,
            tendency=tendency,
        ),
        CommunityType.WOMEN: make_community_state(
            CommunityType.WOMEN,
            ci=ci_marginalized,
            tendency=tendency,
        ),
        CommunityType.SETTLER: make_community_state(
            CommunityType.SETTLER,
            ci=0.2,
        ),
        CommunityType.PATRIARCHAL: make_community_state(
            CommunityType.PATRIARCHAL,
            ci=0.2,
        ),
    }

    # Agent memberships — all in marginalized communities
    agent_memberships: dict[str, set[CommunityType]] = {
        "A1": {CommunityType.NEW_AFRIKAN},
        "A2": {CommunityType.NEW_AFRIKAN},
        "A3": {CommunityType.WOMEN},
        "A4": {CommunityType.WOMEN},
    }

    H = build_test_hypergraph(agent_memberships, community_states)

    return graph, H, community_states, agent_memberships


@pytest.mark.unit
class TestCrisisFragileMarker:
    """Crisis-fragile detection on solidarity edges (FR-008)."""

    def test_low_r_edge_is_crisis_fragile(self) -> None:
        """Solidarity edge where both endpoints have r < 0.3 is crisis-fragile."""
        graph, H, community_states, _memberships = _build_solidarity_scenario(
            ci_marginalized=0.15,
        )
        defines = BifurcationDefines()

        result = consciousness_weighted_solidarity(
            source_id="A1",
            target_id="A3",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # With CI=0.15 (< sigmoid midpoint 0.4), weight should be low
        assert result.weight < 0.3
        assert result.crisis_fragile is True

    def test_high_r_edge_not_crisis_fragile(self) -> None:
        """Solidarity edge where endpoints have r > 0.3 is NOT crisis-fragile."""
        graph, H, community_states, _memberships = _build_solidarity_scenario(
            ci_marginalized=0.7,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        )
        defines = BifurcationDefines()

        result = consciousness_weighted_solidarity(
            source_id="A1",
            target_id="A3",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # With CI=0.7 (> sigmoid midpoint), weight should be significant
        assert result.weight > 0.3
        assert result.crisis_fragile is False

    def test_mixed_r_edge_is_crisis_fragile(self) -> None:
        """If either endpoint has r < 0.3, edge is crisis-fragile (weakest link)."""
        graph: nx.DiGraph = nx.DiGraph()
        for agent_id in ("A1", "A2"):
            graph.add_node(agent_id, _node_type="social_class", wealth=30.0)
        graph.add_edge("A1", "A2", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)

        # A1 in high-CI community (r=0.7), A2 in low-CI community (r=0.1)
        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: make_community_state(
                CommunityType.NEW_AFRIKAN,
                ci=0.7,
                tendency=ConsciousnessTendency.REVOLUTIONARY,
            ),
            CommunityType.WOMEN: make_community_state(
                CommunityType.WOMEN,
                ci=0.1,
            ),
        }
        agent_memberships: dict[str, set[CommunityType]] = {
            "A1": {CommunityType.NEW_AFRIKAN},
            "A2": {CommunityType.WOMEN},
        }
        H = build_test_hypergraph(agent_memberships, community_states)
        defines = BifurcationDefines()

        result = consciousness_weighted_solidarity(
            source_id="A1",
            target_id="A2",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # min(0.7, 0.1) = 0.1 < 0.3 → crisis-fragile
        assert result.crisis_fragile is True


@pytest.mark.unit
class TestAssimilationTrapDetection:
    """AS1/AS2: Same solidarity density, different r → different outcomes."""

    def test_high_solidarity_high_r_weight_significant(self) -> None:
        """AS1: High cross-line solidarity + high r → significant weighted solidarity."""
        graph, H, community_states, _memberships = _build_solidarity_scenario(
            ci_marginalized=0.7,
            tendency=ConsciousnessTendency.REVOLUTIONARY,
        )
        defines = BifurcationDefines()

        result = consciousness_weighted_solidarity(
            source_id="A1",
            target_id="A3",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # High CI → sigmoid output near 1.0 → high weighted solidarity
        assert result.weight > 0.5

    def test_high_solidarity_low_r_weight_collapsed(self) -> None:
        """AS2: High cross-line solidarity + low r → collapsed weighted solidarity."""
        graph, H, community_states, _memberships = _build_solidarity_scenario(
            ci_marginalized=0.1,
        )
        defines = BifurcationDefines()

        result = consciousness_weighted_solidarity(
            source_id="A1",
            target_id="A3",
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )

        # Low CI → sigmoid output near 0.0 → collapsed weighted solidarity
        assert result.weight < 0.2


@pytest.mark.unit
class TestBifurcationResultAssimilationRatio:
    """Bifurcation result includes mean_assimilation_ratio (T028)."""

    def test_result_has_assimilation_ratio(self) -> None:
        """BifurcationResult includes mean_assimilation_ratio field."""
        from babylon.bifurcation.analysis import bifurcation_tendency

        graph, H, community_states, agent_memberships = _build_solidarity_scenario(
            ci_marginalized=0.3,
        )
        defines = BifurcationDefines()

        result = bifurcation_tendency(
            graph=graph,
            H=H,
            contradictions=[colonial_contradiction],
            community_states=community_states,
            agent_memberships=agent_memberships,
            defines=defines,
        )

        assert hasattr(result, "mean_assimilation_ratio_marginalized")
        assert 0.0 <= result.mean_assimilation_ratio_marginalized <= 1.0

    def test_high_fascist_component_high_assimilation(self) -> None:
        """Community with high f/(l+f) has high assimilation_ratio."""
        from babylon.bifurcation.analysis import bifurcation_tendency
        from babylon.models.entities.consciousness import TernaryConsciousness

        graph: nx.DiGraph = nx.DiGraph()
        for agent_id in ("A1", "A2"):
            graph.add_node(agent_id, _node_type="social_class", wealth=30.0)
        graph.add_edge("A1", "A2", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.8)

        # Community with high fascist component: r=0.1, l=0.2, f=0.7
        fascist_consciousness = TernaryConsciousness(r=0.1, l=0.2, f=0.7)
        community_states: dict[CommunityType, CommunityState] = {
            CommunityType.NEW_AFRIKAN: CommunityState(
                community_type=CommunityType.NEW_AFRIKAN,
                consciousness=fascist_consciousness,
                infrastructure=Probability(0.3),
                cohesion=Probability(0.5),
            ),
        }
        agent_memberships: dict[str, set[CommunityType]] = {
            "A1": {CommunityType.NEW_AFRIKAN},
            "A2": {CommunityType.NEW_AFRIKAN},
        }
        H = build_test_hypergraph(agent_memberships, community_states)
        defines = BifurcationDefines()

        result = bifurcation_tendency(
            graph=graph,
            H=H,
            contradictions=[colonial_contradiction],
            community_states=community_states,
            agent_memberships=agent_memberships,
            defines=defines,
        )

        # assimilation_ratio for this community = f/(l+f) = 0.7/0.9 ≈ 0.78
        assert result.mean_assimilation_ratio_marginalized > 0.7

    def test_crisis_fragile_count_in_result(self) -> None:
        """BifurcationResult includes crisis_fragile_edge_count."""
        from babylon.bifurcation.analysis import bifurcation_tendency

        graph, H, community_states, agent_memberships = _build_solidarity_scenario(
            ci_marginalized=0.1,  # Low CI → crisis-fragile edges
        )
        defines = BifurcationDefines()

        result = bifurcation_tendency(
            graph=graph,
            H=H,
            contradictions=[colonial_contradiction],
            community_states=community_states,
            agent_memberships=agent_memberships,
            defines=defines,
        )

        assert hasattr(result, "crisis_fragile_edge_count")
        assert result.crisis_fragile_edge_count >= 0
