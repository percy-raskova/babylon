"""Unit tests for equalization with ground rent integration (FR-010).

Feature: 026-tri-county-economic-substrate (amended by 043)
Date: 2026-04-09

Tests that DefaultHexEqualizationComputer correctly extracts ground rent
from hexes with tenure_composition during the equalization step.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import RentCircuitDefines
from babylon.economics.substrate.equalization import DefaultHexEqualizationComputer
from babylon.economics.substrate.types import (
    HexEconomicState,
    HexGrid,
    HexTenureComposition,
)

from .conftest import OAKLAND_HEX_IDS, WAYNE_HEX_IDS


def _make_tenure(**kwargs: float) -> HexTenureComposition:
    """Build HexTenureComposition with defaults summing to 1.0."""
    defaults = {
        "residential_owner_occupied": 0.4,
        "residential_rental": 0.2,
        "commercial": 0.1,
        "industrial": 0.1,
        "public": 0.1,
        "trust_land": 0.0,
        "vacant_abandoned": 0.1,
    }
    defaults.update(kwargs)
    return HexTenureComposition(**defaults)


def _make_grid_with_tenure(
    c1: float,
    v1: float,
    s1: float,
    c2: float,
    v2: float,
    s2: float,
    tenure1: HexTenureComposition | None = None,
    tenure2: HexTenureComposition | None = None,
) -> HexGrid:
    """Build a two-hex grid with optional tenure data."""
    h1 = WAYNE_HEX_IDS[0]
    h2 = OAKLAND_HEX_IDS[0]

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
                tenure_composition=tenure1,
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
                tenure_composition=tenure2,
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


def _sum_capital(grid: HexGrid) -> float:
    """Sum total capital (c+v+s) across all hexes."""
    return sum(
        h.constant_capital + h.variable_capital + h.surplus_value for h in grid.hexes.values()
    )


@pytest.mark.unit
class TestEqualizationWithGroundRent:
    """Tests for equalization pipeline incorporating ground rent (FR-010)."""

    def test_rent_extraction_reduces_v_and_s(self) -> None:
        """Ground rent extraction reduces v and s in hexes with tenure data.

        Per spec 026 FR-010: equalization MUST incorporate ground rent
        extraction based on HexTenureComposition.
        """
        tenure = _make_tenure()
        grid = _make_grid_with_tenure(
            c1=100,
            v1=100,
            s1=50,
            c2=100,
            v2=100,
            s2=50,
            tenure1=tenure,
            tenure2=tenure,
        )

        defines = RentCircuitDefines(absolute_rent_fraction=0.10)
        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.01, rent_defines=defines)

        h1 = WAYNE_HEX_IDS[0]

        # Both hexes should have reduced v and/or s after rent extraction
        orig_v1 = grid.hexes[h1].variable_capital
        orig_s1 = grid.hexes[h1].surplus_value
        new_v1 = result.hexes[h1].variable_capital
        new_s1 = result.hexes[h1].surplus_value

        # rent_from_v reduces v, rent_from_s reduces s
        assert new_v1 <= orig_v1
        assert new_s1 <= orig_s1

    def test_no_tenure_backward_compatible(self) -> None:
        """Hexes without tenure_composition see no rent extraction.

        FR-012: backward compatibility — no tenure input = identical results.
        """
        grid = _make_grid_with_tenure(
            c1=100,
            v1=50,
            s1=30,
            c2=100,
            v2=50,
            s2=60,
        )

        defines = RentCircuitDefines(absolute_rent_fraction=0.10)
        computer = DefaultHexEqualizationComputer()

        result_with_rent = computer.equalize_capital(grid, alpha=0.01, rent_defines=defines)
        result_without = computer.equalize_capital(grid, alpha=0.01)

        h1 = WAYNE_HEX_IDS[0]
        # Without tenure, results should be identical
        assert result_with_rent.hexes[h1].constant_capital == pytest.approx(
            result_without.hexes[h1].constant_capital
        )

    def test_mixed_tenure_only_affects_tenured_hexes(self) -> None:
        """Only hexes with tenure_composition get rent extracted.

        One hex has tenure, the other doesn't. The tenured hex's v/s
        should decrease while the untenured hex is unaffected by rent.
        """
        tenure = _make_tenure()
        grid = _make_grid_with_tenure(
            c1=100,
            v1=100,
            s1=60,
            c2=100,
            v2=100,
            s2=60,
            tenure1=tenure,
            tenure2=None,
        )

        defines = RentCircuitDefines(absolute_rent_fraction=0.10)
        computer = DefaultHexEqualizationComputer()
        result = computer.equalize_capital(grid, alpha=0.0, rent_defines=defines)

        h1 = WAYNE_HEX_IDS[0]
        h2 = OAKLAND_HEX_IDS[0]

        # alpha=0 means no capital migration, so only rent changes matter
        # h1 (with tenure) should see v/s reduction
        assert result.hexes[h1].surplus_value < grid.hexes[h1].surplus_value

        # h2 (no tenure) should be unchanged in v and s
        assert result.hexes[h2].variable_capital == pytest.approx(grid.hexes[h2].variable_capital)
        assert result.hexes[h2].surplus_value == pytest.approx(grid.hexes[h2].surplus_value)
