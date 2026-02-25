"""Contract: Credit Dynamics and Fictitious Capital (US2, US3, FR-002..FR-006).

These are function signatures defining the public API contract.
Implementations go in src/babylon/economics/credit/.
"""

from __future__ import annotations

from typing import Protocol

from babylon.economics.tensor import NoDataSentinel

# Placeholder type aliases
Currency = float


# ---------------------------------------------------------------------------
# Data Source Protocols
# ---------------------------------------------------------------------------


class InterestRateSource(Protocol):
    """Protocol for FRED interest rate data (national-level)."""

    def get_federal_funds_rate(self, year: int) -> float | None:
        """Get annual average federal funds rate."""
        ...

    def get_treasury_10y(self, year: int) -> float | None:
        """Get annual average 10-year Treasury yield."""
        ...

    def get_baa_spread(self, year: int) -> float | None:
        """Get annual average Baa corporate spread over Treasury."""
        ...


class CreditAggregateSource(Protocol):
    """Protocol for FRED credit aggregate data (national-level)."""

    def get_total_credit(self, year: int) -> Currency | None:
        """Get total credit market debt outstanding (TCMDO)."""
        ...

    def get_government_debt(self, year: int) -> Currency | None:
        """Get federal debt total public debt (GFDEBTN)."""
        ...

    def get_equity_market_cap(self, year: int) -> Currency | None:
        """Get equity market capitalization proxy (Wilshire 5000)."""
        ...


class Z1FinancialAccountsSource(Protocol):
    """Protocol for Fed Z.1 Financial Accounts data (national-level)."""

    def get_corporate_debt(self, year: int) -> Currency | None:
        """Get total corporate debt outstanding."""
        ...

    def get_household_debt(self, year: int) -> Currency | None:
        """Get total household debt (mortgage + consumer + student)."""
        ...

    def get_derivatives_notional(self, year: int) -> Currency | None:
        """Get notional value of derivative contracts."""
        ...


# ---------------------------------------------------------------------------
# Calculator Protocols
# ---------------------------------------------------------------------------


class InterestCalculator(Protocol):
    """Protocol for interest rate and burden computation."""

    def compute_interest_rate_state(
        self,
        year: int,
    ) -> "InterestRateState | NoDataSentinel":
        """Compute national interest rate state from FRED data.

        Returns:
            InterestRateState with base_rate, treasury_10y, baa_spread,
            and computed effective_rate.
        """
        ...

    def compute_county_interest_burden(
        self,
        national_rate: float,
        county_profit_rate: float,
        county_capital_stock: Currency,
    ) -> Currency:
        """Compute interest burden for a county.

        The effective rate is capped at the county profit rate (FR-003).

        Args:
            national_rate: National effective interest rate.
            county_profit_rate: County-level profit rate.
            county_capital_stock: County total capital stock.

        Returns:
            Interest payment = min(national_rate, county_profit_rate) * capital_stock

        Post-conditions:
            - Effective rate <= county_profit_rate (FR-003)
            - Result >= 0
        """
        ...


class CreditCycleDetector(Protocol):
    """Protocol for credit cycle phase detection (FR-006)."""

    def evaluate(
        self,
        profit_rate: float,
        profit_rate_trend: float,
        credit_growth: float,
        default_rate: float,
        current_phase: "CreditCyclePhase",
    ) -> "CreditCyclePhase":
        """Determine credit cycle phase transition.

        Args:
            profit_rate: Current national profit rate.
            profit_rate_trend: First derivative of profit rate.
            credit_growth: YoY credit expansion rate.
            default_rate: Current loan default rate.
            current_phase: Previous tick's credit cycle phase.

        Returns:
            New CreditCyclePhase (may be same as current).

        Post-conditions:
            - Only valid transitions permitted per state machine (FR-006)
            - STAGNATION is terminal (no exits)
        """
        ...


class FictitiousCapitalCalculator(Protocol):
    """Protocol for fictitious capital stock computation (FR-004, FR-005)."""

    def compute_fictitious_capital(
        self,
        year: int,
    ) -> "FictitiousCapitalStock | NoDataSentinel":
        """Compute national fictitious capital stock from Z.1 + FRED data.

        Returns:
            FictitiousCapitalStock with all five categories populated.
        """
        ...

    def compute_financialization_index(
        self,
        fictitious: "FictitiousCapitalStock",
        real_gdp: Currency,
    ) -> float:
        """Compute financialization index = total_claims / real_gdp (FR-005).

        Returns:
            Ratio of fictitious claims to real production. Higher = more fragile.
        """
        ...
