"""Tests for compute_solidarity_ceiling (US6 — Material Solidarity Ceiling).

These tests verify that solidarity between agents is materially bounded
by wage gap ratios, shared exploitation sources, and community membership.

Feature 033 — Bifurcation Topology Analysis.
"""

from __future__ import annotations

import networkx as nx
import pytest
from tests.unit.bifurcation.conftest import (
    assign_communities_to_graph,
    build_ceiling_test_graph,
)

from babylon.bifurcation.ceiling import compute_solidarity_ceiling
from babylon.config.defines import BifurcationDefines
from babylon.models.enums import CommunityType, EdgeType


class TestSolidarityCeilingWageGap:
    """Test wage gap ratio effects on solidarity ceiling."""

    @pytest.mark.unit
    def test_large_wage_gap_ceiling_low(self, bifurcation_defines: BifurcationDefines) -> None:
        """wage_gap > 10.0 should yield ceiling <= wage_ceiling_min (0.3)."""
        # Ratio = 200/10 = 20.0 (well above 10.0 threshold)
        graph = build_ceiling_test_graph(wealth_a=200.0, wealth_b=10.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.wage_gap_ratio >= 10.0
        assert result.base_ceiling <= bifurcation_defines.wage_ceiling_min
        assert result.effective_ceiling <= bifurcation_defines.wage_ceiling_min

    @pytest.mark.unit
    def test_small_wage_gap_ceiling_high(self, bifurcation_defines: BifurcationDefines) -> None:
        """wage_gap < 2.0 should yield ceiling <= wage_ceiling_max (0.9)."""
        # Ratio = 50/40 = 1.25 (below 2.0 threshold)
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.wage_gap_ratio < 2.0
        assert result.base_ceiling == pytest.approx(bifurcation_defines.wage_ceiling_max, abs=1e-6)

    @pytest.mark.unit
    def test_midrange_wage_gap_interpolated(self, bifurcation_defines: BifurcationDefines) -> None:
        """wage_gap = 5.0 should interpolate between min and max."""
        # Ratio = 50/10 = 5.0 (midrange between 2.0 and 10.0)
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=10.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.wage_gap_ratio == pytest.approx(5.0, abs=1e-6)
        # Should be strictly between min and max
        assert result.base_ceiling > bifurcation_defines.wage_ceiling_min
        assert result.base_ceiling < bifurcation_defines.wage_ceiling_max

    @pytest.mark.unit
    def test_boundary_ratio_exactly_low(self, bifurcation_defines: BifurcationDefines) -> None:
        """Ratio exactly at wage_ceiling_low_ratio (2.0) yields max ceiling."""
        # Ratio = 20/10 = 2.0 exactly
        graph = build_ceiling_test_graph(wealth_a=20.0, wealth_b=10.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.wage_gap_ratio == pytest.approx(2.0, abs=1e-6)
        assert result.base_ceiling == pytest.approx(bifurcation_defines.wage_ceiling_max, abs=1e-6)

    @pytest.mark.unit
    def test_boundary_ratio_exactly_high(self, bifurcation_defines: BifurcationDefines) -> None:
        """Ratio exactly at wage_ceiling_high_ratio (10.0) yields min ceiling."""
        # Ratio = 100/10 = 10.0 exactly
        graph = build_ceiling_test_graph(wealth_a=100.0, wealth_b=10.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.wage_gap_ratio == pytest.approx(10.0, abs=1e-6)
        assert result.base_ceiling == pytest.approx(bifurcation_defines.wage_ceiling_min, abs=1e-6)


class TestSolidarityCeilingExploitation:
    """Test shared exploitation source bonus."""

    @pytest.mark.unit
    def test_shared_exploitation_bonus(self, bifurcation_defines: BifurcationDefines) -> None:
        """Shared exploitation source gives +0.2 bonus."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0, shared_exploiter=True)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.exploitation_bonus == pytest.approx(
            bifurcation_defines.shared_exploitation_bonus, abs=1e-6
        )

    @pytest.mark.unit
    def test_no_shared_exploitation_no_bonus(self, bifurcation_defines: BifurcationDefines) -> None:
        """Without shared exploitation source, bonus is 0."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0, shared_exploiter=False)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.exploitation_bonus == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.unit
    def test_separate_exploiters_no_bonus(self, bifurcation_defines: BifurcationDefines) -> None:
        """Different exploitation sources should NOT give bonus."""
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("worker_a", _node_type="social_class", wealth=50.0)
        graph.add_node("worker_b", _node_type="social_class", wealth=40.0)
        graph.add_node("exploiter_1", _node_type="social_class", wealth=500.0)
        graph.add_node("exploiter_2", _node_type="social_class", wealth=500.0)
        # Different exploiters for each worker
        graph.add_edge(
            "exploiter_1",
            "worker_a",
            edge_type=EdgeType.EXPLOITATION,
            solidarity_strength=0.0,
        )
        graph.add_edge(
            "exploiter_2",
            "worker_b",
            edge_type=EdgeType.EXPLOITATION,
            solidarity_strength=0.0,
        )
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.exploitation_bonus == pytest.approx(0.0, abs=1e-6)


class TestSolidarityCeilingCommunity:
    """Test community membership bonus."""

    @pytest.mark.unit
    def test_shared_community_gives_bonus(self, bifurcation_defines: BifurcationDefines) -> None:
        """Shared marginalized community memberships produce community bonus > 0."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED},
            "worker_b": {CommunityType.NEW_AFRIKAN, CommunityType.QUEER},
        }
        assign_communities_to_graph(graph, memberships)

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        # Shared: NEW_AFRIKAN (1 community). Bonus = 0.05 * 1 = 0.05
        assert result.community_bonus > 0.0
        assert result.community_bonus == pytest.approx(0.05, abs=1e-6)

    @pytest.mark.unit
    def test_multiple_shared_communities(self, bifurcation_defines: BifurcationDefines) -> None:
        """Multiple shared communities yield higher bonus."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED, CommunityType.WOMEN},
            "worker_b": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED, CommunityType.WOMEN},
        }
        assign_communities_to_graph(graph, memberships)

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        # 3 shared communities: bonus = 0.05 * 3 = 0.15
        assert result.community_bonus == pytest.approx(0.15, abs=1e-6)

    @pytest.mark.unit
    def test_no_shared_communities_no_bonus(self, bifurcation_defines: BifurcationDefines) -> None:
        """No shared communities yields zero community bonus."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": {CommunityType.NEW_AFRIKAN},
            "worker_b": {CommunityType.WOMEN},
        }
        assign_communities_to_graph(graph, memberships)

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.community_bonus == pytest.approx(0.0, abs=1e-6)


class TestSolidarityCeilingClamping:
    """Test effective ceiling clamping to [0, 1]."""

    @pytest.mark.unit
    def test_effective_ceiling_clamped_to_one(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Effective ceiling should not exceed 1.0 even with all bonuses."""
        # Low wage gap (0.9 base) + exploitation bonus (0.2) + 3 communities (0.15)
        # = 1.25 unclamped, should clamp to 1.0
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=50.0, shared_exploiter=True)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED, CommunityType.WOMEN},
            "worker_b": {CommunityType.NEW_AFRIKAN, CommunityType.DISABLED, CommunityType.WOMEN},
        }
        assign_communities_to_graph(graph, memberships)

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.effective_ceiling <= 1.0
        assert result.effective_ceiling >= 0.0

    @pytest.mark.unit
    def test_effective_ceiling_never_negative(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Effective ceiling should never go below 0.0."""
        # Extreme wage gap, no bonuses
        graph = build_ceiling_test_graph(wealth_a=10000.0, wealth_b=0.001)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.effective_ceiling >= 0.0

    @pytest.mark.unit
    def test_zero_wealth_node_handled(self, bifurcation_defines: BifurcationDefines) -> None:
        """Nodes with zero wealth should not cause division by zero."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=0.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        # Should not raise ZeroDivisionError
        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.effective_ceiling >= 0.0
        assert result.effective_ceiling <= 1.0

    @pytest.mark.unit
    def test_equal_wealth_ratio_one(self, bifurcation_defines: BifurcationDefines) -> None:
        """Equal wealth nodes should have ratio 1.0 (below low threshold)."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=50.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.wage_gap_ratio == pytest.approx(1.0, abs=1e-6)
        assert result.base_ceiling == pytest.approx(bifurcation_defines.wage_ceiling_max, abs=1e-6)


class TestSolidarityCeilingGeographic:
    """Test geographic proximity detection."""

    @pytest.mark.unit
    def test_geographic_proximity_default_false(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Without TENANCY/ADJACENCY edges, geographically_proximate is False."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0)
        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.geographically_proximate is False

    @pytest.mark.unit
    def test_geographic_proximity_with_adjacency(
        self, bifurcation_defines: BifurcationDefines
    ) -> None:
        """Agents sharing ADJACENCY-linked territories are proximate."""
        graph = build_ceiling_test_graph(wealth_a=50.0, wealth_b=40.0)

        # Add territory nodes and tenancy/adjacency edges
        graph.add_node("territory_a", _node_type="territory")
        graph.add_node("territory_b", _node_type="territory")
        graph.add_edge(
            "worker_a",
            "territory_a",
            edge_type=EdgeType.TENANCY,
        )
        graph.add_edge(
            "worker_b",
            "territory_b",
            edge_type=EdgeType.TENANCY,
        )
        graph.add_edge(
            "territory_a",
            "territory_b",
            edge_type=EdgeType.ADJACENCY,
        )

        memberships: dict[str, set[CommunityType]] = {
            "worker_a": set(),
            "worker_b": set(),
        }

        result = compute_solidarity_ceiling(
            node_a_id="worker_a",
            node_b_id="worker_b",
            graph=graph,
            agent_memberships=memberships,
            defines=bifurcation_defines,
        )

        assert result.geographically_proximate is True
