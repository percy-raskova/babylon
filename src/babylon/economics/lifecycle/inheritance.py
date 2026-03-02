"""Inheritance calculator for D' terminus wealth transfer (Feature 030, US3).

Models Pareto-distributed intergenerational wealth transfer when D' cohort
members die. Deducts end-of-life care costs before computing net inheritance.

Feature 038 Extension:
    Class-aware inheritance scaling differentiates transfer amounts by
    ClassPosition. LA households transfer home equity, PROLETARIAT near-zero,
    LUMPENPROLETARIAT zero. Foreclosure severs the inheritance mechanism.

See Also:
    :mod:`babylon.formulas.lifecycle`: compute_pareto_gini pure function.
    ``specs/030-dpd-lifecycle-circuit/spec.md`` FR-007, FR-008, FR-013.
    ``specs/038-unified-class-system/spec.md`` FR-008, FR-010.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from babylon.economics.lifecycle.types import DPDState, InheritanceFlow
from babylon.formulas.lifecycle import compute_pareto_gini

if TYPE_CHECKING:
    from babylon.economics.melt.types import ClassPosition


class InheritanceCalculator(Protocol):
    """Protocol for inheritance flow computation."""

    def compute_inheritance_flow(
        self,
        dpd_state: DPDState,
        pareto_alpha: float,
        care_cost_fraction: float,
    ) -> InheritanceFlow | None:
        """Compute inheritance from D' deaths.

        Args:
            dpd_state: Current population/wealth state.
            pareto_alpha: Pareto shape parameter for wealth distribution.
            care_cost_fraction: Fraction of wealth consumed by D' care.

        Returns:
            InheritanceFlow if deaths > 0, else None.
        """
        ...

    def compute_class_aware_inheritance(
        self,
        dpd_state: DPDState,
        class_position: ClassPosition,
        pareto_alpha: float,
        care_cost_fraction: float,
        *,
        foreclosed: bool = False,
    ) -> InheritanceFlow | None:
        """Compute inheritance scaled by class position (FR-008).

        Args:
            dpd_state: Current population/wealth state.
            class_position: ClassPosition of the household.
            pareto_alpha: Pareto shape parameter for wealth distribution.
            care_cost_fraction: Fraction of wealth consumed by D' care.
            foreclosed: If True, inheritance mechanism is severed.

        Returns:
            InheritanceFlow scaled by class position, or None if no deaths.
        """
        ...

    def apply_dispossession_reduction(
        self,
        dpd_state: DPDState,
        dispossession_amount: float,
    ) -> DPDState:
        """Reduce D' wealth by dispossession amount (FR-008).

        Args:
            dpd_state: Current state.
            dispossession_amount: Amount dispossessed (foreclosure, etc.).

        Returns:
            New DPDState with reduced wealth_d_prime (floored at 0).
        """
        ...


# Class-position scaling factors for inheritance.
# BOURGEOISIE gets full estate, LA gets home equity (primary vehicle),
# PB gets significant capital, PROLETARIAT minimal, LUMPEN zero.
_CLASS_INHERITANCE_SCALE: dict[str, float] = {
    "BOURGEOISIE": 1.0,
    "PETIT_BOURGEOISIE": 0.7,
    "LABOR_ARISTOCRACY": 0.5,
    "PROLETARIAT": 0.05,
    "LUMPENPROLETARIAT": 0.0,
}


class DefaultInheritanceCalculator:
    """Default implementation of InheritanceCalculator.

    Implements FR-007 (intergenerational wealth transfer), FR-008
    (dispossession reduction), and FR-013 (inheritance Gini).
    """

    def compute_inheritance_flow(
        self,
        dpd_state: DPDState,
        pareto_alpha: float,
        care_cost_fraction: float,
    ) -> InheritanceFlow | None:
        """Compute inheritance from D' deaths.

        Deaths = pop_d_prime × rate_d_prime_to_death.
        Wealth proportional to dying fraction transfers, minus care costs.
        Gini from Pareto distribution shape parameter.
        """
        deaths = dpd_state.pop_d_prime * dpd_state.rate_d_prime_to_death
        if deaths <= 0.0:
            return None

        # Proportional wealth of dying cohort
        dying_fraction = deaths / dpd_state.pop_d_prime if dpd_state.pop_d_prime > 0.0 else 0.0
        total_transferred = dying_fraction * float(dpd_state.wealth_d_prime)

        # Care costs consumed before inheritance
        care_consumed = care_cost_fraction * total_transferred
        net_inheritance = total_transferred - care_consumed

        # Gini from Pareto distribution
        inheritance_gini = compute_pareto_gini(alpha=pareto_alpha)

        return InheritanceFlow(
            total_transferred=total_transferred,
            care_consumed=care_consumed,
            net_inheritance=net_inheritance,
            inheritance_gini=inheritance_gini,
        )

    def compute_class_aware_inheritance(
        self,
        dpd_state: DPDState,
        class_position: ClassPosition,
        pareto_alpha: float,
        care_cost_fraction: float,
        *,
        foreclosed: bool = False,
    ) -> InheritanceFlow | None:
        """Compute inheritance scaled by class position.

        Foreclosure severs the inheritance mechanism entirely (returns zero).
        Otherwise, the base inheritance is scaled by a class-position factor:
        BOURGEOISIE=1.0, PB=0.7, LA=0.5, PROLETARIAT=0.05, LUMPEN=0.0.
        """
        # Compute base flow first
        base_flow = self.compute_inheritance_flow(
            dpd_state=dpd_state,
            pareto_alpha=pareto_alpha,
            care_cost_fraction=care_cost_fraction,
        )
        if base_flow is None:
            return None

        # Foreclosure severs the inheritance mechanism
        if foreclosed:
            return InheritanceFlow(
                total_transferred=base_flow.total_transferred,
                care_consumed=base_flow.total_transferred,
                net_inheritance=0.0,
                inheritance_gini=base_flow.inheritance_gini,
            )

        # Scale by class position
        scale = _CLASS_INHERITANCE_SCALE.get(class_position.name, 0.0)
        scaled_net = base_flow.net_inheritance * scale
        # Care consumed absorbs the rest (class-mediated care/debt burden)
        scaled_care = base_flow.total_transferred - scaled_net

        return InheritanceFlow(
            total_transferred=base_flow.total_transferred,
            care_consumed=scaled_care,
            net_inheritance=scaled_net,
            inheritance_gini=base_flow.inheritance_gini,
        )

    def apply_dispossession_reduction(
        self,
        dpd_state: DPDState,
        dispossession_amount: float,
    ) -> DPDState:
        """Reduce D' wealth by dispossession amount, floored at zero."""
        new_wealth = max(0.0, float(dpd_state.wealth_d_prime) - dispossession_amount)
        return dpd_state.model_copy(update={"wealth_d_prime": new_wealth})


__all__ = ["DefaultInheritanceCalculator", "InheritanceCalculator"]
