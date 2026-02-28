"""Legitimation calculator for D-P-D' lifecycle bargain (Feature 030, US2).

Computes legitimation index from material conditions, classifies crisis
state, blends with agitation for bifurcation feed, and models pension
default scenarios.

See Also:
    :mod:`babylon.formulas.lifecycle`: Pure formula for legitimation index.
    :mod:`babylon.economics.lifecycle.types`: LegitimationState model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from babylon.economics.lifecycle.types import LegitimationState
from babylon.formulas.lifecycle import compute_legitimation_index
from babylon.models.enums import LegitimationClassification

if TYPE_CHECKING:
    from babylon.config.defines import LifecycleDefines


class LegitimationCalculator(Protocol):
    """Protocol for legitimation index computation."""

    def compute_index(
        self,
        state: LegitimationState,
        defines: LifecycleDefines,
    ) -> float:
        """Compute weighted legitimation index from state components.

        Args:
            state: Legitimation state with five components.
            defines: Lifecycle configuration with weights.

        Returns:
            Legitimation index in [0, 1].
        """
        ...

    def classify_crisis(
        self,
        index: float,
        defines: LifecycleDefines,
    ) -> LegitimationClassification:
        """Classify legitimation crisis state from index value.

        Args:
            index: Legitimation index in [0, 1].
            defines: Lifecycle configuration with thresholds.

        Returns:
            LegitimationClassification (CRISIS, UNSTABLE, or STABLE).
        """
        ...

    def compute_blended_legitimation(
        self,
        lifecycle_legitimation: float,
        agitation_inverse: float,
        blend_weight: float,
    ) -> float:
        """Blend structural legitimation with agitation inverse.

        Args:
            lifecycle_legitimation: Structural legitimation index.
            agitation_inverse: 1 - mean(agitation) from social class nodes.
            blend_weight: Weight for structural component.

        Returns:
            Blended legitimation in [0, 1].
        """
        ...

    def apply_pension_default(
        self,
        state: LegitimationState,
    ) -> LegitimationState:
        """Model pension default by zeroing pension coverage.

        Args:
            state: Current legitimation state.

        Returns:
            New LegitimationState with pension_coverage=0.
        """
        ...


class DefaultLegitimationCalculator:
    """Default implementation of LegitimationCalculator.

    Uses pure formulas from babylon.formulas.lifecycle and
    threshold classification from LifecycleDefines.
    """

    def compute_index(
        self,
        state: LegitimationState,
        defines: LifecycleDefines,
    ) -> float:
        """Compute weighted legitimation index from state components."""
        return compute_legitimation_index(
            pension_coverage=float(state.pension_coverage),
            ss_replacement_rate=float(state.ss_replacement_rate),
            healthcare_security=float(state.healthcare_security),
            home_ownership_rate=float(state.home_ownership_rate),
            retirement_confidence=float(state.retirement_confidence),
            w_pension=defines.legit_w_pension_coverage,
            w_ss=defines.legit_w_ss_replacement,
            w_health=defines.legit_w_healthcare_security,
            w_home=defines.legit_w_home_ownership,
            w_retire=defines.legit_w_retirement_confidence,
        )

    def classify_crisis(
        self,
        index: float,
        defines: LifecycleDefines,
    ) -> LegitimationClassification:
        """Classify legitimation crisis state from index value."""
        if index < defines.legitimation_crisis_threshold:
            return LegitimationClassification.CRISIS
        if index < defines.legitimation_unstable_threshold:
            return LegitimationClassification.UNSTABLE
        return LegitimationClassification.STABLE

    def compute_blended_legitimation(
        self,
        lifecycle_legitimation: float,
        agitation_inverse: float,
        blend_weight: float,
    ) -> float:
        """Blend structural legitimation with agitation inverse."""
        blended = blend_weight * lifecycle_legitimation + (1.0 - blend_weight) * agitation_inverse
        return max(0.0, min(1.0, blended))

    def apply_pension_default(
        self,
        state: LegitimationState,
    ) -> LegitimationState:
        """Model pension default by zeroing pension coverage."""
        return LegitimationState(
            pension_coverage=0.0,
            ss_replacement_rate=state.ss_replacement_rate,
            healthcare_security=state.healthcare_security,
            home_ownership_rate=state.home_ownership_rate,
            retirement_confidence=state.retirement_confidence,
        )


__all__ = ["DefaultLegitimationCalculator", "LegitimationCalculator"]
