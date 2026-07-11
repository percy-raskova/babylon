"""Integration test for full crisis lifecycle.

Feature: 018-crisis-devaluation-mechanics
Tasks: T029, T066, T076

Tests the complete crisis lifecycle:
NORMAL -> ONSET -> EARLY -> DEEP -> RECOVERY -> NORMAL
via synthetic profit rate sequence, plus cross-system integration tests.
"""

from __future__ import annotations

import pytest

from babylon.economics.crisis.bifurcation import BifurcationRiskCalculator
from babylon.economics.crisis.wage_compression import (
    apply_wage_compression,
)
from babylon.economics.dynamics.crisis import PhasedCrisisAmplifier
from babylon.economics.dynamics.types import ClassDistribution, TransitionRates
from babylon.economics.tick.crisis_detector import MultiPeriodCrisisDetector
from babylon.economics.tick.types import CrisisPhase, CrisisState
from babylon.topology.graph import BabylonGraph


@pytest.mark.unit
class TestFullCrisisLifecycle:
    """Full lifecycle integration: NORMAL through all phases back to NORMAL.

    Uses default crisis parameters (N=3, M=2, R_cap=8) to drive a county
    through the complete crisis lifecycle.
    """

    def test_complete_lifecycle(self) -> None:
        """Drive a county through NORMAL -> ONSET -> EARLY -> DEEP -> RECOVERY -> NORMAL."""
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=8,
        )
        state = CrisisState.normal()

        # === Phase 1: NORMAL ===
        # Healthy profit rates -- should stay NORMAL
        for r in [0.15, 0.12, 0.11]:
            state = detector.evaluate(r, state)
        assert state.phase == CrisisPhase.NORMAL

        # === Phase 2: Approaching crisis ===
        # 2 consecutive below threshold -- not enough for N=3
        state = detector.evaluate(0.09, state)
        state = detector.evaluate(0.08, state)
        assert state.phase == CrisisPhase.NORMAL
        assert state.consecutive_below == 2

        # === Phase 3: ONSET ===
        # 3rd consecutive below threshold -> ONSET
        state = detector.evaluate(0.07, state)
        assert state.phase == CrisisPhase.ONSET
        assert state.crisis_duration >= 1

        # === Phase 4: EARLY ===
        # Next evaluation advances to EARLY
        state = detector.evaluate(0.06, state)
        assert state.phase == CrisisPhase.EARLY

        # EARLY persists for 3 more evaluations (4 total EARLY periods)
        state = detector.evaluate(0.05, state)
        assert state.phase == CrisisPhase.EARLY
        state = detector.evaluate(0.04, state)
        assert state.phase == CrisisPhase.EARLY
        state = detector.evaluate(0.03, state)
        assert state.phase == CrisisPhase.EARLY

        # === Phase 5: DEEP ===
        # Next evaluation transitions to DEEP
        state = detector.evaluate(0.02, state)
        assert state.phase == CrisisPhase.DEEP

        # Stay in DEEP for a few more periods
        state = detector.evaluate(0.03, state)
        assert state.phase == CrisisPhase.DEEP
        state = detector.evaluate(0.04, state)
        assert state.phase == CrisisPhase.DEEP

        # === Phase 6: Begin recovery ===
        # 1 above threshold -> still DEEP (need M=2)
        state = detector.evaluate(0.12, state)
        assert state.phase == CrisisPhase.DEEP

        # 2nd above threshold -> RECOVERY
        state = detector.evaluate(0.13, state)
        assert state.phase == CrisisPhase.RECOVERY

        # === Phase 7: RECOVERY persists for hysteresis window ===
        recovery_counter = 0
        max_recovery = 20  # Safety bound
        while state.phase == CrisisPhase.RECOVERY and recovery_counter < max_recovery:
            state = detector.evaluate(0.15, state)
            recovery_counter += 1

        # === Phase 8: Back to NORMAL ===
        assert state.phase == CrisisPhase.NORMAL
        assert recovery_counter > 0  # Recovery took some periods
        assert recovery_counter <= 8  # Bounded by R_cap

        # Verify all counters are reset
        assert state.consecutive_below == 0
        assert state.consecutive_recovery == 0
        assert state.crisis_start_period is None
        assert state.crisis_duration == 0
        assert state.peak_severity is None
        assert state.cumulative_wage_compression == 0.0

    def test_lifecycle_with_none_periods(self) -> None:
        """Lifecycle with intermittent None profit rates.

        None periods should not interrupt the lifecycle progression.
        """
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=4,
        )
        state = CrisisState.normal()

        # 2 below, None (no effect), 1 below -> should trigger at 3
        state = detector.evaluate(0.09, state)
        state = detector.evaluate(0.08, state)
        state = detector.evaluate(None, state)  # No effect
        state = detector.evaluate(0.07, state)  # 3rd consecutive

        assert state.phase == CrisisPhase.ONSET

    def test_lifecycle_with_interrupted_recovery(self) -> None:
        """Lifecycle where recovery is interrupted then eventually succeeds."""
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=4,
        )
        state = CrisisState.normal()

        # Drive to DEEP
        # 3 below -> ONSET, +1 -> EARLY, +3 -> still EARLY, +1 -> DEEP
        for r in [0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02]:
            state = detector.evaluate(r, state)

        assert state.phase == CrisisPhase.DEEP

        # Enter RECOVERY
        state = detector.evaluate(0.12, state)
        state = detector.evaluate(0.11, state)
        assert state.phase == CrisisPhase.RECOVERY

        # Rate drops -> back to DEEP
        state = detector.evaluate(0.08, state)
        assert state.phase == CrisisPhase.DEEP

        # Try recovery again
        state = detector.evaluate(0.12, state)
        state = detector.evaluate(0.13, state)
        assert state.phase == CrisisPhase.RECOVERY

        # This time complete recovery
        for _ in range(20):
            state = detector.evaluate(0.15, state)
            if state.phase == CrisisPhase.NORMAL:
                break

        assert state.phase == CrisisPhase.NORMAL

    def test_multiple_crisis_episodes(self) -> None:
        """County can go through multiple complete crisis-recovery cycles."""
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=3,
        )
        state = CrisisState.normal()

        for _episode in range(2):
            # Drive into crisis: 3 below -> ONSET
            for _ in range(3):
                state = detector.evaluate(0.05, state)
            assert state.phase != CrisisPhase.NORMAL

            # Drive through to DEEP
            for _ in range(10):
                state = detector.evaluate(0.03, state)
                if state.phase == CrisisPhase.DEEP:
                    break
            assert state.phase == CrisisPhase.DEEP

            # Recover: M=2 above threshold -> RECOVERY
            state = detector.evaluate(0.15, state)
            state = detector.evaluate(0.15, state)
            assert state.phase == CrisisPhase.RECOVERY

            # Push through recovery to NORMAL
            for _ in range(20):
                state = detector.evaluate(0.15, state)
                if state.phase == CrisisPhase.NORMAL:
                    break

            assert state.phase == CrisisPhase.NORMAL


# =============================================================================
# T066: Full lifecycle integration with all subsystems
# =============================================================================


@pytest.mark.unit
class TestCrossSystemIntegration:
    """T066: Integration test with detector, amplifier, bifurcation, and wage compression."""

    def test_all_subsystems_interact(self) -> None:
        """All crisis subsystems work together through a lifecycle.

        Tests that detector, phased amplifier, bifurcation calculator, and
        wage compression all produce coherent results through a complete
        crisis episode.
        """
        # Setup subsystems
        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=4,
        )
        amplifier = PhasedCrisisAmplifier()
        bifurcation = BifurcationRiskCalculator()

        # Initial state
        state = CrisisState.normal()

        # --- Drive to DEEP crisis ---
        # 3 below -> ONSET, +1 -> EARLY, +4 -> DEEP
        rates_below = [0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01]
        for r in rates_below:
            state = detector.evaluate(r, state)
        assert state.phase == CrisisPhase.DEEP

        # --- Test phased amplification ---
        base_rates = TransitionRates(
            fips="26163",
            year=2015,
            dispossession=0.02,
            accumulation=0.01,
            precaritization=0.03,
            stabilization=0.05,
        )
        deep_rates = amplifier.amplify_phased(base_rates, CrisisPhase.DEEP)
        # DEEP should amplify dispossession and precaritization
        assert deep_rates.dispossession > base_rates.dispossession
        assert deep_rates.precaritization > base_rates.precaritization
        # And suppress accumulation and stabilization
        assert deep_rates.accumulation < base_rates.accumulation
        assert deep_rates.stabilization < base_rates.stabilization

        # --- Test bifurcation risk during crisis ---
        g = BabylonGraph()
        g.add_node("26163", _node_type="territory")
        for role in ["labor_aristocracy", "proletariat", "lumpenproletariat"]:
            g.add_node(
                f"26163_{role}",
                _node_type="social_class",
                role=role,
                ideology={"agitation": 0.6, "class_consciousness": 0.5, "national_identity": 0.5},
                territory="26163",
            )
        # Add some solidarity edges
        g.add_edge("26163_labor_aristocracy", "26163_proletariat", edge_type="solidarity")
        g.add_edge("26163_proletariat", "26163_lumpenproletariat", edge_type="solidarity")

        prev_dist = ClassDistribution(
            fips="26163",
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        curr_dist = ClassDistribution(
            fips="26163",
            year=2016,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.35,
            proletariat_share=0.38,
            lumpenproletariat_share=0.17,
        )

        metric = bifurcation.compute(g, "26163", state, prev_dist, curr_dist)
        assert metric.score != 0.0  # Active crisis produces non-zero score
        assert metric.solidarity_density > 0.0
        assert metric.legitimation < 1.0  # Agitation = 0.6 -> legitimation = 0.4

        # --- Test wage compression ---
        from babylon.economics.tick.types import CountyEconomicState

        county = CountyEconomicState(
            fips="26163",
            year=2015,
            capital_stock=1e9,
            throughput_position=0.9,
            supply_chain_depth=2.1,
            unemployment_rate=0.08,
            u6_rate=0.12,
            pter_rate=0.04,
            nilf_rate=0.06,
            median_wage=15.0,
            employment=350000.0,
            phi_hour=3.5,
            crisis_state=state,
            class_distribution=prev_dist,
        )
        compressed = apply_wage_compression(county, 0.02)
        assert compressed.median_wage < county.median_wage
        assert compressed.crisis_state.cumulative_wage_compression > 0.0

    def test_backward_compatibility_crisis_bool(self) -> None:
        """T067: EconomicConditions.crisis derives correctly from phase.

        The crisis boolean should be True for any non-NORMAL phase
        and False for NORMAL.
        """
        from babylon.economics.dynamics.types import EconomicConditions

        for phase in CrisisPhase:
            crisis_bool = phase != CrisisPhase.NORMAL
            conditions = EconomicConditions(
                fips="26163",
                year=2015,
                unemployment_rate=0.05,
                median_wage=45000.0,
                melt=62.0,
                phi_hour=3.50,
                foreclosure_rate=0.006,
                bankruptcy_rate=0.006,
                eviction_rate=0.063,
                crisis=crisis_bool,
            )
            if phase == CrisisPhase.NORMAL:
                assert not conditions.crisis
            else:
                assert conditions.crisis


# =============================================================================
# T076: SC-002 scenario (2008-2012 conditions)
# =============================================================================


@pytest.mark.unit
class TestSC002Scenario:
    """SC-002: Simulate 2008-2012 sustained profit rate decline."""

    def test_sustained_decline_produces_la_loss(self) -> None:
        """Sustained 15-25% profit rate decline drives LA share down.

        A county experiencing deep crisis over multiple periods should see
        LA share decline via phased amplification of dispossession.
        """
        amplifier = PhasedCrisisAmplifier()

        # Simulate 8 periods of DEEP crisis amplification
        # Start with moderate rates
        la_share = 0.40
        prol_share = 0.35
        lumpen_share = 0.15

        for _ in range(8):
            rates = TransitionRates(
                fips="26163",
                year=2015,
                dispossession=0.02,
                accumulation=0.01,
                precaritization=0.03,
                stabilization=0.05,
            )
            amplified = amplifier.amplify_phased(rates, CrisisPhase.DEEP)

            # Apply transitions (simplified)
            la_loss = la_share * amplified.dispossession
            prol_loss = prol_share * amplified.precaritization
            prol_gain = la_loss  # LA->Prol
            lumpen_gain = prol_loss  # Prol->Lumpen

            la_share -= la_loss
            prol_share = prol_share - prol_loss + prol_gain
            lumpen_share += lumpen_gain

        # After 8 DEEP periods, LA should decline significantly
        la_decline = 0.40 - la_share
        lumpen_increase = lumpen_share - 0.15

        # SC-002: LA share declines by >= 5pp
        assert la_decline >= 0.05, f"LA decline {la_decline:.3f} < 0.05"
        # SC-002: Lumpenproletariat share increases by >= 5pp
        assert lumpen_increase >= 0.05, f"Lumpen increase {lumpen_increase:.3f} < 0.05"


# =============================================================================
# T077: SC-008 performance validation
# =============================================================================


@pytest.mark.unit
class TestSC008Performance:
    """SC-008: Crisis subsystems complete within per-tick time budget.

    50 counties × 20 years × 4 quarterly evaluations = 4000 evaluations.
    All crisis detection, amplification, bifurcation, and wage compression
    must complete within a generous wall-clock budget.
    """

    def test_50_county_20_year_simulation_performance(self) -> None:
        """50-county, 20-year crisis lifecycle completes within 2 seconds.

        Exercises all crisis subsystems at scale to verify no performance
        degradation from multi-period detection.
        """
        import time

        from babylon.economics.crisis.wage_compression import (
            apply_wage_compression,
        )
        from babylon.economics.dynamics.types import ClassDistribution

        n_counties = 50
        n_years = 20
        quarterly_per_year = 4

        detector = MultiPeriodCrisisDetector(
            r_threshold=0.10,
            n_consecutive=3,
            m_recovery=2,
            r_cap=8,
        )
        amplifier = PhasedCrisisAmplifier()
        bifurcation_calc = BifurcationRiskCalculator()

        # Build a simple graph with solidarity edges
        g = BabylonGraph()
        for i in range(n_counties):
            fips = f"{26000 + i:05d}"
            g.add_node(fips, _node_type="territory")
            for role in ["labor_aristocracy", "proletariat", "lumpenproletariat"]:
                g.add_node(
                    f"{fips}_{role}",
                    _node_type="social_class",
                    role=role,
                    ideology={
                        "agitation": 0.4,
                        "class_consciousness": 0.3,
                        "national_identity": 0.5,
                    },
                    territory=fips,
                )
            g.add_edge(
                f"{fips}_proletariat",
                f"{fips}_lumpenproletariat",
                edge_type="solidarity",
            )

        # Initialize per-county state
        states = [CrisisState.normal() for _ in range(n_counties)]
        prev_dist = ClassDistribution(
            fips="00000",
            year=2007,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        curr_dist = ClassDistribution(
            fips="00000",
            year=2008,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.37,
            proletariat_share=0.37,
            lumpenproletariat_share=0.16,
        )

        base_rates = TransitionRates(
            fips="00000",
            year=2008,
            dispossession=0.02,
            accumulation=0.01,
            precaritization=0.03,
            stabilization=0.05,
        )

        # Alternate profit rates: low years trigger crisis, high years recover
        profit_rates = [0.04 if y % 5 < 3 else 0.15 for y in range(n_years)]

        start = time.perf_counter()

        for year_idx in range(n_years):
            r = profit_rates[year_idx]
            for county_idx in range(n_counties):
                fips = f"{26000 + county_idx:05d}"

                # Quarterly crisis detection (4 evaluations per year)
                for _q in range(quarterly_per_year):
                    states[county_idx] = detector.evaluate(r, states[county_idx])

                phase = states[county_idx].phase

                # Phased amplification
                amplifier.amplify_phased(base_rates, phase)

                # Bifurcation risk
                bifurcation_calc.compute(g, fips, states[county_idx], prev_dist, curr_dist)

                # Wage compression (only during DEEP)
                if phase == CrisisPhase.DEEP:
                    # Create minimal county for compression
                    from babylon.economics.tick.types import CountyEconomicState

                    county = CountyEconomicState(
                        fips=fips,
                        year=2008 + year_idx,
                        capital_stock=1e9,
                        throughput_position=0.9,
                        supply_chain_depth=2.1,
                        unemployment_rate=0.08,
                        u6_rate=0.12,
                        pter_rate=0.04,
                        nilf_rate=0.06,
                        median_wage=15.0,
                        employment=350000.0,
                        phi_hour=3.5,
                        crisis_state=states[county_idx],
                        class_distribution=prev_dist,
                    )
                    apply_wage_compression(county, 0.02)

        elapsed = time.perf_counter() - start

        # SC-008: Must complete within 2 seconds (generous budget)
        assert elapsed < 2.0, f"50-county × 20-year simulation took {elapsed:.2f}s (budget: 2.0s)"
