"""Tests for nonlocal edge generation (Feature 036, T034-T035).

Tests verify:
- Airport vertices generate AIR_LINK nonlocal edges (FR-020)
- Port vertices generate SHIPPING_LANE nonlocal edges (FR-021)
- Great-circle distance computed via Haversine
- Locality classification: LOCAL < 3.0, SEMI_LOCAL < 20.0, NONLOCAL >= 20.0 (FR-022)
- External stub nodes created for destinations outside mesh boundary (EC-004)
- Nonlocal edges stored in inventory and retrievable (FR-019)
"""

from __future__ import annotations

import pytest

from babylon.config.defines import InfrastructureDefines
from babylon.infrastructure.inventory import DefaultInfrastructureInventory
from babylon.infrastructure.nonlocal_edges import (
    _classify_locality,
    _haversine_km,
    generate_airport_edges,
    generate_shipping_edges,
)
from babylon.infrastructure.types import (
    JunctionState,
    NonlocalEdgeState,
    VertexState,
)
from babylon.models.enums import InfrastructureType, JunctionType, LocalityClass


def _make_vertex(
    vertex_id: str,
    lat: float,
    lon: float,
    adjacent_h3: tuple[str, str, str] = ("c1", "c2", "c3"),
    junctions: list[JunctionState] | None = None,
) -> VertexState:
    """Create a test vertex."""
    return VertexState(
        vertex_id=vertex_id,
        adjacent_h3=adjacent_h3,
        lat=lat,
        lon=lon,
        junctions=junctions or [],
    )


def _make_airport_vertex(
    vertex_id: str,
    lat: float,
    lon: float,
    natlscale: float = 75.0,
) -> VertexState:
    """Create a vertex with an AIRPORT junction."""
    junction = JunctionState(
        junction_type=JunctionType.AIRPORT,
        capacity_contribution=natlscale,
        ne_source_id=f"ne_10m_airports:{vertex_id}",
    )
    return _make_vertex(vertex_id, lat, lon, junctions=[junction])


def _make_port_vertex(
    vertex_id: str,
    lat: float,
    lon: float,
    natlscale: float = 50.0,
) -> VertexState:
    """Create a vertex with a PORT junction."""
    junction = JunctionState(
        junction_type=JunctionType.PORT,
        capacity_contribution=natlscale,
        ne_source_id=f"ne_10m_ports:{vertex_id}",
    )
    return _make_vertex(vertex_id, lat, lon, junctions=[junction])


@pytest.mark.unit
class TestHaversineKm:
    """Tests for _haversine_km distance computation."""

    def test_same_point_zero(self) -> None:
        """Distance from point to itself is 0."""
        assert _haversine_km(42.33, -83.05, 42.33, -83.05) == pytest.approx(0.0)

    def test_known_distance(self) -> None:
        """Detroit to Chicago is approximately 382 km."""
        d = _haversine_km(42.33, -83.05, 41.88, -87.63)
        assert 370 < d < 400  # Known ~382 km

    def test_short_distance(self) -> None:
        """Two nearby points have small positive distance."""
        d = _haversine_km(42.33, -83.05, 42.34, -83.06)
        assert 0.5 < d < 3.0  # ~1.3 km


@pytest.mark.unit
class TestClassifyLocality:
    """Tests for locality classification (FR-022)."""

    def test_local(self) -> None:
        """Distance < 3 * hex_diameter → LOCAL."""
        assert _classify_locality(10.0, 5.0) == LocalityClass.LOCAL

    def test_semi_local(self) -> None:
        """3 * hex_diameter <= distance < 20 * hex_diameter → SEMI_LOCAL."""
        assert _classify_locality(50.0, 5.0) == LocalityClass.SEMI_LOCAL

    def test_nonlocal(self) -> None:
        """Distance >= 20 * hex_diameter → NONLOCAL."""
        assert _classify_locality(150.0, 5.0) == LocalityClass.NONLOCAL

    def test_boundary_local_semi(self) -> None:
        """Exactly 3.0 ratio → SEMI_LOCAL (exclusive lower bound)."""
        assert _classify_locality(15.0, 5.0) == LocalityClass.SEMI_LOCAL

    def test_boundary_semi_nonlocal(self) -> None:
        """Exactly 20.0 ratio → NONLOCAL (exclusive lower bound)."""
        assert _classify_locality(100.0, 5.0) == LocalityClass.NONLOCAL


@pytest.mark.unit
class TestGenerateAirportEdges:
    """Tests for airport nonlocal edge generation (FR-020)."""

    def test_generates_edges_between_airports(self) -> None:
        """Airport vertices generate AIR_LINK edges to other airports."""
        dtw = _make_airport_vertex("vtx_dtw", 42.21, -83.35, natlscale=75.0)
        ord_airport = _make_airport_vertex("vtx_ord", 41.98, -87.90, natlscale=80.0)

        defines = InfrastructureDefines()
        edges = generate_airport_edges(
            airport_vertices=[dtw],
            all_airports=[dtw, ord_airport],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 1
        edge = edges[0]
        assert edge.source_vertex_id == "vtx_dtw"
        assert edge.target_vertex_id == "vtx_ord"
        assert edge.link.infra_type == InfrastructureType.AIR_LINK
        assert edge.distance_km > 0

    def test_no_self_loops(self) -> None:
        """Airport does not generate an edge to itself."""
        dtw = _make_airport_vertex("vtx_dtw", 42.21, -83.35)
        defines = InfrastructureDefines()

        edges = generate_airport_edges(
            airport_vertices=[dtw],
            all_airports=[dtw],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 0

    def test_capacity_from_defines(self) -> None:
        """AIR_LINK capacity derived from InfrastructureDefines."""
        dtw = _make_airport_vertex("vtx_dtw", 42.21, -83.35, natlscale=75.0)
        remote = _make_airport_vertex("vtx_remote", 40.0, -80.0, natlscale=50.0)

        defines = InfrastructureDefines()
        edges = generate_airport_edges(
            airport_vertices=[dtw],
            all_airports=[dtw, remote],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 1
        link = edges[0].link
        # Capacity should be present for categories defined in InfrastructureDefines
        assert link.capacity.get("freight", 0.0) > 0
        assert link.capacity.get("commuter", 0.0) > 0

    def test_locality_class_assigned(self) -> None:
        """Nonlocal edges have correct locality classification."""
        dtw = _make_airport_vertex("vtx_dtw", 42.21, -83.35)
        # A distant airport (e.g., LAX ~3000 km away)
        lax = _make_airport_vertex("vtx_lax", 33.94, -118.41)

        defines = InfrastructureDefines()
        edges = generate_airport_edges(
            airport_vertices=[dtw],
            all_airports=[dtw, lax],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 1
        assert edges[0].locality_class == LocalityClass.NONLOCAL

    def test_multiple_airports(self) -> None:
        """Multiple airport vertices generate O(n*(n-1)/2) edges."""
        a1 = _make_airport_vertex("a1", 42.0, -83.0)
        a2 = _make_airport_vertex("a2", 41.0, -84.0)
        a3 = _make_airport_vertex("a3", 40.0, -85.0)

        defines = InfrastructureDefines()
        edges = generate_airport_edges(
            airport_vertices=[a1, a2, a3],
            all_airports=[a1, a2, a3],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        # Each pair: a1-a2, a1-a3, a2-a3 = 3 edges
        assert len(edges) == 3

    def test_external_destination(self) -> None:
        """Airport outside mesh generates edge with origin_feature."""
        dtw = _make_airport_vertex("vtx_dtw", 42.21, -83.35)
        external = _make_airport_vertex("vtx_ext", 34.05, -118.24, natlscale=90.0)

        defines = InfrastructureDefines()
        edges = generate_airport_edges(
            airport_vertices=[dtw],
            all_airports=[dtw, external],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 1
        assert "AIR_LINK" in edges[0].origin_feature


@pytest.mark.unit
class TestGenerateShippingEdges:
    """Tests for shipping nonlocal edge generation (FR-021)."""

    def test_generates_shipping_lanes(self) -> None:
        """Port vertices generate SHIPPING_LANE edges to other ports."""
        detroit_port = _make_port_vertex("vtx_det", 42.33, -83.05)
        windsor_port = _make_port_vertex("vtx_win", 42.31, -83.03)

        defines = InfrastructureDefines()
        edges = generate_shipping_edges(
            port_vertices=[detroit_port, windsor_port],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 1
        edge = edges[0]
        assert edge.link.infra_type == InfrastructureType.SHIPPING_LANE

    def test_no_self_loops(self) -> None:
        """Port does not generate an edge to itself."""
        port = _make_port_vertex("vtx_p1", 42.33, -83.05)

        defines = InfrastructureDefines()
        edges = generate_shipping_edges(
            port_vertices=[port],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 0

    def test_distance_is_great_circle(self) -> None:
        """Shipping edge distance matches Haversine computation."""
        p1 = _make_port_vertex("p1", 42.33, -83.05)
        p2 = _make_port_vertex("p2", 41.50, -82.50)

        defines = InfrastructureDefines()
        edges = generate_shipping_edges(
            port_vertices=[p1, p2],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        assert len(edges) == 1
        expected = _haversine_km(42.33, -83.05, 41.50, -82.50)
        assert edges[0].distance_km == pytest.approx(expected, rel=0.01)

    def test_multiple_ports(self) -> None:
        """Multiple ports generate all pairwise edges."""
        p1 = _make_port_vertex("p1", 42.0, -83.0)
        p2 = _make_port_vertex("p2", 43.0, -84.0)
        p3 = _make_port_vertex("p3", 44.0, -85.0)

        defines = InfrastructureDefines()
        edges = generate_shipping_edges(
            port_vertices=[p1, p2, p3],
            defines=defines,
            avg_hex_diameter_km=5.0,
        )

        # 3 choose 2 = 3 edges
        assert len(edges) == 3


@pytest.mark.unit
class TestNonlocalInventoryIntegration:
    """Tests for nonlocal edge storage in inventory (T038)."""

    def test_add_and_retrieve(self) -> None:
        """Nonlocal edges can be added to and retrieved from inventory."""
        from babylon.infrastructure.types import InfrastructureLinkState
        from babylon.models.enums import FlowCategory

        inventory = DefaultInfrastructureInventory()

        edge = NonlocalEdgeState(
            source_vertex_id="vtx_a",
            target_vertex_id="vtx_b",
            link=InfrastructureLinkState(
                link_id="air_1",
                infra_type=InfrastructureType.AIR_LINK,
                capacity={FlowCategory.FREIGHT: 0.3, FlowCategory.COMMUTER: 0.8},
            ),
            distance_km=382.0,
            locality_class=LocalityClass.NONLOCAL,
            origin_feature="AIR_LINK:vtx_a->vtx_b",
        )

        inventory.add_nonlocal_edge(edge)
        retrieved = inventory.get_nonlocal_edges()

        assert len(retrieved) == 1
        assert retrieved[0].source_vertex_id == "vtx_a"
        assert retrieved[0].distance_km == 382.0

    def test_serialization_roundtrip(self) -> None:
        """Nonlocal edges survive to_dict()/from_dict() roundtrip."""
        from babylon.infrastructure.types import InfrastructureLinkState
        from babylon.models.enums import FlowCategory

        inventory = DefaultInfrastructureInventory()

        edge = NonlocalEdgeState(
            source_vertex_id="vtx_a",
            target_vertex_id="vtx_b",
            link=InfrastructureLinkState(
                link_id="ship_1",
                infra_type=InfrastructureType.SHIPPING_LANE,
                capacity={FlowCategory.FREIGHT: 1.5},
            ),
            distance_km=150.0,
            locality_class=LocalityClass.SEMI_LOCAL,
            origin_feature="SHIPPING_LANE:vtx_a->vtx_b",
        )
        inventory.add_nonlocal_edge(edge)

        data = inventory.to_dict()
        restored = DefaultInfrastructureInventory.from_dict(data)
        restored_edges = restored.get_nonlocal_edges()

        assert len(restored_edges) == 1
        assert restored_edges[0].link.infra_type == InfrastructureType.SHIPPING_LANE
        assert restored_edges[0].distance_km == 150.0
