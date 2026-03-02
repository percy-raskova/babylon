"""Tests for class-differentiated inheritance and crisis dispossession (Feature 038, US5).

Feature: 038-unified-class-system
TDD Phase: RED then GREEN

Tests cover:
- T040: Class-differentiated inheritance scaling by ClassPosition
- T041: Crisis dispossession (LA->PROLETARIAT via wealth destruction)
"""

from __future__ import annotations

import pytest

from babylon.economics.lifecycle.types import DPDState
from babylon.economics.melt.types import ClassPosition


@pytest.fixture
def base_dpd_state() -> DPDState:
    """Standard D' cohort for inheritance tests."""
    return DPDState(
        pop_d=2000.0,
        pop_p=6000.0,
        pop_d_prime=1000.0,
        rate_d_to_p=0.0556,
        rate_p_to_d_prime=0.0213,
        rate_d_prime_to_death=0.05,
        birth_rate=0.0107,
        wealth_d_prime=5_000_000.0,
    )


class TestClassDifferentiatedInheritance:
    """T040: Inheritance amounts differentiated by ClassPosition."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_la_transfers_equity(self, base_dpd_state: DPDState) -> None:
        """LA households transfer substantial equity (home ownership wealth)."""
        from babylon.economics.lifecycle.inheritance import (
            DefaultInheritanceCalculator,
        )

        calc = DefaultInheritanceCalculator()
        flow = calc.compute_class_aware_inheritance(
            dpd_state=base_dpd_state,
            class_position=ClassPosition.LABOR_ARISTOCRACY,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow is not None
        assert flow.net_inheritance > 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_proletariat_transfers_near_zero(self, base_dpd_state: DPDState) -> None:
        """PROLETARIAT households transfer near-zero (no accumulated wealth)."""
        from babylon.economics.lifecycle.inheritance import (
            DefaultInheritanceCalculator,
        )

        calc = DefaultInheritanceCalculator()
        flow_prol = calc.compute_class_aware_inheritance(
            dpd_state=base_dpd_state,
            class_position=ClassPosition.PROLETARIAT,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        flow_la = calc.compute_class_aware_inheritance(
            dpd_state=base_dpd_state,
            class_position=ClassPosition.LABOR_ARISTOCRACY,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow_prol is not None
        assert flow_la is not None
        # Proletariat inheritance should be much less than LA
        assert flow_prol.net_inheritance < flow_la.net_inheritance * 0.2

    @pytest.mark.unit
    @pytest.mark.math
    def test_foreclosed_la_transfers_zero(self, base_dpd_state: DPDState) -> None:
        """Foreclosed LA household transfers zero (inheritance mechanism severed)."""
        from babylon.economics.lifecycle.inheritance import (
            DefaultInheritanceCalculator,
        )

        calc = DefaultInheritanceCalculator()
        flow = calc.compute_class_aware_inheritance(
            dpd_state=base_dpd_state,
            class_position=ClassPosition.LABOR_ARISTOCRACY,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
            foreclosed=True,
        )
        assert flow is not None
        assert flow.net_inheritance == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_bourgeoisie_transfers_most(self, base_dpd_state: DPDState) -> None:
        """BOURGEOISIE transfers the most inheritance (full capital estate)."""
        from babylon.economics.lifecycle.inheritance import (
            DefaultInheritanceCalculator,
        )

        calc = DefaultInheritanceCalculator()
        flow_bourg = calc.compute_class_aware_inheritance(
            dpd_state=base_dpd_state,
            class_position=ClassPosition.BOURGEOISIE,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        flow_la = calc.compute_class_aware_inheritance(
            dpd_state=base_dpd_state,
            class_position=ClassPosition.LABOR_ARISTOCRACY,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow_bourg is not None
        assert flow_la is not None
        assert flow_bourg.net_inheritance > flow_la.net_inheritance

    @pytest.mark.unit
    @pytest.mark.math
    def test_lumpen_transfers_zero(self, base_dpd_state: DPDState) -> None:
        """LUMPENPROLETARIAT transfers zero (fully excluded, no wealth)."""
        from babylon.economics.lifecycle.inheritance import (
            DefaultInheritanceCalculator,
        )

        calc = DefaultInheritanceCalculator()
        flow = calc.compute_class_aware_inheritance(
            dpd_state=base_dpd_state,
            class_position=ClassPosition.LUMPENPROLETARIAT,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow is not None
        assert flow.net_inheritance == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_class_ordering_preserves_monotonicity(self, base_dpd_state: DPDState) -> None:
        """Inheritance ordering: BOURG > PB > LA > PROL > LUMPEN."""
        from babylon.economics.lifecycle.inheritance import (
            DefaultInheritanceCalculator,
        )

        calc = DefaultInheritanceCalculator()
        results: dict[ClassPosition, float] = {}
        for cp in ClassPosition:
            flow = calc.compute_class_aware_inheritance(
                dpd_state=base_dpd_state,
                class_position=cp,
                pareto_alpha=1.5,
                care_cost_fraction=0.4,
            )
            results[cp] = flow.net_inheritance if flow is not None else 0.0

        assert results[ClassPosition.BOURGEOISIE] > results[ClassPosition.PETIT_BOURGEOISIE]
        assert results[ClassPosition.PETIT_BOURGEOISIE] > results[ClassPosition.LABOR_ARISTOCRACY]
        assert results[ClassPosition.LABOR_ARISTOCRACY] > results[ClassPosition.PROLETARIAT]
        assert results[ClassPosition.PROLETARIAT] >= results[ClassPosition.LUMPENPROLETARIAT]

    @pytest.mark.unit
    @pytest.mark.math
    def test_existing_compute_inheritance_flow_unchanged(self, base_dpd_state: DPDState) -> None:
        """Existing compute_inheritance_flow method still works (backward compat)."""
        from babylon.economics.lifecycle.inheritance import (
            DefaultInheritanceCalculator,
        )

        calc = DefaultInheritanceCalculator()
        flow = calc.compute_inheritance_flow(
            dpd_state=base_dpd_state,
            pareto_alpha=1.5,
            care_cost_fraction=0.4,
        )
        assert flow is not None
        assert flow.net_inheritance > 0.0


class TestCrisisDispossession:
    """T041: Crisis dispossession (LA->PROLETARIAT via wealth destruction)."""

    @pytest.mark.unit
    @pytest.mark.math
    def test_foreclosure_destroys_wealth(self) -> None:
        """Foreclosure event destroys household wealth."""
        from babylon.economics.lifecycle.dispossession import (
            compute_crisis_dispossession,
        )

        result = compute_crisis_dispossession(
            household_wealth=250_000.0,
            foreclosure_rate=0.10,
        )
        assert result.wealth_destroyed > 0.0
        assert result.remaining_wealth < 250_000.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_community_modifiable_rate(self) -> None:
        """Community membership modifies dispossession rate (racialized targeting)."""
        from babylon.economics.lifecycle.dispossession import (
            compute_crisis_dispossession,
        )

        # Base rate
        base = compute_crisis_dispossession(
            household_wealth=250_000.0,
            foreclosure_rate=0.10,
        )
        # Elevated rate for targeted community
        targeted = compute_crisis_dispossession(
            household_wealth=250_000.0,
            foreclosure_rate=0.10,
            community_targeting_multiplier=2.5,
        )
        assert targeted.wealth_destroyed > base.wealth_destroyed

    @pytest.mark.unit
    @pytest.mark.math
    def test_full_foreclosure_zeroes_wealth(self) -> None:
        """100% foreclosure rate zeroes out wealth."""
        from babylon.economics.lifecycle.dispossession import (
            compute_crisis_dispossession,
        )

        result = compute_crisis_dispossession(
            household_wealth=250_000.0,
            foreclosure_rate=1.0,
        )
        assert result.remaining_wealth == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_zero_foreclosure_preserves_wealth(self) -> None:
        """Zero foreclosure rate preserves all wealth."""
        from babylon.economics.lifecycle.dispossession import (
            compute_crisis_dispossession,
        )

        result = compute_crisis_dispossession(
            household_wealth=250_000.0,
            foreclosure_rate=0.0,
        )
        assert result.remaining_wealth == pytest.approx(250_000.0)
        assert result.wealth_destroyed == 0.0

    @pytest.mark.unit
    @pytest.mark.math
    def test_la_to_proletariat_transition(self) -> None:
        """Crisis dispossession can move LA household below 50th percentile threshold."""
        from babylon.economics.lifecycle.dispossession import (
            compute_crisis_dispossession,
        )

        # LA household with 60th percentile wealth equivalent
        result = compute_crisis_dispossession(
            household_wealth=200_000.0,
            foreclosure_rate=0.80,
        )
        # After 80% foreclosure, remaining wealth is much lower
        assert result.remaining_wealth < 200_000.0 * 0.50
        assert result.class_position_change_indicated

    @pytest.mark.unit
    @pytest.mark.math
    def test_dispossession_result_is_frozen(self) -> None:
        """DispossessionResult model is immutable."""
        from pydantic import ValidationError

        from babylon.economics.lifecycle.dispossession import (
            compute_crisis_dispossession,
        )

        result = compute_crisis_dispossession(
            household_wealth=250_000.0,
            foreclosure_rate=0.10,
        )
        with pytest.raises(ValidationError):
            result.remaining_wealth = 0.0  # type: ignore[misc]
