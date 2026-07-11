"""R8 → R7 aggregation functions (Feature 036-R8, Task 4).

Aggregates R8 substrate data upward to produce R7-level attributes:
terrain classification, utility coverage fractions, and infrastructure
edge routing.

See Also:
    :mod:`babylon.domain.geography.r8_types`: HexR8State, R8LinearFeature.
    :mod:`babylon.domain.geography.r8_mesh`: R8 mesh generation.
    :mod:`babylon.domain.geography.types`: TerrainClassification.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from babylon.domain.geography.r8_types import HexR8State, R8LinearFeature
from babylon.domain.geography.types import TerrainClassification

logger = logging.getLogger(__name__)


def aggregate_terrain(
    r8_cells: list[HexR8State],
) -> dict[str, TerrainClassification]:
    """Aggregate R8 terrain data to R7 TerrainClassification.

    Groups R8 cells by ``parent_h3``. For each R7 parent:
    - ``water_coverage_fraction`` = count(WATER children) / total children
    - ``resource_coverage_fraction`` = count(RESOURCE children) / total children
    - terrain_type = WATER if water > 0.5, RESOURCE if resource > 0.5
      (and water is not), else LAND

    Args:
        r8_cells: List of HexR8State objects.

    Returns:
        Dict mapping R7 h3_index to TerrainClassification.
    """
    # Group by parent
    by_parent: dict[str, list[HexR8State]] = defaultdict(list)
    for cell in r8_cells:
        by_parent[cell.parent_h3].append(cell)

    result: dict[str, TerrainClassification] = {}

    for r7_hex, children in by_parent.items():
        total = len(children)
        water_count = sum(1 for c in children if c.terrain_type == "WATER")
        resource_count = sum(1 for c in children if c.terrain_type == "RESOURCE")

        water_fraction = water_count / total if total > 0 else 0.0
        resource_fraction = resource_count / total if total > 0 else 0.0

        if water_fraction > 0.5:
            terrain_type = "WATER"
        elif resource_fraction > 0.5:
            terrain_type = "RESOURCE"
        else:
            terrain_type = "LAND"

        result[r7_hex] = TerrainClassification(
            h3_index=r7_hex,
            terrain_type=terrain_type,
            water_coverage_fraction=water_fraction,
            resource_coverage_fraction=resource_fraction,
        )

    logger.info(
        "Aggregated terrain for %d R7 hexes from %d R8 cells",
        len(result),
        len(r8_cells),
    )

    return result


def aggregate_utility_coverage(
    r8_cells: list[HexR8State],
) -> dict[str, dict[str, float]]:
    """Aggregate R8 utility flags to R7 coverage fractions.

    Groups by ``parent_h3``. For each utility type, computes fraction of
    **LAND** children that have service. WATER cells are excluded from
    both numerator and denominator.

    Args:
        r8_cells: List of HexR8State objects.

    Returns:
        Dict mapping R7 h3_index to dict of utility_name → coverage fraction.
        Utility names: ``water_service``, ``sewer``, ``electric``, ``gas``,
        ``broadband``.
    """
    by_parent: dict[str, list[HexR8State]] = defaultdict(list)
    for cell in r8_cells:
        by_parent[cell.parent_h3].append(cell)

    utility_fields = ("water_service", "sewer", "electric", "gas", "broadband")
    attr_map = {
        "water_service": "has_water_service",
        "sewer": "has_sewer",
        "electric": "has_electric",
        "gas": "has_gas",
        "broadband": "has_broadband",
    }

    result: dict[str, dict[str, float]] = {}

    for r7_hex, children in by_parent.items():
        land_children = [c for c in children if c.terrain_type != "WATER"]
        land_count = len(land_children)

        coverage: dict[str, float] = {}
        for utility in utility_fields:
            if land_count == 0:
                coverage[utility] = 0.0
            else:
                has_count = sum(1 for c in land_children if getattr(c, attr_map[utility]))
                coverage[utility] = has_count / land_count

        result[r7_hex] = coverage

    return result


def aggregate_infrastructure_routing(
    r8_features: list[R8LinearFeature],
    r8_cells: list[HexR8State],
) -> dict[tuple[str, str], list[R8LinearFeature]]:
    """Determine which R7 edges each linear feature crosses.

    Groups features by ``source_feature_id``. For each feature, traces its
    R8 cells. Where consecutive R8 cells have different R7 parents, the
    feature crosses that R7 edge.

    Args:
        r8_features: List of R8LinearFeature objects.
        r8_cells: List of HexR8State objects (for parent lookup).

    Returns:
        Dict mapping canonically ordered R7 edge ``(hex_a, hex_b)`` to
        list of features that cross that edge.
    """
    # Build R8 → R7 parent lookup
    r8_to_r7: dict[str, str] = {cell.h3_index: cell.parent_h3 for cell in r8_cells}

    # Group features by source_feature_id (same feature traversing multiple cells)
    by_feature: dict[str | None, list[R8LinearFeature]] = defaultdict(list)
    for feature in r8_features:
        by_feature[feature.source_feature_id].append(feature)

    result: dict[tuple[str, str], list[R8LinearFeature]] = defaultdict(list)

    for _feature_id, feature_cells in by_feature.items():
        # For each pair of consecutive R8 cells in this feature
        for i in range(len(feature_cells) - 1):
            r8_a = feature_cells[i].h3_index
            r8_b = feature_cells[i + 1].h3_index

            r7_a = r8_to_r7.get(r8_a)
            r7_b = r8_to_r7.get(r8_b)

            if r7_a is None or r7_b is None:
                continue

            # If different R7 parents, this feature crosses an R7 edge
            if r7_a != r7_b:
                sorted_pair = sorted([r7_a, r7_b])
                edge_key: tuple[str, str] = (sorted_pair[0], sorted_pair[1])
                result[edge_key].append(feature_cells[i])

    # Convert defaultdict to regular dict
    return dict(result)


__all__ = [
    "aggregate_infrastructure_routing",
    "aggregate_terrain",
    "aggregate_utility_coverage",
]
