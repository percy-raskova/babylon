"""Tests for financial crisis type definitions (CreditCrisisIndicator, FinancialCrisisAssessment).

Feature: 024-capital-volume-iii (US6, FR-012, FR-016)
TDD Red Phase: Tests define expected behavior for composite crisis signal models.

CreditCrisisIndicator: three boolean signals with computed crisis_probability.
FinancialCrisisAssessment: four boolean signals with computed active_signals and crisis_probability.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.financial_crisis.types import (
    CreditCrisisIndicator,
    FinancialCrisisAssessment,
)

# =============================================================================
# CreditCrisisIndicator
# =============================================================================


@pytest.mark.unit
class TestCreditCrisisIndicatorFrozen:
    """CreditCrisisIndicator must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        indicator = CreditCrisisIndicator()
        with pytest.raises(ValidationError):
            indicator.overproduction_signal = True  # type: ignore[misc]


@pytest.mark.unit
class TestCreditCrisisIndicatorFields:
    """CreditCrisisIndicator field defaults and construction."""

    def test_default_all_false(self) -> None:
        """All signals default to False."""
        indicator = CreditCrisisIndicator()
        assert indicator.overproduction_signal is False
        assert indicator.profit_squeeze is False
        assert indicator.liquidity_crisis is False

    def test_explicit_construction(self) -> None:
        """Explicit True values are accepted."""
        indicator = CreditCrisisIndicator(
            overproduction_signal=True,
            profit_squeeze=True,
            liquidity_crisis=False,
        )
        assert indicator.overproduction_signal is True
        assert indicator.profit_squeeze is True
        assert indicator.liquidity_crisis is False


@pytest.mark.unit
class TestCreditCrisisIndicatorProbability:
    """CreditCrisisIndicator.crisis_probability computed field."""

    def test_no_signals_zero_probability(self) -> None:
        """No signals active -> crisis_probability = 0.0."""
        indicator = CreditCrisisIndicator()
        assert indicator.crisis_probability == pytest.approx(0.0)

    def test_one_signal_one_third(self) -> None:
        """One of three signals active -> crisis_probability = 1/3."""
        indicator = CreditCrisisIndicator(overproduction_signal=True)
        assert indicator.crisis_probability == pytest.approx(1.0 / 3.0)

    def test_two_signals_two_thirds(self) -> None:
        """Two of three signals active -> crisis_probability = 2/3."""
        indicator = CreditCrisisIndicator(
            overproduction_signal=True,
            profit_squeeze=True,
        )
        assert indicator.crisis_probability == pytest.approx(2.0 / 3.0)

    def test_all_signals_full_probability(self) -> None:
        """All three signals active -> crisis_probability = 1.0."""
        indicator = CreditCrisisIndicator(
            overproduction_signal=True,
            profit_squeeze=True,
            liquidity_crisis=True,
        )
        assert indicator.crisis_probability == pytest.approx(1.0)


# =============================================================================
# FinancialCrisisAssessment
# =============================================================================


@pytest.mark.unit
class TestFinancialCrisisAssessmentFrozen:
    """FinancialCrisisAssessment must be immutable (frozen Pydantic model)."""

    def test_frozen_model_rejects_mutation(self) -> None:
        """Attempting to mutate a field raises ValidationError."""
        assessment = FinancialCrisisAssessment(fips_code="26163", year=2020)
        with pytest.raises(ValidationError):
            assessment.profit_squeeze = True  # type: ignore[misc]


@pytest.mark.unit
class TestFinancialCrisisAssessmentFields:
    """FinancialCrisisAssessment field validation."""

    def test_minimal_construction(self) -> None:
        """Construction with required fields only uses defaults (all False)."""
        assessment = FinancialCrisisAssessment(fips_code="26163", year=2020)
        assert assessment.fips_code == "26163"
        assert assessment.year == 2020
        assert assessment.profit_squeeze is False
        assert assessment.overaccumulation is False
        assert assessment.credit_fragility is False
        assert assessment.claims_exceed_surplus is False

    def test_full_construction(self) -> None:
        """Construction with all fields explicit."""
        assessment = FinancialCrisisAssessment(
            fips_code="26163",
            year=2020,
            profit_squeeze=True,
            overaccumulation=True,
            credit_fragility=False,
            claims_exceed_surplus=True,
        )
        assert assessment.profit_squeeze is True
        assert assessment.overaccumulation is True
        assert assessment.credit_fragility is False
        assert assessment.claims_exceed_surplus is True

    def test_fips_too_short_rejected(self) -> None:
        """FIPS code shorter than 5 characters is rejected."""
        with pytest.raises(ValidationError, match="fips_code"):
            FinancialCrisisAssessment(fips_code="2616", year=2020)

    def test_fips_too_long_rejected(self) -> None:
        """FIPS code longer than 5 characters is rejected."""
        with pytest.raises(ValidationError, match="fips_code"):
            FinancialCrisisAssessment(fips_code="261630", year=2020)

    def test_year_below_minimum_rejected(self) -> None:
        """Year below 2007 is rejected by ge constraint."""
        with pytest.raises(ValidationError, match="year"):
            FinancialCrisisAssessment(fips_code="26163", year=2006)

    def test_year_above_maximum_rejected(self) -> None:
        """Year above 2040 is rejected by le constraint."""
        with pytest.raises(ValidationError, match="year"):
            FinancialCrisisAssessment(fips_code="26163", year=2041)


@pytest.mark.unit
class TestFinancialCrisisAssessmentActiveSignals:
    """FinancialCrisisAssessment.active_signals computed field."""

    def test_all_false_zero_signals(self) -> None:
        """All False -> active_signals = 0."""
        assessment = FinancialCrisisAssessment(fips_code="26163", year=2020)
        assert assessment.active_signals == 0

    def test_one_true_one_signal(self) -> None:
        """One True -> active_signals = 1."""
        assessment = FinancialCrisisAssessment(
            fips_code="26163",
            year=2020,
            overaccumulation=True,
        )
        assert assessment.active_signals == 1

    def test_all_true_four_signals(self) -> None:
        """All True -> active_signals = 4."""
        assessment = FinancialCrisisAssessment(
            fips_code="26163",
            year=2020,
            profit_squeeze=True,
            overaccumulation=True,
            credit_fragility=True,
            claims_exceed_surplus=True,
        )
        assert assessment.active_signals == 4


@pytest.mark.unit
class TestFinancialCrisisAssessmentProbability:
    """FinancialCrisisAssessment.crisis_probability computed field."""

    def test_all_false_zero_probability(self) -> None:
        """All False -> crisis_probability = 0.0."""
        assessment = FinancialCrisisAssessment(fips_code="26163", year=2020)
        assert assessment.crisis_probability == pytest.approx(0.0)

    def test_all_true_full_probability(self) -> None:
        """All True -> crisis_probability = 1.0."""
        assessment = FinancialCrisisAssessment(
            fips_code="26163",
            year=2020,
            profit_squeeze=True,
            overaccumulation=True,
            credit_fragility=True,
            claims_exceed_surplus=True,
        )
        assert assessment.crisis_probability == pytest.approx(1.0)

    def test_two_of_four_half_probability(self) -> None:
        """Two of four True -> crisis_probability = 0.5."""
        assessment = FinancialCrisisAssessment(
            fips_code="26163",
            year=2020,
            profit_squeeze=True,
            claims_exceed_surplus=True,
        )
        assert assessment.crisis_probability == pytest.approx(0.5)


@pytest.mark.unit
class TestFinancialCrisisAssessmentNormalFactory:
    """FinancialCrisisAssessment.normal() factory method."""

    def test_normal_factory_defaults(self) -> None:
        """normal() creates assessment with no signals and default fips/year."""
        assessment = FinancialCrisisAssessment.normal()
        assert assessment.fips_code == "00000"
        assert assessment.year == 2020
        assert assessment.active_signals == 0
        assert assessment.crisis_probability == pytest.approx(0.0)

    def test_normal_factory_custom_args(self) -> None:
        """normal() accepts custom fips and year."""
        assessment = FinancialCrisisAssessment.normal(fips="26163", year=2022)
        assert assessment.fips_code == "26163"
        assert assessment.year == 2022
        assert assessment.active_signals == 0
