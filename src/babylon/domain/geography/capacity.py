"""Edge capacity computation (Feature 036, US2).

Computes aggregate edge capacity from infrastructure links, adds natural
capacity for LAND-LAND edges, and enforces WATER-WATER zero capacity.

See Also:
    :mod:`babylon.domain.geography.protocols`: EdgeCapacityCalculator.
    ``specs/036-infrastructure-topology/spec.md``: FR-012 through FR-014.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from babylon.config.defines import InfrastructureDefines
from babylon.domain.geography.types import EdgeCapacityResult, InfrastructureLinkState
from babylon.models.enums import FlowCategory, TerrainType

if TYPE_CHECKING:
    from babylon.domain.geography.inventory import DefaultInfrastructureInventory

# Flow categories that receive natural capacity on LAND-LAND edges (FR-014)
_NATURAL_CATEGORIES = frozenset({FlowCategory.COMMUTER, FlowCategory.CONSCIOUSNESS})


class DefaultEdgeCapacityCalculator:
    """Computes aggregate edge capacity from infrastructure links.

    Algorithm:
    1. Sum effective_capacity (capacity * condition) for each link per category
    2. For LAND-LAND edges, add natural_capacity_coefficient for COMMUTER and
       CONSCIOUSNESS categories
    3. For WATER-WATER edges, force all capacities to zero (FR-013)
    4. total = aggregate + natural

    Args:
        defines: InfrastructureDefines for natural capacity and thresholds.
    """

    def __init__(self, defines: InfrastructureDefines) -> None:
        self._defines = defines

    def compute_edge_capacity(
        self,
        source_h3: str,
        target_h3: str,
        source_terrain: str,
        target_terrain: str,
        links: Sequence[InfrastructureLinkState],
        population_density: float,  # noqa: ARG002
    ) -> EdgeCapacityResult:
        """Compute total capacity for an edge.

        Args:
            source_h3: Source hex H3 index.
            target_h3: Target hex H3 index.
            source_terrain: TerrainType of source hex.
            target_terrain: TerrainType of target hex.
            links: Infrastructure links on this edge.
            population_density: Average population density of adjacent hexes.

        Returns:
            EdgeCapacityResult with per-category capacity breakdown.
        """
        # FR-013: WATER-WATER edges have zero capacity
        if source_terrain == TerrainType.WATER and target_terrain == TerrainType.WATER:
            empty: dict[str, float] = {}
            return EdgeCapacityResult(
                source_h3=source_h3,
                target_h3=target_h3,
                aggregate_capacity=empty,
                natural_capacity=empty,
                total_capacity=empty,
            )

        # 1. Aggregate: sum effective capacities per category
        aggregate: dict[str, float] = {}
        for link in links:
            for category in FlowCategory:
                effective = link.effective_capacity(category)
                if effective > 0.0:
                    aggregate[category] = aggregate.get(category, 0.0) + effective

        # 2. Natural capacity: LAND-LAND only, COMMUTER and CONSCIOUSNESS
        natural: dict[str, float] = {}
        is_land_land = source_terrain == TerrainType.LAND and target_terrain == TerrainType.LAND
        if is_land_land:
            nat_coeff = self._defines.natural_capacity_coefficient
            for category in _NATURAL_CATEGORIES:
                natural[category] = nat_coeff

        # 3. Total = aggregate + natural
        all_categories: set[str] = set(aggregate.keys()) | {str(k) for k in natural}
        total: dict[str, float] = {}
        for cat in all_categories:
            total[cat] = aggregate.get(cat, 0.0) + natural.get(cat, 0.0)

        return EdgeCapacityResult(
            source_h3=source_h3,
            target_h3=target_h3,
            aggregate_capacity=aggregate,
            natural_capacity=natural,
            total_capacity=total,
        )

    def compute_mesh_weights(
        self,
        inventory: DefaultInfrastructureInventory,
        terrain_map: dict[str, str],
        population_map: dict[str, float],
        edges: Sequence[tuple[str, str]],
    ) -> dict[tuple[str, str], dict[str, float]]:
        """Compute total capacity for all edges in the mesh.

        Args:
            inventory: Infrastructure inventory to query.
            terrain_map: Mapping of h3_index to TerrainType.
            population_map: Mapping of h3_index to population density.
            edges: List of (source_h3, target_h3) edge pairs.

        Returns:
            Dict mapping edge pair to total capacity per FlowCategory.
        """
        result: dict[tuple[str, str], dict[str, float]] = {}

        for source_h3, target_h3 in edges:
            links = inventory.get_edge_links(source_h3, target_h3)
            source_terrain = terrain_map.get(source_h3, TerrainType.LAND)
            target_terrain = terrain_map.get(target_h3, TerrainType.LAND)
            pop_a = population_map.get(source_h3, 0.0)
            pop_b = population_map.get(target_h3, 0.0)
            avg_pop = (pop_a + pop_b) / 2.0

            edge_result = self.compute_edge_capacity(
                source_h3=source_h3,
                target_h3=target_h3,
                source_terrain=source_terrain,
                target_terrain=target_terrain,
                links=links,
                population_density=avg_pop,
            )

            # Only include edges with nonzero total capacity
            if edge_result.total_capacity:
                result[(source_h3, target_h3)] = edge_result.total_capacity

        return result
