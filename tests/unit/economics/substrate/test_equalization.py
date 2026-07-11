"""Unit tests for Volume III capital equalization (T023).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests DefaultHexEqualizationComputer: delta_c formula, sum(delta_c)=0,
capital floors, directional flow.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.substrate.equalization import DefaultHexEqualizationComputer
from babylon.domain.economics.substrate.production import DefaultHexProductionComputer
from babylon.domain.economics.substrate.types import (
    HexEconomicState,
    HexGrid,
)

from .conftest import OAKLAND_HEX_IDS, WAYNE_HEX_IDS


def _sum_constant_capital(grid: HexGrid) -> float:
    """Sum constant capital across all hexes."""
    return sum(h.constant_capital for h in grid.hexes.values())


def _make_two_hex_grid(
    c1: float,
    v1: float,
    s1: float,
    c2: float,
    v2: float,
    s2: float,
) -> HexGrid:
    """Create a grid with two hexes for equalization testing.

    Hex 1 is in Wayne County, hex 2 is in Oakland County.
    Both have computed profit rates.
    """
    h1 = WAYNE_HEX_IDS[0]
    h2 = OAKLAND_HEX_IDS[0]

    # Pre-compute profit rates (same as production computer)
    cv1 = c1 + v1
    pr1 = s1 / cv1 if cv1 > 0 else 0.0
    cv2 = c2 + v2
    pr2 = s2 / cv2 if cv2 > 0 else 0.0

    return HexGrid(
        hexes={
            h1: HexEconomicState(
                h3_index=h1,
                county_fips="26163",
                constant_capital=c1,
                variable_capital=v1,
                surplus_value=s1,
                employment=100.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
                profit_rate=pr1,
            ),
            h2: HexEconomicState(
                h3_index=h2,
                county_fips="26125",
                constant_capital=c2,
                variable_capital=v2,
                surplus_value=s2,
                employment=100.0,
                dept_shares=(0.25, 0.25, 0.25, 0.25),
                profit_rate=pr2,
            ),
        },
        county_hex_ids={
            "26163": frozenset({h1}),
            "26125": frozenset({h2}),
        },
        res6_parents={h1: "86wayne", h2: "86oakland"},
        res5_parents={h1: "85wayne", h2: "85oakland"},
        res6_children={"86wayne": frozenset({h1}), "86oakland": frozenset({h2})},
        res5_children={"85wayne": frozenset({h1}), "85oakland": frozenset({h2})},
    )


@pytest.mark.unit
class TestDefaultHexEqualizationComputer:
    """Tests for DefaultHexEqualizationComputer.equalize_capital."""

    def test_delta_c_formula(self) -> None:
        """Test delta_c = alpha * (r_i - r_avg) * c_i is correct.

        Hex 1: c=100, v=50, s=30 -> profit_rate = 30/150 = 0.2
        Hex 2: c=100, v=50, s=60 -> profit_rate = 60/150 = 0.4

        Capital-weighted r_avg = total_s / total_cv = 90/300 = 0.3

        delta_c[1] = 0.01 * (0.2 - 0.3) * 100 = -0.1
        delta_c[2] = 0.01 * (0.4 - 0.3) * 100 = +0.1
        """
        grid = _make_two_hex_grid(
            c1=100.0,
            v1=50.0,
            s1=30.0,
            c2=100.0,
            v2=50.0,
            s2=60.0,
        )
        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.01)

        h1 = WAYNE_HEX_IDS[0]
        h2 = OAKLAND_HEX_IDS[0]

        # Hex 1: c = 100 + (-0.1) = 99.9
        assert result.hexes[h1].constant_capital == pytest.approx(99.9)
        # Hex 2: c = 100 + 0.1 = 100.1
        assert result.hexes[h2].constant_capital == pytest.approx(100.1)

    def test_sum_delta_c_is_zero(self) -> None:
        """Test that sum(delta_c) = 0 when all hexes have same v/c ratio.

        The formula delta_c = alpha * (r_i - r_avg) * c_i conserves
        sum(c) exactly when r_i = s_i/(c_i+v_i) and the capital-weighted
        average r_avg is used AND all hexes have identical v/c ratios
        (so sum(r_i * c_i) = r_avg * sum(c_i)).

        We construct hexes with the same v/c ratio to verify this.
        """
        # Same v/c ratio (v = 0.5*c) but different surplus values
        grid = _make_two_hex_grid(
            c1=100.0,
            v1=50.0,
            s1=30.0,  # r=30/150=0.2
            c2=200.0,
            v2=100.0,
            s2=90.0,  # r=90/300=0.3
        )

        pre_c = _sum_constant_capital(grid)

        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.01)

        post_c = _sum_constant_capital(result)

        assert abs(pre_c - post_c) < 1e-10

    def test_capital_floors_at_zero(self) -> None:
        """Test that constant capital cannot go negative (floors at 0.0).

        Hex with very low c and below-average profit rate: delta_c is negative
        and would push c below zero. Floor prevents it.
        """
        # Hex 1: very low c, low profit rate
        # Hex 2: high c, high profit rate
        grid = _make_two_hex_grid(
            c1=0.001,
            v1=50.0,
            s1=1.0,  # pr = 1/50.001 = ~0.02
            c2=1000.0,
            v2=50.0,
            s2=500.0,  # pr = 500/1050 = ~0.476
        )

        computer = DefaultHexEqualizationComputer()
        # Use a large alpha to force hex 1 below zero
        result = computer.equalize_capital(grid, alpha=10.0)

        h1 = WAYNE_HEX_IDS[0]

        # Should floor at 0.0, not go negative
        assert result.hexes[h1].constant_capital >= 0.0

    def test_directional_flow(self) -> None:
        """Test capital flows from low-profit to high-profit hexes.

        Below-average profit hex loses c, above-average gains c.
        """
        grid = _make_two_hex_grid(
            c1=200.0,
            v1=100.0,
            s1=30.0,  # low profit: 30/300 = 0.1
            c2=200.0,
            v2=100.0,
            s2=120.0,  # high profit: 120/300 = 0.4
        )

        h1 = WAYNE_HEX_IDS[0]
        h2 = OAKLAND_HEX_IDS[0]

        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.01)

        # Low-profit hex loses capital
        assert result.hexes[h1].constant_capital < grid.hexes[h1].constant_capital
        # High-profit hex gains capital
        assert result.hexes[h2].constant_capital > grid.hexes[h2].constant_capital

    def test_equal_profit_rates_no_change(self) -> None:
        """Test that equal profit rates produce no capital migration."""
        # Same profit rate = same c, v, s for both hexes
        grid = _make_two_hex_grid(
            c1=100.0,
            v1=50.0,
            s1=30.0,
            c2=100.0,
            v2=50.0,
            s2=30.0,
        )

        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.01)

        h1 = WAYNE_HEX_IDS[0]
        h2 = OAKLAND_HEX_IDS[0]

        # No migration when profit rates are equal
        assert result.hexes[h1].constant_capital == pytest.approx(100.0)
        assert result.hexes[h2].constant_capital == pytest.approx(100.0)

    def test_empty_grid_returns_same(self) -> None:
        """Test equalization on empty grid returns the same grid."""
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.01)
        assert len(result.hexes) == 0

    def test_profit_rate_recomputed_after_equalization(self) -> None:
        """Test that profit_rate is recomputed with the new c value."""
        grid = _make_two_hex_grid(
            c1=100.0,
            v1=50.0,
            s1=30.0,  # pr = 0.2
            c2=100.0,
            v2=50.0,
            s2=60.0,  # pr = 0.4
        )

        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.01)

        h1 = WAYNE_HEX_IDS[0]
        h2 = OAKLAND_HEX_IDS[0]

        # Verify profit_rate is recomputed for hex 1
        expected_pr1 = result.hexes[h1].surplus_value / (
            result.hexes[h1].constant_capital + result.hexes[h1].variable_capital
        )
        assert result.hexes[h1].profit_rate == pytest.approx(expected_pr1)

        # Verify profit_rate is recomputed for hex 2
        expected_pr2 = result.hexes[h2].surplus_value / (
            result.hexes[h2].constant_capital + result.hexes[h2].variable_capital
        )
        assert result.hexes[h2].profit_rate == pytest.approx(expected_pr2)

    def test_hydrated_grid_equalization(self, hydrated_hex_grid: HexGrid) -> None:
        """Test equalization on hydrated grid with 9 hexes."""
        prod = DefaultHexProductionComputer()
        grid_with_rates = prod.compute_production(hydrated_hex_grid)

        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid_with_rates, alpha=0.01)

        # All 9 hexes should still be present
        assert len(result.hexes) == 9
        # All c values should be non-negative
        for hex_state in result.hexes.values():
            assert hex_state.constant_capital >= 0.0
