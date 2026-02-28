"""Tests for key figure identification and cohesion loss (Feature 031, T026).

Tests identify_key_figures() finding articulation points and
cohesion_loss_on_removal() for vulnerability analysis.
"""

from __future__ import annotations

import networkx as nx
import pytest

from babylon.config.defines import OrganizationDefines
from babylon.models.enums import EdgeType
from babylon.organizations.topology import cohesion_loss_on_removal, identify_key_figures


class TestIdentifyKeyFiguresStar:
    """STAR topology: center is sole articulation point."""

    @pytest.mark.math
    def test_star_center_is_key_figure(self) -> None:
        """Hub of star is the sole articulation point."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-hub", "kf-a", "kf-b", "kf-c"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        G.add_edge("kf-hub", "kf-a", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-hub", "kf-b", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-hub", "kf-c", edge_type=EdgeType.COMMAND)

        key_figs = identify_key_figures("org-001", nodes, G)
        kf_ids = [kf.id for kf in key_figs]
        assert "kf-hub" in kf_ids
        assert len(key_figs) == 1

    @pytest.mark.math
    def test_star_center_is_singleton(self) -> None:
        """Hub of star has is_singleton=True (no structural equivalent)."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-hub", "kf-a", "kf-b", "kf-c"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        G.add_edge("kf-hub", "kf-a", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-hub", "kf-b", edge_type=EdgeType.COMMAND)
        G.add_edge("kf-hub", "kf-c", edge_type=EdgeType.COMMAND)

        key_figs = identify_key_figures("org-001", nodes, G)
        hub_kf = [kf for kf in key_figs if kf.id == "kf-hub"][0]
        assert hub_kf.is_singleton is True

    @pytest.mark.math
    def test_star_center_high_structural_importance(self) -> None:
        """Hub of star has structural_importance > 0.8 (Scenario 8).

        Uses 7-node star (1 hub + 6 leaves) so importance = (6-1)/(7-1) = 0.833.
        """
        G: nx.DiGraph[str] = nx.DiGraph()
        leaves = [f"kf-{i}" for i in range(6)]
        nodes = ["kf-hub", *leaves]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        for leaf in leaves:
            G.add_edge("kf-hub", leaf, edge_type=EdgeType.COMMAND)

        key_figs = identify_key_figures("org-001", nodes, G)
        hub_kf = [kf for kf in key_figs if kf.id == "kf-hub"][0]
        assert hub_kf.structural_importance > 0.8


class TestIdentifyKeyFiguresCell:
    """CELL topology: only cutout nodes are key figures."""

    @pytest.mark.math
    def test_cell_bridge_is_key_figure(self) -> None:
        """Bridge/cutout connecting two cells is the key figure."""
        G: nx.DiGraph[str] = nx.DiGraph()
        cell1 = ["kf-a", "kf-b", "kf-c"]
        cell2 = ["kf-d", "kf-e", "kf-f"]
        bridge = "kf-bridge"
        all_nodes = [*cell1, *cell2, bridge]
        for n in all_nodes:
            G.add_node(n, _node_type="key_figure")

        for i, src in enumerate(cell1):
            for j, tgt in enumerate(cell1):
                if i != j:
                    G.add_edge(src, tgt, edge_type=EdgeType.COMMAND)
        for i, src in enumerate(cell2):
            for j, tgt in enumerate(cell2):
                if i != j:
                    G.add_edge(src, tgt, edge_type=EdgeType.COMMAND)
        G.add_edge("kf-c", bridge, edge_type=EdgeType.COMMAND)
        G.add_edge(bridge, "kf-d", edge_type=EdgeType.COMMAND)

        key_figs = identify_key_figures("org-001", all_nodes, G)
        kf_ids = [kf.id for kf in key_figs]
        assert bridge in kf_ids


class TestIdentifyKeyFiguresMesh:
    """MESH topology: no/few key figures (highly connected)."""

    @pytest.mark.math
    def test_mesh_no_key_figures(self) -> None:
        """Complete graph has no articulation points → no key figures."""
        G: nx.DiGraph[str] = nx.DiGraph()
        nodes = ["kf-a", "kf-b", "kf-c", "kf-d"]
        for n in nodes:
            G.add_node(n, _node_type="key_figure")
        for i, src in enumerate(nodes):
            for j, tgt in enumerate(nodes):
                if i != j:
                    G.add_edge(src, tgt, edge_type=EdgeType.COMMAND)

        key_figs = identify_key_figures("org-001", nodes, G)
        assert len(key_figs) == 0


class TestCohesionLossOnRemoval:
    """cohesion_loss_on_removal: reducing cohesion when key figures removed."""

    @pytest.mark.math
    def test_remove_one_key_figure(self) -> None:
        """Removing one key figure drops cohesion by cohesion_loss_per_key_figure."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.8,
            removed_count=1,
            defines=defines,
        )
        # 0.8 - 0.2 = 0.6
        assert new_cohesion == pytest.approx(0.6)

    @pytest.mark.math
    def test_remove_two_key_figures(self) -> None:
        """Removing two key figures drops cohesion by 2 × loss_per."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.8,
            removed_count=2,
            defines=defines,
        )
        # 0.8 - 2*0.2 = 0.4
        assert new_cohesion == pytest.approx(0.4)

    @pytest.mark.math
    def test_floor_at_min_threshold(self) -> None:
        """Cohesion never drops below min_cohesion_threshold."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.3,
            removed_count=5,
            defines=defines,
        )
        # 0.3 - 5*0.2 = -0.7, clamped to 0.05
        assert new_cohesion == pytest.approx(0.05)

    @pytest.mark.math
    def test_remove_all_key_figures_hits_floor(self) -> None:
        """Removing all key figures leaves cohesion at floor."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.6,
            removed_count=10,
            defines=defines,
        )
        assert new_cohesion == pytest.approx(0.05)

    @pytest.mark.math
    def test_zero_removed(self) -> None:
        """Removing zero key figures = no change."""
        defines = OrganizationDefines()
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.8,
            removed_count=0,
            defines=defines,
        )
        assert new_cohesion == pytest.approx(0.8)

    @pytest.mark.math
    def test_custom_defines(self) -> None:
        """Custom defines override loss and floor values."""
        defines = OrganizationDefines(
            cohesion_loss_per_key_figure=0.1,
            min_cohesion_threshold=0.1,
        )
        new_cohesion = cohesion_loss_on_removal(
            current_cohesion=0.5,
            removed_count=3,
            defines=defines,
        )
        # 0.5 - 3*0.1 = 0.2
        assert new_cohesion == pytest.approx(0.2)
