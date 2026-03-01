"""Tests for edge capacity computation (Feature 036, T019).

Tests aggregate capacity, natural capacity, WATER-WATER zero
enforcement (FR-013), and LAND-LAND natural capacity (FR-014).
"""

from __future__ import annotations

import pytest

from babylon.config.defines import InfrastructureDefines
from babylon.infrastructure.capacity import DefaultEdgeCapacityCalculator
from babylon.infrastructure.types import InfrastructureLinkState
from babylon.models.enums import FlowCategory, InfrastructureType, TerrainType


def _make_link(
    link_id: str = "link_1",
    infra_type: str = InfrastructureType.HIGHWAY,
    condition: float = 1.0,
    capacity: dict[str, float] | None = None,
) -> InfrastructureLinkState:
    """Create a test infrastructure link."""
    default_capacity = {
        FlowCategory.FREIGHT: 1.0,
        FlowCategory.COMMUTER: 1.0,
        FlowCategory.VALUE: 0.5,
        FlowCategory.CONSCIOUSNESS: 0.3,
    }
    return InfrastructureLinkState(
        link_id=link_id,
        infra_type=infra_type,
        capacity=capacity or default_capacity,
        condition=condition,
    )


@pytest.fixture()
def infra_defines() -> InfrastructureDefines:
    """Default infrastructure defines."""
    return InfrastructureDefines()


@pytest.fixture()
def calculator(infra_defines: InfrastructureDefines) -> DefaultEdgeCapacityCalculator:
    """Default capacity calculator."""
    return DefaultEdgeCapacityCalculator(infra_defines)


@pytest.mark.unit
class TestDefaultEdgeCapacityCalculator:
    """Tests for compute_edge_capacity()."""

    def test_no_links_land_land_natural_capacity(
        self,
        calculator: DefaultEdgeCapacityCalculator,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """LAND-LAND edge with no links gets natural capacity for COMMUTER and CONSCIOUSNESS."""
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.LAND,
            links=[],
            population_density=100.0,
        )

        # Natural capacity for COMMUTER and CONSCIOUSNESS
        assert result.natural_capacity[FlowCategory.COMMUTER] > 0.0
        assert result.natural_capacity[FlowCategory.CONSCIOUSNESS] > 0.0
        # No natural capacity for FREIGHT or VALUE
        assert result.natural_capacity.get(FlowCategory.FREIGHT, 0.0) == 0.0
        assert result.natural_capacity.get(FlowCategory.VALUE, 0.0) == 0.0

    def test_water_water_zero_capacity(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """WATER-WATER edges have zero capacity across all categories (FR-013)."""
        link = _make_link()
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.WATER,
            target_terrain=TerrainType.WATER,
            links=[link],
            population_density=100.0,
        )

        for category in FlowCategory:
            assert result.total_capacity.get(category, 0.0) == 0.0

    def test_single_link_aggregate(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """Single link's effective capacity becomes the aggregate."""
        link = _make_link(condition=0.8)
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.LAND,
            links=[link],
            population_density=100.0,
        )

        # Aggregate = effective capacity = capacity * condition
        assert result.aggregate_capacity[FlowCategory.FREIGHT] == pytest.approx(
            1.0 * 0.8,
        )
        assert result.aggregate_capacity[FlowCategory.COMMUTER] == pytest.approx(
            1.0 * 0.8,
        )

    def test_multiple_links_sum(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """Multiple links' effective capacities are summed."""
        link1 = _make_link(link_id="l1", condition=1.0)
        link2 = _make_link(link_id="l2", condition=0.5)
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.LAND,
            links=[link1, link2],
            population_density=100.0,
        )

        # 1.0 * 1.0 + 1.0 * 0.5 = 1.5
        assert result.aggregate_capacity[FlowCategory.FREIGHT] == pytest.approx(1.5)

    def test_total_is_aggregate_plus_natural(
        self,
        calculator: DefaultEdgeCapacityCalculator,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """Total capacity = aggregate + natural for each category."""
        link = _make_link(condition=1.0)
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.LAND,
            links=[link],
            population_density=100.0,
        )

        for category in result.total_capacity:
            expected = result.aggregate_capacity.get(category, 0.0) + result.natural_capacity.get(
                category, 0.0
            )
            assert result.total_capacity[category] == pytest.approx(expected)

    def test_land_water_has_no_natural_capacity(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """LAND-WATER edge gets no natural capacity (only infrastructure-based)."""
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.WATER,
            links=[],
            population_density=100.0,
        )

        for category in FlowCategory:
            assert result.natural_capacity.get(category, 0.0) == 0.0

    def test_degraded_link_reduces_capacity(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """Degraded link condition reduces effective capacity."""
        pristine = _make_link(link_id="pristine", condition=1.0)
        degraded = _make_link(link_id="degraded", condition=0.5)

        result_pristine = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.LAND,
            links=[pristine],
            population_density=100.0,
        )
        result_degraded = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.LAND,
            links=[degraded],
            population_density=100.0,
        )

        assert (
            result_degraded.aggregate_capacity[FlowCategory.FREIGHT]
            < result_pristine.aggregate_capacity[FlowCategory.FREIGHT]
        )

    def test_destroyed_link_zero_contribution(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """Link with condition=0.0 contributes nothing."""
        link = _make_link(condition=0.0)
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.LAND,
            target_terrain=TerrainType.LAND,
            links=[link],
            population_density=100.0,
        )

        for category in FlowCategory:
            assert result.aggregate_capacity.get(category, 0.0) == 0.0

    def test_resource_land_allows_infrastructure(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """RESOURCE-LAND edge allows infrastructure capacity (extraction route)."""
        link = _make_link()
        result = calculator.compute_edge_capacity(
            source_h3="hex_a",
            target_h3="hex_b",
            source_terrain=TerrainType.RESOURCE,
            target_terrain=TerrainType.LAND,
            links=[link],
            population_density=100.0,
        )

        assert result.aggregate_capacity[FlowCategory.FREIGHT] > 0.0


@pytest.mark.unit
class TestComputeMeshWeights:
    """Tests for compute_mesh_weights()."""

    def test_mesh_weights_basic(
        self,
        calculator: DefaultEdgeCapacityCalculator,
    ) -> None:
        """compute_mesh_weights returns weights for all edges."""
        from babylon.infrastructure.inventory import DefaultInfrastructureInventory

        inventory = DefaultInfrastructureInventory()
        link = _make_link()
        inventory.add_edge_link("hex_a", "hex_b", link)

        terrain_map = {
            "hex_a": TerrainType.LAND,
            "hex_b": TerrainType.LAND,
        }
        population_map = {
            "hex_a": 100.0,
            "hex_b": 100.0,
        }
        edges = [("hex_a", "hex_b")]

        result = calculator.compute_mesh_weights(
            inventory=inventory,
            terrain_map=terrain_map,
            population_map=population_map,
            edges=edges,
        )

        assert ("hex_a", "hex_b") in result
        weights = result[("hex_a", "hex_b")]
        assert FlowCategory.FREIGHT in weights
        assert weights[FlowCategory.FREIGHT] > 0.0

    def test_mesh_weights_no_links_natural_only(
        self,
        calculator: DefaultEdgeCapacityCalculator,
        infra_defines: InfrastructureDefines,
    ) -> None:
        """LAND-LAND edge with no links gets natural weight only."""
        from babylon.infrastructure.inventory import DefaultInfrastructureInventory

        inventory = DefaultInfrastructureInventory()
        terrain_map = {
            "hex_a": TerrainType.LAND,
            "hex_b": TerrainType.LAND,
        }
        population_map = {"hex_a": 50.0, "hex_b": 50.0}
        edges = [("hex_a", "hex_b")]

        result = calculator.compute_mesh_weights(
            inventory=inventory,
            terrain_map=terrain_map,
            population_map=population_map,
            edges=edges,
        )

        assert ("hex_a", "hex_b") in result
        weights = result[("hex_a", "hex_b")]
        # Natural capacity for commuter/consciousness only
        assert weights.get(FlowCategory.COMMUTER, 0.0) > 0.0
        assert weights.get(FlowCategory.CONSCIOUSNESS, 0.0) > 0.0
