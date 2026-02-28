"""Tests for CohortDynamicsCalculator (Feature 030, US1).

Covers population conservation, births computation, edge cases,
and subsistence burden calculation.
"""

from __future__ import annotations

import math

import pytest

from babylon.config.defines import LifecycleDefines
from babylon.economics.lifecycle.cohort_dynamics import DefaultCohortDynamicsCalculator
from babylon.economics.lifecycle.types import DPDState


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
