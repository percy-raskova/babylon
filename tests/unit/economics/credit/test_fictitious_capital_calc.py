"""Tests for DefaultFictitiousCapitalCalculator.

Feature: 024-capital-volume-iii (US3, FR-004, FR-005)
TDD Red Phase: Tests define expected behavior for fictitious capital computation.

DefaultFictitiousCapitalCalculator: Computes fictitious capital stock from
Z.1 Financial Accounts and FRED credit aggregate data. Provides
financialization index and overaccumulation detection.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.credit.fictitious_capital import (
    DefaultFictitiousCapitalCalculator,
)
from babylon.domain.economics.credit.types import (
    FINANCIALIZATION_BUBBLE,
    FictitiousCapitalStock,
)
from babylon.domain.economics.tensor import NoDataSentinel

from .conftest import MockCreditAggregateSource, MockZ1Source

# =============================================================================
# compute_fictitious_capital
# =============================================================================


@pytest.mark.unit
class TestComputeFictitiousCapital:
    """DefaultFictitiousCapitalCalculator.compute_fictitious_capital."""

    def test_returns_fictitious_capital_stock(
        self,
        mock_credit_aggregate_source: MockCreditAggregateSource,
        mock_z1_source: MockZ1Source,
    ) -> None:
        """Returns FictitiousCapitalStock when all data available."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=mock_credit_aggregate_source,
            z1_source=mock_z1_source,
        )
        result = calc.compute_fictitious_capital(2020)
        assert isinstance(result, FictitiousCapitalStock)
        assert result.year == 2020
        assert result.government_debt == pytest.approx(27_000_000_000_000.0)
        assert result.corporate_equity == pytest.approx(36_000_000_000_000.0)
        assert result.corporate_debt == pytest.approx(11_000_000_000_000.0)
        assert result.household_debt == pytest.approx(16_000_000_000_000.0)
        assert result.derivatives_notional == pytest.approx(600_000_000_000_000.0)

    def test_returns_no_data_sentinel_when_govt_debt_unavailable(
        self,
        mock_z1_source: MockZ1Source,
    ) -> None:
        """Returns NoDataSentinel when government debt data is missing."""
        empty_credit = MockCreditAggregateSource(data={})
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=empty_credit,
            z1_source=mock_z1_source,
        )
        result = calc.compute_fictitious_capital(2020)
        assert isinstance(result, NoDataSentinel)
        assert not result  # NoDataSentinel is falsy
        assert "Government debt" in result.reason

    def test_returns_no_data_sentinel_when_equity_unavailable(
        self,
        mock_z1_source: MockZ1Source,
    ) -> None:
        """Returns NoDataSentinel when equity market cap data is missing."""
        credit_source = _CreditSourceWithGovtDebtOnly(govt_debt=27_000_000_000_000.0)
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=credit_source,
            z1_source=mock_z1_source,
        )
        result = calc.compute_fictitious_capital(2020)
        assert isinstance(result, NoDataSentinel)
        assert "Equity market cap" in result.reason

    def test_returns_no_data_sentinel_when_corporate_debt_unavailable(
        self,
        mock_credit_aggregate_source: MockCreditAggregateSource,
    ) -> None:
        """Returns NoDataSentinel when Z.1 corporate debt data is missing."""
        empty_z1 = MockZ1Source(data={})
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=mock_credit_aggregate_source,
            z1_source=empty_z1,
        )
        result = calc.compute_fictitious_capital(2020)
        assert isinstance(result, NoDataSentinel)
        assert "Corporate debt" in result.reason

    def test_returns_no_data_sentinel_when_household_debt_unavailable(
        self,
        mock_credit_aggregate_source: MockCreditAggregateSource,
    ) -> None:
        """Returns NoDataSentinel when Z.1 household debt data is missing."""
        # Z1 source with corporate debt but no household debt
        z1_source = _Z1SourceWithCorporateDebtOnly(corporate_debt=11_000_000_000_000.0)
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=mock_credit_aggregate_source,
            z1_source=z1_source,
        )
        result = calc.compute_fictitious_capital(2020)
        assert isinstance(result, NoDataSentinel)
        assert "Household debt" in result.reason

    def test_derivatives_default_zero_when_unavailable(
        self,
        mock_credit_aggregate_source: MockCreditAggregateSource,
    ) -> None:
        """Derivatives default to 0.0 when Z.1 derivatives data is missing."""
        z1_no_derivatives = _Z1SourceWithoutDerivatives(
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=mock_credit_aggregate_source,
            z1_source=z1_no_derivatives,
        )
        result = calc.compute_fictitious_capital(2020)
        assert isinstance(result, FictitiousCapitalStock)
        assert result.derivatives_notional == pytest.approx(0.0)

    def test_crisis_year_2008(
        self,
        mock_credit_aggregate_source: MockCreditAggregateSource,
        mock_z1_source: MockZ1Source,
    ) -> None:
        """2008 crisis year data is correctly assembled."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=mock_credit_aggregate_source,
            z1_source=mock_z1_source,
        )
        result = calc.compute_fictitious_capital(2008)
        assert isinstance(result, FictitiousCapitalStock)
        assert result.year == 2008
        assert result.government_debt == pytest.approx(10_000_000_000_000.0)
        assert result.corporate_equity == pytest.approx(9_000_000_000_000.0)
        assert result.corporate_debt == pytest.approx(7_500_000_000_000.0)
        assert result.household_debt == pytest.approx(13_800_000_000_000.0)


# =============================================================================
# compute_financialization_index
# =============================================================================


@pytest.mark.unit
class TestComputeFinancializationIndex:
    """DefaultFictitiousCapitalCalculator.compute_financialization_index."""

    def test_financialization_index_normal(self) -> None:
        """Financialization index = total_claims / real_gdp."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=MockCreditAggregateSource(),
            z1_source=MockZ1Source(),
        )
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        real_gdp = 21_000_000_000_000.0
        index = calc.compute_financialization_index(stock, real_gdp)
        expected = stock.total_claims / real_gdp
        assert index == pytest.approx(expected)

    def test_financialization_index_delegates_to_ratio_to_real(self) -> None:
        """compute_financialization_index delegates to FictitiousCapitalStock.ratio_to_real."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=MockCreditAggregateSource(),
            z1_source=MockZ1Source(),
        )
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=10_000.0,
            corporate_equity=20_000.0,
            corporate_debt=5_000.0,
            household_debt=15_000.0,
        )
        real_gdp = 25_000.0
        assert calc.compute_financialization_index(stock, real_gdp) == pytest.approx(
            stock.ratio_to_real(real_gdp)
        )


# =============================================================================
# check_overaccumulation
# =============================================================================


@pytest.mark.unit
class TestCheckOveraccumulation:
    """DefaultFictitiousCapitalCalculator.check_overaccumulation."""

    def test_overaccumulation_above_threshold(self) -> None:
        """Returns True when financialization_index > FINANCIALIZATION_BUBBLE."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=MockCreditAggregateSource(),
            z1_source=MockZ1Source(),
        )
        assert calc.check_overaccumulation(FINANCIALIZATION_BUBBLE + 0.1) is True

    def test_no_overaccumulation_below_threshold(self) -> None:
        """Returns False when financialization_index < FINANCIALIZATION_BUBBLE."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=MockCreditAggregateSource(),
            z1_source=MockZ1Source(),
        )
        assert calc.check_overaccumulation(FINANCIALIZATION_BUBBLE - 0.1) is False

    def test_no_overaccumulation_at_threshold(self) -> None:
        """Returns False when financialization_index == FINANCIALIZATION_BUBBLE (strict >)."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=MockCreditAggregateSource(),
            z1_source=MockZ1Source(),
        )
        assert calc.check_overaccumulation(FINANCIALIZATION_BUBBLE) is False

    def test_overaccumulation_with_real_data(self) -> None:
        """Integration-style: compute full pipeline and check overaccumulation."""
        calc = DefaultFictitiousCapitalCalculator(
            credit_source=MockCreditAggregateSource(),
            z1_source=MockZ1Source(),
        )
        stock_result = calc.compute_fictitious_capital(2020)
        assert isinstance(stock_result, FictitiousCapitalStock)
        # total_claims = 27T + 36T + 11T + 16T = 90T
        # real_gdp ~21T -> ratio ~4.28 > FINANCIALIZATION_BUBBLE (3.5)
        real_gdp = 21_000_000_000_000.0
        index = calc.compute_financialization_index(stock_result, real_gdp)
        assert calc.check_overaccumulation(index) is True


# =============================================================================
# Helper Mock Sources for Edge Cases
# =============================================================================


class _CreditSourceWithGovtDebtOnly:
    """Credit source that has government debt but no equity market cap."""

    def __init__(self, govt_debt: float) -> None:
        self._govt_debt = govt_debt

    def get_total_credit(self, year: int) -> float | None:
        return None

    def get_government_debt(self, year: int) -> float | None:
        return self._govt_debt

    def get_equity_market_cap(self, year: int) -> float | None:
        return None


class _Z1SourceWithCorporateDebtOnly:
    """Z1 source that has corporate debt but no household debt."""

    def __init__(self, corporate_debt: float) -> None:
        self._corporate_debt = corporate_debt

    def get_corporate_debt(self, year: int) -> float | None:
        return self._corporate_debt

    def get_household_debt(self, year: int) -> float | None:
        return None

    def get_derivatives_notional(self, year: int) -> float | None:
        return None


class _Z1SourceWithoutDerivatives:
    """Z1 source that has debts but no derivatives data."""

    def __init__(self, corporate_debt: float, household_debt: float) -> None:
        self._corporate_debt = corporate_debt
        self._household_debt = household_debt

    def get_corporate_debt(self, year: int) -> float | None:
        return self._corporate_debt

    def get_household_debt(self, year: int) -> float | None:
        return self._household_debt

    def get_derivatives_notional(self, year: int) -> float | None:
        return None
