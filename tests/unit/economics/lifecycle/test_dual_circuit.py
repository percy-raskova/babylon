"""Tests for DualCircuitCalculator (Feature 030, US7).

Covers sandwich squeeze, legitimation-driven allocation, dispossession
short-circuit, fertility nexus, and shadow subsidy computation.
"""

from __future__ import annotations

import pytest

from babylon.economics.lifecycle.dual_circuit import DefaultDualCircuitCalculator


class TestDualCircuitCalculator:
    """T016: DualCircuitCalculator tests."""

    @pytest.fixture
    def calc(self) -> DefaultDualCircuitCalculator:
        return DefaultDualCircuitCalculator()

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_7_squeeze_active(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Scenario 7: Wage 50k < demands 57k → squeeze active."""
        result = calc.compute_sandwich_squeeze(
            dependency_ratio=0.65,
            p_phase_wage=50_000.0,
            d_prime_care_cost=15_000.0,
            d_gen2_investment_cost=12_000.0,
            subsistence_cost=30_000.0,
            squeeze_threshold=0.6,
        )
        assert result["shortfall"] < 0.0
        assert abs(result["shortfall"] - (-7_000.0)) < 1.0
        assert result["squeeze_active"]

    @pytest.mark.unit
    @pytest.mark.math
    def test_squeeze_inactive_below_threshold(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Below threshold → no squeeze, full funding."""
        result = calc.compute_sandwich_squeeze(
            dependency_ratio=0.4,
            p_phase_wage=80_000.0,
            d_prime_care_cost=10_000.0,
            d_gen2_investment_cost=10_000.0,
            subsistence_cost=30_000.0,
            squeeze_threshold=0.6,
        )
        assert not result["squeeze_active"]

    @pytest.mark.unit
    @pytest.mark.math
    def test_legitimation_driven_allocation_low(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Low legitimation → prioritize self over D' care."""
        allocation = calc.compute_resource_allocation(
            p_phase_wage=50_000.0,
            subsistence_cost=30_000.0,
            d_prime_cost=15_000.0,
            d_gen2_cost=12_000.0,
            legitimation_index=0.2,
        )
        # Low legitimation: subsistence first, then split remainder
        assert allocation["subsistence"] == 30_000.0
        # D' and D_g2 compete for remaining 20k
        assert allocation["d_prime_funding"] + allocation["d_gen2_funding"] <= 20_000.0 + 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_legitimation_driven_allocation_high(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """High legitimation → bias toward D_g2 investment."""
        allocation = calc.compute_resource_allocation(
            p_phase_wage=80_000.0,
            subsistence_cost=30_000.0,
            d_prime_cost=15_000.0,
            d_gen2_cost=12_000.0,
            legitimation_index=0.8,
        )
        assert allocation["subsistence"] == 30_000.0
        # Enough to fully fund both
        assert allocation["d_prime_funding"] >= 15_000.0 - 1.0
        assert allocation["d_gen2_funding"] >= 12_000.0 - 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_dispossession_short_circuit(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Dispossession hits both circuits simultaneously."""
        d_prime_impact, inheritance_impact = calc.compute_dispossession_effects(
            dispossession_amount=100_000.0,
            d_prime_wealth=500_000.0,
            home_ownership_rate=0.66,
        )
        assert d_prime_impact > 0.0
        assert inheritance_impact > 0.0
        # Both impacts sum to dispossession amount
        assert abs(d_prime_impact + inheritance_impact - 100_000.0) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_fertility_nexus_crisis(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Legitimation crisis → lower fertility, higher consciousness."""
        adj_fertility, ideology_shift = calc.apply_legitimation_fertility_nexus(
            legitimation_index=0.2,
            baseline_fertility_rate=0.0107,
            crisis_threshold=0.3,
        )
        assert adj_fertility < 0.0107
        assert adj_fertility >= 0.0
        assert ideology_shift > 0.0  # Shift toward class consciousness

    @pytest.mark.unit
    @pytest.mark.math
    def test_fertility_nexus_stable(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Stable legitimation → no fertility/ideology change."""
        adj_fertility, ideology_shift = calc.apply_legitimation_fertility_nexus(
            legitimation_index=0.6,
            baseline_fertility_rate=0.0107,
            crisis_threshold=0.3,
        )
        assert abs(adj_fertility - 0.0107) < 0.0001
        assert ideology_shift == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_shadow_subsidy_positive(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Shadow subsidy must always be positive (SC-014)."""
        subsidy = calc.compute_shadow_subsidy(
            p_g2_labor_value=60_000.0,
            wage_paid_for_d_g2=12_000.0,
        )
        assert subsidy > 0.0
        assert abs(subsidy - 48_000.0) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_shadow_subsidy_zero_investment(
        self,
        calc: DefaultDualCircuitCalculator,
    ) -> None:
        """Zero D_g2 investment → full labor value is shadow subsidy."""
        subsidy = calc.compute_shadow_subsidy(
            p_g2_labor_value=60_000.0,
            wage_paid_for_d_g2=0.0,
        )
        assert abs(subsidy - 60_000.0) < 1.0
