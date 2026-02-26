"""Surplus value distribution calculator.

Feature: 024-capital-volume-iii (US1, FR-001, FR-016, FR-019)

Decomposes surplus value into competing claims using federal data sources.
Interest, rent, and taxes are data-driven; profit of enterprise is the
residual: p = s - i - r - t.

See Also:
    :class:`SurplusValueDistribution`: The decomposition model.
    :class:`DebtAccumulation`: Cumulative debt tracker.
    :mod:`babylon.economics.distribution.data_sources`: Data source protocols.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from babylon.economics.distribution.data_sources import (
    InterestIncomeSource,
    RentalIncomeSource,
    TaxOnSurplusSource,
)
from babylon.economics.distribution.types import (
    DebtAccumulation,
    SurplusValueDistribution,
)
from babylon.economics.tensor import NoDataSentinel


@runtime_checkable
class DistributionCalculator(Protocol):
    """Protocol for surplus value distribution computation.

    Implementations decompose total surplus into interest, rent, taxes,
    and residual profit of enterprise. Also tracks cumulative debt when
    enterprise profit is negative.
    """

    def compute_distribution(
        self,
        fips: str,
        year: int,
        total_surplus: float,
        county_profit_rate: float,
        national_interest_rate: float,
    ) -> SurplusValueDistribution | NoDataSentinel:
        """Decompose surplus into p + i + r + t.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.
            total_surplus: Total surplus value from ValueTensor4x3.
            county_profit_rate: County-level profit rate (s/C).
            national_interest_rate: National average interest rate.

        Returns:
            SurplusValueDistribution if data available, NoDataSentinel otherwise.
        """
        ...

    def update_debt_accumulation(
        self,
        current_debt: DebtAccumulation,
        enterprise_profit: float,
        new_year: int,
    ) -> DebtAccumulation:
        """Update cumulative debt tracker based on enterprise profit.

        Args:
            current_debt: Current debt state.
            enterprise_profit: Enterprise profit for the period.
            new_year: Calendar year for the updated state.

        Returns:
            Updated DebtAccumulation.
        """
        ...


class DefaultDistributionCalculator:
    """Data-driven surplus value distribution.

    Interest, rent, and taxes are derived from federal data sources.
    Profit of enterprise is the residual: p = s - i - r - t.

    Args:
        rental_source: BEA rental income data source.
        tax_source: IRS/BEA corporate tax data source.
        interest_source: FRED/BEA net interest data source.
    """

    def __init__(
        self,
        rental_source: RentalIncomeSource,
        tax_source: TaxOnSurplusSource,
        interest_source: InterestIncomeSource,
    ) -> None:
        self._rental_source = rental_source
        self._tax_source = tax_source
        self._interest_source = interest_source

    def compute_distribution(
        self,
        fips: str,
        year: int,
        total_surplus: float,
        county_profit_rate: float,
        national_interest_rate: float,
    ) -> SurplusValueDistribution | NoDataSentinel:
        """Decompose surplus into p + i + r + t.

        Args:
            fips: 5-digit county FIPS code.
            year: Calendar year.
            total_surplus: Total surplus value from ValueTensor4x3.
            county_profit_rate: County-level profit rate (s/C).
            national_interest_rate: National average interest rate.

        Returns:
            SurplusValueDistribution if all data available, NoDataSentinel otherwise.
        """
        # Zero surplus -> all-zero distribution (no data source queries needed)
        if total_surplus == 0.0:
            return SurplusValueDistribution(
                fips_code=fips,
                year=year,
                total_surplus_produced=0.0,
                interest_payments=0.0,
                ground_rent=0.0,
                taxes_on_surplus=0.0,
            )

        # Fetch data-driven national components and scale to county level.
        # Implied county capital stock C ≈ surplus / profit_rate (Marx: s = r·C).
        # County interest burden = effective_rate × C = rate × (surplus / profit_rate).
        # National rent/tax totals are scaled by county's surplus share of
        # national surplus (approximated as county_profit_rate × C_national proxy).
        safe_profit_rate = max(county_profit_rate, 1e-4)
        implied_capital = total_surplus / safe_profit_rate

        # County interest: derived from capital stock × effective rate (FR-003)
        county_interest = national_interest_rate * implied_capital

        # National rent total → scaled to county by capital share
        national_rent = self._rental_source.get_rental_income(fips, year)
        if national_rent is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Rental income data unavailable for {fips}/{year}",
            )

        # Approximate county share: county surplus / national surplus proxy
        # National surplus ≈ national_rent / rentier_share_of_surplus (≈8%)
        national_surplus_proxy = national_rent / 0.08
        county_share = min(total_surplus / max(national_surplus_proxy, 1.0), 1.0)
        rent = national_rent * county_share

        national_tax = self._tax_source.get_corporate_tax(fips, year)
        if national_tax is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"Corporate tax data unavailable for {fips}/{year}",
            )
        tax = national_tax * county_share

        # Verify interest data availability (FR-015)
        interest_check = self._interest_source.get_national_net_interest(year)
        if interest_check is None:
            return NoDataSentinel(
                fips=fips,
                year=year,
                reason=f"National interest data unavailable for {year}",
            )

        return SurplusValueDistribution(
            fips_code=fips,
            year=year,
            total_surplus_produced=total_surplus,
            interest_payments=county_interest,
            ground_rent=rent,
            taxes_on_surplus=tax,
        )

    def update_debt_accumulation(
        self,
        current_debt: DebtAccumulation,
        enterprise_profit: float,
        new_year: int,
    ) -> DebtAccumulation:
        """Update cumulative debt tracker.

        Args:
            current_debt: Current debt state.
            enterprise_profit: Enterprise profit for the period.
            new_year: Calendar year for the updated state.

        Returns:
            Updated DebtAccumulation.
        """
        return DebtAccumulation.update(current_debt, enterprise_profit, new_year)
