"""Tests for DefaultFinancialCrisisAssessor.

Feature: 024-capital-volume-iii (US6, FR-012)
TDD Red Phase: Tests define expected behavior for integrated crisis assessment.

Uses threshold constants from credit/types.py:
  INTEREST_BURDEN_SQUEEZE (0.4), FINANCIALIZATION_BUBBLE (3.5),
  CREDIT_FRAGILITY_THRESHOLD (0.02).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.financial_crisis.assessment import DefaultFinancialCrisisAssessor
from babylon.domain.economics.financial_crisis.types import FinancialCrisisAssessment
from tests.unit.economics.financial_crisis.conftest import CrisisScenario

# =============================================================================
# DefaultFinancialCrisisAssessor
# =============================================================================


@pytest.mark.unit
class TestDefaultFinancialCrisisAssessorNormal:
    """Normal scenario: all indicators within safe bounds."""

    def test_assess_normal_no_signals(
        self,
        normal_scenario: CrisisScenario,
    ) -> None:
        """Normal scenario triggers no crisis signals."""
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=normal_scenario.interest_burden_ratio,
            financialization_ratio=normal_scenario.financialization_ratio,
            default_rate=normal_scenario.default_rate,
            credit_spread=normal_scenario.credit_spread,
            claims_exceed_surplus=normal_scenario.claims_exceed_surplus,
        )
        assert isinstance(result, FinancialCrisisAssessment)
        assert result.profit_squeeze is False
        assert result.overaccumulation is False
        assert result.credit_fragility is False
        assert result.claims_exceed_surplus is False
        assert result.active_signals == 0
        assert result.crisis_probability == pytest.approx(0.0)


@pytest.mark.unit
class TestDefaultFinancialCrisisAssessorCrisis:
    """Crisis scenario: all indicators in crisis territory."""

    def test_assess_crisis_most_signals(
        self,
        crisis_scenario: CrisisScenario,
    ) -> None:
        """Crisis scenario triggers profit_squeeze, overaccumulation, claims_exceed_surplus.

        Note: credit_fragility is NOT triggered because
        default_rate (0.05) * credit_spread (0.06) = 0.003 < CREDIT_FRAGILITY_THRESHOLD (0.02).
        """
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=crisis_scenario.interest_burden_ratio,
            financialization_ratio=crisis_scenario.financialization_ratio,
            default_rate=crisis_scenario.default_rate,
            credit_spread=crisis_scenario.credit_spread,
            claims_exceed_surplus=crisis_scenario.claims_exceed_surplus,
        )
        assert isinstance(result, FinancialCrisisAssessment)
        assert result.profit_squeeze is True
        assert result.overaccumulation is True
        assert result.credit_fragility is False  # 0.05 * 0.06 = 0.003 < 0.02
        assert result.claims_exceed_surplus is True
        assert result.active_signals == 3
        assert result.crisis_probability == pytest.approx(0.75)


@pytest.mark.unit
class TestDefaultFinancialCrisisAssessorLatentVulnerability:
    """Latent vulnerability: surface stability but financialization building."""

    def test_assess_latent_only_overaccumulation(
        self,
        latent_vulnerability_scenario: CrisisScenario,
    ) -> None:
        """Latent vulnerability triggers only overaccumulation signal."""
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=latent_vulnerability_scenario.interest_burden_ratio,
            financialization_ratio=latent_vulnerability_scenario.financialization_ratio,
            default_rate=latent_vulnerability_scenario.default_rate,
            credit_spread=latent_vulnerability_scenario.credit_spread,
            claims_exceed_surplus=latent_vulnerability_scenario.claims_exceed_surplus,
        )
        assert isinstance(result, FinancialCrisisAssessment)
        assert result.profit_squeeze is False
        assert result.overaccumulation is True
        assert result.credit_fragility is False
        assert result.claims_exceed_surplus is False
        assert result.active_signals == 1
        assert result.crisis_probability == pytest.approx(0.25)


@pytest.mark.unit
class TestDefaultFinancialCrisisAssessorThresholdBoundary:
    """Boundary tests at threshold values."""

    def test_exact_interest_burden_threshold_not_triggered(self) -> None:
        """Interest burden exactly at threshold (0.4) does NOT trigger (strict >)."""
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=0.4,
            financialization_ratio=2.0,
            default_rate=0.01,
            credit_spread=0.01,
            claims_exceed_surplus=False,
        )
        assert result.profit_squeeze is False

    def test_exact_financialization_threshold_not_triggered(self) -> None:
        """Financialization exactly at threshold (3.5) does NOT trigger (strict >)."""
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=0.1,
            financialization_ratio=3.5,
            default_rate=0.01,
            credit_spread=0.01,
            claims_exceed_surplus=False,
        )
        assert result.overaccumulation is False

    def test_exact_credit_fragility_threshold_not_triggered(self) -> None:
        """Credit fragility product exactly at threshold (0.02) does NOT trigger (strict >)."""
        assessor = DefaultFinancialCrisisAssessor()
        # default_rate=0.02 * credit_spread=1.0 = 0.02 exactly (no FP error)
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=0.1,
            financialization_ratio=2.0,
            default_rate=0.02,
            credit_spread=1.0,
            claims_exceed_surplus=False,
        )
        assert result.credit_fragility is False
