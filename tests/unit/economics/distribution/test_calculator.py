"""Unit tests for DefaultDistributionCalculator.

Feature: 024-capital-volume-iii (US1, FR-001, FR-016, FR-019)
TDD Red Phase: Tests define expected behavior for data-driven distribution.

The calculator fetches interest, rent, and tax from data sources,
then constructs a SurplusValueDistribution where profit is the residual.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.distribution.calculator import DefaultDistributionCalculator
from babylon.domain.economics.distribution.types import (
    DebtAccumulation,
    SurplusValueDistribution,
)
from babylon.domain.economics.tensor import NoDataSentinel

from .conftest import (
    MockInterestIncomeSource,
    MockRentalIncomeSource,
    MockTaxOnSurplusSource,
)


@pytest.mark.unit
class TestComputeDistribution:
    """DefaultDistributionCalculator.compute_distribution returns valid decomposition."""

    def test_returns_surplus_value_distribution(
        self,
        mock_rental_source: MockRentalIncomeSource,
        mock_tax_source: MockTaxOnSurplusSource,
        mock_interest_source: MockInterestIncomeSource,
    ) -> None:
        """compute_distribution returns a SurplusValueDistribution instance."""
        calc = DefaultDistributionCalculator(
            rental_source=mock_rental_source,
            tax_source=mock_tax_source,
            interest_source=mock_interest_source,
        )
        result = calc.compute_distribution(
            fips="26163",
            year=2020,
            total_surplus=10_000_000_000.0,
            county_profit_rate=0.05,
            national_interest_rate=0.04,
        )
        assert isinstance(result, SurplusValueDistribution)

    def test_accounting_identity_holds(
        self,
        mock_rental_source: MockRentalIncomeSource,
        mock_tax_source: MockTaxOnSurplusSource,
        mock_interest_source: MockInterestIncomeSource,
    ) -> None:
        """s = p + i + r + t holds within DISTRIBUTION_EPSILON."""
        calc = DefaultDistributionCalculator(
            rental_source=mock_rental_source,
            tax_source=mock_tax_source,
            interest_source=mock_interest_source,
        )
        result = calc.compute_distribution(
            fips="26163",
            year=2020,
            total_surplus=10_000_000_000.0,
            county_profit_rate=0.05,
            national_interest_rate=0.04,
        )
        assert isinstance(result, SurplusValueDistribution)
        assert result.distribution_complete is True

    def test_zero_surplus_produces_all_zero_distribution(
        self,
        mock_rental_source: MockRentalIncomeSource,
        mock_tax_source: MockTaxOnSurplusSource,
        mock_interest_source: MockInterestIncomeSource,
    ) -> None:
        """Zero surplus produces all-zero distribution without querying data sources."""
        calc = DefaultDistributionCalculator(
            rental_source=mock_rental_source,
            tax_source=mock_tax_source,
            interest_source=mock_interest_source,
        )
        result = calc.compute_distribution(
            fips="26163",
            year=2020,
            total_surplus=0.0,
            county_profit_rate=0.05,
            national_interest_rate=0.04,
        )
        assert isinstance(result, SurplusValueDistribution)
        assert result.total_surplus_produced == 0.0
        assert result.interest_payments == 0.0
        assert result.ground_rent == 0.0
        assert result.taxes_on_surplus == 0.0
        assert result.profit_of_enterprise == pytest.approx(0.0)


@pytest.mark.unit
class TestComputeDistributionNoData:
    """NoDataSentinel returned when data sources lack required data."""

    def test_missing_rental_income_returns_sentinel(self) -> None:
        """Missing rental income returns NoDataSentinel with rental-specific reason."""
        rental_source = MockRentalIncomeSource(data={})  # No data
        tax_source = MockTaxOnSurplusSource()
        interest_source = MockInterestIncomeSource()

        calc = DefaultDistributionCalculator(
            rental_source=rental_source,
            tax_source=tax_source,
            interest_source=interest_source,
        )
        result = calc.compute_distribution(
            fips="26163",
            year=2020,
            total_surplus=10_000_000_000.0,
            county_profit_rate=0.05,
            national_interest_rate=0.04,
        )
        assert isinstance(result, NoDataSentinel)
        assert "ental" in result.reason.lower() or "rental" in result.reason.lower()

    def test_missing_tax_data_returns_sentinel(self) -> None:
        """Missing tax data returns NoDataSentinel with tax-specific reason."""
        rental_source = MockRentalIncomeSource()
        tax_source = MockTaxOnSurplusSource(data={})  # No data
        interest_source = MockInterestIncomeSource()

        calc = DefaultDistributionCalculator(
            rental_source=rental_source,
            tax_source=tax_source,
            interest_source=interest_source,
        )
        result = calc.compute_distribution(
            fips="26163",
            year=2020,
            total_surplus=10_000_000_000.0,
            county_profit_rate=0.05,
            national_interest_rate=0.04,
        )
        assert isinstance(result, NoDataSentinel)
        assert "tax" in result.reason.lower()

    def test_missing_interest_data_returns_sentinel(self) -> None:
        """Missing interest data returns NoDataSentinel with interest-specific reason."""
        rental_source = MockRentalIncomeSource()
        tax_source = MockTaxOnSurplusSource()
        interest_source = MockInterestIncomeSource(data={})  # No data

        calc = DefaultDistributionCalculator(
            rental_source=rental_source,
            tax_source=tax_source,
            interest_source=interest_source,
        )
        result = calc.compute_distribution(
            fips="26163",
            year=2020,
            total_surplus=10_000_000_000.0,
            county_profit_rate=0.05,
            national_interest_rate=0.04,
        )
        assert isinstance(result, NoDataSentinel)
        assert "interest" in result.reason.lower()


@pytest.mark.unit
class TestUpdateDebtAccumulation:
    """DefaultDistributionCalculator.update_debt_accumulation delegates correctly."""

    def test_negative_profit_increases_debt(
        self,
        mock_rental_source: MockRentalIncomeSource,
        mock_tax_source: MockTaxOnSurplusSource,
        mock_interest_source: MockInterestIncomeSource,
    ) -> None:
        """Negative enterprise profit increases accumulated debt."""
        calc = DefaultDistributionCalculator(
            rental_source=mock_rental_source,
            tax_source=mock_tax_source,
            interest_source=mock_interest_source,
        )
        current = DebtAccumulation.default(fips="26163", year=2020)
        updated = calc.update_debt_accumulation(
            current_debt=current,
            enterprise_profit=-1_000.0,
            new_year=2021,
        )
        assert updated.accumulated_debt == pytest.approx(1_000.0)
        assert updated.consecutive_deficit_ticks == 1

    def test_positive_profit_retires_debt(
        self,
        mock_rental_source: MockRentalIncomeSource,
        mock_tax_source: MockTaxOnSurplusSource,
        mock_interest_source: MockInterestIncomeSource,
    ) -> None:
        """Positive enterprise profit retires accumulated debt."""
        calc = DefaultDistributionCalculator(
            rental_source=mock_rental_source,
            tax_source=mock_tax_source,
            interest_source=mock_interest_source,
        )
        current = DebtAccumulation(
            fips_code="26163",
            year=2020,
            accumulated_debt=2_000.0,
            consecutive_deficit_ticks=3,
        )
        updated = calc.update_debt_accumulation(
            current_debt=current,
            enterprise_profit=800.0,
            new_year=2021,
        )
        assert updated.accumulated_debt == pytest.approx(1_200.0)
        assert updated.consecutive_deficit_ticks == 0
