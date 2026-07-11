"""Dual circuit interference calculator for D-P-D' x P-D-P' (Feature 030, US7).

Computes resource competition, dispossession short-circuit effects,
legitimation-fertility nexus, sandwich squeeze, and shadow subsidy.

See Also:
    :mod:`babylon.formulas.lifecycle`: compute_shadow_subsidy pure function.
    ``specs/030-dpd-lifecycle-circuit/spec.md`` FR-020 through FR-023.
"""

from __future__ import annotations

from typing import Protocol

from babylon.formulas.lifecycle import compute_shadow_subsidy as _compute_shadow_subsidy


class DualCircuitCalculator(Protocol):
    """Protocol for dual-circuit interference computation."""

    def compute_sandwich_squeeze(
        self,
        dependency_ratio: float,
        p_phase_wage: float,
        d_prime_care_cost: float,
        d_gen2_investment_cost: float,
        subsistence_cost: float,
        squeeze_threshold: float,
    ) -> dict[str, object]:
        """Compute sandwich squeeze when dependency exceeds threshold.

        Args:
            dependency_ratio: (pop_D + pop_D') / pop_P.
            p_phase_wage: Annual P-phase income.
            d_prime_care_cost: Annual D' care cost.
            d_gen2_investment_cost: Annual D_g2 child investment.
            subsistence_cost: Base subsistence cost.
            squeeze_threshold: Dependency ratio threshold.

        Returns:
            Dict with shortfall, squeeze_active, allocation details.
        """
        ...

    def compute_resource_allocation(
        self,
        p_phase_wage: float,
        subsistence_cost: float,
        d_prime_cost: float,
        d_gen2_cost: float,
        legitimation_index: float,
    ) -> dict[str, float]:
        """Allocate P-phase resources based on legitimation signal.

        Args:
            p_phase_wage: Annual P-phase income.
            subsistence_cost: Non-negotiable subsistence.
            d_prime_cost: D' care obligation.
            d_gen2_cost: Next-gen investment.
            legitimation_index: Legitimation index [0, 1].

        Returns:
            Dict with subsistence, d_prime_funding, d_gen2_funding, shortfall.
        """
        ...

    def compute_dispossession_effects(
        self,
        dispossession_amount: float,
        d_prime_wealth: float,
        home_ownership_rate: float,
    ) -> tuple[float, float]:
        """Partition dispossession across both circuits.

        Args:
            dispossession_amount: Total amount dispossessed.
            d_prime_wealth: Current D' wealth.
            home_ownership_rate: Home ownership fraction.

        Returns:
            (d_prime_impact, inheritance_impact) summing to dispossession.
        """
        ...

    def apply_legitimation_fertility_nexus(
        self,
        legitimation_index: float,
        baseline_fertility_rate: float,
        crisis_threshold: float,
    ) -> tuple[float, float]:
        """Adjust fertility and ideology when legitimation drops.

        Args:
            legitimation_index: Current legitimation index.
            baseline_fertility_rate: Base fertility rate.
            crisis_threshold: Threshold below which nexus activates.

        Returns:
            (adjusted_fertility, ideology_shift).
        """
        ...

    def compute_shadow_subsidy(
        self,
        p_g2_labor_value: float,
        wage_paid_for_d_g2: float,
    ) -> float:
        """Compute generational shadow subsidy.

        Args:
            p_g2_labor_value: Value of P_g2 labor-power.
            wage_paid_for_d_g2: Wages paid toward D_g2 socialization.

        Returns:
            Shadow subsidy (always positive).
        """
        ...


class DefaultDualCircuitCalculator:
    """Default implementation of DualCircuitCalculator.

    Implements FR-020 through FR-023 for dual-circuit interference
    between D-P-D' (lifecycle reproduction) and P-D-P' (class
    reproduction) circuits.
    """

    def compute_sandwich_squeeze(
        self,
        dependency_ratio: float,
        p_phase_wage: float,
        d_prime_care_cost: float,
        d_gen2_investment_cost: float,
        subsistence_cost: float,
        squeeze_threshold: float,
    ) -> dict[str, object]:
        """Compute sandwich squeeze when dependency exceeds threshold."""
        total_demands = subsistence_cost + d_prime_care_cost + d_gen2_investment_cost
        shortfall = p_phase_wage - total_demands
        squeeze_active = dependency_ratio > squeeze_threshold and shortfall < 0.0

        return {
            "total_demands": total_demands,
            "shortfall": shortfall,
            "squeeze_active": squeeze_active,
            "dependency_ratio": dependency_ratio,
        }

    def compute_resource_allocation(
        self,
        p_phase_wage: float,
        subsistence_cost: float,
        d_prime_cost: float,
        d_gen2_cost: float,
        legitimation_index: float,
    ) -> dict[str, float]:
        """Allocate P-phase resources based on legitimation signal.

        Subsistence is always first priority. Remaining funds split
        between D' care and D_g2 investment based on legitimation.

        High legitimation (>= 0.5): bias toward D_g2 (future investment)
        Low legitimation (< 0.3): bias toward self-preservation (D' cut)
        """
        # Subsistence is non-negotiable
        subsistence_actual = min(p_phase_wage, subsistence_cost)
        remaining = max(0.0, p_phase_wage - subsistence_actual)

        total_care = d_prime_cost + d_gen2_cost
        if total_care <= 0.0 or remaining <= 0.0:
            return {
                "subsistence": subsistence_actual,
                "d_prime_funding": 0.0,
                "d_gen2_funding": 0.0,
                "shortfall": p_phase_wage - (subsistence_cost + d_prime_cost + d_gen2_cost),
            }

        # Legitimation determines allocation bias
        if legitimation_index >= 0.5:
            # High legitimation: D' promise credible, invest in next gen
            d_gen2_share = 0.6
        elif legitimation_index >= 0.3:
            # Unstable: balanced
            d_gen2_share = 0.4
        else:
            # Crisis: prioritize self (D' care = preserving own future)
            d_gen2_share = 0.2

        d_prime_share = 1.0 - d_gen2_share

        # Allocate remaining to each, capped at actual cost
        d_prime_funding = min(remaining * d_prime_share, d_prime_cost)
        d_gen2_funding = min(remaining * d_gen2_share, d_gen2_cost)

        # If either is under-funded and the other has surplus, redistribute
        d_prime_surplus = max(0.0, remaining * d_prime_share - d_prime_cost)
        d_gen2_surplus = max(0.0, remaining * d_gen2_share - d_gen2_cost)
        d_prime_funding = min(d_prime_funding + d_gen2_surplus, d_prime_cost)
        d_gen2_funding = min(d_gen2_funding + d_prime_surplus, d_gen2_cost)

        shortfall = p_phase_wage - (subsistence_cost + d_prime_cost + d_gen2_cost)

        return {
            "subsistence": subsistence_actual,
            "d_prime_funding": d_prime_funding,
            "d_gen2_funding": d_gen2_funding,
            "shortfall": shortfall,
        }

    def compute_dispossession_effects(
        self,
        dispossession_amount: float,
        d_prime_wealth: float,
        home_ownership_rate: float,
    ) -> tuple[float, float]:
        """Partition dispossession across D-P-D' and P-D-P' circuits.

        Home ownership fraction determines the split: the portion tied
        to home equity hits inheritance (P-D-P'), the rest hits D'
        security (D-P-D').
        """
        # d_prime_wealth reserved for wealth-proportional dispossession scaling
        _ = d_prime_wealth
        if dispossession_amount <= 0.0:
            return (0.0, 0.0)

        # Home equity fraction goes to inheritance impact
        inheritance_share = min(1.0, max(0.0, home_ownership_rate))
        inheritance_impact = dispossession_amount * inheritance_share
        d_prime_impact = dispossession_amount * (1.0 - inheritance_share)

        return (d_prime_impact, inheritance_impact)

    def apply_legitimation_fertility_nexus(
        self,
        legitimation_index: float,
        baseline_fertility_rate: float,
        crisis_threshold: float,
    ) -> tuple[float, float]:
        """Adjust fertility and ideology shift when legitimation drops.

        Below crisis threshold: fertility declines proportionally,
        and ideology shifts toward class consciousness.
        """
        if legitimation_index >= crisis_threshold:
            return (baseline_fertility_rate, 0.0)

        # Deficit proportional to how far below threshold
        deficit = crisis_threshold - legitimation_index
        deficit_fraction = min(1.0, deficit / crisis_threshold)

        # Fertility declines proportionally (max 50% reduction)
        fertility_reduction = 0.5 * deficit_fraction
        adjusted_fertility = max(0.0, baseline_fertility_rate * (1.0 - fertility_reduction))

        # Ideology shifts toward class consciousness proportionally
        ideology_shift = 0.1 * deficit_fraction

        return (adjusted_fertility, ideology_shift)

    def compute_shadow_subsidy(
        self,
        p_g2_labor_value: float,
        wage_paid_for_d_g2: float,
    ) -> float:
        """Compute generational shadow subsidy using pure formula."""
        return _compute_shadow_subsidy(
            p_g2_labor_value=p_g2_labor_value,
            wage_paid_for_d_g2=wage_paid_for_d_g2,
        )


__all__ = ["DefaultDualCircuitCalculator", "DualCircuitCalculator"]
