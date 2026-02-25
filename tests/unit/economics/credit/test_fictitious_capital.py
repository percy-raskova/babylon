"""Tests for FictitiousCapitalStock model.

Feature: 024-capital-volume-iii (US3, FR-004, FR-005)
TDD Red Phase: Tests define expected behavior for fictitious capital stock model.

FictitiousCapitalStock: Accumulated financial claims on future value production.
Tracks government debt, corporate equity, corporate debt, household debt, and
derivatives notional. Derivatives are excluded from total_claims to avoid
double-counting.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from babylon.economics.credit.types import FictitiousCapitalStock

# =============================================================================
# Frozen (Immutability)
# =============================================================================


@pytest.mark.unit
class TestFictitiousCapitalStockFrozen:
    """FictitiousCapitalStock must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        with pytest.raises(ValidationError):
            stock.government_debt = 0.0  # type: ignore[misc]


# =============================================================================
# Field Validation
# =============================================================================


@pytest.mark.unit
class TestFictitiousCapitalStockFields:
    """FictitiousCapitalStock field validation."""

    def test_valid_construction(self) -> None:
        """Normal construction with all required fields succeeds."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        assert stock.year == 2020
        assert stock.government_debt == pytest.approx(27_000_000_000_000.0)
        assert stock.corporate_equity == pytest.approx(36_000_000_000_000.0)
        assert stock.corporate_debt == pytest.approx(11_000_000_000_000.0)
        assert stock.household_debt == pytest.approx(16_000_000_000_000.0)
        assert stock.derivatives_notional == pytest.approx(0.0)

    def test_full_construction_with_derivatives(self) -> None:
        """Construction with all fields including derivatives."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
            derivatives_notional=600_000_000_000_000.0,
        )
        assert stock.derivatives_notional == pytest.approx(600_000_000_000_000.0)

    def test_negative_government_debt_rejected(self) -> None:
        """Negative government_debt is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="government_debt"):
            FictitiousCapitalStock(
                year=2020,
                government_debt=-1.0,
                corporate_equity=36_000_000_000_000.0,
                corporate_debt=11_000_000_000_000.0,
                household_debt=16_000_000_000_000.0,
            )

    def test_negative_corporate_equity_rejected(self) -> None:
        """Negative corporate_equity is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="corporate_equity"):
            FictitiousCapitalStock(
                year=2020,
                government_debt=27_000_000_000_000.0,
                corporate_equity=-1.0,
                corporate_debt=11_000_000_000_000.0,
                household_debt=16_000_000_000_000.0,
            )

    def test_negative_corporate_debt_rejected(self) -> None:
        """Negative corporate_debt is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="corporate_debt"):
            FictitiousCapitalStock(
                year=2020,
                government_debt=27_000_000_000_000.0,
                corporate_equity=36_000_000_000_000.0,
                corporate_debt=-1.0,
                household_debt=16_000_000_000_000.0,
            )

    def test_negative_household_debt_rejected(self) -> None:
        """Negative household_debt is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="household_debt"):
            FictitiousCapitalStock(
                year=2020,
                government_debt=27_000_000_000_000.0,
                corporate_equity=36_000_000_000_000.0,
                corporate_debt=11_000_000_000_000.0,
                household_debt=-1.0,
            )

    def test_negative_derivatives_notional_rejected(self) -> None:
        """Negative derivatives_notional is rejected by ge=0 constraint."""
        with pytest.raises(ValidationError, match="derivatives_notional"):
            FictitiousCapitalStock(
                year=2020,
                government_debt=27_000_000_000_000.0,
                corporate_equity=36_000_000_000_000.0,
                corporate_debt=11_000_000_000_000.0,
                household_debt=16_000_000_000_000.0,
                derivatives_notional=-1.0,
            )

    def test_zero_values_accepted(self) -> None:
        """Zero values for all fields are valid."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=0.0,
            corporate_equity=0.0,
            corporate_debt=0.0,
            household_debt=0.0,
            derivatives_notional=0.0,
        )
        assert stock.government_debt == 0.0
        assert stock.corporate_equity == 0.0
        assert stock.corporate_debt == 0.0
        assert stock.household_debt == 0.0
        assert stock.derivatives_notional == 0.0


# =============================================================================
# Computed Field: total_claims
# =============================================================================


@pytest.mark.unit
class TestFictitiousCapitalStockTotalClaims:
    """FictitiousCapitalStock.total_claims computed field."""

    def test_total_claims_sum(self) -> None:
        """total_claims = govt_debt + corp_equity + corp_debt + household_debt."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        expected = (
            27_000_000_000_000.0
            + 36_000_000_000_000.0
            + 11_000_000_000_000.0
            + 16_000_000_000_000.0
        )
        assert stock.total_claims == pytest.approx(expected)

    def test_total_claims_excludes_derivatives(self) -> None:
        """Derivatives notional is tracked but excluded from total_claims."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
            derivatives_notional=600_000_000_000_000.0,
        )
        expected_without_derivatives = (
            27_000_000_000_000.0
            + 36_000_000_000_000.0
            + 11_000_000_000_000.0
            + 16_000_000_000_000.0
        )
        assert stock.total_claims == pytest.approx(expected_without_derivatives)

    def test_total_claims_zero_when_all_zero(self) -> None:
        """total_claims = 0 when all component fields are 0."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=0.0,
            corporate_equity=0.0,
            corporate_debt=0.0,
            household_debt=0.0,
        )
        assert stock.total_claims == pytest.approx(0.0)


# =============================================================================
# Method: ratio_to_real
# =============================================================================


@pytest.mark.unit
class TestFictitiousCapitalStockRatioToReal:
    """FictitiousCapitalStock.ratio_to_real method."""

    def test_ratio_to_real_normal(self) -> None:
        """ratio_to_real = total_claims / real_gdp for positive GDP."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        real_gdp = 21_000_000_000_000.0
        expected = stock.total_claims / real_gdp
        assert stock.ratio_to_real(real_gdp) == pytest.approx(expected)

    def test_ratio_to_real_zero_gdp_returns_inf(self) -> None:
        """ratio_to_real returns float('inf') when real_gdp is zero."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        result = stock.ratio_to_real(0.0)
        assert math.isinf(result)
        assert result > 0

    def test_ratio_to_real_negative_gdp_returns_inf(self) -> None:
        """ratio_to_real returns float('inf') when real_gdp is negative."""
        stock = FictitiousCapitalStock(
            year=2020,
            government_debt=27_000_000_000_000.0,
            corporate_equity=36_000_000_000_000.0,
            corporate_debt=11_000_000_000_000.0,
            household_debt=16_000_000_000_000.0,
        )
        result = stock.ratio_to_real(-1.0)
        assert math.isinf(result)
        assert result > 0

    def test_ratio_to_real_crisis_year(self) -> None:
        """2008 crisis: financialization ratio above FINANCIALIZATION_BUBBLE."""
        stock = FictitiousCapitalStock(
            year=2008,
            government_debt=10_000_000_000_000.0,
            corporate_equity=9_000_000_000_000.0,
            corporate_debt=7_500_000_000_000.0,
            household_debt=13_800_000_000_000.0,
        )
        # Real GDP in 2008 ~14.7T -> total_claims ~40.3T -> ratio ~2.74
        real_gdp = 14_700_000_000_000.0
        ratio = stock.ratio_to_real(real_gdp)
        assert ratio > 2.0  # Clearly above normal
        assert ratio == pytest.approx(stock.total_claims / real_gdp)
