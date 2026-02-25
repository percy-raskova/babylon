"""Contract: Surplus Value Distribution (US1, FR-001, FR-016, FR-019).

These are function signatures defining the public API contract.
Implementations go in src/babylon/economics/distribution/.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.tensor import NoDataSentinel

# Placeholder type aliases for contract readability
Currency = float
EPSILON = 1e-9


# ---------------------------------------------------------------------------
# Data Source Protocols
# ---------------------------------------------------------------------------


class RentalIncomeSource(Protocol):
    """Protocol for BEA rental income data (county-level)."""

    def get_rental_income(self, fips: str, year: int) -> Currency | None:
        """Get total rental income of persons for a county-year.

        Returns:
            Rental income in current dollars, or None if unavailable.
        """
        ...


class TaxOnSurplusSource(Protocol):
    """Protocol for IRS/BEA tax on corporate income (county-level)."""

    def get_corporate_tax(self, fips: str, year: int) -> Currency | None:
        """Get corporate income tax for a county-year.

        Returns:
            Tax amount in current dollars, or None if unavailable.
        """
        ...


class InterestIncomeSource(Protocol):
    """Protocol for FRED/BEA net interest data (national-level)."""

    def get_national_net_interest(self, year: int) -> Currency | None:
        """Get national net interest income for a year.

        Returns:
            Net interest in current dollars, or None if unavailable.
        """
        ...


# ---------------------------------------------------------------------------
# Calculator Protocol
# ---------------------------------------------------------------------------


class DistributionCalculator(Protocol):
    """Protocol for surplus value distribution computation."""

    def compute_distribution(
        self,
        fips: str,
        year: int,
        total_surplus: Currency,
        county_profit_rate: float,
        national_interest_rate: float,
    ) -> "SurplusValueDistribution | NoDataSentinel":
        """Decompose total surplus into p + i + r + t.

        Args:
            fips: County FIPS code.
            year: Distribution year.
            total_surplus: Total surplus value from ValueTensor4x3.
            county_profit_rate: County-level profit rate.
            national_interest_rate: National effective interest rate.

        Returns:
            SurplusValueDistribution or NoDataSentinel if data unavailable.

        Post-conditions:
            - interest + rent + taxes + profit == total_surplus (within EPSILON)
            - interest >= 0, rent >= 0, taxes >= 0
            - profit may be negative (claims exceed surplus)
        """
        ...

    def update_debt_accumulation(
        self,
        current_debt: "DebtAccumulation",
        enterprise_profit: Currency,
    ) -> "DebtAccumulation":
        """Update cumulative debt tracker based on current period profit.

        Args:
            current_debt: Previous debt accumulation state.
            enterprise_profit: Current period profit (may be negative).

        Returns:
            Updated DebtAccumulation with accumulated_debt adjusted.

        Post-conditions:
            - If profit < 0: accumulated_debt increases by |profit|
            - If profit > 0: accumulated_debt decreases by min(profit, debt)
            - accumulated_debt >= 0 always
        """
        ...
