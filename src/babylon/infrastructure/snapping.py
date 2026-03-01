"""Spatial snapping of NE features to H3 mesh edges/vertices (Feature 036).

Snaps Natural Earth linear features (roads, railroads) to H3 mesh edges
by testing intersection with buffered shared boundaries. Snaps point
features (airports, ports) to nearest mesh vertex by Haversine distance.

See Also:
    :mod:`babylon.infrastructure.protocols`: SpatialSnapper.
    ``specs/036-infrastructure-topology/spec.md``: FR-011, FR-017.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

import h3
from shapely.geometry import Polygon  # type: ignore[import-untyped]

from babylon.config.defines import InfrastructureDefines
from babylon.infrastructure.types import (
    InfrastructureLinkState,
    JunctionState,
    VertexState,
)
from babylon.models.enums import FlowCategory, InfrastructureType, JunctionType

if TYPE_CHECKING:
    from babylon.infrastructure.natural_earth_reader import (
        NaturalEarthReader,
        RoadFeature,
    )

# Maximum snap distance for point features in degrees (~20 km at 42N)
_MAX_SNAP_DISTANCE_DEG = 0.2


def _hex_polygon(h3_index: str) -> Polygon:
    """Convert H3 cell boundary to Shapely polygon (lon/lat order)."""
    boundary = h3.cell_to_boundary(h3_index)
    return Polygon([(lon, lat) for lat, lon in boundary])


def _classify_road(road: RoadFeature) -> str:
    """Classify a NE road feature into InfrastructureType.

    Mapping:
    - ``expressway=1`` or ``road_type="Major Highway"`` → HIGHWAY
    - ``road_type="Secondary Highway"`` → ARTERIAL
    - Everything else → LOCAL_ROAD

    Args:
        road: NE road feature.

    Returns:
        InfrastructureType value.
    """
    if road.expressway == 1 or road.road_type == "Major Highway":
        return InfrastructureType.HIGHWAY
    if road.road_type == "Secondary Highway":
        return InfrastructureType.ARTERIAL
    return InfrastructureType.LOCAL_ROAD


def _road_capacity(infra_type: str, defines: InfrastructureDefines) -> dict[str, float]:
    """Build capacity dict for a road's infrastructure type.

    Args:
        infra_type: InfrastructureType value.
        defines: InfrastructureDefines for coefficient lookup.

    Returns:
        Dict of FlowCategory → capacity.
    """
    capacity: dict[str, float] = {}
    for category in FlowCategory:
        val = defines.get_capacity(infra_type, category)
        if val > 0.0:
            capacity[category] = val
    return capacity


def _make_link_id(source_table: str, ogc_fid: int, edge_key: str) -> str:
    """Create a deterministic link ID from source metadata.

    Args:
        source_table: NE table name (e.g., "ne_10m_roads").
        ogc_fid: Feature ID from the NE table.
        edge_key: Canonical edge key string.

    Returns:
        Unique link ID string.
    """
    raw = f"{source_table}:{ogc_fid}:{edge_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _haversine_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in degrees between two points.

    Uses the Euclidean approximation on longitude adjusted by cos(lat).
    Sufficient for vertex-to-feature snapping at city scale.

    Args:
        lat1: Latitude of point 1.
        lon1: Longitude of point 1.
        lat2: Latitude of point 2.
        lon2: Longitude of point 2.

    Returns:
        Approximate distance in degrees.
    """
    dlat = lat2 - lat1
    dlon = (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(dlat * dlat + dlon * dlon)


class DefaultSpatialSnapper:
    """Snaps NE geographic features to H3 mesh edges and vertices.

    Linear features (roads, railroads) are snapped to edges by testing
    intersection with a buffered shared boundary polygon. Point features
    (airports, ports) are snapped to the nearest vertex within a distance
    tolerance.

    Args:
        reader: NaturalEarthReader for loading geographic features.
        defines: InfrastructureDefines for capacity coefficients and tolerances.
    """

    def __init__(
        self,
        reader: NaturalEarthReader,
        defines: InfrastructureDefines,
    ) -> None:
        self._reader = reader
        self._defines = defines

    def snap_linear_features(
        self,
        edges: Sequence[tuple[str, str]],
    ) -> dict[tuple[str, str], list[InfrastructureLinkState]]:
        """Snap NE linear features (roads, railroads) to H3 edges.

        Algorithm:
        1. Compute mesh bounding box from all edge cells
        2. Load all NE roads and railroads in the bbox
        3. For each edge, compute shared boundary polygon
        4. Buffer boundary by hex_diameter * snap_buffer_fraction
        5. Test each feature against the buffered boundary
        6. Create InfrastructureLinkState for each match

        Args:
            edges: List of (source_h3, target_h3) edge pairs.

        Returns:
            Dict mapping edge pairs to lists of snapped infrastructure links.
        """
        if not edges:
            return {}

        # Collect all unique cells and compute mesh bbox
        all_cells: set[str] = set()
        for src, tgt in edges:
            all_cells.add(src)
            all_cells.add(tgt)

        bbox = self._compute_bbox(all_cells)

        # Load features
        roads = self._reader.load_roads(bbox)
        railroads = self._reader.load_railroads(bbox)

        if not roads and not railroads:
            return {}

        # Pre-compute hex polygons and shared boundary buffers per edge
        result: dict[tuple[str, str], list[InfrastructureLinkState]] = {}

        for src, tgt in edges:
            edge_key = f"{src}|{tgt}"
            poly_src = _hex_polygon(src)
            poly_tgt = _hex_polygon(tgt)

            # Shared boundary
            shared = poly_src.boundary.intersection(poly_tgt.boundary)
            if shared.is_empty:
                continue

            # Buffer the boundary
            hex_diameter = math.sqrt(poly_src.area) * 2.0
            buffer_dist = hex_diameter * self._defines.snap_buffer_fraction
            snap_zone = shared.buffer(buffer_dist)

            links: list[InfrastructureLinkState] = []

            # Test roads
            for road in roads:
                if road.geometry.intersects(snap_zone):
                    infra_type = _classify_road(road)
                    capacity = _road_capacity(infra_type, self._defines)
                    link_id = _make_link_id(
                        road.source_table or "ne_10m_roads",
                        road.ogc_fid,
                        edge_key,
                    )
                    links.append(
                        InfrastructureLinkState(
                            link_id=link_id,
                            infra_type=infra_type,
                            capacity=capacity,
                            ne_source_id=f"{road.source_table}:{road.ogc_fid}",
                        ),
                    )

            # Test railroads
            for railroad in railroads:
                if railroad.geometry.intersects(snap_zone):
                    capacity = _road_capacity(InfrastructureType.RAIL, self._defines)
                    link_id = _make_link_id(
                        railroad.source_table or "ne_10m_railroads",
                        railroad.ogc_fid,
                        edge_key,
                    )
                    links.append(
                        InfrastructureLinkState(
                            link_id=link_id,
                            infra_type=InfrastructureType.RAIL,
                            capacity=capacity,
                            ne_source_id=(f"{railroad.source_table}:{railroad.ogc_fid}"),
                        ),
                    )

            if links:
                result[(src, tgt)] = links

        return result

    def snap_point_features(
        self,
        vertices: Sequence[VertexState],
    ) -> dict[str, list[JunctionState]]:
        """Snap NE point features (airports, ports) to H3 vertices.

        For each point feature, finds the nearest vertex within tolerance
        and creates a JunctionState.

        Args:
            vertices: List of vertex states with positions.

        Returns:
            Dict mapping vertex_id to lists of snapped junction states.
        """
        if not vertices:
            return {}

        # Compute bbox from vertex positions
        lats = [v.lat for v in vertices]
        lons = [v.lon for v in vertices]
        bbox = (min(lons) - 0.5, min(lats) - 0.5, max(lons) + 0.5, max(lats) + 0.5)

        airports = self._reader.load_airports(bbox)
        ports = self._reader.load_ports(bbox)

        result: dict[str, list[JunctionState]] = {}

        # Snap airports
        for airport in airports:
            pt_lon = airport.geometry.centroid.x
            pt_lat = airport.geometry.centroid.y
            best_vertex, best_dist = self._find_nearest_vertex(
                pt_lat,
                pt_lon,
                vertices,
            )
            if best_vertex is not None and best_dist <= _MAX_SNAP_DISTANCE_DEG:
                junction = JunctionState(
                    junction_type=JunctionType.AIRPORT,
                    capacity_contribution=airport.natlscale,
                    ne_source_id=f"ne_10m_airports:{airport.ogc_fid}",
                )
                if best_vertex.vertex_id not in result:
                    result[best_vertex.vertex_id] = []
                result[best_vertex.vertex_id].append(junction)

        # Snap ports
        for port in ports:
            pt_lon = port.geometry.centroid.x
            pt_lat = port.geometry.centroid.y
            best_vertex, best_dist = self._find_nearest_vertex(
                pt_lat,
                pt_lon,
                vertices,
            )
            if best_vertex is not None and best_dist <= _MAX_SNAP_DISTANCE_DEG:
                junction = JunctionState(
                    junction_type=JunctionType.PORT,
                    capacity_contribution=port.natlscale,
                    ne_source_id=f"ne_10m_ports:{port.ogc_fid}",
                )
                if best_vertex.vertex_id not in result:
                    result[best_vertex.vertex_id] = []
                result[best_vertex.vertex_id].append(junction)

        return result

    @staticmethod
    def _find_nearest_vertex(
        lat: float,
        lon: float,
        vertices: Sequence[VertexState],
    ) -> tuple[VertexState | None, float]:
        """Find the nearest vertex to a point.

        Args:
            lat: Point latitude.
            lon: Point longitude.
            vertices: Candidate vertices.

        Returns:
            Tuple of (nearest vertex or None, distance in degrees).
        """
        best_vertex: VertexState | None = None
        best_dist = float("inf")

        for vertex in vertices:
            dist = _haversine_deg(lat, lon, vertex.lat, vertex.lon)
            if dist < best_dist:
                best_dist = dist
                best_vertex = vertex

        return best_vertex, best_dist

    @staticmethod
    def _compute_bbox(cells: set[str]) -> tuple[float, float, float, float]:
        """Compute bounding box for a set of H3 cells.

        Args:
            cells: Set of H3 cell index strings.

        Returns:
            (min_lon, min_lat, max_lon, max_lat) tuple.
        """
        min_lat = float("inf")
        min_lon = float("inf")
        max_lat = float("-inf")
        max_lon = float("-inf")

        for cell in cells:
            lat, lon = h3.cell_to_latlng(cell)
            min_lat = min(min_lat, lat)
            min_lon = min(min_lon, lon)
            max_lat = max(max_lat, lat)
            max_lon = max(max_lon, lon)

        # Add margin (~1 hex diameter at resolution 7)
        margin = 0.05
        return (
            min_lon - margin,
            min_lat - margin,
            max_lon + margin,
            max_lat + margin,
        )
