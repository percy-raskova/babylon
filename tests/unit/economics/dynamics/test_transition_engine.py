"""Tests for the class transition engine.

Feature: 016-class-dynamics-engine
Tasks: T020a, T020b, T034
"""

from __future__ import annotations

import logging

import pytest

from babylon.domain.economics.dynamics.accumulation import DefaultAccumulationCalculator
from babylon.domain.economics.dynamics.crisis import DefaultCrisisAmplifier
from babylon.domain.economics.dynamics.dispossession import DefaultDispossessionCalculator
from babylon.domain.economics.dynamics.hardcoded_data import (
    HardcodedNationalDispossessionSource,
)
from babylon.domain.economics.dynamics.savings_schedule import DefaultSavingsRateSchedule
from babylon.domain.economics.dynamics.transition_engine import DefaultClassTransitionEngine
from babylon.domain.economics.dynamics.types import (
    ClassDistribution,
    EconomicConditions,
)
from babylon.domain.economics.tensor import NoDataSentinel
from tests.unit.economics.dynamics.conftest import (
    MockCrisisAmplifier,
    MockDispossessionDataSource,
    MockSavingsRateSource,
)


def _make_engine(
    *,
    crisis_amplifier: float = 1.0,
    recovery_dampener: float = 1.0,
) -> DefaultClassTransitionEngine:
    """Helper to build engine with real data sources."""
    savings = DefaultSavingsRateSchedule()
    acc_calc = DefaultAccumulationCalculator(savings)
    disp_source = HardcodedNationalDispossessionSource()
    disp_calc = DefaultDispossessionCalculator(disp_source)
    crisis = DefaultCrisisAmplifier(
        crisis_amplifier=crisis_amplifier,
        recovery_dampener=recovery_dampener,
    )
    return DefaultClassTransitionEngine(
        accumulation_calculator=acc_calc,
        dispossession_calculator=disp_calc,
        crisis_amplifier=crisis,
    )


class TestPrecaritizationRate:
    """Tests for FR-015 precaritization formula."""

    def test_precaritization_increases_with_unemployment(self) -> None:
        """Higher unemployment -> higher precaritization rate."""
        engine = _make_engine()
        low_unemp = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.04,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.063,
            crisis=False,
        )
        high_unemp = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.15,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.063,
            crisis=False,
        )
        low_rate = engine._compute_precaritization_rate(low_unemp)
        high_rate = engine._compute_precaritization_rate(high_unemp)
        assert high_rate > low_rate

    def test_precaritization_increases_with_eviction(self) -> None:
        """Higher eviction rate -> higher precaritization rate."""
        engine = _make_engine()
        low_evict = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.05,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.02,
            crisis=False,
        )
        high_evict = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.05,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.10,
            crisis=False,
        )
        low_rate = engine._compute_precaritization_rate(low_evict)
        high_rate = engine._compute_precaritization_rate(high_evict)
        assert high_rate > low_rate


class TestStabilizationRate:
    """Tests for FR-016 stabilization formula."""

    def test_stabilization_increases_with_employment(self) -> None:
        """Lower unemployment -> higher stabilization rate."""
        engine = _make_engine()
        low_unemp = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.04,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.063,
            crisis=False,
        )
        high_unemp = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.15,
            median_wage=45000.0,
            melt=62.0,
            phi_hour=3.50,
            foreclosure_rate=0.006,
            bankruptcy_rate=0.006,
            eviction_rate=0.063,
            crisis=False,
        )
        low_u_stab = engine._compute_stabilization_rate(low_unemp)
        high_u_stab = engine._compute_stabilization_rate(high_unemp)
        assert low_u_stab > high_u_stab

    def test_stabilization_zero_at_full_unemployment(self) -> None:
        """Full unemployment (1.0) -> zero stabilization."""
        engine = _make_engine()
        full_unemp = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=1.0,
            median_wage=0.0,
            melt=62.0,
            phi_hour=0.0,
            foreclosure_rate=0.0,
            bankruptcy_rate=0.0,
            eviction_rate=0.0,
            crisis=False,
        )
        rate = engine._compute_stabilization_rate(full_unemp)
        assert rate == pytest.approx(0.0)


class TestClassTransitionEngine:
    """Tests for DefaultClassTransitionEngine per US3 acceptance scenarios."""

    def test_scenario1_stable_small_perturbation(
        self,
        stable_distribution: ClassDistribution,
        stable_conditions: EconomicConditions,
    ) -> None:
        """S1: Stable conditions -> small perturbation, sum=1.0 (SC-001).

        Given stable conditions, the distribution changes by less than
        2% per period and still sums to 1.0.
        """
        engine = _make_engine()
        result = engine.simulate_transitions(stable_distribution, stable_conditions)

        assert isinstance(result, ClassDistribution)
        assert result.total_share_check()

        # Total change < 2% per SC-001
        la_change = abs(
            result.labor_aristocracy_share - stable_distribution.labor_aristocracy_share
        )
        prol_change = abs(result.proletariat_share - stable_distribution.proletariat_share)
        lumpen_change = abs(
            result.lumpenproletariat_share - stable_distribution.lumpenproletariat_share
        )
        total_change = la_change + prol_change + lumpen_change
        assert total_change < 0.02

    def test_scenario2_crisis_la_decreases_lumpen_increases(
        self,
        stable_distribution: ClassDistribution,
    ) -> None:
        """S2: Crisis conditions -> LA decreases, lumpen increases."""
        engine = _make_engine(crisis_amplifier=2.5, recovery_dampener=0.3)
        crisis_cond = EconomicConditions(
            fips="26163",
            year=2010,
            unemployment_rate=0.15,
            median_wage=35000.0,
            melt=58.0,
            phi_hour=3.00,
            foreclosure_rate=0.046,
            bankruptcy_rate=0.013,
            eviction_rate=0.070,
            crisis=True,
        )
        result = engine.simulate_transitions(stable_distribution, crisis_cond)

        assert isinstance(result, ClassDistribution)
        assert result.labor_aristocracy_share < stable_distribution.labor_aristocracy_share
        assert result.lumpenproletariat_share > stable_distribution.lumpenproletariat_share

    def test_scenario3_recovery_lumpen_decreases(
        self,
        stable_distribution: ClassDistribution,
    ) -> None:
        """S3: Recovery conditions -> lumpen decreases (upward mobility).

        Requires low enough unemployment and eviction that
        stabilization_rate * lumpen_pool > precaritization_rate * prol_pool.
        """
        engine = _make_engine()
        recovery = EconomicConditions(
            fips="26163",
            year=2015,
            unemployment_rate=0.03,
            median_wage=50000.0,
            melt=65.0,
            phi_hour=4.00,
            foreclosure_rate=0.004,
            bankruptcy_rate=0.005,
            eviction_rate=0.030,
            crisis=False,
        )
        result = engine.simulate_transitions(stable_distribution, recovery)

        assert isinstance(result, ClassDistribution)
        assert result.lumpenproletariat_share < stable_distribution.lumpenproletariat_share

    def test_scenario4_sum_to_one_invariant(
        self,
        stable_distribution: ClassDistribution,
        stable_conditions: EconomicConditions,
    ) -> None:
        """S4: Sum-to-one invariant always holds (SC-005)."""
        engine = _make_engine()
        result = engine.simulate_transitions(stable_distribution, stable_conditions)

        assert isinstance(result, ClassDistribution)
        total = (
            result.bourgeoisie_share
            + result.petit_bourgeoisie_share
            + result.labor_aristocracy_share
            + result.proletariat_share
            + result.lumpenproletariat_share
        )
        assert abs(total - 1.0) < 0.001

    def test_scenario5_continuous_flows(
        self,
        stable_distribution: ClassDistribution,
        stable_conditions: EconomicConditions,
    ) -> None:
        """S5: Transitions are continuous (no discrete jumps)."""
        engine = _make_engine()
        result = engine.simulate_transitions(stable_distribution, stable_conditions)

        assert isinstance(result, ClassDistribution)
        # No share should change by more than 10% in one period
        max_change = 0.10
        assert (
            abs(result.labor_aristocracy_share - stable_distribution.labor_aristocracy_share)
            < max_change
        )
        assert abs(result.proletariat_share - stable_distribution.proletariat_share) < max_change
        assert (
            abs(result.lumpenproletariat_share - stable_distribution.lumpenproletariat_share)
            < max_change
        )

    def test_degenerate_distribution_no_crash(self) -> None:
        """Edge: Degenerate distribution (one class = 0.9) handled gracefully."""
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.89,
            proletariat_share=0.005,
            lumpenproletariat_share=0.005,
        )
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
        engine = _make_engine()
        result = engine.simulate_transitions(dist, cond)

        assert isinstance(result, ClassDistribution)
        assert result.total_share_check()

    def test_no_data_sentinel_propagation(self) -> None:
        """Edge: Missing dispossession data -> NoDataSentinel propagated."""
        savings = MockSavingsRateSource()
        from babylon.domain.economics.dynamics.accumulation import DefaultAccumulationCalculator

        acc_calc = DefaultAccumulationCalculator(savings)
        # Empty data source for dispossession
        disp_source = MockDispossessionDataSource(
            foreclosure={},
            bankruptcy={},
            eviction={},
        )
        disp_calc = DefaultDispossessionCalculator(disp_source)
        crisis = MockCrisisAmplifier()
        engine = DefaultClassTransitionEngine(
            accumulation_calculator=acc_calc,
            dispossession_calculator=disp_calc,
            crisis_amplifier=crisis,
        )
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
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
        result = engine.simulate_transitions(dist, cond)
        assert isinstance(result, NoDataSentinel)

    def test_fips_mismatch_raises_error(
        self,
        stable_distribution: ClassDistribution,
    ) -> None:
        """Edge: FIPS mismatch between dist and conditions -> ValueError."""
        engine = _make_engine()
        mismatched = EconomicConditions(
            fips="06037",
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
        with pytest.raises(ValueError, match="FIPS"):
            engine.simulate_transitions(stable_distribution, mismatched)

    def test_year_advances_by_one(
        self,
        stable_distribution: ClassDistribution,
        stable_conditions: EconomicConditions,
    ) -> None:
        """Result year is dist.year + 1."""
        engine = _make_engine()
        result = engine.simulate_transitions(stable_distribution, stable_conditions)

        assert isinstance(result, ClassDistribution)
        assert result.year == stable_distribution.year + 1

    def test_bourgeoisie_and_pb_preserved(
        self,
        stable_distribution: ClassDistribution,
        stable_conditions: EconomicConditions,
    ) -> None:
        """B and PB shares are unchanged through transition."""
        engine = _make_engine()
        result = engine.simulate_transitions(stable_distribution, stable_conditions)

        assert isinstance(result, ClassDistribution)
        assert result.bourgeoisie_share == stable_distribution.bourgeoisie_share
        assert result.petit_bourgeoisie_share == stable_distribution.petit_bourgeoisie_share

    def test_protocol_compliance(self) -> None:
        """DefaultClassTransitionEngine satisfies ClassTransitionEngine protocol."""
        from babylon.domain.economics.dynamics.data_sources import ClassTransitionEngine

        engine: ClassTransitionEngine = _make_engine()
        dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
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
        result = engine.simulate_transitions(dist, cond)
        assert isinstance(result, ClassDistribution)


class TestMultiPeriodValidation:
    """Tests for US5 historical validation (T026).

    Validates multi-period simulation against SC-008 composition ranges
    and SC-004 recovery monotonicity criteria.
    """

    @staticmethod
    def _run_multi_period(
        start_dist: ClassDistribution,
        conditions: list[EconomicConditions],
        *,
        crisis_amplifier: float = 2.5,
        recovery_dampener: float = 0.3,
    ) -> list[ClassDistribution]:
        """Run multi-period simulation, returning distribution per period.

        Args:
            start_dist: Initial class distribution.
            conditions: List of EconomicConditions per year.
            crisis_amplifier: Crisis downward multiplier.
            recovery_dampener: Crisis upward multiplier.

        Returns:
            List of ClassDistribution including start_dist at index 0.
        """
        engine = _make_engine(
            crisis_amplifier=crisis_amplifier,
            recovery_dampener=recovery_dampener,
        )
        distributions: list[ClassDistribution] = [start_dist]
        current = start_dist
        for cond in conditions:
            result = engine.simulate_transitions(current, cond)
            assert isinstance(result, ClassDistribution)
            current = result
            distributions.append(current)
        return distributions

    def test_sc008_2010_to_2019_within_composition_ranges(
        self,
        historical_conditions_2007_2020: list[EconomicConditions],
    ) -> None:
        """SC-008: Post-crisis to 2019 distribution within composition ranges.

        Ranges: B 0.5-2%, PB 5-15%, LA 30-50%, P 25-45%, L 10-25%.
        Starting from 2012 (end of crisis) with crisis-degraded distribution.
        """
        conditions_2012_onward = [c for c in historical_conditions_2007_2020 if c.year >= 2012]

        # Post-crisis starting distribution (crisis degraded LA, elevated lumpen)
        start = ClassDistribution(
            fips="26163",
            year=2012,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.36,
            proletariat_share=0.34,
            lumpenproletariat_share=0.20,
        )

        distributions = self._run_multi_period(start, conditions_2012_onward)
        final = distributions[-1]

        # SC-008 composition ranges
        assert 0.005 <= final.bourgeoisie_share <= 0.02
        assert 0.05 <= final.petit_bourgeoisie_share <= 0.15
        assert 0.30 <= final.labor_aristocracy_share <= 0.50
        assert 0.25 <= final.proletariat_share <= 0.45
        assert 0.10 <= final.lumpenproletariat_share <= 0.25

    def test_crisis_years_directional_match(
        self,
        historical_conditions_2007_2020: list[EconomicConditions],
    ) -> None:
        """Crisis years (2008-2012) show LA decrease and lumpen increase.

        Over the full crisis period, cumulative LA should decrease and
        cumulative lumpen should increase relative to pre-crisis levels.
        """
        # Run from 2007 through 2012 (6 years of conditions)
        conditions_2007_2012 = [c for c in historical_conditions_2007_2020 if c.year <= 2012]

        start = ClassDistribution(
            fips="26163",
            year=2007,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.42,
            proletariat_share=0.34,
            lumpenproletariat_share=0.14,
        )

        distributions = self._run_multi_period(start, conditions_2007_2012)
        # Compare end-of-crisis (2012 result, index 6) vs start
        post_crisis = distributions[-1]

        assert post_crisis.labor_aristocracy_share < start.labor_aristocracy_share
        assert post_crisis.lumpenproletariat_share > start.lumpenproletariat_share

    def test_sc004_recovery_monotonic_lumpen_decrease(
        self,
        historical_conditions_2007_2020: list[EconomicConditions],
    ) -> None:
        """SC-004: Recovery (2013-2019) shows lumpen share decreasing.

        Over the recovery period, the general trend should show lumpen
        decreasing. We test that the final lumpen is lower than initial
        recovery-period lumpen.
        """
        conditions_recovery = [c for c in historical_conditions_2007_2020 if 2013 <= c.year <= 2019]

        # Start recovery with elevated lumpen from crisis
        start = ClassDistribution(
            fips="26163",
            year=2013,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.37,
            proletariat_share=0.34,
            lumpenproletariat_share=0.19,
        )

        distributions = self._run_multi_period(start, conditions_recovery)
        final = distributions[-1]

        # Lumpen should decrease over recovery period
        assert final.lumpenproletariat_share < start.lumpenproletariat_share

    def test_sum_to_one_every_period(
        self,
        historical_conditions_2007_2020: list[EconomicConditions],
    ) -> None:
        """Sum-to-one invariant holds at every time step."""
        start = ClassDistribution(
            fips="26163",
            year=2007,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.42,
            proletariat_share=0.34,
            lumpenproletariat_share=0.14,
        )

        distributions = self._run_multi_period(start, historical_conditions_2007_2020)

        for dist in distributions:
            total = (
                dist.bourgeoisie_share
                + dist.petit_bourgeoisie_share
                + dist.labor_aristocracy_share
                + dist.proletariat_share
                + dist.lumpenproletariat_share
            )
            assert abs(total - 1.0) < 0.001, f"year={dist.year}: total={total}"

    def test_no_share_exceeds_bounds(
        self,
        historical_conditions_2007_2020: list[EconomicConditions],
    ) -> None:
        """No share goes negative or above 1.0 at any time step."""
        conditions_all = historical_conditions_2007_2020

        start = ClassDistribution(
            fips="26163",
            year=2007,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.42,
            proletariat_share=0.34,
            lumpenproletariat_share=0.14,
        )

        distributions = self._run_multi_period(start, conditions_all)

        for dist in distributions:
            assert dist.labor_aristocracy_share >= 0.0
            assert dist.proletariat_share >= 0.0
            assert dist.lumpenproletariat_share >= 0.0
            assert dist.labor_aristocracy_share <= 1.0
            assert dist.proletariat_share <= 1.0
            assert dist.lumpenproletariat_share <= 1.0


class TestValidationLogging:
    """Tests for FR-011: validation results logged per period (T034)."""

    def test_warning_logged_for_unusual_rates(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """FR-011: Unusual transition rates produce warning-level log entries."""
        engine = _make_engine(crisis_amplifier=2.5, recovery_dampener=0.3)
        dist = ClassDistribution(
            fips="26163",
            year=2010,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        crisis_cond = EconomicConditions(
            fips="26163",
            year=2010,
            unemployment_rate=0.15,
            median_wage=35000.0,
            melt=58.0,
            phi_hour=3.00,
            foreclosure_rate=0.046,
            bankruptcy_rate=0.013,
            eviction_rate=0.070,
            crisis=True,
        )

        with caplog.at_level(logging.WARNING, logger="babylon.domain.economics.dynamics"):
            engine.simulate_transitions(dist, crisis_cond)

        # Should have logged at least one validation warning
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_messages) > 0
        assert any(
            "validation" in msg.lower() or "outside" in msg.lower() for msg in warning_messages
        )

    def test_no_warning_for_normal_rates(
        self,
        caplog: pytest.LogCaptureFixture,
        stable_distribution: ClassDistribution,
        stable_conditions: EconomicConditions,
    ) -> None:
        """FR-011: Normal conditions produce no validation warnings."""
        engine = _make_engine()

        with caplog.at_level(logging.WARNING, logger="babylon.domain.economics.dynamics"):
            engine.simulate_transitions(stable_distribution, stable_conditions)

        # Should have no validation warnings for stable conditions
        warning_messages = [
            r.message
            for r in caplog.records
            if r.levelno >= logging.WARNING and "validation" in r.message.lower()
        ]
        assert len(warning_messages) == 0
