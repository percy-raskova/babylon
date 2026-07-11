"""Tests for Class Dynamics Engine type definitions.

Feature: 016-class-dynamics-engine
Task: T003
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.dynamics.types import (
    AccumulationResult,
    ClassDistribution,
    DispossessionRisk,
    EconomicConditions,
    SavingsRateSchedule,
    TransitionRates,
)


class TestClassDistribution:
    """Tests for ClassDistribution frozen model."""

    def test_valid_distribution_creates_successfully(self) -> None:
        """Standard US class distribution creates without error."""
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        assert dist.fips == "26163"
        assert dist.year == 2015

    def test_sum_to_one_invariant_passes(self) -> None:
        """Shares summing to 1.0 pass validation."""
        dist = ClassDistribution(
            fips="00000",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        assert dist.total_share_check()

    def test_sum_to_one_within_tolerance(self) -> None:
        """Shares summing to 1.0 within 0.001 tolerance pass."""
        dist = ClassDistribution(
            fips="00000",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.4005,
            proletariat_share=0.3495,
            lumpenproletariat_share=0.15,
        )
        assert dist.total_share_check()

    def test_sum_exceeds_tolerance_fails_validation(self) -> None:
        """Shares not summing to 1.0 beyond tolerance raise ValidationError."""
        with pytest.raises(ValidationError, match="sum"):
            ClassDistribution(
                fips="00000",
                year=2015,
                bourgeoisie_share=0.01,
                petit_bourgeoisie_share=0.09,
                labor_aristocracy_share=0.50,
                proletariat_share=0.35,
                lumpenproletariat_share=0.15,
            )

    def test_negative_share_fails_validation(self) -> None:
        """Negative share values raise ValidationError."""
        with pytest.raises(ValidationError):
            ClassDistribution(
                fips="00000",
                year=2015,
                bourgeoisie_share=-0.01,
                petit_bourgeoisie_share=0.10,
                labor_aristocracy_share=0.41,
                proletariat_share=0.35,
                lumpenproletariat_share=0.15,
            )

    def test_frozen_immutability(self) -> None:
        """ClassDistribution is frozen (immutable)."""
        dist = ClassDistribution(
            fips="00000",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        with pytest.raises(ValidationError):
            dist.labor_aristocracy_share = 0.50  # type: ignore[misc]

    def test_dynamic_shares_returns_three_tuple(self) -> None:
        """dynamic_shares() returns (LA, proletariat, lumpen) tuple."""
        dist = ClassDistribution(
            fips="00000",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        la, prol, lumpen = dist.dynamic_shares()
        assert la == pytest.approx(0.40)
        assert prol == pytest.approx(0.35)
        assert lumpen == pytest.approx(0.15)

    def test_with_updated_dynamics_returns_new_distribution(self) -> None:
        """with_updated_dynamics() returns new ClassDistribution preserving B/PB."""
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        new_dist = dist.with_updated_dynamics(la=0.38, prol=0.36, lumpen=0.16)
        assert new_dist.bourgeoisie_share == 0.01
        assert new_dist.petit_bourgeoisie_share == 0.09
        assert new_dist.labor_aristocracy_share == pytest.approx(0.38)
        assert new_dist.proletariat_share == pytest.approx(0.36)
        assert new_dist.lumpenproletariat_share == pytest.approx(0.16)
        assert new_dist.year == 2016  # year + 1

    def test_with_updated_dynamics_preserves_fips(self) -> None:
        """with_updated_dynamics() preserves FIPS code."""
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        new_dist = dist.with_updated_dynamics(la=0.40, prol=0.35, lumpen=0.15)
        assert new_dist.fips == "26163"


class TestEconomicConditions:
    """Tests for EconomicConditions frozen model."""

    def test_valid_conditions_create_successfully(self) -> None:
        """Standard conditions create without error."""
        cond = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.05,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.063,
            crisis=False,
        )
        assert cond.fips == "26163"
        assert cond.crisis is False

    def test_frozen_immutability(self) -> None:
        """EconomicConditions is frozen."""
        cond = EconomicConditions(
            fips="00000",
            year=2015,
            unemployment_rate=0.05,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.063,
            crisis=False,
        )
        with pytest.raises(ValidationError):
            cond.crisis = True  # type: ignore[misc]

    def test_melt_must_be_positive(self) -> None:
        """MELT must be > 0 (division guard)."""
        with pytest.raises(ValidationError):
            EconomicConditions(
                fips="00000",
                year=2015,
                unemployment_rate=0.05,
                median_wage=45000.0,
                melt=0.0,
                phi_hour=0.0,
                foreclosure_rate=0.0,
                bankruptcy_rate=0.0,
                eviction_rate=0.0,
                crisis=False,
            )

    def test_rates_clamped_to_unit_interval(self) -> None:
        """Rates exceeding 1.0 fail validation."""
        with pytest.raises(ValidationError):
            EconomicConditions(
                fips="00000",
                year=2015,
                unemployment_rate=1.5,
                median_wage=45000.0,
                melt=62.0,
                phi_hour=0.0,
                foreclosure_rate=0.0,
                bankruptcy_rate=0.0,
                eviction_rate=0.0,
                crisis=False,
            )


class TestTransitionRates:
    """Tests for TransitionRates frozen model."""

    def test_valid_rates_create_successfully(self) -> None:
        """Standard transition rates create without error."""
        rates = TransitionRates(
            fips="26163",
            year=2015,
            dispossession=0.01,
            accumulation=0.005,
            precaritization=0.02,
            stabilization=0.05,
        )
        assert rates.dispossession == pytest.approx(0.01)

    def test_rates_non_negative(self) -> None:
        """Negative rates fail validation."""
        with pytest.raises(ValidationError):
            TransitionRates(
                fips="00000",
                year=2015,
                dispossession=-0.01,
                accumulation=0.005,
                precaritization=0.02,
                stabilization=0.05,
            )

    def test_rates_at_most_one(self) -> None:
        """Rates > 1.0 fail validation."""
        with pytest.raises(ValidationError):
            TransitionRates(
                fips="00000",
                year=2015,
                dispossession=1.5,
                accumulation=0.005,
                precaritization=0.02,
                stabilization=0.05,
            )

    def test_frozen_immutability(self) -> None:
        """TransitionRates is frozen."""
        rates = TransitionRates(
            fips="00000",
            year=2015,
            dispossession=0.01,
            accumulation=0.005,
            precaritization=0.02,
            stabilization=0.05,
        )
        with pytest.raises(ValidationError):
            rates.dispossession = 0.5  # type: ignore[misc]


class TestAccumulationResult:
    """Tests for AccumulationResult frozen model."""

    def test_positive_accumulation(self) -> None:
        """Positive accumulation creates successfully."""
        result = AccumulationResult(
            wage=60000.0,
            consumption=50000.0,
            savings_rate=0.15,
            phi_adjustment=0.03,
            annual_accumulation=1500.0,
            years_to_threshold=94.7,
        )
        assert result.annual_accumulation == pytest.approx(1500.0)
        assert result.years_to_threshold == pytest.approx(94.7)

    def test_negative_accumulation_allowed(self) -> None:
        """Negative annual_accumulation is allowed (wealth destruction)."""
        result = AccumulationResult(
            wage=30000.0,
            consumption=35000.0,
            savings_rate=0.03,
            phi_adjustment=0.0,
            annual_accumulation=-5000.0,
            years_to_threshold=None,
        )
        assert result.annual_accumulation < 0.0
        assert result.years_to_threshold is None

    def test_frozen_immutability(self) -> None:
        """AccumulationResult is frozen."""
        result = AccumulationResult(
            wage=60000.0,
            consumption=50000.0,
            savings_rate=0.15,
            phi_adjustment=0.0,
            annual_accumulation=1500.0,
            years_to_threshold=None,
        )
        with pytest.raises(ValidationError):
            result.wage = 0.0  # type: ignore[misc]


class TestDispossessionRisk:
    """Tests for DispossessionRisk frozen model."""

    def test_valid_risk_creates_successfully(self) -> None:
        """Standard risk assessment creates without error."""
        risk = DispossessionRisk(
            fips="26163",
            year=2015,
            foreclosure_risk=0.006,
            bankruptcy_risk=0.006,
            eviction_risk=0.063,
            la_to_p_rate=0.01,
            p_to_l_component=0.04,
            foreclosure_available=True,
            bankruptcy_available=True,
            eviction_available=True,
        )
        assert risk.la_to_p_rate == pytest.approx(0.01)
        assert risk.p_to_l_component == pytest.approx(0.04)

    def test_all_sources_available_flag(self) -> None:
        """Availability flags track per-source data presence."""
        risk = DispossessionRisk(
            fips="00000",
            year=2015,
            foreclosure_risk=0.006,
            bankruptcy_risk=0.0,
            eviction_risk=0.063,
            la_to_p_rate=0.01,
            p_to_l_component=0.04,
            foreclosure_available=True,
            bankruptcy_available=False,
            eviction_available=True,
        )
        assert risk.foreclosure_available is True
        assert risk.bankruptcy_available is False

    def test_frozen_immutability(self) -> None:
        """DispossessionRisk is frozen."""
        risk = DispossessionRisk(
            fips="00000",
            year=2015,
            foreclosure_risk=0.006,
            bankruptcy_risk=0.006,
            eviction_risk=0.063,
            la_to_p_rate=0.01,
            p_to_l_component=0.04,
            foreclosure_available=True,
            bankruptcy_available=True,
            eviction_available=True,
        )
        with pytest.raises(ValidationError):
            risk.la_to_p_rate = 0.5  # type: ignore[misc]


class TestSavingsRateSchedule:
    """Tests for SavingsRateSchedule frozen model."""

    def test_default_schedule_creates_successfully(self) -> None:
        """Default savings rate schedule creates without error."""
        schedule = SavingsRateSchedule(
            rates={
                "BOURGEOISIE": 0.38,
                "PETIT_BOURGEOISIE": 0.20,
                "LABOR_ARISTOCRACY": 0.12,
                "PROLETARIAT": 0.03,
                "LUMPENPROLETARIAT": 0.00,
            },
            phi_cap=0.05,
        )
        assert schedule.rates["LABOR_ARISTOCRACY"] == pytest.approx(0.12)
        assert schedule.phi_cap == pytest.approx(0.05)

    def test_frozen_immutability(self) -> None:
        """SavingsRateSchedule is frozen."""
        schedule = SavingsRateSchedule(
            rates={
                "BOURGEOISIE": 0.38,
                "PETIT_BOURGEOISIE": 0.20,
                "LABOR_ARISTOCRACY": 0.12,
                "PROLETARIAT": 0.03,
                "LUMPENPROLETARIAT": 0.00,
            },
            phi_cap=0.05,
        )
        with pytest.raises(ValidationError):
            schedule.phi_cap = 0.10  # type: ignore[misc]
