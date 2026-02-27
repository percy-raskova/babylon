"""Unit tests for Volume I production computation (T018).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests DefaultHexProductionComputer: profit_rate, exploitation_rate,
total capital conservation, zero-employment edge case.
"""

from __future__ import annotations

import pytest

from babylon.economics.substrate.production import DefaultHexProductionComputer
from babylon.economics.substrate.types import (
    HexEconomicState,
    HexGrid,
)

from .conftest import WAYNE_HEX_IDS


def _sum_total_capital(grid: HexGrid) -> float:
    """Sum c + v + s across all hexes."""
    total = 0.0
    for h in grid.hexes.values():
        total += h.constant_capital + h.variable_capital + h.surplus_value
    return total


@pytest.mark.unit
class TestDefaultHexProductionComputer:
    """Tests for DefaultHexProductionComputer.compute_production."""

    def test_correct_profit_rate(self) -> None:
        """Test profit_rate = s / (c + v) computed correctly."""
        h3_id = WAYNE_HEX_IDS[0]
        grid = HexGrid(
            hexes={
                h3_id: HexEconomicState(
                    h3_index=h3_id,
                    county_fips="26163",
                    constant_capital=100.0,
                    variable_capital=50.0,
                    surplus_value=30.0,
                    employment=10.0,
                    dept_shares=(0.25, 0.25, 0.25, 0.25),
                ),
            },
            county_hex_ids={"26163": frozenset({h3_id})},
            res6_parents={h3_id: "86parent"},
            res5_parents={h3_id: "85parent"},
            res6_children={"86parent": frozenset({h3_id})},
            res5_children={"85parent": frozenset({h3_id})},
        )

        computer = DefaultHexProductionComputer()
        result = computer.compute_production(grid)

        # profit_rate = s / (c + v) = 30 / (100 + 50) = 0.2
        assert result.hexes[h3_id].profit_rate == pytest.approx(0.2)

    def test_correct_exploitation_rate(self) -> None:
        """Test exploitation_rate = s / v computed correctly."""
        h3_id = WAYNE_HEX_IDS[0]
        grid = HexGrid(
            hexes={
                h3_id: HexEconomicState(
                    h3_index=h3_id,
                    county_fips="26163",
                    constant_capital=100.0,
                    variable_capital=50.0,
                    surplus_value=30.0,
                    employment=10.0,
                    dept_shares=(0.25, 0.25, 0.25, 0.25),
                ),
            },
            county_hex_ids={"26163": frozenset({h3_id})},
            res6_parents={h3_id: "86parent"},
            res5_parents={h3_id: "85parent"},
            res6_children={"86parent": frozenset({h3_id})},
            res5_children={"85parent": frozenset({h3_id})},
        )

        computer = DefaultHexProductionComputer()
        result = computer.compute_production(grid)

        # exploitation_rate = s / v = 30 / 50 = 0.6
        assert result.hexes[h3_id].exploitation_rate == pytest.approx(0.6)

    def test_total_capital_conserved(self, hydrated_hex_grid: HexGrid) -> None:
        """Test that sum(c+v+s) is preserved after production computation."""
        computer = DefaultHexProductionComputer()
        pre_total = _sum_total_capital(hydrated_hex_grid)
        result = computer.compute_production(hydrated_hex_grid)
        post_total = _sum_total_capital(result)

        assert abs(pre_total - post_total) < 1e-10

    def test_zero_employment_no_division_error(self) -> None:
        """Test that zero-employment hex does not cause division by zero."""
        h3_id = WAYNE_HEX_IDS[0]
        grid = HexGrid(
            hexes={
                h3_id: HexEconomicState(
                    h3_index=h3_id,
                    county_fips="26163",
                    constant_capital=0.0,
                    variable_capital=0.0,
                    surplus_value=0.0,
                    employment=0.0,
                    dept_shares=(0.25, 0.25, 0.25, 0.25),
                ),
            },
            county_hex_ids={"26163": frozenset({h3_id})},
            res6_parents={h3_id: "86parent"},
            res5_parents={h3_id: "85parent"},
            res6_children={"86parent": frozenset({h3_id})},
            res5_children={"85parent": frozenset({h3_id})},
        )

        computer = DefaultHexProductionComputer()
        result = computer.compute_production(grid)

        # With c=v=s=0, profit_rate and exploitation_rate should be 0.0
        assert result.hexes[h3_id].profit_rate == 0.0
        assert result.hexes[h3_id].exploitation_rate == 0.0

    def test_zero_variable_capital_exploitation_rate(self) -> None:
        """Test exploitation_rate = 0 when v = 0 but c and s nonzero."""
        h3_id = WAYNE_HEX_IDS[0]
        grid = HexGrid(
            hexes={
                h3_id: HexEconomicState(
                    h3_index=h3_id,
                    county_fips="26163",
                    constant_capital=100.0,
                    variable_capital=0.0,
                    surplus_value=20.0,
                    employment=5.0,
                    dept_shares=(0.25, 0.25, 0.25, 0.25),
                ),
            },
            county_hex_ids={"26163": frozenset({h3_id})},
            res6_parents={h3_id: "86parent"},
            res5_parents={h3_id: "85parent"},
            res6_children={"86parent": frozenset({h3_id})},
            res5_children={"85parent": frozenset({h3_id})},
        )

        computer = DefaultHexProductionComputer()
        result = computer.compute_production(grid)

        # v = 0, so exploitation_rate falls back to 0.0
        assert result.hexes[h3_id].exploitation_rate == 0.0
        # profit_rate = s / (c + v) = 20 / 100 = 0.2
        assert result.hexes[h3_id].profit_rate == pytest.approx(0.2)

    def test_hydrated_grid_production(self, hydrated_hex_grid: HexGrid) -> None:
        """Test production on hydrated grid sets nonzero rates."""
        computer = DefaultHexProductionComputer()
        result = computer.compute_production(hydrated_hex_grid)

        # All hydrated hexes have c, v, s > 0, so profit_rate > 0
        for h3_id, hex_state in result.hexes.items():
            assert hex_state.profit_rate > 0.0, f"Hex {h3_id} has zero profit_rate"
            assert hex_state.exploitation_rate > 0.0, f"Hex {h3_id} has zero exploitation_rate"

    def test_capital_values_unchanged(self) -> None:
        """Test that c, v, s values are not modified by production."""
        h3_id = WAYNE_HEX_IDS[0]
        c, v, s = 100.0, 50.0, 30.0
        grid = HexGrid(
            hexes={
                h3_id: HexEconomicState(
                    h3_index=h3_id,
                    county_fips="26163",
                    constant_capital=c,
                    variable_capital=v,
                    surplus_value=s,
                    employment=10.0,
                    dept_shares=(0.25, 0.25, 0.25, 0.25),
                ),
            },
            county_hex_ids={"26163": frozenset({h3_id})},
            res6_parents={h3_id: "86parent"},
            res5_parents={h3_id: "85parent"},
            res6_children={"86parent": frozenset({h3_id})},
            res5_children={"85parent": frozenset({h3_id})},
        )

        computer = DefaultHexProductionComputer()
        result = computer.compute_production(grid)

        assert result.hexes[h3_id].constant_capital == c
        assert result.hexes[h3_id].variable_capital == v
        assert result.hexes[h3_id].surplus_value == s

    def test_empty_grid(self) -> None:
        """Test production on empty grid returns empty grid."""
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        computer = DefaultHexProductionComputer()
        result = computer.compute_production(grid)
        assert len(result.hexes) == 0
