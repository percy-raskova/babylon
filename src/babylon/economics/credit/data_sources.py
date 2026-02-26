"""Data source protocols for credit dynamics and fictitious capital.

Feature: 024-capital-volume-iii (US2, US3, FR-002, FR-004, FR-017)
"""

from __future__ import annotations

from typing import Protocol


class InterestRateSource(Protocol):
    """Protocol for FRED interest rate data (national-level).

    Data sources: FEDFUNDS, DGS10, BAA10Y.
    """

    def get_federal_funds_rate(self, year: int) -> float | None:
        """Get annual average federal funds effective rate.

        Args:
            year: Calendar year.

        Returns:
            Rate as decimal (e.g., 0.05 for 5%), or None if unavailable.
        """
        ...

    def get_treasury_10y(self, year: int) -> float | None:
        """Get annual average 10-year Treasury constant maturity rate.

        Args:
            year: Calendar year.

        Returns:
            Rate as decimal, or None if unavailable.
        """
        ...

    def get_baa_spread(self, year: int) -> float | None:
        """Get annual average Moody's Baa corporate bond spread over 10Y Treasury.

        Args:
            year: Calendar year.

        Returns:
            Spread as decimal, or None if unavailable.
        """
        ...


class CreditAggregateSource(Protocol):
    """Protocol for FRED credit aggregate data (national-level).

    Data sources: TCMDO, GFDEBTN, NCBEILQ027S.
    """

    def get_total_credit(self, year: int) -> float | None:
        """Get total credit market debt outstanding (TCMDO).

        Args:
            year: Calendar year.

        Returns:
            Total credit in current dollars, or None if unavailable.
        """
        ...

    def get_government_debt(self, year: int) -> float | None:
        """Get federal debt total public debt (GFDEBTN).

        Args:
            year: Calendar year.

        Returns:
            Government debt in current dollars, or None if unavailable.
        """
        ...

    def get_equity_market_cap(self, year: int) -> float | None:
        """Get equity market capitalization proxy (Wilshire 5000).

        Args:
            year: Calendar year.

        Returns:
            Market cap in current dollars, or None if unavailable.
        """
        ...


class Z1FinancialAccountsSource(Protocol):
    """Protocol for Fed Z.1 Financial Accounts data (national-level).

    Data source: Federal Reserve Financial Accounts of the United States.
    Constitution III.4 approved source (added for Feature 024).
    """

    def get_corporate_debt(self, year: int) -> float | None:
        """Get total corporate debt outstanding.

        Args:
            year: Calendar year.

        Returns:
            Corporate debt in current dollars, or None if unavailable.
        """
        ...

    def get_household_debt(self, year: int) -> float | None:
        """Get total household debt (mortgage + consumer + student).

        Args:
            year: Calendar year.

        Returns:
            Household debt in current dollars, or None if unavailable.
        """
        ...

    def get_derivatives_notional(self, year: int) -> float | None:
        """Get notional value of derivative contracts.

        Args:
            year: Calendar year.

        Returns:
            Derivatives notional in current dollars, or None if unavailable.
        """
        ...


# ---------------------------------------------------------------------------
# Concrete adapters (Feature 024)
# ---------------------------------------------------------------------------


class FredInterestRateAdapter:
    """Adapts FRED data to :class:`InterestRateSource` protocol.

    Takes a pre-loaded mapping of series_id -> {year -> value} and
    exposes it through the protocol methods.

    Args:
        series_data: Dict mapping FRED series IDs to yearly value dicts.
            Expected keys: ``"FEDFUNDS"``, ``"DGS10"``, ``"BAA10Y"``.
    """

    def __init__(self, series_data: dict[str, dict[int, float]]) -> None:
        self._series = series_data

    def get_federal_funds_rate(self, year: int) -> float | None:
        """Get annual average federal funds effective rate.

        Args:
            year: Calendar year.

        Returns:
            Rate as decimal (e.g., 0.05 for 5%), or None if unavailable.
        """
        return self._series.get("FEDFUNDS", {}).get(year)

    def get_treasury_10y(self, year: int) -> float | None:
        """Get annual average 10-year Treasury constant maturity rate.

        Args:
            year: Calendar year.

        Returns:
            Rate as decimal, or None if unavailable.
        """
        return self._series.get("DGS10", {}).get(year)

    def get_baa_spread(self, year: int) -> float | None:
        """Get annual average Moody's Baa corporate bond spread over 10Y Treasury.

        Args:
            year: Calendar year.

        Returns:
            Spread as decimal, or None if unavailable.
        """
        return self._series.get("BAA10Y", {}).get(year)


class FredCreditAggregateAdapter:
    """Adapts FRED data to :class:`CreditAggregateSource` protocol.

    Takes a pre-loaded mapping of series_id -> {year -> value} and
    exposes it through the protocol methods.

    Args:
        series_data: Dict mapping FRED series IDs to yearly value dicts.
            Expected keys: ``"TCMDO"``, ``"GFDEBTN"``, ``"NCBEILQ027S"``.
    """

    def __init__(self, series_data: dict[str, dict[int, float]]) -> None:
        self._series = series_data

    def get_total_credit(self, year: int) -> float | None:
        """Get total credit market debt outstanding (TCMDO).

        Args:
            year: Calendar year.

        Returns:
            Total credit in current dollars, or None if unavailable.
        """
        return self._series.get("TCMDO", {}).get(year)

    def get_government_debt(self, year: int) -> float | None:
        """Get federal debt total public debt (GFDEBTN).

        Args:
            year: Calendar year.

        Returns:
            Government debt in current dollars, or None if unavailable.
        """
        return self._series.get("GFDEBTN", {}).get(year)

    def get_equity_market_cap(self, year: int) -> float | None:
        """Get equity market capitalization proxy (Wilshire 5000).

        Args:
            year: Calendar year.

        Returns:
            Market cap in current dollars, or None if unavailable.
        """
        return self._series.get("NCBEILQ027S", {}).get(year)
