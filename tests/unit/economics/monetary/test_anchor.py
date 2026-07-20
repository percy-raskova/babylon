"""Tests for the monetary anchor (Vol III calibrates; the scissors integrates).

Design: docs/superpowers/specs/2026-07-18-vol3-money-scissors-design.md §3.3 (D1).

Contract clause 1: any absent input yields a NoDataSentinel carrying a SPECIFIC
reason. A zero is never fabricated (Constitution III.11).
"""

from __future__ import annotations

import math

import pytest

from babylon.domain.economics.credit.types import FictitiousCapitalStock
from babylon.domain.economics.distribution.types import SurplusValueDistribution
from babylon.domain.economics.monetary.anchor import (
    NATIONAL_FIPS,
    UNKNOWN_YEAR,
    fictitious_anchor,
    serviceability_anchor,
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


def _distribution(
    *,
    surplus: float = 100.0,
    interest: float = 25.0,
    fips: str = "26163",
    year: int = 2020,
) -> SurplusValueDistribution:
    """Build a distribution with the interest claim under test."""
    return SurplusValueDistribution(
        fips_code=fips,
        year=year,
        total_surplus_produced=surplus,
        interest_payments=interest,
        ground_rent=10.0,
        taxes_on_surplus=15.0,
    )


@pytest.mark.unit
class TestServiceabilityAnchorAbsence:
    """serviceability_anchor returns an honest sentinel when input is absent."""

    def test_absent_distribution_returns_sentinel(self) -> None:
        """No SurplusValueDistribution computed: sentinel, not a zero burden."""
        result = serviceability_anchor(None)
        assert isinstance(result, NoDataSentinel)
        assert result.fips == NATIONAL_FIPS
        assert result.year == UNKNOWN_YEAR
        assert "SurplusValueDistribution" in result.reason

    def test_zero_surplus_returns_sentinel_not_the_computed_field_zero(self) -> None:
        """financialization_share silently returns 0.0 at zero surplus; we must not."""
        zero_surplus = _distribution(surplus=0.0, interest=0.0)
        assert zero_surplus.financialization_share == 0.0
        result = serviceability_anchor(zero_surplus)
        assert isinstance(result, NoDataSentinel)
        assert result.fips == "26163"
        assert result.year == 2020
        assert "zero surplus" in result.reason

    def test_absence_is_falsy_and_never_a_float(self) -> None:
        """The sentinel supports the walrus pattern and is not a number."""
        result = serviceability_anchor(None)
        assert not result
        assert not isinstance(result, float)


@pytest.mark.unit
class TestServiceabilityAnchorDegenerate:
    """Non-finite field values must degrade to sentinels, never inf/nan floats.

    total_surplus_produced and interest_payments are both constrained only by
    ``ge=0`` (no upper bound, no allow_inf_nan=False), so +inf is a valid
    Pydantic field value even though NaN is rejected (nan >= 0 is False).
    """

    def test_infinite_surplus_returns_sentinel_not_a_fabricated_zero(self) -> None:
        """25.0 / inf silently evaluates to 0.0 -- indistinguishable from a
        county that genuinely pays no interest. Must be a sentinel instead.
        """
        infinite_surplus = _distribution(surplus=float("inf"), interest=25.0)
        result = serviceability_anchor(infinite_surplus)
        assert isinstance(result, NoDataSentinel)
        assert not isinstance(result, float)
        assert result.fips == "26163"
        assert result.year == 2020
        assert "non-finite surplus" in result.reason

    def test_infinite_interest_returns_sentinel_not_raw_inf(self) -> None:
        """inf / 100.0 must not escape as a raw float('inf')."""
        infinite_interest = _distribution(surplus=100.0, interest=float("inf"))
        result = serviceability_anchor(infinite_interest)
        assert isinstance(result, NoDataSentinel)
        assert not isinstance(result, float)
        assert result.fips == "26163"
        assert result.year == 2020
        assert "non-finite interest burden" in result.reason

    def test_present_anchor_is_always_finite(self) -> None:
        """No degenerate input escapes as inf or nan."""
        result = serviceability_anchor(_distribution())
        assert isinstance(result, float)
        assert math.isfinite(result)


@pytest.mark.unit
class TestFictitiousAnchorDegenerate:
    """Degenerate ratios degrade to sentinels rather than infinities or raises."""

    def test_zero_real_output_returns_sentinel(self) -> None:
        """ratio_to_real returns inf at zero output; the anchor must not."""
        result = fictitious_anchor(_stock(2020), 0.0)
        assert isinstance(result, NoDataSentinel)
        assert result.year == 2020
        assert "non-positive real output" in result.reason

    def test_negative_real_output_returns_sentinel(self) -> None:
        """A negative output observable is absence, not a value."""
        result = fictitious_anchor(_stock(2020), -25.0)
        assert isinstance(result, NoDataSentinel)
        assert "non-positive real output" in result.reason

    def test_nan_real_output_returns_sentinel(self) -> None:
        """NaN is neither <= 0 nor > 0 under IEEE-754; it must still be caught.

        math.log(nan) returns nan silently (no exception), so a naive
        ``real_output <= 0.0`` guard lets a NaN observable escape as a raw
        float instead of an honest sentinel.
        """
        result = fictitious_anchor(_stock(2020), float("nan"))
        assert isinstance(result, NoDataSentinel)
        assert not isinstance(result, float)
        assert result.year == 2020
        assert "non-positive real output" in result.reason

    def test_infinite_real_output_returns_sentinel(self) -> None:
        """+inf real output must also be caught, not just non-positive values."""
        result = fictitious_anchor(_stock(2020), float("inf"))
        assert isinstance(result, NoDataSentinel)
        assert result.year == 2020

    def test_zero_total_claims_returns_sentinel(self) -> None:
        """log(0) is undefined; zero claims is absence of a log anchor."""
        empty = FictitiousCapitalStock(
            year=2020,
            government_debt=0.0,
            corporate_equity=0.0,
            corporate_debt=0.0,
            household_debt=0.0,
        )
        result = fictitious_anchor(empty, 50.0)
        assert isinstance(result, NoDataSentinel)
        assert result.year == 2020
        assert "zero total claims" in result.reason

    def test_present_anchor_is_always_finite(self) -> None:
        """No degenerate input escapes as inf or nan."""
        result = fictitious_anchor(_stock(2020), 50.0)
        assert isinstance(result, float)
        assert math.isfinite(result)


@pytest.mark.unit
class TestServiceabilityAnchorPresent:
    """serviceability_anchor computes interest_payments / total_surplus_produced."""

    def test_returns_the_interest_burden(self) -> None:
        """25.0 interest against 100.0 surplus is a burden of 0.25."""
        assert serviceability_anchor(_distribution()) == pytest.approx(0.25)

    def test_zero_interest_with_positive_surplus_is_a_real_zero(self) -> None:
        """A county that genuinely pays no interest reads 0.0, not a sentinel."""
        result = serviceability_anchor(_distribution(interest=0.0))
        assert isinstance(result, float)
        assert result == pytest.approx(0.0)

    def test_burden_above_one_is_a_legitimate_reading(self) -> None:
        """Interest exceeding surplus is the debt-spiral condition, not an error."""
        overclaimed = _distribution(surplus=50.0, interest=75.0)
        assert overclaimed.profit_of_enterprise < 0.0
        result = serviceability_anchor(overclaimed)
        assert isinstance(result, float)
        assert result == pytest.approx(1.5)

    def test_matches_financialization_share_when_surplus_is_positive(self) -> None:
        """Where the computed field is well-defined the anchor agrees with it."""
        distribution = _distribution()
        assert serviceability_anchor(distribution) == pytest.approx(
            distribution.financialization_share
        )


@pytest.mark.unit
class TestAnchorModuleContract:
    """The anchor is publicly exported and structurally pure (clauses 3 and 4)."""

    def test_exported_from_the_monetary_package(self) -> None:
        """U6 imports the anchor from the package, not the submodule."""
        import babylon.domain.economics.monetary as monetary

        assert "fictitious_anchor" in monetary.__all__
        assert "serviceability_anchor" in monetary.__all__
        assert monetary.fictitious_anchor is fictitious_anchor
        assert monetary.serviceability_anchor is serviceability_anchor

    def test_imports_nothing_from_the_engine_layer(self) -> None:
        """domain/ must not import engine/ (Program 14 layering)."""
        from pathlib import Path

        from babylon.domain.economics.monetary import anchor as anchor_module

        source = Path(str(anchor_module.__file__)).read_text(encoding="utf-8")
        assert "babylon.engine" not in source
        assert "babylon.web" not in source

    def test_uses_no_rng_and_no_wall_clock(self) -> None:
        """Determinism (Constitution III.7): zero RNG, zero clock, zero I/O."""
        from pathlib import Path

        from babylon.domain.economics.monetary import anchor as anchor_module

        source = Path(str(anchor_module.__file__)).read_text(encoding="utf-8")
        for forbidden in ("import random", "import time", "from datetime", "open("):
            assert forbidden not in source, f"anchor.py must not contain {forbidden!r}"
