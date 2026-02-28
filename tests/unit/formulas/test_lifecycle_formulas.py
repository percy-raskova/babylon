"""Tests for D-P-D' lifecycle circuit formulas (Feature 030).

Tests cover 6 pure functions implementing population flow, dependency ratio,
legitimation index, Pareto Gini, ideology transmission, and shadow subsidy.
"""

from __future__ import annotations

import math

import pytest

from babylon.formulas.lifecycle import (
    compute_dependency_ratio,
    compute_ideology_transmission,
    compute_legitimation_index,
    compute_pareto_gini,
    compute_population_flow,
    compute_shadow_subsidy,
)


class TestComputePopulationFlow:
    """T005: Population flow conservation arithmetic."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_1_conservation(self) -> None:
        """Scenario 1: Basic population flow conserves population."""
        pop_d, pop_p, pop_d_prime = 2150.0, 6050.0, 1800.0
        birth_rate = 0.0107
        rate_d_to_p = 0.0556
        rate_p_to_d_prime = 0.0213
        rate_d_prime_to_death = 0.039

        result = compute_population_flow(
            pop_d=pop_d,
            pop_p=pop_p,
            pop_d_prime=pop_d_prime,
            birth_rate=birth_rate,
            rate_d_to_p=rate_d_to_p,
            rate_p_to_d_prime=rate_p_to_d_prime,
            rate_d_prime_to_death=rate_d_prime_to_death,
        )

        new_d, new_p, new_d_prime, births, deaths = result
        total_old = pop_d + pop_p + pop_d_prime
        total_new = new_d + new_p + new_d_prime
        conservation_error = abs(total_new - total_old - births + deaths) / total_old
        assert conservation_error < 0.001, f"Conservation error: {conservation_error}"

    @pytest.mark.unit
    @pytest.mark.math
    def test_births_from_p_phase(self) -> None:
        """Births are proportional to P-phase population."""
        _, _, _, births, _ = compute_population_flow(
            pop_d=2150.0,
            pop_p=6050.0,
            pop_d_prime=1800.0,
            birth_rate=0.0107,
            rate_d_to_p=0.0556,
            rate_p_to_d_prime=0.0213,
            rate_d_prime_to_death=0.039,
        )
        assert abs(births - 0.0107 * 6050.0) < 0.01

    @pytest.mark.unit
    @pytest.mark.math
    def test_zero_population_edge_case(self) -> None:
        """Zero D population produces no D-to-P flow."""
        new_d, new_p, new_d_prime, births, deaths = compute_population_flow(
            pop_d=0.0,
            pop_p=1000.0,
            pop_d_prime=500.0,
            birth_rate=0.01,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.04,
        )
        assert new_d >= 0.0
        assert new_p >= 0.0
        assert new_d_prime >= 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_negative_populations_clamped(self) -> None:
        """Extreme rates cannot produce negative populations."""
        new_d, new_p, new_d_prime, _, _ = compute_population_flow(
            pop_d=10.0,
            pop_p=10.0,
            pop_d_prime=10.0,
            birth_rate=0.0,
            rate_d_to_p=0.99,
            rate_p_to_d_prime=0.99,
            rate_d_prime_to_death=0.99,
        )
        assert new_d >= 0.0
        assert new_p >= 0.0
        assert new_d_prime >= 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_all_populations_non_negative(self) -> None:
        """All output populations must be non-negative."""
        new_d, new_p, new_d_prime, _, _ = compute_population_flow(
            pop_d=100.0,
            pop_p=0.0,
            pop_d_prime=100.0,
            birth_rate=0.0,
            rate_d_to_p=0.5,
            rate_p_to_d_prime=0.5,
            rate_d_prime_to_death=0.5,
        )
        assert new_d >= 0.0
        assert new_p >= 0.0
        assert new_d_prime >= 0.0


class TestComputeDependencyRatio:
    """T005: Dependency ratio computation."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_standard_case(self) -> None:
        """Standard dependency ratio."""
        ratio = compute_dependency_ratio(pop_d=2150.0, pop_p=6050.0, pop_d_prime=1800.0)
        expected = (2150.0 + 1800.0) / 6050.0
        assert abs(ratio - expected) < 0.0001

    @pytest.mark.unit
    @pytest.mark.math
    def test_zero_p_returns_inf(self) -> None:
        """Zero productive population yields infinite dependency."""
        ratio = compute_dependency_ratio(pop_d=100.0, pop_p=0.0, pop_d_prime=100.0)
        assert math.isinf(ratio)


class TestComputeLegitimationIndex:
    """T005: Weighted legitimation index computation."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_2_value(self) -> None:
        """Scenario 2: Exact legitimation index = 0.6055."""
        index = compute_legitimation_index(
            pension_coverage=0.73,
            ss_replacement_rate=0.43,
            healthcare_security=0.60,
            home_ownership_rate=0.66,
            retirement_confidence=0.50,
            w_home=0.35,
            w_health=0.30,
            w_retire=0.20,
            w_pension=0.10,
            w_ss=0.05,
        )
        assert abs(index - 0.6055) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_all_02_yields_02(self) -> None:
        """Degradation: all 0.2 → index = 0.2 (CRISIS)."""
        index = compute_legitimation_index(
            pension_coverage=0.2,
            ss_replacement_rate=0.2,
            healthcare_security=0.2,
            home_ownership_rate=0.2,
            retirement_confidence=0.2,
            w_home=0.35,
            w_health=0.30,
            w_retire=0.20,
            w_pension=0.10,
            w_ss=0.05,
        )
        assert abs(index - 0.2) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_weight_ordering_matters(self) -> None:
        """Higher-weighted components have more influence on the index."""
        # Home ownership high, everything else low
        index_home_high = compute_legitimation_index(
            pension_coverage=0.1,
            ss_replacement_rate=0.1,
            healthcare_security=0.1,
            home_ownership_rate=0.9,
            retirement_confidence=0.1,
            w_home=0.35,
            w_health=0.30,
            w_retire=0.20,
            w_pension=0.10,
            w_ss=0.05,
        )
        # SS replacement high, everything else low
        index_ss_high = compute_legitimation_index(
            pension_coverage=0.1,
            ss_replacement_rate=0.9,
            healthcare_security=0.1,
            home_ownership_rate=0.1,
            retirement_confidence=0.1,
            w_home=0.35,
            w_health=0.30,
            w_retire=0.20,
            w_pension=0.10,
            w_ss=0.05,
        )
        assert index_home_high > index_ss_high


class TestComputeParetoGini:
    """T005: Pareto Gini coefficient."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_alpha_1_5_gives_0_5(self) -> None:
        """α=1.5 → Gini = 1/(2×1.5 - 1) = 0.5."""
        gini = compute_pareto_gini(alpha=1.5)
        assert abs(gini - 0.5) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_higher_alpha_lower_gini(self) -> None:
        """Higher α means less inequality."""
        gini_low_alpha = compute_pareto_gini(alpha=1.5)
        gini_high_alpha = compute_pareto_gini(alpha=3.0)
        assert gini_high_alpha < gini_low_alpha


class TestComputeIdeologyTransmission:
    """T005: Ideology transmission at D→P transition."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_6_value(self) -> None:
        """Scenario 6: 0.7×0.3 + 0.3×0.8 = 0.45."""
        result = compute_ideology_transmission(
            caregiver_ideology=0.3,
            institutional_hegemony=0.8,
            caregiver_weight=0.7,
            institutional_weight=0.3,
        )
        assert abs(result - 0.45) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_pure_caregiver(self) -> None:
        """All caregiver weight → result equals caregiver ideology."""
        result = compute_ideology_transmission(
            caregiver_ideology=0.3,
            institutional_hegemony=0.8,
            caregiver_weight=1.0,
            institutional_weight=0.0,
        )
        assert abs(result - 0.3) < 0.001


class TestComputeShadowSubsidy:
    """T005: Shadow subsidy always positive."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_positive_subsidy(self) -> None:
        """Shadow subsidy must be positive when there is surplus extraction."""
        subsidy = compute_shadow_subsidy(
            p_g2_labor_value=60000.0,
            wage_paid_for_d_g2=12000.0,
        )
        assert subsidy > 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_zero_labor_value_zero_subsidy(self) -> None:
        """No next-gen labor value means no shadow subsidy."""
        subsidy = compute_shadow_subsidy(
            p_g2_labor_value=0.0,
            wage_paid_for_d_g2=0.0,
        )
        assert subsidy == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_subsidy_equals_difference(self) -> None:
        """Shadow subsidy = value produced - investment cost."""
        subsidy = compute_shadow_subsidy(
            p_g2_labor_value=50000.0,
            wage_paid_for_d_g2=12000.0,
        )
        assert abs(subsidy - 38000.0) < 0.01
