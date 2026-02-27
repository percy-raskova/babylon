"""Unit tests for multi-resolution aggregation (T024).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests DefaultResolutionAggregator: r7->r6 summation, r7->r5 summation,
hierarchical conservation, capital-weighted profit rate, invalid resolution.
"""

from __future__ import annotations

import pytest

from babylon.economics.substrate.aggregation import DefaultResolutionAggregator
from babylon.economics.substrate.production import DefaultHexProductionComputer
from babylon.economics.substrate.types import HexGrid


def _sum_total_capital(grid: HexGrid) -> float:
    """Sum c + v + s across all hexes."""
    total = 0.0
    for h in grid.hexes.values():
        total += h.constant_capital + h.variable_capital + h.surplus_value
    return total


@pytest.mark.unit
class TestDefaultResolutionAggregator:
    """Tests for DefaultResolutionAggregator."""

    def test_aggregate_r7_to_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Test r7 -> r6 summation produces correct number of parents."""
        aggregator = DefaultResolutionAggregator()
        r6_totals = aggregator.aggregate(hydrated_hex_grid, target_resolution=6)

        # 3 counties, each with 1 r6 parent -> 3 parent IDs
        assert len(r6_totals) == 3

        # Each parent total should be positive (hydrated grid has nonzero capital)
        for parent_id, total in r6_totals.items():
            assert total > 0.0, f"Parent {parent_id} has zero total capital"

    def test_aggregate_r7_to_r5(self, hydrated_hex_grid: HexGrid) -> None:
        """Test r7 -> r5 summation produces correct number of parents."""
        aggregator = DefaultResolutionAggregator()
        r5_totals = aggregator.aggregate(hydrated_hex_grid, target_resolution=5)

        # 3 counties, each with 1 r5 parent -> 3 parent IDs
        assert len(r5_totals) == 3

        for parent_id, total in r5_totals.items():
            assert total > 0.0, f"Parent {parent_id} has zero total capital"

    def test_hierarchical_conservation(self, hydrated_hex_grid: HexGrid) -> None:
        """Test that sum of r6 parent values equals sum of all r7 hexes."""
        aggregator = DefaultResolutionAggregator()

        r6_totals = aggregator.aggregate(hydrated_hex_grid, target_resolution=6)
        r5_totals = aggregator.aggregate(hydrated_hex_grid, target_resolution=5)

        hex_total = _sum_total_capital(hydrated_hex_grid)
        r6_sum = sum(r6_totals.values())
        r5_sum = sum(r5_totals.values())

        assert abs(hex_total - r6_sum) < 1e-10
        assert abs(hex_total - r5_sum) < 1e-10

    def test_r6_and_r5_match(self, hydrated_hex_grid: HexGrid) -> None:
        """Test that r6 and r5 aggregations yield the same global total."""
        aggregator = DefaultResolutionAggregator()

        r6_sum = sum(aggregator.aggregate(hydrated_hex_grid, target_resolution=6).values())
        r5_sum = sum(aggregator.aggregate(hydrated_hex_grid, target_resolution=5).values())

        assert abs(r6_sum - r5_sum) < 1e-10

    def test_invalid_resolution_raises_value_error(self, hydrated_hex_grid: HexGrid) -> None:
        """Test that target_resolution not in {5, 6} raises ValueError."""
        aggregator = DefaultResolutionAggregator()

        with pytest.raises(ValueError, match="target_resolution must be 5 or 6"):
            aggregator.aggregate(hydrated_hex_grid, target_resolution=4)

        with pytest.raises(ValueError, match="target_resolution must be 5 or 6"):
            aggregator.aggregate(hydrated_hex_grid, target_resolution=7)

    def test_capital_weighted_profit_rate_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Test capital-weighted profit rate at r6."""
        # First compute production to populate profit rates
        prod = DefaultHexProductionComputer()
        grid_with_rates = prod.compute_production(hydrated_hex_grid)

        aggregator = DefaultResolutionAggregator()
        weighted_rates = aggregator.compute_weighted_profit_rate(
            grid_with_rates, target_resolution=6
        )

        assert len(weighted_rates) == 3

        # Verify by manual calculation for one parent
        for parent_id, rate in weighted_rates.items():
            child_ids = grid_with_rates.res6_children[parent_id]
            total_s = 0.0
            total_cv = 0.0
            for child_id in child_ids:
                h = grid_with_rates.hexes[child_id]
                total_s += h.surplus_value
                total_cv += h.constant_capital + h.variable_capital

            expected_rate = total_s / total_cv if total_cv > 0 else 0.0
            assert rate == pytest.approx(expected_rate)

    def test_capital_weighted_profit_rate_r5(self, hydrated_hex_grid: HexGrid) -> None:
        """Test capital-weighted profit rate at r5."""
        prod = DefaultHexProductionComputer()
        grid_with_rates = prod.compute_production(hydrated_hex_grid)

        aggregator = DefaultResolutionAggregator()
        weighted_rates = aggregator.compute_weighted_profit_rate(
            grid_with_rates, target_resolution=5
        )

        assert len(weighted_rates) == 3

        for parent_id, rate in weighted_rates.items():
            assert rate > 0.0, f"Parent {parent_id} has zero weighted profit rate"

    def test_weighted_profit_rate_invalid_resolution(self, hydrated_hex_grid: HexGrid) -> None:
        """Test compute_weighted_profit_rate raises for invalid resolution."""
        aggregator = DefaultResolutionAggregator()

        with pytest.raises(ValueError, match="target_resolution must be 5 or 6"):
            aggregator.compute_weighted_profit_rate(hydrated_hex_grid, target_resolution=3)

    def test_empty_grid_aggregation(self) -> None:
        """Test aggregation on empty grid returns empty dict."""
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        aggregator = DefaultResolutionAggregator()
        r6_totals = aggregator.aggregate(grid, target_resolution=6)
        assert len(r6_totals) == 0

    def test_per_county_totals_r6(self, hydrated_hex_grid: HexGrid) -> None:
        """Test that each r6 parent total equals its children's sum."""
        aggregator = DefaultResolutionAggregator()
        r6_totals = aggregator.aggregate(hydrated_hex_grid, target_resolution=6)

        for parent_id, total in r6_totals.items():
            child_ids = hydrated_hex_grid.res6_children[parent_id]
            child_sum = 0.0
            for child_id in child_ids:
                h = hydrated_hex_grid.hexes[child_id]
                child_sum += h.constant_capital + h.variable_capital + h.surplus_value
            assert total == pytest.approx(child_sum)
