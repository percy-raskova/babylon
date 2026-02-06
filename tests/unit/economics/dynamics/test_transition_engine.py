"""Tests for the class transition engine.

Feature: 016-class-dynamics-engine
Tasks: T020a, T020b
"""

from __future__ import annotations

import pytest
from tests.unit.economics.dynamics.conftest import (
    MockCrisisAmplifier,
    MockDispossessionDataSource,
    MockSavingsRateSource,
)

from babylon.economics.dynamics.accumulation import DefaultAccumulationCalculator
from babylon.economics.dynamics.crisis import DefaultCrisisAmplifier
from babylon.economics.dynamics.dispossession import DefaultDispossessionCalculator
from babylon.economics.dynamics.hardcoded_data import (
    HardcodedNationalDispossessionSource,
)
from babylon.economics.dynamics.savings_schedule import DefaultSavingsRateSchedule
from babylon.economics.dynamics.transition_engine import DefaultClassTransitionEngine
from babylon.economics.dynamics.types import (
    ClassDistribution,
    EconomicConditions,
)
from babylon.economics.tensor import NoDataSentinel


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
        from babylon.economics.dynamics.accumulation import DefaultAccumulationCalculator

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
        from babylon.economics.dynamics.data_sources import ClassTransitionEngine

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
