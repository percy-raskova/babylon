"""R8 mesh generation and terrain classification (Feature 036-R8, Tasks 2-3).

Generates H3 resolution 8 children from R7 parents and classifies terrain
from geographic data sources.

See Also:
    :mod:`babylon.infrastructure.r8_types`: HexR8State model.
    :mod:`babylon.infrastructure.r8_aggregation`: R8 → R7 aggregation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import h3

from babylon.infrastructure.r8_types import HexR8State

if TYPE_CHECKING:
    from shapely.geometry import Polygon  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def generate_r8_mesh(
    r7_indices: set[str],
    county_map: dict[str, str],
) -> list[HexR8State]:
    """Generate R8 cells for all R7 parents.

    For each R7 hex, calls ``h3.cell_to_children(r7_hex, 8)`` to get 7 R8
    children. All children are initialized with ``terrain_type=LAND``, all
    utilities True, and ``elevation_m=None`` (stub).

    Args:
        r7_indices: Set of H3 resolution 7 cell index strings.
        county_map: Mapping of R7 h3_index → 5-digit county FIPS.

    Returns:
        List of HexR8State objects for all generated R8 children.
    """
    if not r7_indices:
        return []

    r8_cells: list[HexR8State] = []

    for r7_hex in sorted(r7_indices):
        county_fips = county_map[r7_hex]
        children = h3.cell_to_children(r7_hex, 8)

        for r8_hex in sorted(children):
            cell = HexR8State(
                h3_index=r8_hex,
                parent_h3=r7_hex,
                county_fips=county_fips,
                terrain_type="LAND",
                water_fraction=0.0,
                elevation_m=None,
                has_water_service=True,
                has_sewer=True,
                has_electric=True,
                has_gas=True,
                has_broadband=True,
            )
            r8_cells.append(cell)

    logger.info(
        "Generated %d R8 cells from %d R7 parents",
        len(r8_cells),
        len(r7_indices),
    )

    return r8_cells


def classify_r8_terrain(
    r8_cells: list[HexR8State],
    water_polygons: list[Polygon],
) -> list[HexR8State]:
    """Classify each R8 cell by terrain type from water polygons.

    For each R8 cell, computes the fraction of cell area covered by water
    polygons. If ``water_fraction > 0.5``, the cell is classified as WATER.
    WATER cells get all utility flags set to False.

    RESOURCE classification is deferred — returns zero RESOURCE cells.

    Uses the same Shapely intersection pattern as
    ``DefaultTerrainClassifier`` in ``terrain.py``.

    Args:
        r8_cells: List of HexR8State objects to classify.
        water_polygons: Shapely Polygon objects representing water bodies.

    Returns:
        New list of HexR8State objects with updated terrain classification.
    """
    from shapely.geometry import Polygon as ShapelyPolygon

    if not water_polygons:
        return list(r8_cells)

    classified: list[HexR8State] = []

    for cell in r8_cells:
        # H3 boundary returns (lat, lon) — Shapely needs (lon, lat)
        boundary = h3.cell_to_boundary(cell.h3_index)
        hex_poly = ShapelyPolygon([(lon, lat) for lat, lon in boundary])
        hex_area = hex_poly.area

        if hex_area == 0.0:
            classified.append(cell)
            continue

        # Compute water coverage
        water_fraction = 0.0
        for water_poly in water_polygons:
            intersection = hex_poly.intersection(water_poly)
            if not intersection.is_empty:
                water_fraction += intersection.area / hex_area

        water_fraction = min(water_fraction, 1.0)

        # Classify: WATER if majority coverage
        if water_fraction > 0.5:
            classified.append(
                HexR8State(
                    h3_index=cell.h3_index,
                    parent_h3=cell.parent_h3,
                    county_fips=cell.county_fips,
                    terrain_type="WATER",
                    water_fraction=water_fraction,
                    elevation_m=cell.elevation_m,
                    has_water_service=False,
                    has_sewer=False,
                    has_electric=False,
                    has_gas=False,
                    has_broadband=False,
                )
            )
        else:
            classified.append(
                HexR8State(
                    h3_index=cell.h3_index,
                    parent_h3=cell.parent_h3,
                    county_fips=cell.county_fips,
                    terrain_type="LAND",
                    water_fraction=water_fraction,
                    elevation_m=cell.elevation_m,
                    has_water_service=cell.has_water_service,
                    has_sewer=cell.has_sewer,
                    has_electric=cell.has_electric,
                    has_gas=cell.has_gas,
                    has_broadband=cell.has_broadband,
                )
            )

    logger.info(
        "Classified %d R8 cells: %d LAND, %d WATER",
        len(classified),
        sum(1 for c in classified if c.terrain_type == "LAND"),
        sum(1 for c in classified if c.terrain_type == "WATER"),
    )

    return classified


__all__ = [
    "classify_r8_terrain",
    "generate_r8_mesh",
]
