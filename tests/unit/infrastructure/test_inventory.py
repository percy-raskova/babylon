"""Tests for infrastructure inventory management (Feature 036, T018).

Tests CRUD operations on edge links and vertex state queries.
"""

from __future__ import annotations

import pytest

from babylon.infrastructure.inventory import DefaultInfrastructureInventory
from babylon.infrastructure.types import (
    InfrastructureLinkState,
    JunctionState,
    NonlocalEdgeState,
    VertexState,
)
from babylon.models.enums import (
    FlowCategory,
    InfrastructureType,
    JunctionType,
    LocalityClass,
)


def _make_link(
    link_id: str = "link_1",
    infra_type: str = InfrastructureType.HIGHWAY,
    condition: float = 1.0,
) -> InfrastructureLinkState:
    """Create a test infrastructure link."""
    return InfrastructureLinkState(
        link_id=link_id,
        infra_type=infra_type,
        capacity={
            FlowCategory.FREIGHT: 1.0,
            FlowCategory.COMMUTER: 1.0,
            FlowCategory.VALUE: 0.5,
            FlowCategory.CONSCIOUSNESS: 0.3,
        },
        condition=condition,
    )


def _make_vertex(
    vertex_id: str = "vtx_1",
    cells: tuple[str, str, str] = ("cell_a", "cell_b", "cell_c"),
) -> VertexState:
    """Create a test vertex state."""
    return VertexState(
        vertex_id=vertex_id,
        adjacent_h3=cells,
        lat=42.33,
        lon=-83.05,
    )


@pytest.mark.unit
class TestDefaultInfrastructureInventoryEdges:
    """Tests for edge link operations."""

    def test_empty_inventory_no_links(self) -> None:
        """New inventory has no links on any edge."""
        inventory = DefaultInfrastructureInventory()
        links = inventory.get_edge_links("hex_a", "hex_b")
        assert links == []

    def test_add_and_get_edge_link(self) -> None:
        """Adding a link makes it retrievable."""
        inventory = DefaultInfrastructureInventory()
        link = _make_link()
        inventory.add_edge_link("hex_a", "hex_b", link)

        links = inventory.get_edge_links("hex_a", "hex_b")
        assert len(links) == 1
        assert links[0].link_id == "link_1"

    def test_canonical_edge_ordering(self) -> None:
        """Edge keys are canonically ordered regardless of argument order."""
        inventory = DefaultInfrastructureInventory()
        link = _make_link()
        inventory.add_edge_link("hex_b", "hex_a", link)

        # Should be retrievable in either order
        links_ab = inventory.get_edge_links("hex_a", "hex_b")
        links_ba = inventory.get_edge_links("hex_b", "hex_a")
        assert len(links_ab) == 1
        assert len(links_ba) == 1
        assert links_ab[0].link_id == links_ba[0].link_id

    def test_multiple_links_on_edge(self) -> None:
        """Multiple links can coexist on the same edge."""
        inventory = DefaultInfrastructureInventory()
        link1 = _make_link(link_id="highway_1")
        link2 = _make_link(link_id="rail_1", infra_type=InfrastructureType.RAIL)
        inventory.add_edge_link("hex_a", "hex_b", link1)
        inventory.add_edge_link("hex_a", "hex_b", link2)

        links = inventory.get_edge_links("hex_a", "hex_b")
        assert len(links) == 2
        ids = {lnk.link_id for lnk in links}
        assert ids == {"highway_1", "rail_1"}

    def test_degrade_link(self) -> None:
        """Degrading a link reduces its condition."""
        inventory = DefaultInfrastructureInventory()
        link = _make_link(link_id="degradable")
        inventory.add_edge_link("hex_a", "hex_b", link)

        result = inventory.degrade_link("degradable", 0.3)
        assert result.condition == pytest.approx(0.7)

    def test_degrade_link_clamps_to_zero(self) -> None:
        """Degrading past zero clamps to 0.0."""
        inventory = DefaultInfrastructureInventory()
        link = _make_link(link_id="fragile", condition=0.2)
        inventory.add_edge_link("hex_a", "hex_b", link)

        result = inventory.degrade_link("fragile", 0.5)
        assert result.condition == 0.0

    def test_degrade_link_not_found(self) -> None:
        """Degrading nonexistent link raises KeyError."""
        inventory = DefaultInfrastructureInventory()
        with pytest.raises(KeyError, match="nonexistent"):
            inventory.degrade_link("nonexistent", 0.1)

    def test_degrade_link_persists(self) -> None:
        """Degradation is reflected in subsequent get_edge_links calls."""
        inventory = DefaultInfrastructureInventory()
        link = _make_link(link_id="persistent")
        inventory.add_edge_link("hex_a", "hex_b", link)

        inventory.degrade_link("persistent", 0.4)
        links = inventory.get_edge_links("hex_a", "hex_b")
        assert links[0].condition == pytest.approx(0.6)

    def test_get_all_edges(self) -> None:
        """get_all_edges returns all edge keys with links."""
        inventory = DefaultInfrastructureInventory()
        inventory.add_edge_link("hex_a", "hex_b", _make_link(link_id="l1"))
        inventory.add_edge_link("hex_c", "hex_d", _make_link(link_id="l2"))

        edges = inventory.get_all_edges()
        assert len(edges) == 2


@pytest.mark.unit
class TestDefaultInfrastructureInventoryVertices:
    """Tests for vertex state operations."""

    def test_get_vertex_not_found(self) -> None:
        """get_vertex returns None for unknown vertex."""
        inventory = DefaultInfrastructureInventory()
        assert inventory.get_vertex("nonexistent") is None

    def test_add_and_get_vertex(self) -> None:
        """Adding a vertex makes it retrievable."""
        inventory = DefaultInfrastructureInventory()
        vertex = _make_vertex()
        inventory.add_vertex(vertex)

        result = inventory.get_vertex("vtx_1")
        assert result is not None
        assert result.vertex_id == "vtx_1"

    def test_add_junction_to_vertex(self) -> None:
        """Adding a junction to a vertex is reflected in queries."""
        inventory = DefaultInfrastructureInventory()
        vertex = _make_vertex()
        inventory.add_vertex(vertex)

        junction = JunctionState(
            junction_type=JunctionType.INTERCHANGE,
            capacity_contribution=5.0,
        )
        inventory.add_junction("vtx_1", junction)

        result = inventory.get_vertex("vtx_1")
        assert result is not None
        assert len(result.junctions) == 1
        assert result.junctions[0].junction_type == JunctionType.INTERCHANGE


@pytest.mark.unit
class TestDefaultInfrastructureInventoryNonlocal:
    """Tests for nonlocal edge operations."""

    def test_empty_nonlocal_edges(self) -> None:
        """New inventory has no nonlocal edges."""
        inventory = DefaultInfrastructureInventory()
        assert inventory.get_nonlocal_edges() == []

    def test_add_nonlocal_edge(self) -> None:
        """Adding a nonlocal edge makes it retrievable."""
        inventory = DefaultInfrastructureInventory()
        link = _make_link(link_id="air_1", infra_type=InfrastructureType.AIR_LINK)
        edge = NonlocalEdgeState(
            source_vertex_id="vtx_a",
            target_vertex_id="vtx_b",
            link=link,
            distance_km=100.0,
            locality_class=LocalityClass.NONLOCAL,
            origin_feature="DTW Airport",
        )
        inventory.add_nonlocal_edge(edge)

        edges = inventory.get_nonlocal_edges()
        assert len(edges) == 1
        assert edges[0].origin_feature == "DTW Airport"


@pytest.mark.unit
class TestDefaultInfrastructureInventorySerialization:
    """Tests for to_dict/from_dict serialization."""

    def test_roundtrip(self) -> None:
        """Serialize and deserialize preserves state."""
        inventory = DefaultInfrastructureInventory()

        # Add edge links
        link = _make_link(link_id="rt_link")
        inventory.add_edge_link("hex_a", "hex_b", link)

        # Add vertex
        vertex = _make_vertex(vertex_id="rt_vtx")
        inventory.add_vertex(vertex)

        # Serialize
        data = inventory.to_dict()
        restored = DefaultInfrastructureInventory.from_dict(data)

        # Verify
        links = restored.get_edge_links("hex_a", "hex_b")
        assert len(links) == 1
        assert links[0].link_id == "rt_link"

        vtx = restored.get_vertex("rt_vtx")
        assert vtx is not None
        assert vtx.vertex_id == "rt_vtx"
