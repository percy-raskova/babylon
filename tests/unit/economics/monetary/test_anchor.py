"""Tests for the monetary anchor (Vol III calibrates; the scissors integrates).

Design: docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md §3.3 (D1).

Contract clause 1: any absent input yields a NoDataSentinel carrying a SPECIFIC
reason. A zero is never fabricated (Constitution III.11).
"""

from __future__ import annotations

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
