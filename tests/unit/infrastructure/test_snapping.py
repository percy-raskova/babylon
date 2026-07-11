"""Tests for spatial snapping of NE features to H3 edges (Feature 036, T017).

Uses mock NaturalEarthReader with canned Shapely geometries.
"""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import h3
import pytest
from shapely.geometry import LineString, Polygon  # type: ignore[import-untyped]

from babylon.config.defines import InfrastructureDefines
from babylon.domain.geography.natural_earth_reader import (
    AirportFeature,
    PortFeature,
    RailroadFeature,
    RoadFeature,
)
from babylon.domain.geography.snapping import DefaultSpatialSnapper
from babylon.domain.geography.types import VertexState
from babylon.models.enums import InfrastructureType, JunctionType


def _hex_polygon(h3_index: str) -> Polygon:
    """Convert H3 cell boundary to Shapely polygon (lon/lat order)."""
    boundary = h3.cell_to_boundary(h3_index)
    return Polygon([(lon, lat) for lat, lon in boundary])


def _shared_boundary_line(h3_a: str, h3_b: str) -> LineString:
    """Approximate shared boundary between two adjacent hexes as a LineString."""
    poly_a = _hex_polygon(h3_a)
    poly_b = _hex_polygon(h3_b)
    shared = poly_a.boundary.intersection(poly_b.boundary)
    # May be MultiPoint or LineString
    if shared.is_empty:
        # Cells not adjacent — return line through midpoint
        ca = poly_a.centroid
        cb = poly_b.centroid
        mid_x = (ca.x + cb.x) / 2
        mid_y = (ca.y + cb.y) / 2
        return LineString([(mid_x - 0.001, mid_y), (mid_x + 0.001, mid_y)])
    if hasattr(shared, "geoms"):
        # MultiPoint — connect points
        coords = [(p.x, p.y) for p in shared.geoms]
        return LineString(coords)
    return shared if isinstance(shared, LineString) else LineString(shared.coords)


def _make_mock_reader(
    roads: list[RoadFeature] | None = None,
    railroads: list[RailroadFeature] | None = None,
    airports: list[AirportFeature] | None = None,
    ports: list[PortFeature] | None = None,
) -> MagicMock:
    """Create a mock NaturalEarthReader returning canned features."""
    reader = MagicMock()
    reader.load_lakes.return_value = []
    reader.load_roads.return_value = roads or []
    reader.load_railroads.return_value = railroads or []
    reader.load_airports.return_value = airports or []
    reader.load_ports.return_value = ports or []
    reader.load_geography_regions.return_value = []
    return reader


@pytest.fixture()
def infra_defines() -> InfrastructureDefines:
    """Default infrastructure defines."""
    return InfrastructureDefines()


@pytest.fixture()
def detroit_center() -> str:
    """H3 cell at Detroit center, resolution 7."""
    return h3.latlng_to_cell(42.33, -83.05, 7)


@pytest.fixture()
def detroit_ring(detroit_center: str) -> set[str]:
    """Center + ring(1) = 7 cells."""
    return h3.grid_disk(detroit_center, 1)


@pytest.mark.unit
class TestDefaultSpatialSnapperLinear:
    """Tests for snap_linear_features()."""

    def test_no_features_no_links(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Empty NE data produces no links on any edge."""
        ring = h3.grid_disk(detroit_center, 1)
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        reader = _make_mock_reader()
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        assert len(result) == 0 or all(len(v) == 0 for v in result.values())

    def test_road_snaps_to_crossing_edge(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """A road crossing a hex boundary is snapped to that edge."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        # Create a road along the shared boundary
        boundary_line = _shared_boundary_line(detroit_center, neighbor)
        road = RoadFeature(
            ogc_fid=1,
            name="I-94",
            prefix="I",
            number="94",
            road_class="Interstate",
            road_type="Major Highway",
            expressway=1,
            scalerank=3,
            geometry=boundary_line.buffer(0.0005),
            source_table="ne_10m_roads",
        )

        reader = _make_mock_reader(roads=[road])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        assert edge in result
        assert len(result[edge]) >= 1
        link = result[edge][0]
        assert link.infra_type == InfrastructureType.HIGHWAY

    def test_railroad_snaps_to_edge(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """A railroad crossing a hex boundary is snapped to that edge."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        boundary_line = _shared_boundary_line(detroit_center, neighbor)
        railroad = RailroadFeature(
            ogc_fid=1,
            name="CSX Main",
            scalerank=5,
            mult_track=1,
            geometry=boundary_line.buffer(0.0005),
            source_table="ne_10m_railroads",
        )

        reader = _make_mock_reader(railroads=[railroad])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        assert edge in result
        assert len(result[edge]) >= 1
        link = result[edge][0]
        assert link.infra_type == InfrastructureType.RAIL

    def test_non_crossing_road_not_snapped(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """A road far from any edge boundary is not snapped."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        # Create a road far away (offset by large amount)
        far_line = LineString([(-80.0, 40.0), (-80.0, 41.0)])
        road = RoadFeature(
            ogc_fid=1,
            name="Far Road",
            prefix="",
            number="",
            road_class="",
            road_type="Major Highway",
            expressway=0,
            scalerank=8,
            geometry=far_line,
            source_table="ne_10m_roads",
        )

        reader = _make_mock_reader(roads=[road])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        assert edge not in result or len(result.get(edge, [])) == 0

    def test_road_type_mapping_arterial(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Secondary Highway maps to ARTERIAL type."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        boundary_line = _shared_boundary_line(detroit_center, neighbor)
        road = RoadFeature(
            ogc_fid=2,
            name="M-10",
            prefix="M",
            number="10",
            road_class="State",
            road_type="Secondary Highway",
            expressway=0,
            scalerank=5,
            geometry=boundary_line.buffer(0.0005),
            source_table="ne_10m_roads",
        )

        reader = _make_mock_reader(roads=[road])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        assert edge in result
        link = result[edge][0]
        assert link.infra_type == InfrastructureType.ARTERIAL

    def test_local_road_mapping(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Non-major, non-secondary roads map to LOCAL_ROAD."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        boundary_line = _shared_boundary_line(detroit_center, neighbor)
        road = RoadFeature(
            ogc_fid=3,
            name="Local St",
            prefix="",
            number="",
            road_class="",
            road_type="Road",
            expressway=0,
            scalerank=8,
            geometry=boundary_line.buffer(0.0005),
            source_table="ne_10m_roads",
        )

        reader = _make_mock_reader(roads=[road])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        assert edge in result
        link = result[edge][0]
        assert link.infra_type == InfrastructureType.LOCAL_ROAD

    def test_link_has_capacity_per_category(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Snapped links have capacity dict with FlowCategory keys."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        boundary_line = _shared_boundary_line(detroit_center, neighbor)
        road = RoadFeature(
            ogc_fid=1,
            name="I-75",
            prefix="I",
            number="75",
            road_class="Interstate",
            road_type="Major Highway",
            expressway=1,
            scalerank=3,
            geometry=boundary_line.buffer(0.0005),
            source_table="ne_10m_roads",
        )

        reader = _make_mock_reader(roads=[road])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        link = result[edge][0]
        assert "freight" in link.capacity
        assert "commuter" in link.capacity
        assert link.capacity["freight"] == infra_defines.highway_freight

    def test_multiple_features_on_same_edge(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Multiple features crossing same boundary produce multiple links."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        boundary_line = _shared_boundary_line(detroit_center, neighbor)
        road = RoadFeature(
            ogc_fid=1,
            name="I-94",
            prefix="I",
            number="94",
            road_class="Interstate",
            road_type="Major Highway",
            expressway=1,
            scalerank=3,
            geometry=boundary_line.buffer(0.0005),
            source_table="ne_10m_roads",
        )
        railroad = RailroadFeature(
            ogc_fid=2,
            name="CSX",
            scalerank=5,
            mult_track=1,
            geometry=boundary_line.buffer(0.0003),
            source_table="ne_10m_railroads",
        )

        reader = _make_mock_reader(roads=[road], railroads=[railroad])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        assert edge in result
        assert len(result[edge]) == 2
        types = {link.infra_type for link in result[edge]}
        assert InfrastructureType.HIGHWAY in types
        assert InfrastructureType.RAIL in types

    def test_link_has_ne_source_id(
        self,
        detroit_center: str,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Links record NE source ID for provenance."""
        ring = list(h3.grid_disk(detroit_center, 1))
        neighbor = next(c for c in ring if c != detroit_center)
        edge = tuple(sorted([detroit_center, neighbor]))

        boundary_line = _shared_boundary_line(detroit_center, neighbor)
        road = RoadFeature(
            ogc_fid=42,
            name="Test Road",
            prefix="",
            number="",
            road_class="",
            road_type="Major Highway",
            expressway=1,
            scalerank=3,
            geometry=boundary_line.buffer(0.0005),
            source_table="ne_10m_roads",
        )

        reader = _make_mock_reader(roads=[road])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_linear_features([edge])

        link = result[edge][0]
        assert link.ne_source_id is not None
        assert "42" in link.ne_source_id


@pytest.mark.unit
class TestDefaultSpatialSnapperPoint:
    """Tests for snap_point_features()."""

    def test_airport_snaps_to_nearest_vertex(
        self,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Airport snaps to nearest vertex within tolerance."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        ring = list(h3.grid_disk(center, 1))
        neighbors = [c for c in ring if c != center]

        # Create vertices from three adjacent cells
        sorted_triple = tuple(sorted([center, neighbors[0], neighbors[1]]))
        vertex_id = hashlib.sha256("|".join(sorted_triple).encode()).hexdigest()[:16]

        lats = []
        lons = []
        for c in sorted_triple:
            lat, lon = h3.cell_to_latlng(c)
            lats.append(lat)
            lons.append(lon)

        vertex = VertexState(
            vertex_id=vertex_id,
            adjacent_h3=sorted_triple,
            lat=sum(lats) / 3.0,
            lon=sum(lons) / 3.0,
        )

        # Place airport at vertex position
        from shapely.geometry import Point  # type: ignore[import-untyped]

        airport = AirportFeature(
            ogc_fid=1,
            name="Test Airport",
            iata_code="TST",
            scalerank=3,
            natlscale=30.0,
            type_="major",
            geometry=Point(vertex.lon, vertex.lat),
        )

        reader = _make_mock_reader(airports=[airport])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_point_features([vertex])

        assert vertex_id in result
        assert len(result[vertex_id]) >= 1
        junction = result[vertex_id][0]
        assert junction.junction_type == JunctionType.AIRPORT

    def test_port_snaps_to_nearest_vertex(
        self,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Port snaps to nearest vertex within tolerance."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        ring = list(h3.grid_disk(center, 1))
        neighbors = [c for c in ring if c != center]

        sorted_triple = tuple(sorted([center, neighbors[0], neighbors[1]]))
        vertex_id = hashlib.sha256("|".join(sorted_triple).encode()).hexdigest()[:16]

        lats = []
        lons = []
        for c in sorted_triple:
            lat, lon = h3.cell_to_latlng(c)
            lats.append(lat)
            lons.append(lon)

        vertex = VertexState(
            vertex_id=vertex_id,
            adjacent_h3=sorted_triple,
            lat=sum(lats) / 3.0,
            lon=sum(lons) / 3.0,
        )

        from shapely.geometry import Point  # type: ignore[import-untyped]

        port = PortFeature(
            ogc_fid=1,
            name="Test Port",
            scalerank=3,
            natlscale=30.0,
            geometry=Point(vertex.lon, vertex.lat),
        )

        reader = _make_mock_reader(ports=[port])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_point_features([vertex])

        assert vertex_id in result
        junction = result[vertex_id][0]
        assert junction.junction_type == JunctionType.PORT

    def test_far_point_not_snapped(
        self,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Points far from any vertex are not snapped."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        ring = list(h3.grid_disk(center, 1))
        neighbors = [c for c in ring if c != center]

        sorted_triple = tuple(sorted([center, neighbors[0], neighbors[1]]))
        vertex_id = hashlib.sha256("|".join(sorted_triple).encode()).hexdigest()[:16]

        lats = []
        lons = []
        for c in sorted_triple:
            lat, lon = h3.cell_to_latlng(c)
            lats.append(lat)
            lons.append(lon)

        vertex = VertexState(
            vertex_id=vertex_id,
            adjacent_h3=sorted_triple,
            lat=sum(lats) / 3.0,
            lon=sum(lons) / 3.0,
        )

        from shapely.geometry import Point  # type: ignore[import-untyped]

        far_airport = AirportFeature(
            ogc_fid=1,
            name="Far Airport",
            iata_code="FAR",
            scalerank=3,
            natlscale=30.0,
            type_="major",
            geometry=Point(-70.0, 35.0),  # Far away
        )

        reader = _make_mock_reader(airports=[far_airport])
        snapper = DefaultSpatialSnapper(reader, infra_defines)
        result = snapper.snap_point_features([vertex])

        assert vertex_id not in result or len(result.get(vertex_id, [])) == 0
