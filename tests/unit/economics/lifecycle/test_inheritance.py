"""Tests for InheritanceCalculator (Feature 030, US3).

Covers Pareto-distributed inheritance at D' terminus, care cost deduction,
dispossession-driven reduction, and Gini coefficient validation.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.lifecycle.inheritance import DefaultInheritanceCalculator
from babylon.domain.economics.lifecycle.types import DPDState, InheritanceFlow


class TestInheritanceCalculator:
    """T019: InheritanceCalculator tests."""

    @pytest.fixture
    def calc(self) -> DefaultInheritanceCalculator:
        return DefaultInheritanceCalculator()

    @pytest.fixture
    def scenario_3_state(self) -> DPDState:
        """Scenario 3: D' cohort of 1000 with $10M aggregate wealth."""
        return DPDState(
            pop_d=2150.0,
            pop_p=6050.0,
            pop_d_prime=1000.0,
            rate_d_to_p=0.0556,
            rate_p_to_d_prime=0.0213,
            rate_d_prime_to_death=0.039,
            birth_rate=0.0107,
            wealth_d_prime=10_000_000.0,
        )

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_3_inheritance_flow(
        self,
        calc: DefaultInheritanceCalculator,
        scenario_3_state: DPDState,
    ) -> None:
        """Scenario 3: 39 deaths from 1000 D' → $390k transferred, $156k care, $234k net."""
        flow = calc.compute_inheritance_flow(
            dpd_state=scenario_3_state,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert isinstance(flow, InheritanceFlow)
        # 39 deaths out of 1000 @ $10M wealth → $390k total
        assert abs(flow.total_transferred - 390_000.0) < 1.0
        # 40% consumed by care
        assert abs(flow.care_consumed - 156_000.0) < 1.0
        # Net = $234k
        assert abs(flow.net_inheritance - 234_000.0) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_scenario_3_gini(
        self,
        calc: DefaultInheritanceCalculator,
        scenario_3_state: DPDState,
    ) -> None:
        """Pareto α=1.5 → Gini = 0.5."""
        flow = calc.compute_inheritance_flow(
            dpd_state=scenario_3_state,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert abs(flow.inheritance_gini - 0.5) < 0.001

    @pytest.mark.unit
    @pytest.mark.math
    def test_care_cost_fraction_deduction(
        self,
        calc: DefaultInheritanceCalculator,
    ) -> None:
        """Care cost fraction consumes expected portion of wealth."""
        state = DPDState(
            pop_d=100.0,
            pop_p=500.0,
            pop_d_prime=100.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.10,
            birth_rate=0.01,
            wealth_d_prime=1_000_000.0,
        )
        flow = calc.compute_inheritance_flow(
            dpd_state=state,
            pareto_alpha=1.5,
            care_cost_fraction=0.6,
        )
        # 10 deaths out of 100 @ $1M → $100k total
        assert abs(flow.total_transferred - 100_000.0) < 1.0
        # 60% care
        assert abs(flow.care_consumed - 60_000.0) < 1.0
        assert abs(flow.net_inheritance - 40_000.0) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_no_deaths_no_inheritance(
        self,
        calc: DefaultInheritanceCalculator,
    ) -> None:
        """Zero deaths → no inheritance flow (None returned)."""
        state = DPDState(
            pop_d=100.0,
            pop_p=500.0,
            pop_d_prime=100.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.0,
            birth_rate=0.01,
            wealth_d_prime=1_000_000.0,
        )
        flow = calc.compute_inheritance_flow(
            dpd_state=state,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow is None

    @pytest.mark.unit
    @pytest.mark.math
    def test_zero_wealth_zero_inheritance(
        self,
        calc: DefaultInheritanceCalculator,
    ) -> None:
        """Zero D' wealth → zero inheritance amounts."""
        state = DPDState(
            pop_d=100.0,
            pop_p=500.0,
            pop_d_prime=100.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.05,
            birth_rate=0.01,
            wealth_d_prime=0.0,
        )
        flow = calc.compute_inheritance_flow(
            dpd_state=state,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        # Deaths occur but no wealth → zero transfer
        assert flow is not None
        assert flow.total_transferred == 0.0
        assert flow.net_inheritance == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_dispossession_reduces_inheritance(
        self,
        calc: DefaultInheritanceCalculator,
    ) -> None:
        """Dispossession reduces D' wealth → reduces inheritance."""
        state_before = DPDState(
            pop_d=100.0,
            pop_p=500.0,
            pop_d_prime=100.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.05,
            birth_rate=0.01,
            wealth_d_prime=1_000_000.0,
        )
        state_after = DPDState(
            pop_d=100.0,
            pop_p=500.0,
            pop_d_prime=100.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.05,
            birth_rate=0.01,
            wealth_d_prime=500_000.0,  # 50% dispossessed
        )
        flow_before = calc.compute_inheritance_flow(
            dpd_state=state_before,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        flow_after = calc.compute_inheritance_flow(
            dpd_state=state_after,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow_before is not None
        assert flow_after is not None
        assert flow_after.net_inheritance < flow_before.net_inheritance
        # Proportional reduction: 50% wealth → 50% inheritance
        assert abs(flow_after.net_inheritance / flow_before.net_inheritance - 0.5) < 0.01

    @pytest.mark.unit
    @pytest.mark.math
    def test_inheritance_gini_exceeds_income_gini(
        self,
        calc: DefaultInheritanceCalculator,
        scenario_3_state: DPDState,
    ) -> None:
        """SC-003: Gini(inheritance) > Gini(income) for standard α."""
        flow = calc.compute_inheritance_flow(
            dpd_state=scenario_3_state,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow is not None
        # Inheritance Gini at α=1.5 is 0.5
        # US income Gini is ~0.485 (from Chetty Table 8 default)
        assert flow.inheritance_gini > 0.485

    @pytest.mark.unit
    @pytest.mark.math
    def test_apply_dispossession_reduction(
        self,
        calc: DefaultInheritanceCalculator,
    ) -> None:
        """Dispossession reduces wealth_d_prime by specified amount."""
        state = DPDState(
            pop_d=100.0,
            pop_p=500.0,
            pop_d_prime=100.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.05,
            birth_rate=0.01,
            wealth_d_prime=1_000_000.0,
        )
        reduced = calc.apply_dispossession_reduction(
            dpd_state=state,
            dispossession_amount=300_000.0,
        )
        assert abs(reduced.wealth_d_prime - 700_000.0) < 1.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_dispossession_floors_at_zero(
        self,
        calc: DefaultInheritanceCalculator,
    ) -> None:
        """Dispossession cannot make wealth negative."""
        state = DPDState(
            pop_d=100.0,
            pop_p=500.0,
            pop_d_prime=100.0,
            rate_d_to_p=0.05,
            rate_p_to_d_prime=0.02,
            rate_d_prime_to_death=0.05,
            birth_rate=0.01,
            wealth_d_prime=100_000.0,
        )
        reduced = calc.apply_dispossession_reduction(
            dpd_state=state,
            dispossession_amount=500_000.0,
        )
        assert reduced.wealth_d_prime == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_higher_alpha_lower_gini(
        self,
        calc: DefaultInheritanceCalculator,
        scenario_3_state: DPDState,
    ) -> None:
        """Higher Pareto α → lower Gini (more equal distribution)."""
        flow_15 = calc.compute_inheritance_flow(
            dpd_state=scenario_3_state,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        flow_20 = calc.compute_inheritance_flow(
            dpd_state=scenario_3_state,
            pareto_alpha=2.0,
            care_cost_fraction=0.4,
        )
        assert flow_15 is not None
        assert flow_20 is not None
        # α=1.5 → Gini=0.5, α=2.0 → Gini=1/3≈0.333
        assert flow_15.inheritance_gini > flow_20.inheritance_gini
