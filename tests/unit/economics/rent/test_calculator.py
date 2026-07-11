"""Tests for rent calculators.

Feature: 024-capital-volume-iii (US4, FR-007, FR-008, FR-009)
TDD Red Phase: Tests define expected behavior for rent extraction and
housing decomposition computation.

DefaultRentCalculator: Computes RentExtraction from CountyRentalIncomeSource.
DefaultHousingDecompositionCalculator: Decomposes housing values using Census data.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.rent.calculator import (
    DefaultHousingDecompositionCalculator,
    DefaultRentCalculator,
)
from babylon.domain.economics.rent.types import HousingValueDecomposition, RentExtraction
from babylon.domain.economics.tensor import NoDataSentinel

from .conftest import MockCountyRentalIncomeSource, MockHousingDataSource

# =============================================================================
# DefaultRentCalculator.compute_rent_extraction
# =============================================================================


@pytest.mark.unit
class TestComputeRentExtraction:
    """DefaultRentCalculator.compute_rent_extraction."""

    def test_returns_rent_extraction(
        self,
        mock_county_rental_source: MockCountyRentalIncomeSource,
    ) -> None:
        """Returns RentExtraction when all data available."""
        calc = DefaultRentCalculator(rental_source=mock_county_rental_source)
        result = calc.compute_rent_extraction("26163", 2020)
        assert isinstance(result, RentExtraction)
        assert result.fips_code == "26163"
        assert result.year == 2020
        assert result.agricultural_rent == pytest.approx(50_000_000.0)
        assert result.resource_rent == pytest.approx(10_000_000.0)
        assert result.urban_rent == pytest.approx(2_400_000_000.0)

    def test_total_rent_computed(
        self,
        mock_county_rental_source: MockCountyRentalIncomeSource,
    ) -> None:
        """total_rent sums the three categories."""
        calc = DefaultRentCalculator(rental_source=mock_county_rental_source)
        result = calc.compute_rent_extraction("26163", 2020)
        assert isinstance(result, RentExtraction)
        expected = 50_000_000.0 + 10_000_000.0 + 2_400_000_000.0
        assert result.total_rent == pytest.approx(expected)

    def test_returns_no_data_sentinel_when_agricultural_unavailable(self) -> None:
        """Returns NoDataSentinel when agricultural rent data missing."""
        empty_source = MockCountyRentalIncomeSource(data={})
        calc = DefaultRentCalculator(rental_source=empty_source)
        result = calc.compute_rent_extraction("26163", 2020)
        assert isinstance(result, NoDataSentinel)
        assert not result  # Falsy
        assert "Agricultural rent" in result.reason

    def test_returns_no_data_sentinel_when_resource_unavailable(self) -> None:
        """Returns NoDataSentinel when resource rent data missing."""
        partial_source = _AgOnlyRentalSource(agricultural=50_000_000.0)
        calc = DefaultRentCalculator(rental_source=partial_source)
        result = calc.compute_rent_extraction("26163", 2020)
        assert isinstance(result, NoDataSentinel)
        assert "Resource rent" in result.reason

    def test_returns_no_data_sentinel_when_urban_unavailable(self) -> None:
        """Returns NoDataSentinel when urban rent data missing."""
        partial_source = _AgResourceOnlyRentalSource(
            agricultural=50_000_000.0,
            resource=10_000_000.0,
        )
        calc = DefaultRentCalculator(rental_source=partial_source)
        result = calc.compute_rent_extraction("26163", 2020)
        assert isinstance(result, NoDataSentinel)
        assert "Urban rent" in result.reason

    def test_oakland_county_data(
        self,
        mock_county_rental_source: MockCountyRentalIncomeSource,
    ) -> None:
        """Oakland County (26125) data is correctly assembled."""
        calc = DefaultRentCalculator(rental_source=mock_county_rental_source)
        result = calc.compute_rent_extraction("26125", 2020)
        assert isinstance(result, RentExtraction)
        assert result.agricultural_rent == pytest.approx(120_000_000.0)
        assert result.resource_rent == pytest.approx(5_000_000.0)
        assert result.urban_rent == pytest.approx(4_100_000_000.0)


# =============================================================================
# DefaultRentCalculator.compute_rent_share
# =============================================================================


@pytest.mark.unit
class TestComputeRentShare:
    """DefaultRentCalculator.compute_rent_share."""

    def test_rent_share_normal(
        self,
        mock_county_rental_source: MockCountyRentalIncomeSource,
    ) -> None:
        """Returns rent share as fraction of surplus."""
        calc = DefaultRentCalculator(rental_source=mock_county_rental_source)
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=50_000_000.0,
            resource_rent=10_000_000.0,
            urban_rent=2_400_000_000.0,
        )
        total_surplus = 10_000_000_000.0
        share = calc.compute_rent_share(rent, total_surplus)
        assert share == pytest.approx(rent.total_rent / total_surplus)

    def test_rent_share_zero_surplus(
        self,
        mock_county_rental_source: MockCountyRentalIncomeSource,
    ) -> None:
        """Returns 0.0 when surplus is zero."""
        calc = DefaultRentCalculator(rental_source=mock_county_rental_source)
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=50_000_000.0,
            resource_rent=10_000_000.0,
            urban_rent=2_400_000_000.0,
        )
        assert calc.compute_rent_share(rent, 0.0) == pytest.approx(0.0)


# =============================================================================
# DefaultHousingDecompositionCalculator.decompose_housing_value
# =============================================================================


@pytest.mark.unit
class TestDecomposeHousingValue:
    """DefaultHousingDecompositionCalculator.decompose_housing_value."""

    def test_returns_housing_value_decomposition(
        self,
        mock_housing_source: MockHousingDataSource,
    ) -> None:
        """Returns HousingValueDecomposition when all data available."""
        calc = DefaultHousingDecompositionCalculator(
            housing_source=mock_housing_source,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, HousingValueDecomposition)
        assert result.fips_code == "26163"
        assert result.year == 2020

    def test_components_sum_to_market_price(
        self,
        mock_housing_source: MockHousingDataSource,
    ) -> None:
        """construction + rent_cap + speculation = market_price."""
        calc = DefaultHousingDecompositionCalculator(
            housing_source=mock_housing_source,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, HousingValueDecomposition)
        sum_of_parts = (
            result.construction_value + result.ground_rent_capitalized + result.speculative_premium
        )
        assert sum_of_parts == pytest.approx(result.market_price)

    def test_construction_value_uses_cost_index(
        self,
        mock_housing_source: MockHousingDataSource,
    ) -> None:
        """Construction value = home_value * (cost_index / 200)."""
        calc = DefaultHousingDecompositionCalculator(
            housing_source=mock_housing_source,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, HousingValueDecomposition)
        # home_value=52000, cost_index=100 -> 52000 * 100/200 = 26000
        assert result.construction_value == pytest.approx(26_000.0)

    def test_ground_rent_capitalized_formula(
        self,
        mock_housing_source: MockHousingDataSource,
    ) -> None:
        """Ground rent capitalized = (monthly_rent * 12) / interest_rate."""
        calc = DefaultHousingDecompositionCalculator(
            housing_source=mock_housing_source,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, HousingValueDecomposition)
        # monthly_rent=850, rate=0.05 -> (850*12)/0.05 = 204000
        expected_rent_cap = (850.0 * 12) / 0.05
        assert result.ground_rent_capitalized == pytest.approx(expected_rent_cap)

    def test_speculative_premium_is_residual(
        self,
        mock_housing_source: MockHousingDataSource,
    ) -> None:
        """Speculative premium = max(0, home_value - construction - rent_cap)."""
        calc = DefaultHousingDecompositionCalculator(
            housing_source=mock_housing_source,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, HousingValueDecomposition)
        # home=52000, construction=26000, rent_cap=204000
        # residual = 52000 - 26000 - 204000 = -178000 -> clamped to 0
        assert result.speculative_premium == pytest.approx(0.0)

    def test_speculative_premium_positive_when_overvalued(self) -> None:
        """Speculative premium is positive when home price exceeds fundamentals."""
        # High home value, low rent -> speculative bubble
        housing = MockHousingDataSource(
            home_values={("99999", 2020): 500_000.0},
            gross_rent={("99999", 2020): 500.0},
            construction_index={2020: 100.0},
        )
        calc = DefaultHousingDecompositionCalculator(
            housing_source=housing,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("99999", 2020)
        assert isinstance(result, HousingValueDecomposition)
        # construction = 500000 * 100/200 = 250000
        # rent_cap = (500*12)/0.05 = 120000
        # speculative = max(0, 500000 - 250000 - 120000) = 130000
        assert result.speculative_premium == pytest.approx(130_000.0)
        assert result.speculative_premium > 0.0

    def test_returns_no_data_sentinel_when_home_value_unavailable(self) -> None:
        """Returns NoDataSentinel when home value data missing."""
        empty_housing = MockHousingDataSource(
            home_values={},
            gross_rent={("26163", 2020): 850.0},
            construction_index={2020: 100.0},
        )
        calc = DefaultHousingDecompositionCalculator(
            housing_source=empty_housing,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, NoDataSentinel)
        assert "Median home value" in result.reason

    def test_returns_no_data_sentinel_when_rent_unavailable(self) -> None:
        """Returns NoDataSentinel when gross rent data missing."""
        no_rent_housing = MockHousingDataSource(
            home_values={("26163", 2020): 52_000.0},
            gross_rent={},
            construction_index={2020: 100.0},
        )
        calc = DefaultHousingDecompositionCalculator(
            housing_source=no_rent_housing,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, NoDataSentinel)
        assert "Median gross rent" in result.reason

    def test_returns_no_data_sentinel_when_cost_index_unavailable(self) -> None:
        """Returns NoDataSentinel when construction cost index missing."""
        no_index_housing = MockHousingDataSource(
            home_values={("26163", 2020): 52_000.0},
            gross_rent={("26163", 2020): 850.0},
            construction_index={},
        )
        calc = DefaultHousingDecompositionCalculator(
            housing_source=no_index_housing,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, NoDataSentinel)
        assert "Construction cost index" in result.reason

    def test_fictitious_fraction_computed(
        self,
        mock_housing_source: MockHousingDataSource,
    ) -> None:
        """fictitious_fraction is correctly computed from decomposition."""
        calc = DefaultHousingDecompositionCalculator(
            housing_source=mock_housing_source,
            national_interest_rate=0.05,
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, HousingValueDecomposition)
        # When speculative_premium = 0, fictitious = rent_cap / market_price
        # market_price = construction + rent_cap + 0 = 26000 + 204000 = 230000
        expected = 204_000.0 / (26_000.0 + 204_000.0)
        assert result.fictitious_fraction == pytest.approx(expected)

    def test_interest_rate_floor(self) -> None:
        """Interest rate is floored at 0.01 to prevent division by near-zero."""
        housing = MockHousingDataSource(
            home_values={("26163", 2020): 52_000.0},
            gross_rent={("26163", 2020): 850.0},
            construction_index={2020: 100.0},
        )
        calc = DefaultHousingDecompositionCalculator(
            housing_source=housing,
            national_interest_rate=0.001,  # Below floor
        )
        result = calc.decompose_housing_value("26163", 2020)
        assert isinstance(result, HousingValueDecomposition)
        # Should use max(0.001, 0.01) = 0.01
        expected_rent_cap = (850.0 * 12) / 0.01
        assert result.ground_rent_capitalized == pytest.approx(expected_rent_cap)


# =============================================================================
# Helper Mock Sources for Edge Cases
# =============================================================================


class _AgOnlyRentalSource:
    """Rental source that only has agricultural rent data."""

    def __init__(self, agricultural: float) -> None:
        self._agricultural = agricultural

    def get_agricultural_rent(self, fips: str, year: int) -> float | None:
        return self._agricultural

    def get_resource_rent(self, fips: str, year: int) -> float | None:
        return None

    def get_urban_rent(self, fips: str, year: int) -> float | None:
        return None


class _AgResourceOnlyRentalSource:
    """Rental source that has agricultural and resource but no urban data."""

    def __init__(self, agricultural: float, resource: float) -> None:
        self._agricultural = agricultural
        self._resource = resource

    def get_agricultural_rent(self, fips: str, year: int) -> float | None:
        return self._agricultural

    def get_resource_rent(self, fips: str, year: int) -> float | None:
        return self._resource

    def get_urban_rent(self, fips: str, year: int) -> float | None:
        return None
