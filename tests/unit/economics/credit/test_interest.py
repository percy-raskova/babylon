"""Tests for interest rate computation and county interest burden.

Feature: 024-capital-volume-iii (US2, FR-002, FR-003)
TDD Red Phase: Tests define expected behavior for DefaultInterestCalculator.

FR-003: Effective interest rate for industrial borrowers NEVER exceeds county profit rate.
"""

from __future__ import annotations

import pytest
from tests.unit.economics.credit.conftest import MockInterestRateSource

from babylon.economics.credit.interest import DefaultInterestCalculator
from babylon.economics.credit.types import InterestRateState
from babylon.economics.tensor import NoDataSentinel

# =============================================================================
# compute_interest_rate_state
# =============================================================================


@pytest.mark.unit
class TestComputeInterestRateState:
    """DefaultInterestCalculator.compute_interest_rate_state from FRED data."""

    def test_returns_interest_rate_state_for_known_year(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """Successful lookup returns InterestRateState with FRED values."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        result = calc.compute_interest_rate_state(2020)
        assert isinstance(result, InterestRateState)
        assert result.year == 2020
        assert result.base_rate == pytest.approx(0.0036)
        assert result.treasury_10y == pytest.approx(0.0089)
        assert result.baa_spread == pytest.approx(0.0234)

    def test_returns_sentinel_for_unknown_year(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """Missing year returns NoDataSentinel with descriptive reason."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        result = calc.compute_interest_rate_state(1999)
        assert isinstance(result, NoDataSentinel)
        assert not result  # Sentinel is falsy
        assert "1999" in result.reason

    def test_returns_sentinel_when_fed_funds_unavailable(self) -> None:
        """Partial data: only fed_funds missing returns sentinel."""
        # Create source that returns None for fed funds but valid for others
        source = MockInterestRateSource(
            data={
                2020: (None, 0.0089, 0.0234),  # type: ignore[dict-item]
            }
        )

        # Override to return None for fed_funds
        def _get_fed_funds(year: int) -> float | None:
            return None

        source.get_federal_funds_rate = _get_fed_funds  # type: ignore[assignment]

        calc = DefaultInterestCalculator(rate_source=source)
        result = calc.compute_interest_rate_state(2020)
        assert isinstance(result, NoDataSentinel)
        assert "Federal funds rate" in result.reason

    def test_crisis_year_data(self, mock_interest_rate_source: MockInterestRateSource) -> None:
        """2008 crisis year returns valid state with wide spreads."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        result = calc.compute_interest_rate_state(2008)
        assert isinstance(result, InterestRateState)
        assert result.base_rate == pytest.approx(0.0193)
        assert result.baa_spread == pytest.approx(0.0349)
        assert result.effective_rate == pytest.approx(0.0193 + 0.0349)


# =============================================================================
# compute_county_interest_burden (FR-003)
# =============================================================================


@pytest.mark.unit
class TestComputeCountyInterestBurden:
    """DefaultInterestCalculator.compute_county_interest_burden (FR-003).

    FR-003: Effective rate = min(national_rate, county_profit_rate).
    Interest burden = effective_rate * capital_stock.
    """

    def test_normal_case_national_rate_below_profit(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """When national rate < county profit rate, use national rate."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        # 3% national rate, 5% county profit rate, $1M capital stock
        burden = calc.compute_county_interest_burden(
            national_rate=0.03,
            county_profit_rate=0.05,
            county_capital_stock=1_000_000.0,
        )
        # Uses national rate 3%
        assert burden == pytest.approx(0.03 * 1_000_000.0)

    def test_cap_case_national_rate_exceeds_profit(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """FR-003: When national rate > county profit rate, cap at profit rate."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        # 5% national rate, 2% county profit rate, $1M capital stock
        burden = calc.compute_county_interest_burden(
            national_rate=0.05,
            county_profit_rate=0.02,
            county_capital_stock=1_000_000.0,
        )
        # Capped at county profit rate 2%
        assert burden == pytest.approx(0.02 * 1_000_000.0)

    def test_effective_rate_never_exceeds_profit_rate(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """FR-003 invariant: effective rate <= county profit rate always."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        # Many test cases: national rates from 0.01 to 0.20
        for national in [0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]:
            county_profit = 0.04
            capital = 500_000.0
            burden = calc.compute_county_interest_burden(
                national_rate=national,
                county_profit_rate=county_profit,
                county_capital_stock=capital,
            )
            effective = burden / capital
            assert effective <= county_profit + 1e-10, (
                f"FR-003 violated: effective {effective} > profit {county_profit} "
                f"with national rate {national}"
            )

    def test_zero_profit_rate_yields_zero_burden(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """Zero profit rate means zero interest burden (can't extract interest)."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        burden = calc.compute_county_interest_burden(
            national_rate=0.05,
            county_profit_rate=0.0,
            county_capital_stock=1_000_000.0,
        )
        assert burden == pytest.approx(0.0)

    def test_zero_capital_stock_yields_zero_burden(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """Zero capital stock means zero interest burden."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        burden = calc.compute_county_interest_burden(
            national_rate=0.05,
            county_profit_rate=0.05,
            county_capital_stock=0.0,
        )
        assert burden == pytest.approx(0.0)

    def test_equal_rates_uses_either(
        self, mock_interest_rate_source: MockInterestRateSource
    ) -> None:
        """When national rate equals county profit rate, result is the same."""
        calc = DefaultInterestCalculator(rate_source=mock_interest_rate_source)
        burden = calc.compute_county_interest_burden(
            national_rate=0.04,
            county_profit_rate=0.04,
            county_capital_stock=1_000_000.0,
        )
        assert burden == pytest.approx(0.04 * 1_000_000.0)
