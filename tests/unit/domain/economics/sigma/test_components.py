"""Unit tests for babylon.domain.economics.sigma.components (RED phase first)."""

from __future__ import annotations

import pytest

from babylon.domain.economics.sigma.components import (
    compute_capital_intensity,
    compute_organic_composition,
    compute_vertically_integrated_labor_content,
)


class TestComputeOrganicComposition:
    def test_occ_is_capital_stock_over_wage_bill(self) -> None:
        assert compute_organic_composition(capital_stock=300.0, wage_bill=100.0) == pytest.approx(
            3.0
        )

    def test_raises_on_zero_wage_bill(self) -> None:
        with pytest.raises(ValueError, match="wage_bill"):
            compute_organic_composition(capital_stock=100.0, wage_bill=0.0)

    def test_raises_on_negative_wage_bill(self) -> None:
        with pytest.raises(ValueError, match="wage_bill"):
            compute_organic_composition(capital_stock=100.0, wage_bill=-5.0)


class TestComputeCapitalIntensity:
    def test_capital_intensity_is_capital_stock_over_employment(self) -> None:
        assert compute_capital_intensity(
            capital_stock=1_000_000.0, employment=10.0
        ) == pytest.approx(100_000.0)

    def test_raises_on_zero_employment(self) -> None:
        with pytest.raises(ValueError, match="employment"):
            compute_capital_intensity(capital_stock=1_000_000.0, employment=0.0)

    def test_raises_on_negative_employment(self) -> None:
        with pytest.raises(ValueError, match="employment"):
            compute_capital_intensity(capital_stock=1_000_000.0, employment=-1.0)


class TestComputeVerticallyIntegratedLaborContent:
    def test_dot_product_of_overlapping_industries(self) -> None:
        total_requirements = {"334": 1.2, "221": 0.3, "999": 0.5}
        labor_coefficients = {"334": 0.01, "221": 0.02}
        # Only "334" and "221" overlap: 1.2*0.01 + 0.3*0.02 = 0.012 + 0.006 = 0.018
        result = compute_vertically_integrated_labor_content(
            total_requirements=total_requirements,
            labor_coefficients=labor_coefficients,
        )
        assert result == pytest.approx(0.018)

    def test_raises_on_no_overlapping_industries(self) -> None:
        with pytest.raises(ValueError, match="no overlapping"):
            compute_vertically_integrated_labor_content(
                total_requirements={"334": 1.2},
                labor_coefficients={"221": 0.02},
            )

    def test_raises_on_empty_inputs(self) -> None:
        with pytest.raises(ValueError, match="no overlapping"):
            compute_vertically_integrated_labor_content(
                total_requirements={},
                labor_coefficients={},
            )

    def test_raises_on_negative_coefficient(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            compute_vertically_integrated_labor_content(
                total_requirements={"334": -1.0},
                labor_coefficients={"334": 0.01},
            )
