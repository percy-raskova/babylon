"""Integration tests for the full substrate pipeline (T027).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Full pipeline: hydrate -> Vol I -> Vol II -> Vol III -> aggregation -> conservation.
Verifies conservation at each stage and overall pipeline correctness.
"""

from __future__ import annotations

import time

import pytest

from babylon.economics.substrate.aggregation import DefaultResolutionAggregator
from babylon.economics.substrate.conservation import DefaultConservationChecker
from babylon.economics.substrate.equalization import DefaultHexEqualizationComputer
from babylon.economics.substrate.production import DefaultHexProductionComputer
from babylon.economics.substrate.types import (
    HexEconomicState,
    HexGrid,
)

# Reuse test fixtures from unit tests
WAYNE_HEX_IDS: list[str] = [
    "872830828ffffff",
    "872830829ffffff",
    "87283082affffff",
]
OAKLAND_HEX_IDS: list[str] = [
    "872830880ffffff",
    "872830881ffffff",
    "872830882ffffff",
]
MACOMB_HEX_IDS: list[str] = [
    "872830890ffffff",
    "872830891ffffff",
    "872830892ffffff",
]
ALL_HEX_IDS: list[str] = WAYNE_HEX_IDS + OAKLAND_HEX_IDS + MACOMB_HEX_IDS


def _build_hydrated_grid() -> HexGrid:
    """Build a hydrated hex grid for integration testing.

    Wayne hexes: higher employment, lower c/v (service economy).
    Oakland hexes: moderate employment, higher c/v (suburban).
    Macomb hexes: lower employment, highest c/v (manufacturing).
    """
    hexes: dict[str, HexEconomicState] = {}

    for i, h3_id in enumerate(WAYNE_HEX_IDS):
        hexes[h3_id] = HexEconomicState(
            h3_index=h3_id,
            county_fips="26163",
            constant_capital=100.0 + i * 10,
            variable_capital=80.0 + i * 5,
            surplus_value=40.0 + i * 3,
            employment=1000.0 + i * 100,
            dept_shares=(0.20, 0.35, 0.25, 0.20),
        )

    for i, h3_id in enumerate(OAKLAND_HEX_IDS):
        hexes[h3_id] = HexEconomicState(
            h3_index=h3_id,
            county_fips="26125",
            constant_capital=150.0 + i * 10,
            variable_capital=60.0 + i * 5,
            surplus_value=50.0 + i * 3,
            employment=800.0 + i * 100,
            dept_shares=(0.25, 0.30, 0.25, 0.20),
        )

    for i, h3_id in enumerate(MACOMB_HEX_IDS):
        hexes[h3_id] = HexEconomicState(
            h3_index=h3_id,
            county_fips="26099",
            constant_capital=200.0 + i * 10,
            variable_capital=50.0 + i * 5,
            surplus_value=60.0 + i * 3,
            employment=600.0 + i * 100,
            dept_shares=(0.35, 0.25, 0.20, 0.20),
        )

    res6_parents: dict[str, str] = {}
    res5_parents: dict[str, str] = {}
    res6_children: dict[str, frozenset[str]] = {}
    res5_children: dict[str, frozenset[str]] = {}

    county_hex_map = {
        "26163": WAYNE_HEX_IDS,
        "26125": OAKLAND_HEX_IDS,
        "26099": MACOMB_HEX_IDS,
    }

    for fips, ids in county_hex_map.items():
        r6_parent = f"86{fips}ffffff"
        r5_parent = f"85{fips}fffffff"
        r6_set: set[str] = set()
        r5_set: set[str] = set()
        for h3_id in ids:
            res6_parents[h3_id] = r6_parent
            res5_parents[h3_id] = r5_parent
            r6_set.add(h3_id)
            r5_set.add(h3_id)
        res6_children[r6_parent] = frozenset(r6_set)
        res5_children[r5_parent] = frozenset(r5_set)

    return HexGrid(
        hexes=hexes,
        county_hex_ids={
            "26163": frozenset(WAYNE_HEX_IDS),
            "26125": frozenset(OAKLAND_HEX_IDS),
            "26099": frozenset(MACOMB_HEX_IDS),
        },
        res6_parents=res6_parents,
        res5_parents=res5_parents,
        res6_children=res6_children,
        res5_children=res5_children,
    )


def _sum_total_capital(grid: HexGrid) -> float:
    """Sum c + v + s across all hexes."""
    total = 0.0
    for h in grid.hexes.values():
        total += h.constant_capital + h.variable_capital + h.surplus_value
    return total


def _sum_variable_capital(grid: HexGrid) -> float:
    """Sum v across all hexes."""
    total = 0.0
    for h in grid.hexes.values():
        total += h.variable_capital
    return total


def _sum_constant_capital(grid: HexGrid) -> float:
    """Sum c across all hexes."""
    total = 0.0
    for h in grid.hexes.values():
        total += h.constant_capital
    return total


@pytest.mark.integration
class TestSubstratePipeline:
    """Full pipeline integration tests."""

    def test_full_pipeline_single_tick(self) -> None:
        """Test complete pipeline: Vol I -> Vol III -> conservation check.

        Note: Vol II (circulation) requires a commuter OD matrix, which
        is tested separately. This tests the core pipeline without
        external data dependencies.
        """
        checker = DefaultConservationChecker()

        # Step 1: Hydrate
        grid = _build_hydrated_grid()
        initial_total = _sum_total_capital(grid)
        assert initial_total > 0.0, "Hydrated grid should have nonzero capital"

        # Step 2: Volume I - Production (rate computation)
        production = DefaultHexProductionComputer()
        grid_post_prod = production.compute_production(grid)

        # Conservation: total capital unchanged
        assert checker.check_total_capital(grid, grid_post_prod, "production")

        # Verify rates are computed
        for hex_state in grid_post_prod.hexes.values():
            assert hex_state.profit_rate > 0.0
            assert hex_state.exploitation_rate > 0.0

        # Step 3: Volume III - Equalization (capital migration)
        equalization = DefaultHexEqualizationComputer()
        grid_post_eq = equalization.equalize_capital(grid_post_prod, alpha=0.01)

        # Conservation: total capital preserved (sum(delta_c) = 0)
        total_pre_eq = _sum_total_capital(grid_post_prod)
        total_post_eq = _sum_total_capital(grid_post_eq)
        # Note: equalization only moves constant capital, but total c+v+s
        # changes because we floor at 0 and recompute profit rates.
        # However, with small alpha and no flooring, delta should be ~0.
        assert abs(total_pre_eq - total_post_eq) < 1.0, (
            f"Total capital changed significantly: {total_pre_eq} -> {total_post_eq}"
        )

        # Step 4: Aggregation
        aggregator = DefaultResolutionAggregator()
        r6_totals = aggregator.aggregate(grid_post_eq, target_resolution=6)
        r5_totals = aggregator.aggregate(grid_post_eq, target_resolution=5)

        # Verify aggregation covers all counties
        assert len(r6_totals) == 3  # 3 counties = 3 r6 parents
        assert len(r5_totals) == 3  # 3 r5 parents

        # Verify r6 totals sum to grid total
        r6_sum = sum(r6_totals.values())
        assert abs(r6_sum - total_post_eq) < 1e-10

        # Verify weighted profit rates
        r6_rates = aggregator.compute_weighted_profit_rate(grid_post_eq, 6)
        for rate in r6_rates.values():
            assert 0.0 < rate < 2.0, f"Weighted profit rate out of range: {rate}"

    def test_multi_tick_equalization_convergence(self) -> None:
        """Test that multiple ticks of equalization converge profit rates.

        SC-003: Capital should shift from low-profit to high-profit hexes.
        """
        grid = _build_hydrated_grid()

        production = DefaultHexProductionComputer()
        equalization = DefaultHexEqualizationComputer()

        # Compute initial rates
        grid = production.compute_production(grid)
        initial_rates = {h3_id: hex_state.profit_rate for h3_id, hex_state in grid.hexes.items()}

        # Run 50 equalization ticks
        max_ticks = 50
        for _tick in range(max_ticks):
            grid = equalization.equalize_capital(grid, alpha=0.01)
            grid = production.compute_production(grid)

        final_rates = {h3_id: hex_state.profit_rate for h3_id, hex_state in grid.hexes.items()}

        # Profit rates should converge (variance decreases)
        initial_variance = _compute_variance(list(initial_rates.values()))
        final_variance = _compute_variance(list(final_rates.values()))

        assert final_variance < initial_variance, (
            f"Profit rate variance did not decrease: "
            f"initial={initial_variance:.6f}, final={final_variance:.6f}"
        )

    def test_equalization_directional_flow(self) -> None:
        """Test SC-003: capital shifts from Wayne toward Oakland.

        Oakland has higher profit rates (higher c/v ratio + higher s),
        so capital should flow from Wayne to Oakland.
        """
        grid = _build_hydrated_grid()

        production = DefaultHexProductionComputer()
        equalization = DefaultHexEqualizationComputer()

        grid = production.compute_production(grid)

        initial_wayne_c = sum(grid.hexes[h].constant_capital for h in WAYNE_HEX_IDS)
        initial_oakland_c = sum(grid.hexes[h].constant_capital for h in OAKLAND_HEX_IDS)

        # Run 100 equalization ticks
        max_ticks = 100
        for _tick in range(max_ticks):
            grid = equalization.equalize_capital(grid, alpha=0.01)
            grid = production.compute_production(grid)

        final_wayne_c = sum(grid.hexes[h].constant_capital for h in WAYNE_HEX_IDS)
        final_oakland_c = sum(grid.hexes[h].constant_capital for h in OAKLAND_HEX_IDS)

        # Capital should shift: Wayne c should decrease or Oakland c should increase
        wayne_delta = final_wayne_c - initial_wayne_c
        oakland_delta = final_oakland_c - initial_oakland_c

        # At least one directional shift should occur
        assert (wayne_delta < 0) or (oakland_delta > 0), (
            f"No directional capital shift detected: "
            f"Wayne delta={wayne_delta:.4f}, Oakland delta={oakland_delta:.4f}"
        )

    def test_pipeline_performance(self) -> None:
        """Test SC-004: single tick resolves in under 5.0 seconds.

        On 9 mock hexes this should be trivially fast, but verifies
        the pipeline doesn't have accidental O(n^3) overhead.
        """
        grid = _build_hydrated_grid()

        production = DefaultHexProductionComputer()
        equalization = DefaultHexEqualizationComputer()
        aggregator = DefaultResolutionAggregator()

        start = time.monotonic()

        # Full tick: production -> equalization -> aggregation
        grid = production.compute_production(grid)
        grid = equalization.equalize_capital(grid, alpha=0.01)
        aggregator.aggregate(grid, 6)
        aggregator.aggregate(grid, 5)
        aggregator.compute_weighted_profit_rate(grid, 6)

        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Single tick took {elapsed:.2f}s (>5.0s budget)"

    def test_hierarchical_conservation(self) -> None:
        """Test that r7 children sum equals r6/r5 parent aggregation."""
        grid = _build_hydrated_grid()
        production = DefaultHexProductionComputer()
        grid = production.compute_production(grid)

        aggregator = DefaultResolutionAggregator()
        checker = DefaultConservationChecker()

        # R6 aggregation
        r6_totals = aggregator.aggregate(grid, 6)
        r6_total = sum(r6_totals.values())
        grid_total = _sum_total_capital(grid)
        assert abs(r6_total - grid_total) < 1e-10

        # R5 aggregation
        r5_totals = aggregator.aggregate(grid, 5)
        r5_total = sum(r5_totals.values())
        assert abs(r5_total - grid_total) < 1e-10

        # Hierarchical check via conservation checker
        assert checker.check_hierarchical_aggregation(grid, 6)
        assert checker.check_hierarchical_aggregation(grid, 5)

    def test_multi_tick_conservation_logging(self) -> None:
        """Test FR-015: conservation warnings logged but don't halt.

        Run multiple ticks and verify the simulation continues even
        if floating-point drift accumulates.
        """
        grid = _build_hydrated_grid()
        production = DefaultHexProductionComputer()
        equalization = DefaultHexEqualizationComputer()
        checker = DefaultConservationChecker()

        initial_total = _sum_total_capital(grid)

        max_ticks = 50
        for _tick in range(max_ticks):
            pre_grid = grid
            grid = production.compute_production(grid)
            grid = equalization.equalize_capital(grid, alpha=0.01)

            # Non-halting check (logs warning if violated)
            checker.check_total_capital(pre_grid, grid, f"tick_{_tick}")

        final_total = _sum_total_capital(grid)

        # After 50 ticks, total capital may drift slightly due to
        # equalization flooring at zero, but should remain close
        assert abs(initial_total - final_total) < initial_total * 0.1, (
            f"Total capital drifted >10%: initial={initial_total}, final={final_total}"
        )


def _compute_variance(values: list[float]) -> float:
    """Compute variance of a list of floats."""
    if not values:
        return 0.0
    n = len(values)
    mean = sum(values) / n
    return sum((v - mean) ** 2 for v in values) / n
