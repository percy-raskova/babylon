"""Tests for junction cascade degradation (Feature 036, T030-T031).

Tests verify:
- Junction degrade cascades to 3 adjacent edges (FR-018)
- Cascade reduces link conditions proportionally
- Junction condition is tracked after degradation
"""

from __future__ import annotations

import pytest

from babylon.infrastructure.inventory import DefaultInfrastructureInventory
from babylon.infrastructure.types import (
    InfrastructureLinkState,
    JunctionState,
    VertexState,
)
from babylon.models.enums import FlowCategory, InfrastructureType, JunctionType


def _make_link(
    link_id: str = "link_1",
    condition: float = 1.0,
) -> InfrastructureLinkState:
    """Create a test link."""
    return InfrastructureLinkState(
        link_id=link_id,
        infra_type=InfrastructureType.HIGHWAY,
        capacity={FlowCategory.FREIGHT: 1.0, FlowCategory.COMMUTER: 1.0},
        condition=condition,
    )


@pytest.mark.unit
class TestJunctionCascade:
    """Tests for degrade_junction() cascade behavior (FR-018)."""

    def test_cascade_affects_three_edges(self) -> None:
        """Junction degradation cascades to all 3 edge pairs from adjacent cells."""
        inventory = DefaultInfrastructureInventory()

        # Setup vertex with 3 adjacent cells
        vertex = VertexState(
            vertex_id="vtx_1",
            adjacent_h3=("cell_a", "cell_b", "cell_c"),
            lat=42.33,
            lon=-83.05,
        )
        inventory.add_vertex(vertex)

        # Add junction
        junction = JunctionState(
            junction_type=JunctionType.INTERCHANGE,
            capacity_contribution=10.0,
            condition=1.0,
        )
        inventory.add_junction("vtx_1", junction)

        # Add links on all 3 edges formed by pairs of adjacent cells
        inventory.add_edge_link("cell_a", "cell_b", _make_link(link_id="ab_link"))
        inventory.add_edge_link("cell_a", "cell_c", _make_link(link_id="ac_link"))
        inventory.add_edge_link("cell_b", "cell_c", _make_link(link_id="bc_link"))

        # Degrade the junction
        affected = inventory.degrade_junction("vtx_1", JunctionType.INTERCHANGE, 0.4)

        # Should affect 3 edges
        assert len(affected) == 3

    def test_cascade_reduces_link_conditions(self) -> None:
        """Links on cascaded edges have reduced conditions."""
        inventory = DefaultInfrastructureInventory()

        vertex = VertexState(
            vertex_id="vtx_1",
            adjacent_h3=("cell_a", "cell_b", "cell_c"),
            lat=42.33,
            lon=-83.05,
        )
        inventory.add_vertex(vertex)

        junction = JunctionState(
            junction_type=JunctionType.INTERCHANGE,
            capacity_contribution=10.0,
            condition=1.0,
        )
        inventory.add_junction("vtx_1", junction)

        inventory.add_edge_link("cell_a", "cell_b", _make_link(link_id="ab_link"))
        inventory.add_edge_link("cell_a", "cell_c", _make_link(link_id="ac_link"))
        inventory.add_edge_link("cell_b", "cell_c", _make_link(link_id="bc_link"))

        # Degrade junction by 0.4 → cascade delta = 0.4 * 0.5 = 0.2
        inventory.degrade_junction("vtx_1", JunctionType.INTERCHANGE, 0.4)

        # Check links — all should have condition reduced by cascade_delta
        ab_links = inventory.get_edge_links("cell_a", "cell_b")
        assert ab_links[0].condition == pytest.approx(0.8)  # 1.0 - 0.2

        ac_links = inventory.get_edge_links("cell_a", "cell_c")
        assert ac_links[0].condition == pytest.approx(0.8)

        bc_links = inventory.get_edge_links("cell_b", "cell_c")
        assert bc_links[0].condition == pytest.approx(0.8)

    def test_junction_condition_reduced(self) -> None:
        """Junction's own condition is reduced after degradation."""
        inventory = DefaultInfrastructureInventory()

        vertex = VertexState(
            vertex_id="vtx_1",
            adjacent_h3=("cell_a", "cell_b", "cell_c"),
            lat=42.33,
            lon=-83.05,
        )
        inventory.add_vertex(vertex)

        junction = JunctionState(
            junction_type=JunctionType.INTERCHANGE,
            capacity_contribution=10.0,
            condition=1.0,
        )
        inventory.add_junction("vtx_1", junction)

        inventory.degrade_junction("vtx_1", JunctionType.INTERCHANGE, 0.3)

        vtx = inventory.get_vertex("vtx_1")
        assert vtx is not None
        assert vtx.junctions[0].condition == pytest.approx(0.7)

    def test_cascade_with_no_links(self) -> None:
        """Junction degradation on edges without links affects nothing."""
        inventory = DefaultInfrastructureInventory()

        vertex = VertexState(
            vertex_id="vtx_1",
            adjacent_h3=("cell_a", "cell_b", "cell_c"),
            lat=42.33,
            lon=-83.05,
        )
        inventory.add_vertex(vertex)

        junction = JunctionState(
            junction_type=JunctionType.INTERCHANGE,
            capacity_contribution=10.0,
            condition=1.0,
        )
        inventory.add_junction("vtx_1", junction)

        # No edge links added — cascade affects no edges
        affected = inventory.degrade_junction("vtx_1", JunctionType.INTERCHANGE, 0.4)
        assert len(affected) == 0

    def test_junction_not_found_raises(self) -> None:
        """Degrading nonexistent junction type raises KeyError."""
        inventory = DefaultInfrastructureInventory()

        vertex = VertexState(
            vertex_id="vtx_1",
            adjacent_h3=("cell_a", "cell_b", "cell_c"),
            lat=42.33,
            lon=-83.05,
        )
        inventory.add_vertex(vertex)

        with pytest.raises(KeyError, match="INTERCHANGE"):
            inventory.degrade_junction("vtx_1", JunctionType.INTERCHANGE, 0.1)

    def test_vertex_not_found_raises(self) -> None:
        """Degrading junction on nonexistent vertex raises KeyError."""
        inventory = DefaultInfrastructureInventory()
        with pytest.raises(KeyError, match="nonexistent"):
            inventory.degrade_junction("nonexistent", JunctionType.INTERCHANGE, 0.1)
