"""Cohort dynamics calculator for D-P-D' lifecycle transitions.

Feature: 030-dpd-lifecycle-circuit (US1, US4, US5)

Protocol + Default implementation for population cohort transitions
across the three lifecycle phases.

See Also:
    :mod:`babylon.formulas.lifecycle`: Pure formulas used by this calculator.
    :mod:`babylon.economics.lifecycle.types`: DPDState model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from babylon.economics.lifecycle.types import DPDState
from babylon.formulas.lifecycle import (
    compute_ideology_transmission,
    compute_population_flow,
)

if TYPE_CHECKING:
    from babylon.config.defines import LifecycleDefines


class CohortDynamicsCalculator(Protocol):
    """Protocol for population cohort transition computation."""

    def compute_transitions(
        self,
        dpd_state: DPDState,
        defines: LifecycleDefines,
    ) -> DPDState:
        """Compute one-tick population transitions.

        Args:
            dpd_state: Current population state.
            defines: Lifecycle configuration parameters.

        Returns:
            New DPDState after transitions.
        """
        ...

    def verify_conservation(
        self,
        old: DPDState,
        new: DPDState,
        tolerance: float = 0.001,
    ) -> bool:
        """Verify population conservation within tolerance.

        Args:
            old: Previous tick state.
            new: Current tick state.
            tolerance: Maximum relative error allowed.

        Returns:
            True if conservation holds.
        """
        ...

    def compute_subsistence_burden(
        self,
        dependency_ratio: float,
        base_subsistence: float,
    ) -> float:
        """Compute subsistence burden scaled by dependency ratio.

        Args:
            dependency_ratio: (pop_D + pop_D') / pop_P.
            base_subsistence: Base per-capita subsistence cost.

        Returns:
            Adjusted subsistence burden.
        """
        ...

    def compute_ideology_transmission(
        self,
        caregiver_ideology: float,
        institutional_hegemony: float,
        defines: LifecycleDefines,
        community_tendency: float | None = None,
    ) -> float:
        """Compute ideology transmitted at D→P transition.

        Args:
            caregiver_ideology: Caregiver consciousness level.
            institutional_hegemony: Institutional hegemonic pressure.
            defines: Lifecycle configuration.
            community_tendency: Optional community ideological tendency.

        Returns:
            Transmitted ideology value.
        """
        ...

    def apply_differential_rates(
        self,
        dpd_state: DPDState,
        defines: LifecycleDefines,
        *,
        early_mortality_modifier: float = 1.0,
        carceral_modifier: float = 1.0,
    ) -> DPDState:
        """Apply racial/carceral differential rates to transitions.

        Args:
            dpd_state: Current population state.
            defines: Lifecycle configuration.
            early_mortality_modifier: Multiplier on P→D' transition.
            carceral_modifier: Multiplier on P→D' via incarceration.

        Returns:
            Modified DPDState with differential rates applied.
        """
        ...


class DefaultCohortDynamicsCalculator:
    """Default implementation of CohortDynamicsCalculator.

    Uses pure formulas from babylon.formulas.lifecycle for population
    flow computation and ideology transmission.
    """

    def compute_transitions(
        self,
        dpd_state: DPDState,
        defines: LifecycleDefines,
    ) -> DPDState:
        """Compute one-tick population transitions."""
        # defines reserved for future phase-specific rate adjustments
        _ = defines
        new_d, new_p, new_d_prime, births, deaths = compute_population_flow(
            pop_d=dpd_state.pop_d,
            pop_p=dpd_state.pop_p,
            pop_d_prime=dpd_state.pop_d_prime,
            birth_rate=dpd_state.birth_rate,
            rate_d_to_p=dpd_state.rate_d_to_p,
            rate_p_to_d_prime=dpd_state.rate_p_to_d_prime,
            rate_d_prime_to_death=dpd_state.rate_d_prime_to_death,
        )

        # Compute new D' wealth: proportionally reduced by deaths
        old_total = dpd_state.pop_d_prime
        wealth_d_prime = dpd_state.wealth_d_prime
        if old_total > 0.0 and deaths > 0.0:
            surviving_fraction = max(0.0, 1.0 - deaths / old_total)
            wealth_d_prime = wealth_d_prime * surviving_fraction

        return DPDState(
            pop_d=new_d,
            pop_p=new_p,
            pop_d_prime=new_d_prime,
            rate_d_to_p=dpd_state.rate_d_to_p,
            rate_p_to_d_prime=dpd_state.rate_p_to_d_prime,
            rate_d_prime_to_death=dpd_state.rate_d_prime_to_death,
            birth_rate=dpd_state.birth_rate,
            wealth_d_prime=max(0.0, wealth_d_prime),
        )

    def verify_conservation(
        self,
        old: DPDState,
        new: DPDState,
        tolerance: float = 0.001,
    ) -> bool:
        """Verify population conservation within tolerance."""
        births = old.birth_rate * old.pop_p
        deaths = old.rate_d_prime_to_death * old.pop_d_prime
        old_total = old.total_population
        if old_total == 0.0:
            return True
        expected = old_total + births - deaths
        actual = new.total_population
        return abs(actual - expected) / old_total < tolerance

    def compute_subsistence_burden(
        self,
        dependency_ratio: float,
        base_subsistence: float,
    ) -> float:
        """Compute subsistence burden scaled by dependency ratio."""
        import math

        if math.isinf(dependency_ratio):
            return base_subsistence * 10.0  # Cap at 10x
        return base_subsistence * (1.0 + dependency_ratio)

    def compute_ideology_transmission(
        self,
        caregiver_ideology: float,
        institutional_hegemony: float,
        defines: LifecycleDefines,
        community_tendency: float | None = None,
    ) -> float:
        """Compute ideology transmitted at D→P transition."""
        raw = compute_ideology_transmission(
            caregiver_ideology=caregiver_ideology,
            institutional_hegemony=institutional_hegemony,
            caregiver_weight=defines.ideology_caregiver_weight,
            institutional_weight=defines.ideology_institutional_weight,
        )

        # Apply regression toward mean
        r = defines.ideology_regression_coefficient
        if r > 0.0:
            raw = raw * (1.0 - r) + 0.5 * r

        # Community tendency amplification
        if community_tendency is not None:
            raw = raw + 0.1 * (community_tendency - raw)

        return max(0.0, min(1.0, raw))

    def apply_differential_rates(
        self,
        dpd_state: DPDState,
        defines: LifecycleDefines,
        *,
        early_mortality_modifier: float = 1.0,
        carceral_modifier: float = 1.0,
    ) -> DPDState:
        """Apply racial/carceral differential rates."""
        # defines reserved for future covariate adjustments
        _ = defines
        # Modify P→D' rate with mortality and carceral modifiers
        base_p_to_d_prime = dpd_state.rate_p_to_d_prime
        # Carceral modifier adds a premature exit channel
        carceral_addition = base_p_to_d_prime * (carceral_modifier - 1.0) * 0.1
        modified_rate = base_p_to_d_prime * early_mortality_modifier + carceral_addition
        modified_rate = min(1.0, max(0.0, modified_rate))

        return DPDState(
            pop_d=dpd_state.pop_d,
            pop_p=dpd_state.pop_p,
            pop_d_prime=dpd_state.pop_d_prime,
            rate_d_to_p=dpd_state.rate_d_to_p,
            rate_p_to_d_prime=modified_rate,
            rate_d_prime_to_death=dpd_state.rate_d_prime_to_death,
            birth_rate=dpd_state.birth_rate,
            wealth_d_prime=dpd_state.wealth_d_prime,
        )


__all__ = ["CohortDynamicsCalculator", "DefaultCohortDynamicsCalculator"]
