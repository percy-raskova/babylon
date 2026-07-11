"""Tests for CohortDynamicsCalculator (Feature 030, US1, US4, US5).

Covers population conservation, births computation, edge cases,
subsistence burden calculation, ideology transmission (US4),
and differential P-phase duration (US5).
"""

from __future__ import annotations

import math

import pytest

from babylon.config.defines import LifecycleDefines
from babylon.domain.economics.lifecycle.cohort_dynamics import DefaultCohortDynamicsCalculator
from babylon.domain.economics.lifecycle.types import DPDState


class TestCohortDynamicsCalculator:
    """T008: CohortDynamicsCalculator tests."""

    @pytest.fixture
    def calc(self) -> DefaultCohortDynamicsCalculator:
        return DefaultCohortDynamicsCalculator()

    @pytest.fixture
    def defines(self) -> LifecycleDefines:
        return LifecycleDefines()

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_1_conservation(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        scenario_1_dpd_state: DPDState,
    ) -> None:
        """Scenario 1: Population conservation within 0.1% tolerance."""
        new_state = calc.compute_transitions(scenario_1_dpd_state, defines)
        assert calc.verify_conservation(scenario_1_dpd_state, new_state)

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_1_births(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        scenario_1_dpd_state: DPDState,
    ) -> None:
        """Births = birth_rate × pop_P ≈ 64.7."""
        new_state = calc.compute_transitions(scenario_1_dpd_state, defines)
        expected_births = 0.0107 * 6050.0
        # Births show up as increase in D phase minus outflows
        # Total pop change + deaths = births
        deaths = 0.039 * 1800.0
        total_change = new_state.total_population - scenario_1_dpd_state.total_population
        actual_births = total_change + deaths
        assert abs(actual_births - expected_births) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_zero_d_population(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Zero D population: no D-to-P flow, only births enter D."""
        state = DPDState(
            pop_d=0.0,
            pop_p=1000.0,
            pop_d_prime=500.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.04,
            birth_rate=0.01,
            wealth_d_prime=100000.0,
        )
        new_state = calc.compute_transitions(state, defines)
        assert new_state.pop_d >= 0.0
        assert new_state.pop_p >= 0.0
        assert new_state.pop_d_prime >= 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_zero_p_dependency_ratio(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Zero P population yields infinite dependency ratio."""
        state = DPDState(
            pop_d=500.0,
            pop_p=0.0,
            pop_d_prime=500.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.04,
            birth_rate=0.01,
        )
        assert math.isinf(state.dependency_ratio)

    @pytest.mark.unit
    @pytest.mark.math
    def test_negative_population_clamping(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Extreme outflow rates cannot produce negative populations."""
        state = DPDState(
            pop_d=10.0,
            pop_p=10.0,
            pop_d_prime=10.0,
            rate_d_to_p=0.99,
            rate_p_to_d_prime=0.99,
            rate_d_prime_to_death=0.99,
            birth_rate=0.0,
        )
        new_state = calc.compute_transitions(state, defines)
        assert new_state.pop_d >= 0.0
        assert new_state.pop_p >= 0.0
        assert new_state.pop_d_prime >= 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_subsistence_burden_standard(
        self,
        calc: DefaultCohortDynamicsCalculator,
    ) -> None:
        """Subsistence burden scales with dependency ratio."""
        burden = calc.compute_subsistence_burden(
            dependency_ratio=0.65,
            base_subsistence=30000.0,
        )
        assert abs(burden - 30000.0 * 1.65) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_subsistence_burden_infinite_ratio(
        self,
        calc: DefaultCohortDynamicsCalculator,
    ) -> None:
        """Infinite dependency ratio caps burden at 10x."""
        burden = calc.compute_subsistence_burden(
            dependency_ratio=math.inf,
            base_subsistence=30000.0,
        )
        assert abs(burden - 300000.0) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_wealth_reduced_by_deaths(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        scenario_1_dpd_state: DPDState,
    ) -> None:
        """D' wealth decreases proportionally to deaths."""
        new_state = calc.compute_transitions(scenario_1_dpd_state, defines)
        assert new_state.wealth_d_prime < scenario_1_dpd_state.wealth_d_prime
        assert new_state.wealth_d_prime >= 0.0


class TestIdeologyTransmission:
    """T025: Ideology transmission during D→P transition (US4)."""

    @pytest.fixture
    def calc(self) -> DefaultCohortDynamicsCalculator:
        return DefaultCohortDynamicsCalculator()

    @pytest.fixture
    def defines(self) -> LifecycleDefines:
        return LifecycleDefines()

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_6_raw_blending(
        self,
        calc: DefaultCohortDynamicsCalculator,
    ) -> None:
        """Scenario 6: 0.7×0.3 + 0.3×0.8 = 0.45 raw blend.

        With regression (r=0) disabled, expect exactly 0.45.
        """
        defines_no_regression = LifecycleDefines(ideology_regression_coefficient=0.0)
        result = calc.compute_ideology_transmission(
            caregiver_ideology=0.3,
            institutional_hegemony=0.8,
            defines=defines_no_regression,
        )
        assert abs(result - 0.45) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_6_with_regression(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Scenario 6 with default regression (r=0.4).

        raw = 0.45
        regressed = 0.45 * (1 - 0.4) + 0.5 * 0.4 = 0.27 + 0.20 = 0.47
        """
        result = calc.compute_ideology_transmission(
            caregiver_ideology=0.3,
            institutional_hegemony=0.8,
            defines=defines,
        )
        expected = 0.45 * 0.6 + 0.5 * 0.4
        assert abs(result - expected) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_regression_toward_mean(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """SC-005: Regression pulls extreme values toward 0.5 population mean.

        With extreme caregiver (1.0) and extreme institutional (1.0):
        raw = 0.7*1.0 + 0.3*1.0 = 1.0
        regressed = 1.0*(1-0.4) + 0.5*0.4 = 0.6 + 0.2 = 0.8
        Result is closer to 0.5 than input.
        """
        result = calc.compute_ideology_transmission(
            caregiver_ideology=1.0,
            institutional_hegemony=1.0,
            defines=defines,
        )
        # Must be pulled toward mean (< 1.0)
        assert result < 1.0
        assert result > 0.5

    @pytest.mark.unit
    @pytest.mark.math
    def test_regression_preserves_correlation(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """SC-005: Correlation r > 0.3 between caregiver and transmitted ideology.

        Higher caregiver ideology → higher transmitted value (monotonic).
        """
        results = []
        for caregiver in [0.1, 0.3, 0.5, 0.7, 0.9]:
            r = calc.compute_ideology_transmission(
                caregiver_ideology=caregiver,
                institutional_hegemony=0.5,
                defines=defines,
            )
            results.append(r)
        # Monotonically increasing
        for i in range(len(results) - 1):
            assert results[i] < results[i + 1]

    @pytest.mark.unit
    @pytest.mark.math
    def test_community_tendency_amplification(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Community tendency pulls transmitted ideology toward community value.

        With community_tendency > raw: result shifts upward.
        With community_tendency < raw: result shifts downward.
        """
        base = calc.compute_ideology_transmission(
            caregiver_ideology=0.3,
            institutional_hegemony=0.8,
            defines=defines,
        )
        with_high_community = calc.compute_ideology_transmission(
            caregiver_ideology=0.3,
            institutional_hegemony=0.8,
            defines=defines,
            community_tendency=0.9,
        )
        with_low_community = calc.compute_ideology_transmission(
            caregiver_ideology=0.3,
            institutional_hegemony=0.8,
            defines=defines,
            community_tendency=0.1,
        )
        assert with_high_community > base
        assert with_low_community < base

    @pytest.mark.unit
    @pytest.mark.math
    def test_strong_hegemonic_schooling(
        self,
        calc: DefaultCohortDynamicsCalculator,
    ) -> None:
        """Strong institutional hegemony pulls toward dominant ideology.

        When institutional_hegemony=1.0 and caregiver=0.0,
        result reflects institutional weight (0.3 × 1.0 = 0.3 raw).
        """
        defines_no_regression = LifecycleDefines(ideology_regression_coefficient=0.0)
        result = calc.compute_ideology_transmission(
            caregiver_ideology=0.0,
            institutional_hegemony=1.0,
            defines=defines_no_regression,
        )
        # 0.7*0.0 + 0.3*1.0 = 0.3
        assert abs(result - 0.3) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_output_clamped_to_unit_interval(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """Output is always clamped to [0, 1]."""
        result_high = calc.compute_ideology_transmission(
            caregiver_ideology=1.0,
            institutional_hegemony=1.0,
            defines=defines,
            community_tendency=1.0,
        )
        result_low = calc.compute_ideology_transmission(
            caregiver_ideology=0.0,
            institutional_hegemony=0.0,
            defines=defines,
            community_tendency=0.0,
        )
        assert 0.0 <= result_high <= 1.0
        assert 0.0 <= result_low <= 1.0


class TestDifferentialRates:
    """T028: Differential P-phase duration by race/carceral (US5)."""

    @pytest.fixture
    def calc(self) -> DefaultCohortDynamicsCalculator:
        return DefaultCohortDynamicsCalculator()

    @pytest.fixture
    def defines(self) -> LifecycleDefines:
        return LifecycleDefines()

    @pytest.fixture
    def base_state(self) -> DPDState:
        """Standard population state for differential rate tests."""
        return DPDState(
            pop_d=2150.0,
            pop_p=6050.0,
            pop_d_prime=1800.0,
            rate_d_to_p=0.0556,
            rate_p_to_d_prime=0.0213,
            rate_d_prime_to_death=0.039,
            birth_rate=0.0107,
            wealth_d_prime=10_000_000.0,
        )

    @pytest.mark.unit
    @pytest.mark.math
    def test_early_mortality_increases_p_to_d_prime(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        base_state: DPDState,
    ) -> None:
        """Black P→D' rate > White via early_mortality_modifier=1.24."""
        white_state = calc.apply_differential_rates(
            base_state, defines, early_mortality_modifier=1.0
        )
        black_state = calc.apply_differential_rates(
            base_state, defines, early_mortality_modifier=1.24
        )
        assert black_state.rate_p_to_d_prime > white_state.rate_p_to_d_prime

    @pytest.mark.unit
    @pytest.mark.math
    def test_carceral_modifier_increases_exit_rate(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        base_state: DPDState,
    ) -> None:
        """Carceral modifier > 1.0 increases P→D' transition rate."""
        no_carceral = calc.apply_differential_rates(base_state, defines, carceral_modifier=1.0)
        with_carceral = calc.apply_differential_rates(base_state, defines, carceral_modifier=2.8)
        assert with_carceral.rate_p_to_d_prime > no_carceral.rate_p_to_d_prime

    @pytest.mark.unit
    @pytest.mark.math
    def test_combined_modifiers_compound(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        base_state: DPDState,
    ) -> None:
        """Both modifiers compound to increase P→D' rate further."""
        mortality_only = calc.apply_differential_rates(
            base_state, defines, early_mortality_modifier=1.24
        )
        carceral_only = calc.apply_differential_rates(base_state, defines, carceral_modifier=2.8)
        both = calc.apply_differential_rates(
            base_state, defines, early_mortality_modifier=1.24, carceral_modifier=2.8
        )
        assert both.rate_p_to_d_prime > mortality_only.rate_p_to_d_prime
        assert both.rate_p_to_d_prime > carceral_only.rate_p_to_d_prime

    @pytest.mark.unit
    @pytest.mark.math
    def test_modified_rate_capped_at_one(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        base_state: DPDState,
    ) -> None:
        """Extreme modifiers cannot push rate above 1.0."""
        extreme = calc.apply_differential_rates(
            base_state, defines, early_mortality_modifier=50.0, carceral_modifier=50.0
        )
        assert extreme.rate_p_to_d_prime <= 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_modified_rate_non_negative(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        base_state: DPDState,
    ) -> None:
        """Modified rate never goes below 0.0."""
        result = calc.apply_differential_rates(
            base_state, defines, early_mortality_modifier=0.0, carceral_modifier=0.0
        )
        assert result.rate_p_to_d_prime >= 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_no_modifiers_preserves_rate(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
        base_state: DPDState,
    ) -> None:
        """Default modifiers (1.0) preserve original rate."""
        result = calc.apply_differential_rates(
            base_state, defines, early_mortality_modifier=1.0, carceral_modifier=1.0
        )
        assert abs(result.rate_p_to_d_prime - base_state.rate_p_to_d_prime) < 0.0001

    @pytest.mark.unit
    @pytest.mark.math
    def test_differential_rates_compound_dependency_burden(
        self,
        calc: DefaultCohortDynamicsCalculator,
        defines: LifecycleDefines,
    ) -> None:
        """SC-004: Higher P→D' rate compounds into higher dependency burden.

        With differential rates, more P exits to D' → fewer productive workers
        → higher dependency ratio → structural inequality compounds.
        """
        white = DPDState(
            pop_d=2000.0,
            pop_p=6000.0,
            pop_d_prime=2000.0,
            rate_d_to_p=0.055,
            rate_p_to_d_prime=0.021,
            rate_d_prime_to_death=0.039,
            birth_rate=0.011,
            wealth_d_prime=1_000_000.0,
        )
        black = calc.apply_differential_rates(
            white, defines, early_mortality_modifier=1.24, carceral_modifier=2.8
        )

        # Simulate 5 ticks of transitions
        white_state = white
        black_state = black
        for _ in range(5):
            white_state = calc.compute_transitions(white_state, defines)
            black_state = calc.compute_transitions(black_state, defines)

        # Black population has fewer productive workers (shorter P phase)
        assert black_state.pop_p < white_state.pop_p
        # Black population has higher dependency ratio (more D' burden)
        assert black_state.dependency_ratio > white_state.dependency_ratio
