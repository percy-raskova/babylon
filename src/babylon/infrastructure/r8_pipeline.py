"""R8 substrate initialization pipeline (Feature 036-R8, Task 6).

Orchestrates the end-to-end R8 substrate generation:
NaturalEarthReader → mesh generation → terrain classification →
linear feature extraction → R7 aggregation.

See Also:
    :mod:`babylon.infrastructure.r8_types`: HexR8State, R8LinearFeature.
    :mod:`babylon.infrastructure.r8_mesh`: generate_r8_mesh, classify_r8_terrain.
    :mod:`babylon.infrastructure.r8_aggregation`: R8 → R7 aggregation.
    :mod:`babylon.infrastructure.natural_earth_reader`: NE data reader.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import h3

from babylon.infrastructure.r8_aggregation import (
    aggregate_infrastructure_routing,
    aggregate_terrain,
    aggregate_utility_coverage,
)
from babylon.infrastructure.r8_mesh import classify_r8_terrain, generate_r8_mesh
from babylon.infrastructure.r8_types import R8FeatureType, R8LinearFeature

if TYPE_CHECKING:
    from babylon.infrastructure.natural_earth_reader import (
        BBox,
        NaturalEarthReader,
        RoadFeature,
    )
    from babylon.infrastructure.r8_types import HexR8State
    from babylon.infrastructure.types import TerrainClassification

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NE road_type → R8FeatureType mapping
# ---------------------------------------------------------------------------

_ROAD_TYPE_MAP: dict[str, R8FeatureType] = {
    "Major Highway": R8FeatureType.HIGHWAY,
    "Beltway": R8FeatureType.HIGHWAY,
    "Bypass": R8FeatureType.HIGHWAY,
    "Secondary Highway": R8FeatureType.ARTERIAL,
    "Road": R8FeatureType.LOCAL_ROAD,
}

# NA supplement road class mapping
_ROAD_CLASS_MAP: dict[str, R8FeatureType] = {
    "Interstate": R8FeatureType.HIGHWAY,
    "Federal": R8FeatureType.HIGHWAY,
    "State": R8FeatureType.ARTERIAL,
    "Other": R8FeatureType.LOCAL_ROAD,
}


def _classify_road(road: RoadFeature) -> R8FeatureType:
    """Map a NE road feature to an R8FeatureType.

    Checks ``road_type`` first (global table), then ``road_class``
    (NA supplement table). Falls back to LOCAL_ROAD.
    """
    if road.road_type and road.road_type in _ROAD_TYPE_MAP:
        return _ROAD_TYPE_MAP[road.road_type]
    if road.road_class and road.road_class in _ROAD_CLASS_MAP:
        return _ROAD_CLASS_MAP[road.road_class]
    return R8FeatureType.LOCAL_ROAD


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class R8SubstrateResult:
    """Result of the R8 substrate build pipeline.

    Contains both R8-level data and aggregated R7-level results.

    Attributes:
        r8_cells: All R8 cells with classified terrain.
        r8_features: Linear infrastructure features mapped to R8 cells.
        r7_terrain: Aggregated R7 terrain classifications.
        r7_utility_coverage: Aggregated R7 utility coverage fractions.
        r7_edge_crossings: R7 edges crossed by linear features.
    """

    r8_cells: list[HexR8State] = field(default_factory=list)
    r8_features: list[R8LinearFeature] = field(default_factory=list)
    r7_terrain: dict[str, TerrainClassification] = field(default_factory=dict)
    r7_utility_coverage: dict[str, dict[str, float]] = field(default_factory=dict)
    r7_edge_crossings: dict[tuple[str, str], list[R8LinearFeature]] = field(
        default_factory=dict,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def build_r8_substrate(
    r7_indices: set[str],
    county_map: dict[str, str],
    bbox: BBox,
    ne_reader: NaturalEarthReader | None = None,
) -> R8SubstrateResult:
    """Build the complete R8 substrate from R7 hexes and NE data.

    Pipeline:

    1. **Generate** R8 mesh (7 children per R7 parent)
    2. **Load** water polygons from NE lakes tables
    3. **Classify** R8 terrain (WATER if >50% lake coverage)
    4. **Load** roads and railroads from NE
    5. **Map** NE features to R8 cells as R8LinearFeature objects
    6. **Aggregate** R8 → R7 terrain, utility coverage, and edge crossings

    Args:
        r7_indices: Set of R7 H3 cell indices.
        county_map: R7 h3_index → 5-digit county FIPS.
        bbox: (min_lon, min_lat, max_lon, max_lat) bounding box for NE queries.
        ne_reader: NaturalEarthReader instance. If None, creates a default one.

    Returns:
        R8SubstrateResult with all R8 and aggregated R7 data.
    """
    if ne_reader is None:
        from babylon.infrastructure.natural_earth_reader import NaturalEarthReader

        ne_reader = NaturalEarthReader()

    # Step 1: Generate R8 mesh
    logger.info("Step 1: Generating R8 mesh from %d R7 hexes", len(r7_indices))
    r8_cells = generate_r8_mesh(r7_indices, county_map)

    # Step 2: Load water polygons
    logger.info("Step 2: Loading lake polygons from NE for bbox %s", bbox)
    lakes = ne_reader.load_lakes(bbox)
    water_polygons = [lake.geometry for lake in lakes]
    logger.info("Loaded %d lake features (%d polygons)", len(lakes), len(water_polygons))

    # Step 3: Classify terrain
    logger.info("Step 3: Classifying R8 terrain")
    r8_cells = classify_r8_terrain(r8_cells, water_polygons)

    # Step 4: Load roads and railroads
    logger.info("Step 4: Loading roads and railroads from NE")
    roads = ne_reader.load_roads(bbox)
    railroads = ne_reader.load_railroads(bbox)
    logger.info("Loaded %d roads, %d railroads", len(roads), len(railroads))

    # Build R8 cell index lookup for spatial matching
    r8_index_set = {cell.h3_index for cell in r8_cells}

    # Step 5: Map NE features to R8 cells
    logger.info("Step 5: Mapping linear features to R8 cells")
    r8_features: list[R8LinearFeature] = []

    # Map roads to R8 cells
    for road in roads:
        feature_type = _classify_road(road)
        feature_name = road.name or f"{road.prefix}{road.number}" or None

        # Sample points along the LineString and find containing R8 cells
        matched_cells = _linestring_to_r8_cells(road.geometry, r8_index_set)
        for r8_hex in matched_cells:
            r8_features.append(
                R8LinearFeature(
                    h3_index=r8_hex,
                    feature_type=feature_type,
                    feature_name=feature_name if feature_name else None,
                    source_dataset=road.source_table or "ne_10m_roads",
                    source_feature_id=str(road.ogc_fid),
                ),
            )

    # Map railroads to R8 cells
    for rr in railroads:
        matched_cells = _linestring_to_r8_cells(rr.geometry, r8_index_set)
        for r8_hex in matched_cells:
            r8_features.append(
                R8LinearFeature(
                    h3_index=r8_hex,
                    feature_type=R8FeatureType.RAIL,
                    feature_name=rr.name if rr.name else None,
                    source_dataset=rr.source_table or "ne_10m_railroads",
                    source_feature_id=str(rr.ogc_fid),
                ),
            )

    logger.info("Mapped %d R8 linear features", len(r8_features))

    # Step 6: Aggregate R8 → R7
    logger.info("Step 6: Aggregating R8 → R7")
    r7_terrain = aggregate_terrain(r8_cells)
    r7_utility_coverage = aggregate_utility_coverage(r8_cells)
    r7_edge_crossings = aggregate_infrastructure_routing(r8_features, r8_cells)

    logger.info(
        "Pipeline complete: %d R8 cells, %d features, %d R7 terrain, %d edge crossings",
        len(r8_cells),
        len(r8_features),
        len(r7_terrain),
        len(r7_edge_crossings),
    )

    return R8SubstrateResult(
        r8_cells=r8_cells,
        r8_features=r8_features,
        r7_terrain=r7_terrain,
        r7_utility_coverage=r7_utility_coverage,
        r7_edge_crossings=r7_edge_crossings,
    )


def _linestring_to_r8_cells(
    geometry: object,
    r8_index_set: set[str],
    sample_interval_m: float = 500.0,
) -> list[str]:
    """Sample a LineString geometry and find containing R8 cells.

    Walks along the geometry at intervals, converting each point to an
    R8 H3 cell index. Only returns cells that are in the provided set.

    Args:
        geometry: Shapely LineString or MultiLineString.
        r8_index_set: Set of valid R8 cell indices to match against.
        sample_interval_m: Approximate sampling interval in meters.

    Returns:
        Ordered list of unique R8 cell indices the feature passes through.
    """
    from shapely.geometry import LineString, MultiLineString  # type: ignore[import-untyped]

    lines: list[LineString] = []
    if isinstance(geometry, MultiLineString):
        lines = list(geometry.geoms)
    elif isinstance(geometry, LineString):
        lines = [geometry]
    else:
        return []

    seen: set[str] = set()
    result: list[str] = []

    for line in lines:
        # Approximate: 1 degree ≈ 111 km; at 500m intervals
        length = line.length  # in degrees
        # Convert degrees to approximate meters (rough at this scale)
        approx_length_m = length * 111_000
        n_samples = max(2, int(approx_length_m / sample_interval_m))

        for i in range(n_samples + 1):
            fraction = i / n_samples
            point = line.interpolate(fraction, normalized=True)
            r8_hex = h3.latlng_to_cell(point.y, point.x, 8)

            if r8_hex in r8_index_set and r8_hex not in seen:
                seen.add(r8_hex)
                result.append(r8_hex)

    return result


__all__ = [
    "R8SubstrateResult",
    "build_r8_substrate",
]
