"""Nonlocal edge generation for airports and shipping lanes (Feature 036, US4).

Airports generate AIR_LINK edges connecting to destination airports.
Ports generate SHIPPING_LANE edges connecting to other Great Lakes ports.
Distance computed via Haversine formula; locality classified per FR-022.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: FR-019 through FR-022.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from babylon.config.defines import InfrastructureDefines
from babylon.infrastructure.types import (
    InfrastructureLinkState,
    NonlocalEdgeState,
    VertexState,
)
from babylon.models.enums import (
    FlowCategory,
    InfrastructureType,
    JunctionType,
    LocalityClass,
)

# Earth radius in km (mean radius per WGS-84)
_EARTH_RADIUS_KM = 6371.0


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Compute great-circle distance between two points in kilometers.

    Args:
        lat1: Latitude of point 1 (degrees).
        lon1: Longitude of point 1 (degrees).
        lat2: Latitude of point 2 (degrees).
        lon2: Longitude of point 2 (degrees).

    Returns:
        Distance in kilometers.
    """
    rlat1 = math.radians(lat1)
    rlat2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2.0) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return _EARTH_RADIUS_KM * c


def _classify_locality(
    distance_km: float,
    avg_hex_diameter_km: float,
) -> str:
    """Classify nonlocal edge by distance ratio (FR-022).

    Ratio = distance_km / avg_hex_diameter_km.
    LOCAL < 3.0, SEMI_LOCAL < 20.0, NONLOCAL >= 20.0.

    Args:
        distance_km: Great-circle distance between endpoints.
        avg_hex_diameter_km: Average hex diameter in km.

    Returns:
        LocalityClass value.
    """
    ratio = distance_km / avg_hex_diameter_km
    if ratio < 3.0:
        return LocalityClass.LOCAL
    if ratio < 20.0:
        return LocalityClass.SEMI_LOCAL
    return LocalityClass.NONLOCAL


def _build_air_link_capacity(defines: InfrastructureDefines) -> dict[str, float]:
    """Build capacity dict for an AIR_LINK from defines.

    Args:
        defines: InfrastructureDefines for coefficient lookup.

    Returns:
        Dict of FlowCategory → capacity for AIR_LINK.
    """
    capacity: dict[str, float] = {}
    for category in FlowCategory:
        val = defines.get_capacity(InfrastructureType.AIR_LINK, category)
        if val > 0.0:
            capacity[category] = val
    return capacity


def _build_shipping_capacity(defines: InfrastructureDefines) -> dict[str, float]:
    """Build capacity dict for a SHIPPING_LANE from defines.

    Args:
        defines: InfrastructureDefines for coefficient lookup.

    Returns:
        Dict of FlowCategory → capacity for SHIPPING_LANE.
    """
    capacity: dict[str, float] = {}
    for category in FlowCategory:
        val = defines.get_capacity(InfrastructureType.SHIPPING_LANE, category)
        if val > 0.0:
            capacity[category] = val
    return capacity


def _scale_capacity(
    base_capacity: dict[str, float],
    source_scale: float,
    dest_scale: float,
) -> dict[str, float]:
    """Scale base capacity by the minimum natlscale of both endpoints.

    Uses min(source, dest) / 100.0 as scaling factor so smaller
    airports/ports bottleneck the connection.

    Args:
        base_capacity: Base capacity from defines.
        source_scale: Source vertex natlscale.
        dest_scale: Destination vertex natlscale.

    Returns:
        Scaled capacity dict.
    """
    scale_factor = min(source_scale, dest_scale) / 100.0
    return {cat: val * scale_factor for cat, val in base_capacity.items()}


def _get_junction_scale(
    vertex: VertexState,
    junction_type: str,
) -> float:
    """Get natlscale from a vertex's junction of the given type.

    Args:
        vertex: Vertex to inspect.
        junction_type: JunctionType to find.

    Returns:
        capacity_contribution (natlscale proxy), or 50.0 default.
    """
    for junction in vertex.junctions:
        if junction.junction_type == junction_type:
            return junction.capacity_contribution
    return 50.0  # default if junction not found


def generate_airport_edges(
    airport_vertices: Sequence[VertexState],
    all_airports: Sequence[VertexState],
    defines: InfrastructureDefines,
    avg_hex_diameter_km: float,
) -> list[NonlocalEdgeState]:
    """Generate AIR_LINK nonlocal edges between airport vertices.

    Creates edges from each airport in ``airport_vertices`` to every
    other airport in ``all_airports`` (excluding self-loops). This
    allows ``airport_vertices`` to be the mesh-local airports and
    ``all_airports`` to include external destinations.

    Args:
        airport_vertices: Airport vertices originating edges.
        all_airports: All airport vertices (including external).
        defines: InfrastructureDefines for capacity coefficients.
        avg_hex_diameter_km: Average hex diameter for locality classification.

    Returns:
        List of NonlocalEdgeState for all generated AIR_LINK edges.
    """
    base_capacity = _build_air_link_capacity(defines)
    edges: list[NonlocalEdgeState] = []
    seen: set[tuple[str, str]] = set()

    for source in airport_vertices:
        source_scale = _get_junction_scale(source, JunctionType.AIRPORT)

        for dest in all_airports:
            if dest.vertex_id == source.vertex_id:
                continue

            # Canonical pair to avoid duplicates
            a, b = sorted([source.vertex_id, dest.vertex_id])
            pair = (a, b)
            if pair in seen:
                continue
            seen.add(pair)

            dest_scale = _get_junction_scale(dest, JunctionType.AIRPORT)
            capacity = _scale_capacity(base_capacity, source_scale, dest_scale)

            distance = _haversine_km(source.lat, source.lon, dest.lat, dest.lon)
            locality = _classify_locality(distance, avg_hex_diameter_km)

            link = InfrastructureLinkState(
                link_id=f"air_{source.vertex_id}_{dest.vertex_id}",
                infra_type=InfrastructureType.AIR_LINK,
                capacity=capacity,
            )

            edges.append(
                NonlocalEdgeState(
                    source_vertex_id=source.vertex_id,
                    target_vertex_id=dest.vertex_id,
                    link=link,
                    distance_km=distance,
                    locality_class=locality,
                    origin_feature=f"AIR_LINK:{source.vertex_id}->{dest.vertex_id}",
                ),
            )

    return edges


def generate_shipping_edges(
    port_vertices: Sequence[VertexState],
    defines: InfrastructureDefines,
    avg_hex_diameter_km: float,
) -> list[NonlocalEdgeState]:
    """Generate SHIPPING_LANE nonlocal edges between port vertices.

    Creates edges between all pairs of port vertices.

    Args:
        port_vertices: Port vertices to connect.
        defines: InfrastructureDefines for capacity coefficients.
        avg_hex_diameter_km: Average hex diameter for locality classification.

    Returns:
        List of NonlocalEdgeState for all generated SHIPPING_LANE edges.
    """
    base_capacity = _build_shipping_capacity(defines)
    edges: list[NonlocalEdgeState] = []

    port_list = list(port_vertices)
    max_idx = len(port_list)

    for i in range(max_idx):
        source = port_list[i]
        source_scale = _get_junction_scale(source, JunctionType.PORT)

        for j in range(i + 1, max_idx):
            dest = port_list[j]
            dest_scale = _get_junction_scale(dest, JunctionType.PORT)

            capacity = _scale_capacity(base_capacity, source_scale, dest_scale)
            distance = _haversine_km(source.lat, source.lon, dest.lat, dest.lon)
            locality = _classify_locality(distance, avg_hex_diameter_km)

            link = InfrastructureLinkState(
                link_id=f"ship_{source.vertex_id}_{dest.vertex_id}",
                infra_type=InfrastructureType.SHIPPING_LANE,
                capacity=capacity,
            )

            edges.append(
                NonlocalEdgeState(
                    source_vertex_id=source.vertex_id,
                    target_vertex_id=dest.vertex_id,
                    link=link,
                    distance_km=distance,
                    locality_class=locality,
                    origin_feature=(f"SHIPPING_LANE:{source.vertex_id}->{dest.vertex_id}"),
                ),
            )

    return edges
