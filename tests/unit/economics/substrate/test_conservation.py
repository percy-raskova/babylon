"""Unit tests for conservation invariant checking (T009).

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Tests DefaultConservationChecker: total capital conservation, variable
capital conservation, hierarchical aggregation checks.
"""

from __future__ import annotations

import logging

import pytest

from babylon.domain.economics.substrate.conservation import DefaultConservationChecker
from babylon.domain.economics.substrate.types import (
    HexEconomicState,
    HexGrid,
)

from .conftest import WAYNE_HEX_IDS


def _make_single_hex_grid(
    c: float = 100.0,
    v: float = 50.0,
    s: float = 25.0,
) -> HexGrid:
    """Create a minimal grid with one hex for conservation testing."""
    h3_id = WAYNE_HEX_IDS[0]
    return HexGrid(
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
        res6_parents={h3_id: "8626163ffffff"},
        res5_parents={h3_id: "8526163fffffff"},
        res6_children={"8626163ffffff": frozenset({h3_id})},
        res5_children={"8526163fffffff": frozenset({h3_id})},
    )


@pytest.mark.unit
class TestCheckTotalCapital:
    """Tests for DefaultConservationChecker.check_total_capital."""

    def test_passes_when_identical(self) -> None:
        """Test conservation passes when pre and post grids are identical."""
        checker = DefaultConservationChecker()
        grid = _make_single_hex_grid(c=100.0, v=50.0, s=25.0)
        assert checker.check_total_capital(grid, grid, "identity") is True

    def test_passes_within_tolerance(self) -> None:
        """Test conservation passes when diff is within tolerance."""
        checker = DefaultConservationChecker(tolerance=1e-10)
        pre = _make_single_hex_grid(c=100.0, v=50.0, s=25.0)
        # Post has negligible difference (< 1e-10)
        post = _make_single_hex_grid(c=100.0, v=50.0, s=25.0)
        assert checker.check_total_capital(pre, post, "negligible_diff") is True

    def test_fails_beyond_tolerance(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test conservation fails when diff exceeds tolerance."""
        checker = DefaultConservationChecker(tolerance=1e-10)
        pre = _make_single_hex_grid(c=100.0, v=50.0, s=25.0)  # total=175
        post = _make_single_hex_grid(c=100.0, v=50.0, s=26.0)  # total=176

        with caplog.at_level(logging.WARNING):
            result = checker.check_total_capital(pre, post, "production")

        assert result is False
        assert "Conservation violation" in caplog.text
        assert "production" in caplog.text

    def test_zero_capital_passes(self) -> None:
        """Test conservation passes with zero-capital grids."""
        checker = DefaultConservationChecker()
        pre = _make_single_hex_grid(c=0.0, v=0.0, s=0.0)
        post = _make_single_hex_grid(c=0.0, v=0.0, s=0.0)
        assert checker.check_total_capital(pre, post, "zero_capital") is True

    def test_multi_hex_conservation(self, hydrated_hex_grid: HexGrid) -> None:
        """Test conservation check on hydrated grid (9 hexes) against itself."""
        checker = DefaultConservationChecker()
        assert (
            checker.check_total_capital(hydrated_hex_grid, hydrated_hex_grid, "hydrated_identity")
            is True
        )


@pytest.mark.unit
class TestCheckVariableCapital:
    """Tests for DefaultConservationChecker.check_variable_capital."""

    def test_passes_when_identical(self) -> None:
        """Test variable capital conservation passes on identical grids."""
        checker = DefaultConservationChecker()
        grid = _make_single_hex_grid(v=50.0)
        assert checker.check_variable_capital(grid, grid, "identity") is True

    def test_fails_beyond_tolerance(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test variable capital conservation fails when v changes."""
        checker = DefaultConservationChecker(tolerance=1e-10)
        pre = _make_single_hex_grid(v=50.0)
        post = _make_single_hex_grid(v=51.0)

        with caplog.at_level(logging.WARNING):
            result = checker.check_variable_capital(pre, post, "circulation")

        assert result is False
        assert "Conservation violation" in caplog.text
        assert "circulation" in caplog.text

    def test_passes_within_tolerance(self) -> None:
        """Test variable capital conservation passes within tolerance."""
        checker = DefaultConservationChecker(tolerance=1e-10)
        grid = _make_single_hex_grid(v=50.0)
        assert checker.check_variable_capital(grid, grid, "exact") is True


@pytest.mark.unit
class TestCheckHierarchicalAggregation:
    """Tests for DefaultConservationChecker.check_hierarchical_aggregation."""

    def test_complete_children_at_res6(self, hydrated_hex_grid: HexGrid) -> None:
        """Test hierarchical check passes with all children present at r6."""
        checker = DefaultConservationChecker()
        result = checker.check_hierarchical_aggregation(hydrated_hex_grid, target_resolution=6)
        assert result is True

    def test_complete_children_at_res5(self, hydrated_hex_grid: HexGrid) -> None:
        """Test hierarchical check passes with all children present at r5."""
        checker = DefaultConservationChecker()
        result = checker.check_hierarchical_aggregation(hydrated_hex_grid, target_resolution=5)
        assert result is True

    def test_missing_children_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test hierarchical check fails when children are missing."""
        checker = DefaultConservationChecker()
        # Create grid with children in hierarchy but missing from hexes
        missing_h3_id = "872830899ffffff"
        grid = HexGrid(
            hexes={},  # No hexes at all
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={"86parent_ffffff": frozenset({missing_h3_id})},
            res5_children={},
        )

        with caplog.at_level(logging.WARNING):
            result = checker.check_hierarchical_aggregation(grid, target_resolution=6)

        assert result is False
        assert "missing" in caplog.text

    def test_unsupported_resolution_fails(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test hierarchical check fails for unsupported resolution."""
        checker = DefaultConservationChecker()
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )

        with caplog.at_level(logging.WARNING):
            result = checker.check_hierarchical_aggregation(grid, target_resolution=4)

        assert result is False
        assert "Unsupported target resolution" in caplog.text

    def test_empty_grid_passes(self) -> None:
        """Test hierarchical check passes on empty grid (no parents to check)."""
        checker = DefaultConservationChecker()
        grid = HexGrid(
            hexes={},
            county_hex_ids={},
            res6_parents={},
            res5_parents={},
            res6_children={},
            res5_children={},
        )
        # No children map entries, so loop body never executes -> True
        assert checker.check_hierarchical_aggregation(grid, target_resolution=6) is True
