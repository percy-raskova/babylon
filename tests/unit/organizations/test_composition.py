"""Tests for composition calculators (Feature 031, T017-T019/T028).

Tests class_composition, community_composition, lifecycle_composition,
and effective_capacity calculators.
"""

from __future__ import annotations

import pytest

from babylon.models.enums import EdgeType, OrgType
from babylon.organizations.composition import (
    class_composition,
    community_composition,
    effective_capacity,
    lifecycle_composition,
)
from babylon.organizations.types import CompositionResult
from babylon.topology.graph import BabylonGraph


class TestClassComposition:
    """class_composition: analyze class makeup via MEMBERSHIP edges."""

    @pytest.mark.math
    def test_single_membership(self) -> None:
        """Single MEMBERSHIP edge with weight."""
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization", org_type=OrgType.POLITICAL_FACTION)
        G.add_node("sc-001", _node_type="social_class", role="labor_aristocracy")
        G.add_edge("org-001", "sc-001", edge_type=EdgeType.MEMBERSHIP, weight=100)

        result = class_composition("org-001", G)
        assert isinstance(result, CompositionResult)
        assert result.axis == "class"
        assert result.total_members == pytest.approx(100.0)
        assert "labor_aristocracy" in result.distribution
        assert result.distribution["labor_aristocracy"] == pytest.approx(1.0)

    @pytest.mark.math
    def test_multiple_classes(self) -> None:
        """Multiple MEMBERSHIP edges to different classes."""
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")
        G.add_node("sc-prole", _node_type="social_class", role="internal_proletariat")
        G.add_node("sc-la", _node_type="social_class", role="labor_aristocracy")
        G.add_edge("org-001", "sc-prole", edge_type=EdgeType.MEMBERSHIP, weight=60)
        G.add_edge("org-001", "sc-la", edge_type=EdgeType.MEMBERSHIP, weight=40)

        result = class_composition("org-001", G)
        assert result.total_members == pytest.approx(100.0)
        assert result.distribution["internal_proletariat"] == pytest.approx(0.6)
        assert result.distribution["labor_aristocracy"] == pytest.approx(0.4)

    @pytest.mark.math
    def test_no_memberships(self) -> None:
        """No MEMBERSHIP edges = empty distribution."""
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")

        result = class_composition("org-001", G)
        assert result.total_members == pytest.approx(0.0)
        assert result.distribution == {}

    @pytest.mark.math
    def test_ignores_non_membership_edges(self) -> None:
        """Only counts MEMBERSHIP edges, not PRESENCE or COMMAND."""
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")
        G.add_node("sc-001", _node_type="social_class", role="proletariat")
        G.add_node("t-001", _node_type="territory")
        G.add_edge("org-001", "sc-001", edge_type=EdgeType.MEMBERSHIP, weight=50)
        G.add_edge("org-001", "t-001", edge_type=EdgeType.PRESENCE)

        result = class_composition("org-001", G)
        assert result.total_members == pytest.approx(50.0)


class TestCommunityComposition:
    """community_composition: analyze community makeup via MEMBERSHIP edges."""

    @pytest.mark.math
    def test_single_community(self) -> None:
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")
        G.add_node("sc-001", _node_type="social_class", community="new_afrikan")
        G.add_edge("org-001", "sc-001", edge_type=EdgeType.MEMBERSHIP, weight=80)

        result = community_composition("org-001", G)
        assert result.axis == "community"
        assert result.total_members == pytest.approx(80.0)
        assert result.distribution["new_afrikan"] == pytest.approx(1.0)

    @pytest.mark.math
    def test_mixed_communities(self) -> None:
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")
        G.add_node("sc-001", _node_type="social_class", community="new_afrikan")
        G.add_node("sc-002", _node_type="social_class", community="settler")
        G.add_edge("org-001", "sc-001", edge_type=EdgeType.MEMBERSHIP, weight=70)
        G.add_edge("org-001", "sc-002", edge_type=EdgeType.MEMBERSHIP, weight=30)

        result = community_composition("org-001", G)
        assert result.distribution["new_afrikan"] == pytest.approx(0.7)
        assert result.distribution["settler"] == pytest.approx(0.3)

    @pytest.mark.math
    def test_no_memberships(self) -> None:
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")

        result = community_composition("org-001", G)
        assert result.total_members == pytest.approx(0.0)
        assert result.distribution == {}


class TestLifecycleComposition:
    """lifecycle_composition: analyze D-P-D' phases via MEMBERSHIP edges."""

    @pytest.mark.math
    def test_single_phase(self) -> None:
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")
        G.add_node("sc-001", _node_type="social_class", lifecycle_phase="adult")
        G.add_edge("org-001", "sc-001", edge_type=EdgeType.MEMBERSHIP, weight=100)

        result = lifecycle_composition("org-001", G)
        assert result.axis == "lifecycle"
        assert result.total_members == pytest.approx(100.0)
        assert result.distribution["adult"] == pytest.approx(1.0)

    @pytest.mark.math
    def test_mixed_phases(self) -> None:
        G = BabylonGraph()
        G.add_node("org-001", _node_type="organization")
        G.add_node("sc-p", _node_type="social_class", lifecycle_phase="adult")
        G.add_node("sc-d", _node_type="social_class", lifecycle_phase="youth")
        G.add_node("sc-dp", _node_type="social_class", lifecycle_phase="elder")
        G.add_edge("org-001", "sc-p", edge_type=EdgeType.MEMBERSHIP, weight=60)
        G.add_edge("org-001", "sc-d", edge_type=EdgeType.MEMBERSHIP, weight=20)
        G.add_edge("org-001", "sc-dp", edge_type=EdgeType.MEMBERSHIP, weight=20)

        result = lifecycle_composition("org-001", G)
        assert result.total_members == pytest.approx(100.0)
        assert result.distribution["adult"] == pytest.approx(0.6)
        assert result.distribution["youth"] == pytest.approx(0.2)
        assert result.distribution["elder"] == pytest.approx(0.2)


class TestEffectiveCapacity:
    """effective_capacity: lifecycle-weighted capacity constraint."""

    @pytest.mark.math
    def test_all_adults(self) -> None:
        """All adults = full capacity (1.0 fraction)."""
        lifecycle = CompositionResult(
            distribution={"adult": 1.0},
            total_members=100.0,
            axis="lifecycle",
        )
        cap = effective_capacity(lifecycle, elder_capacity_factor=0.2)
        assert cap == pytest.approx(1.0)

    @pytest.mark.math
    def test_with_elders(self) -> None:
        """Elders reduce effective capacity."""
        lifecycle = CompositionResult(
            distribution={"adult": 0.6, "elder": 0.4},
            total_members=100.0,
            axis="lifecycle",
        )
        # effective = 0.6 * 1.0 + 0.4 * 0.2 = 0.6 + 0.08 = 0.68
        cap = effective_capacity(lifecycle, elder_capacity_factor=0.2)
        assert cap == pytest.approx(0.68)

    @pytest.mark.math
    def test_all_elders(self) -> None:
        """All elders = reduced capacity."""
        lifecycle = CompositionResult(
            distribution={"elder": 1.0},
            total_members=100.0,
            axis="lifecycle",
        )
        cap = effective_capacity(lifecycle, elder_capacity_factor=0.2)
        assert cap == pytest.approx(0.2)

    @pytest.mark.math
    def test_empty_composition(self) -> None:
        """Empty composition = zero capacity."""
        lifecycle = CompositionResult(
            distribution={},
            total_members=0.0,
            axis="lifecycle",
        )
        cap = effective_capacity(lifecycle, elder_capacity_factor=0.2)
        assert cap == pytest.approx(0.0)

    @pytest.mark.math
    def test_youth_zero_capacity(self) -> None:
        """Youth contribute zero capacity."""
        lifecycle = CompositionResult(
            distribution={"youth": 0.5, "adult": 0.5},
            total_members=100.0,
            axis="lifecycle",
        )
        # effective = 0.5 * 0.0 + 0.5 * 1.0 = 0.5
        cap = effective_capacity(lifecycle, elder_capacity_factor=0.2)
        assert cap == pytest.approx(0.5)
