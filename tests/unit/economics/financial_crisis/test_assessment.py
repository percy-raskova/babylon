"""Tests for DefaultFinancialCrisisAssessor.

Feature: 024-capital-volume-iii (US6, FR-012)
TDD Red Phase: Tests define expected behavior for integrated crisis assessment.

Uses threshold constants from credit/types.py:
  INTEREST_BURDEN_SQUEEZE (0.4), FINANCIALIZATION_BUBBLE (3.5),
  and the GameDefines-backed accessor credit_fragility_threshold() (1.0e-3,
  ``capital_vol3.credit_fragility_threshold``).
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
        """Crisis scenario triggers all four signals.

        ``credit_fragility`` joined the other three when U2.3's review fix
        recalibrated the threshold off its percent-scaled 0.02 onto the
        decimal scale the inputs actually carry: default_rate (0.05) *
        credit_spread (0.06) = 3.0e-3 > credit_fragility_threshold()
        (1.0e-3). Under the old threshold this scenario — deliberately built
        as "all indicators in crisis territory" — still published
        credit_fragility=False, which was the tell that the predicate was
        structurally unreachable on any real county-year.
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
        assert result.credit_fragility is True  # 0.05 * 0.06 = 3.0e-3 > 1.0e-3
        assert result.claims_exceed_surplus is True
        assert result.active_signals == 4
        assert result.crisis_probability == pytest.approx(1.0)


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
        """Fragility product exactly at threshold (1.0e-3) does NOT trigger (strict >)."""
        assessor = DefaultFinancialCrisisAssessor()
        # default_rate=1.0e-3 * credit_spread=1.0 = 1.0e-3 exactly: x * 1.0 == x
        # in IEEE-754, so this lands on the boundary with no rounding slack.
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=0.1,
            financialization_ratio=2.0,
            default_rate=1.0e-3,
            credit_spread=1.0,
            claims_exceed_surplus=False,
        )
        assert result.credit_fragility is False


# =============================================================================
# Honest absence + reachability (code-review U2.3 findings 4 and 5)
# =============================================================================


@pytest.mark.unit
class TestUnmeasuredSignalsArePropagatedAsNone:
    """Constitution III.11: an absent input publishes ``None``, not ``False``.

    A permanently-``False`` boolean is indistinguishable from a genuine
    "measured, no crisis" reading. Both inputs below can be absent at the
    live call site — ``financialization_ratio`` when the fictitious-capital
    calculator returns a ``NoDataSentinel``, ``credit_spread`` when the
    interest calculator does.
    """

    def test_absent_financialization_ratio_yields_none_overaccumulation(self) -> None:
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=0.1,
            financialization_ratio=None,
            default_rate=0.02,
            credit_spread=0.03,
            claims_exceed_surplus=False,
        )
        assert result.overaccumulation is None
        assert result.active_signals == 0
        assert result.measured_signals == 3

    def test_absent_credit_spread_yields_none_credit_fragility(self) -> None:
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=0.1,
            financialization_ratio=2.0,
            default_rate=0.02,
            credit_spread=None,
            claims_exceed_surplus=False,
        )
        assert result.credit_fragility is None
        assert result.measured_signals == 3

    def test_crisis_probability_divides_by_measured_signals_only(self) -> None:
        """An unmeasured signal must not dilute the probability toward 0."""
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2020,
            interest_burden_ratio=0.9,
            financialization_ratio=None,
            default_rate=0.02,
            credit_spread=0.001,
            claims_exceed_surplus=False,
        )
        assert result.overaccumulation is None
        assert result.active_signals == 1
        assert result.measured_signals == 3
        assert result.crisis_probability == pytest.approx(1 / 3)

    def test_nothing_measured_is_zero_probability_not_a_division_error(self) -> None:
        assessment = FinancialCrisisAssessment(
            fips_code="26163",
            year=2020,
            profit_squeeze=None,
            overaccumulation=None,
            credit_fragility=None,
            claims_exceed_surplus=None,
        )
        assert assessment.measured_signals == 0
        assert assessment.crisis_probability == pytest.approx(0.0)


@pytest.mark.unit
class TestCreditFragilityIsReachableWithRealInputs:
    """Finding U2.3-5: the predicate must be able to fire on real data.

    Before the fix ``credit_spread`` received ``InterestRateState.effective_rate``
    (base + spread, a decimal) against a threshold of 0.02 calibrated for
    percent-scaled inputs, so ``default_rate * spread > 0.02`` required a 100%
    borrowing rate. ``credit_fragility`` was hardwired ``False`` for every
    county in every year of the shipped wiring.
    """

    def test_two_thousand_eight_peak_spread_trips_the_flag(self) -> None:
        """FRED BAA10Y peaked at 5.56% (0.0556) in Dec 2008.

        With the documented 2% default-rate estimate the fragility product is
        1.11e-3, which must exceed the recalibrated threshold.
        """
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2008,
            interest_burden_ratio=0.1,
            financialization_ratio=2.0,
            default_rate=0.02,
            credit_spread=0.0556,
            claims_exceed_surplus=False,
        )
        assert result.credit_fragility is True

    def test_calm_year_spread_does_not_trip_the_flag(self) -> None:
        """BAA10Y in a calm year (~1.8%) must leave the flag down.

        A threshold that fires on every year would be as useless as one that
        never fires; this pins the discriminating power, not just reachability.
        """
        assessor = DefaultFinancialCrisisAssessor()
        result = assessor.assess(
            fips="26163",
            year=2019,
            interest_burden_ratio=0.1,
            financialization_ratio=2.0,
            default_rate=0.02,
            credit_spread=0.018,
            claims_exceed_surplus=False,
        )
        assert result.credit_fragility is False
