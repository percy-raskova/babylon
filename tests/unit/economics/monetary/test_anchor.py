"""Tests for the monetary anchor (Vol III calibrates; the scissors integrates).

Design: docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md §3.3 (D1).

Contract clause 1: any absent input yields a NoDataSentinel carrying a SPECIFIC
reason. A zero is never fabricated (Constitution III.11).
"""

from __future__ import annotations

import math

import pytest

from babylon.domain.economics.credit.types import FictitiousCapitalStock
from babylon.domain.economics.monetary.anchor import (
    NATIONAL_FIPS,
    UNKNOWN_YEAR,
    fictitious_anchor,
)
from babylon.domain.economics.tensor import NoDataSentinel


def _stock(year: int = 2020) -> FictitiousCapitalStock:
    """Build a stock whose total_claims is exactly 100.0."""
    return FictitiousCapitalStock(
        year=year,
        government_debt=20.0,
        corporate_equity=40.0,
        corporate_debt=10.0,
        household_debt=30.0,
    )


@pytest.mark.unit
class TestFictitiousAnchorAbsence:
    """fictitious_anchor returns an honest sentinel when an input is absent."""

    def test_absent_stock_returns_sentinel(self) -> None:
        """No published FictitiousCapitalStock: sentinel, not a zero."""
        result = fictitious_anchor(None, 50.0)
        assert isinstance(result, NoDataSentinel)
        assert result.fips == NATIONAL_FIPS
        assert result.year == UNKNOWN_YEAR
        assert "fictitious_anchor" in result.reason
        assert "FictitiousCapitalStock" in result.reason

    def test_absent_stock_sentinel_is_falsy(self) -> None:
        """The sentinel supports the walrus/falsy consumer pattern."""
        assert not fictitious_anchor(None, 50.0)

    def test_absent_real_output_returns_sentinel_carrying_the_stock_year(self) -> None:
        """The stock exists but no real output observable: sentinel with the year."""
        result = fictitious_anchor(_stock(2020), None)
        assert isinstance(result, NoDataSentinel)
        assert result.fips == NATIONAL_FIPS
        assert result.year == 2020
        assert "real output" in result.reason

    def test_absence_never_returns_a_float(self) -> None:
        """Absence is never expressed as a number."""
        assert not isinstance(fictitious_anchor(None, None), float)

    def test_zero_total_claims_returns_sentinel_not_domain_error(self) -> None:
        """An all-zero stock is a legitimate Pydantic value, not an error input.

        Every field on FictitiousCapitalStock is constrained only with
        ge=0.0, so government_debt=corporate_equity=corporate_debt=
        household_debt=0.0 constructs cleanly and total_claims == 0.0.
        ratio_to_real then returns 0.0 (real_output > 0), and math.log(0.0)
        raises ValueError -- fictitious_anchor must intercept that and return
        an honest sentinel instead of crashing the tick (Constitution III.11).
        """
        zero_stock = FictitiousCapitalStock(
            year=2020,
            government_debt=0.0,
            corporate_equity=0.0,
            corporate_debt=0.0,
            household_debt=0.0,
        )
        result = fictitious_anchor(zero_stock, 50.0)
        assert isinstance(result, NoDataSentinel)
        assert result.fips == NATIONAL_FIPS
        assert result.year == 2020
        assert "total_claims" in result.reason


@pytest.mark.unit
class TestFictitiousAnchorPresent:
    """fictitious_anchor computes log(total_claims / real_output) when data exists."""

    def test_returns_log_of_the_real_ratio(self) -> None:
        """total_claims 100.0 over real output 50.0 is ln(2.0)."""
        result = fictitious_anchor(_stock(2020), 50.0)
        assert result == pytest.approx(math.log(2.0))

    def test_par_claims_anchor_at_zero(self) -> None:
        """Claims exactly equal to real output anchor at log-ratio 0.0."""
        result = fictitious_anchor(_stock(2020), 100.0)
        assert result == pytest.approx(0.0)

    def test_undervalued_claims_anchor_below_zero(self) -> None:
        """Claims below real output give a negative log anchor."""
        result = fictitious_anchor(_stock(2020), 200.0)
        assert isinstance(result, float)
        assert result < 0.0

    def test_derivatives_are_excluded_from_the_anchor(self) -> None:
        """derivatives_notional is tracked but never enters total_claims."""
        with_derivatives = FictitiousCapitalStock(
            year=2020,
            government_debt=20.0,
            corporate_equity=40.0,
            corporate_debt=10.0,
            household_debt=30.0,
            derivatives_notional=900.0,
        )
        assert fictitious_anchor(with_derivatives, 50.0) == pytest.approx(
            fictitious_anchor(_stock(2020), 50.0)
        )
