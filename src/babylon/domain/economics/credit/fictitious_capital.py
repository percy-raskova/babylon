"""Fictitious capital stock computation.

Feature: 024-capital-volume-iii (US3, FR-004, FR-005)

Computes the stock of fictitious capital (financial claims on future value
production) from Z.1 Financial Accounts and FRED credit aggregate data.
Provides financialization index as a crisis indicator.

See Also:
    :class:`FictitiousCapitalStock`: Data model for accumulated claims.
    :mod:`babylon.domain.economics.credit.types`: Threshold constants.
"""

from __future__ import annotations

from typing import Protocol

from babylon.domain.economics.credit.data_sources import (
    CreditAggregateSource,
    Z1FinancialAccountsSource,
)
from babylon.domain.economics.credit.types import FINANCIALIZATION_BUBBLE, FictitiousCapitalStock
from babylon.domain.economics.tensor import NoDataSentinel


class FictitiousCapitalCalculator(Protocol):
    """Protocol for fictitious capital computation.

    Implementations assemble financial claim data from multiple sources
    and provide crisis indicators (financialization index, overaccumulation).
    """

    def compute_fictitious_capital(self, year: int) -> FictitiousCapitalStock | NoDataSentinel:
        """Compute fictitious capital stock for a given year.

        Args:
            year: Calendar year.

        Returns:
            FictitiousCapitalStock if all required data available,
            NoDataSentinel otherwise.
        """
        ...

    def compute_financialization_index(
        self, fictitious: FictitiousCapitalStock, real_gdp: float
    ) -> float:
        """Compute financialization index = total_claims / real_gdp.

        Args:
            fictitious: Fictitious capital stock snapshot.
            real_gdp: Real GDP in current dollars.

        Returns:
            Ratio of total financial claims to real production.
        """
        ...

    def check_overaccumulation(self, financialization_index: float) -> bool:
        """Check whether financialization index exceeds bubble threshold.

        Args:
            financialization_index: Ratio of total claims to real GDP.

        Returns:
            True if index exceeds FINANCIALIZATION_BUBBLE threshold.
        """
        ...


class DefaultFictitiousCapitalCalculator:
    """Default implementation of fictitious capital computation.

    Assembles financial claim data from FRED credit aggregates (government
    debt, equity market cap) and Z.1 Financial Accounts (corporate debt,
    household debt, derivatives notional).

    Args:
        credit_source: FRED credit aggregate data source.
        z1_source: Fed Z.1 Financial Accounts data source.
    """

    def __init__(
        self,
        credit_source: CreditAggregateSource,
        z1_source: Z1FinancialAccountsSource,
    ) -> None:
        self._credit_source = credit_source
        self._z1_source = z1_source

    def compute_fictitious_capital(self, year: int) -> FictitiousCapitalStock | NoDataSentinel:
        """Compute fictitious capital stock for a given year.

        Args:
            year: Calendar year.

        Returns:
            FictitiousCapitalStock if all required data available,
            NoDataSentinel with reason otherwise.
        """
        govt_debt = self._credit_source.get_government_debt(year)
        if govt_debt is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Government debt unavailable for {year}",
            )

        equity = self._credit_source.get_equity_market_cap(year)
        if equity is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Equity market cap unavailable for {year}",
            )

        corp_debt = self._z1_source.get_corporate_debt(year)
        if corp_debt is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Corporate debt (Z.1) unavailable for {year}",
            )

        household_debt = self._z1_source.get_household_debt(year)
        if household_debt is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Household debt (Z.1) unavailable for {year}",
            )

        derivatives = self._z1_source.get_derivatives_notional(year)

        return FictitiousCapitalStock(
            year=year,
            government_debt=govt_debt,
            corporate_equity=equity,
            corporate_debt=corp_debt,
            household_debt=household_debt,
            derivatives_notional=derivatives if derivatives is not None else 0.0,
        )

    def compute_financialization_index(
        self, fictitious: FictitiousCapitalStock, real_gdp: float
    ) -> float:
        """Compute financialization index = total_claims / real_gdp.

        Args:
            fictitious: Fictitious capital stock snapshot.
            real_gdp: Real GDP in current dollars.

        Returns:
            Ratio of total financial claims to real production.
        """
        return fictitious.ratio_to_real(real_gdp)

    def check_overaccumulation(self, financialization_index: float) -> bool:
        """Check whether financialization index exceeds bubble threshold.

        Args:
            financialization_index: Ratio of total claims to real GDP.

        Returns:
            True if index strictly exceeds FINANCIALIZATION_BUBBLE.
        """
        return financialization_index > FINANCIALIZATION_BUBBLE
