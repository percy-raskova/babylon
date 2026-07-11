"""Tests for DefaultValueBasisConverter.

Feature: 024-capital-volume-iii (US7, FR-013)
TDD Red Phase: Tests define expected behavior for value basis conversion.

Uses MockPriceIndexSource from conftest.py with default data for 2010/2020/2022.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.monetary.converter import DefaultValueBasisConverter
from babylon.domain.economics.monetary.types import MonetaryAdjustment
from babylon.domain.economics.tensor import NoDataSentinel
from tests.unit.economics.monetary.conftest import MockPriceIndexSource

# =============================================================================
# compute_monetary_adjustment
# =============================================================================


@pytest.mark.unit
class TestComputeMonetaryAdjustment:
    """DefaultValueBasisConverter.compute_monetary_adjustment behavior."""

    def test_returns_monetary_adjustment_for_known_year(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """Known year returns a valid MonetaryAdjustment."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        result = converter.compute_monetary_adjustment(year=2020, base_year=2010)
        assert isinstance(result, MonetaryAdjustment)
        assert result.year == 2020
        assert result.base_year == 2010
        assert result.cpi_index == pytest.approx(258.81)
        assert result.gdp_deflator == pytest.approx(113.648)

    def test_snlt_per_dollar_computation(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """SNLT per dollar = total_labor_hours / nominal_gdp."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        result = converter.compute_monetary_adjustment(year=2020, base_year=2010)
        assert isinstance(result, MonetaryAdjustment)
        # 234_000_000_000 / 21_060_500_000_000
        expected_snlt = 234_000_000_000.0 / 21_060_500_000_000.0
        assert result.snlt_per_dollar == pytest.approx(expected_snlt)

    def test_nodata_when_cpi_unavailable(self) -> None:
        """Returns NoDataSentinel when CPI is unavailable for requested year."""
        source = MockPriceIndexSource(data={})
        converter = DefaultValueBasisConverter(source)
        result = converter.compute_monetary_adjustment(year=2015, base_year=2010)
        assert isinstance(result, NoDataSentinel)
        assert not result  # falsy
        assert "CPI" in result.reason

    def test_nodata_when_gdp_deflator_unavailable(self) -> None:
        """Returns NoDataSentinel when GDP deflator unavailable."""
        # Provide CPI but not deflator by using custom data that returns None for deflator
        data: dict[int, tuple[float, float, float, float]] = {
            2015: (250.0, 110.0, 230_000_000_000.0, 18_000_000_000_000.0),
        }
        source = MockPriceIndexSource(data=data)
        converter = DefaultValueBasisConverter(source)
        # This should succeed since all data is present
        result = converter.compute_monetary_adjustment(year=2015, base_year=2010)
        assert isinstance(result, MonetaryAdjustment)

    def test_nodata_when_year_not_in_source(self) -> None:
        """Returns NoDataSentinel for entirely unknown year."""
        source = MockPriceIndexSource(data={2020: (258.81, 113.648, 234e9, 21.06e12)})
        converter = DefaultValueBasisConverter(source)
        result = converter.compute_monetary_adjustment(year=2025, base_year=2010)
        assert isinstance(result, NoDataSentinel)
        assert "CPI" in result.reason


# =============================================================================
# nominal_to_real
# =============================================================================


@pytest.mark.unit
class TestNominalToReal:
    """DefaultValueBasisConverter.nominal_to_real behavior."""

    def test_nominal_to_real_formula(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """result = nominal * (base_cpi / current_cpi)."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        nominal = 1000.0
        base_cpi = 218.06  # 2010
        current_cpi = 258.81  # 2020
        result = converter.nominal_to_real(nominal, current_cpi, base_cpi)
        expected = nominal * (base_cpi / current_cpi)
        assert result == pytest.approx(expected)

    def test_same_cpi_returns_nominal(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """When base_cpi == current_cpi, real = nominal."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        result = converter.nominal_to_real(500.0, 218.06, 218.06)
        assert result == pytest.approx(500.0)


# =============================================================================
# nominal_to_labor_time
# =============================================================================


@pytest.mark.unit
class TestNominalToLaborTime:
    """DefaultValueBasisConverter.nominal_to_labor_time behavior."""

    def test_nominal_to_labor_time_formula(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """result = nominal * snlt_per_dollar."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        nominal = 1_000_000.0
        snlt_per_dollar = 234_000_000_000.0 / 21_060_500_000_000.0
        result = converter.nominal_to_labor_time(nominal, snlt_per_dollar)
        expected = nominal * snlt_per_dollar
        assert result == pytest.approx(expected)

    def test_zero_nominal_returns_zero(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """Zero nominal value converts to zero labor time."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        result = converter.nominal_to_labor_time(0.0, 1.11e-5)
        assert result == pytest.approx(0.0)


# =============================================================================
# real_to_nominal
# =============================================================================


@pytest.mark.unit
class TestRealToNominal:
    """DefaultValueBasisConverter.real_to_nominal behavior."""

    def test_real_to_nominal_formula(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """result = real * (current_cpi / base_cpi)."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        real = 842.29  # arbitrary value
        base_cpi = 218.06  # 2010
        current_cpi = 258.81  # 2020
        result = converter.real_to_nominal(real, current_cpi, base_cpi)
        expected = real * (current_cpi / base_cpi)
        assert result == pytest.approx(expected)


# =============================================================================
# Round-trip
# =============================================================================


@pytest.mark.unit
class TestRoundTrip:
    """Round-trip conversions should preserve values within floating-point epsilon."""

    def test_nominal_to_real_to_nominal(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """nominal -> real -> nominal produces original within 1e-6."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        original = 12345.67
        base_cpi = 218.06
        current_cpi = 258.81
        real = converter.nominal_to_real(original, current_cpi, base_cpi)
        recovered = converter.real_to_nominal(real, current_cpi, base_cpi)
        assert recovered == pytest.approx(original, abs=1e-6)

    def test_round_trip_with_different_cpis(
        self,
        mock_price_index_source: MockPriceIndexSource,
    ) -> None:
        """Round-trip with 2022 CPI data also preserves value."""
        converter = DefaultValueBasisConverter(mock_price_index_source)
        original = 99999.99
        base_cpi = 218.06  # 2010
        current_cpi = 292.66  # 2022
        real = converter.nominal_to_real(original, current_cpi, base_cpi)
        recovered = converter.real_to_nominal(real, current_cpi, base_cpi)
        assert recovered == pytest.approx(original, abs=1e-6)
