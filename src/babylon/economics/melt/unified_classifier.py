"""Unified class position classifier with dual-criteria validation (Feature 038).

This module wraps the existing DefaultClassPositionClassifier with:
1. Optional community filtration (FR-003, FR-004) via apply_filtration()
2. Dual-criteria validation (FR-002) comparing accounting vs wealth criteria
3. CALIBRATION_DISAGREEMENT event emission on disagreement

The UnifiedClassifier is backward compatible: when no community memberships
are provided, it produces identical results to DefaultClassPositionClassifier.

Feature: 038-unified-class-system
Date: 2026-03-01
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.core.protocol_kit import CachedSource
from babylon.economics.melt.class_position import DefaultClassPositionClassifier
from babylon.economics.melt.types import ClassPosition, PrecarityStatus

if TYPE_CHECKING:
    from babylon.models.entities.community import CommunityMembership, CommunityState


class DualCriteriaResult(BaseModel):
    """Result of FR-002 dual-criteria validation.

    Compares accounting criterion (V_produced vs V_reproduction) against
    wealth percentile classification. Used for calibration logging.

    Args:
        wealth_class: ClassPosition from wealth percentile criterion.
        accounting_class: ClassPosition from accounting criterion.
        agrees: True if both criteria produce the same ClassPosition.
        magnitude: Disagreement magnitude in percentile-equivalent terms.
            Must be 0.0 when agrees is True.
    """

    model_config = ConfigDict(frozen=True)

    wealth_class: ClassPosition
    accounting_class: ClassPosition
    agrees: bool
    magnitude: float = Field(ge=0.0)

    @model_validator(mode="after")
    def _validate_consistency(self) -> DualCriteriaResult:
        """Ensure agrees flag is consistent with class values and magnitude."""
        classes_match = self.wealth_class == self.accounting_class
        if self.agrees and not classes_match:
            msg = (
                f"agrees=True but wealth_class={self.wealth_class.name} "
                f"!= accounting_class={self.accounting_class.name}"
            )
            raise ValueError(msg)
        if not self.agrees and classes_match:
            msg = f"agrees=False but both classes are {self.wealth_class.name}"
            raise ValueError(msg)
        if self.agrees and self.magnitude != 0.0:
            msg = f"agrees=True but magnitude={self.magnitude} (must be 0.0)"
            raise ValueError(msg)
        return self


class UnifiedClassifier(Protocol):
    """Protocol for unified class position classification (Feature 038).

    Wraps the existing ClassPositionClassifier with filtration and
    dual-criteria validation.
    """

    def classify_with_filtration(
        self,
        wealth_percentile: float,
        precarity: PrecarityStatus,
        memberships: list[CommunityMembership] | None = None,
        community_states: dict[str, CommunityState] | None = None,
    ) -> ClassPosition:
        """Classify household with optional community filtration.

        Args:
            wealth_percentile: Wealth percentile 0-100.
            precarity: PrecarityStatus for proletariat/lumpen distinction.
            memberships: Optional community memberships for filtration.
            community_states: Optional community states for modifier lookup.

        Returns:
            ClassPosition after applying any filtration predicates.
        """
        ...

    def classify_dual_criteria(
        self,
        wealth_percentile: float,
        precarity: PrecarityStatus,
        v_produced: float,
        v_reproduction: float,
        memberships: list[CommunityMembership] | None = None,
        community_states: dict[str, CommunityState] | None = None,
    ) -> DualCriteriaResult:
        """Compare accounting criterion vs wealth percentile classification.

        Args:
            wealth_percentile: Wealth percentile 0-100.
            precarity: PrecarityStatus.
            v_produced: Value produced by household.
            v_reproduction: Value required for household reproduction.
            memberships: Optional community memberships for filtration.
            community_states: Optional community states.

        Returns:
            DualCriteriaResult with agreement status and magnitude.
        """
        ...


# Accounting criterion thresholds as ratios of V_produced / V_reproduction
_SURPLUS_THRESHOLD = 1.5  # V_produced > 1.5 * V_reproduction -> bourgeois-relation
_SIMPLE_REPRO_UPPER = 1.2  # V_produced within 0.8-1.2 * V_reproduction -> proletarian
_SIMPLE_REPRO_LOWER = 0.8
_DEPENDENT_THRESHOLD = 0.5  # V_produced < 0.5 * V_reproduction -> lumpen-relation


def _accounting_criterion(v_produced: float, v_reproduction: float) -> ClassPosition:
    """Map accounting criterion (V_produced vs V_reproduction) to ClassPosition.

    Args:
        v_produced: Value produced by household.
        v_reproduction: Value required for household reproduction.

    Returns:
        ClassPosition derived from the accounting criterion.
    """
    if v_reproduction <= 0.0:
        return ClassPosition.BOURGEOISIE

    ratio = v_produced / v_reproduction
    if ratio >= _SURPLUS_THRESHOLD:
        return ClassPosition.BOURGEOISIE
    if ratio >= _SIMPLE_REPRO_UPPER:
        return ClassPosition.PETIT_BOURGEOISIE
    if ratio >= _SIMPLE_REPRO_LOWER:
        return ClassPosition.PROLETARIAT
    if ratio >= _DEPENDENT_THRESHOLD:
        return ClassPosition.PROLETARIAT
    return ClassPosition.LUMPENPROLETARIAT


class DefaultUnifiedClassifier(CachedSource[float]):
    """Default implementation wrapping DefaultClassPositionClassifier.

    Backward compatible: no memberships -> same result as base classifier.
    """

    def __init__(self) -> None:
        super().__init__()
        self._base = DefaultClassPositionClassifier()

    def classify_with_filtration(
        self,
        wealth_percentile: float,
        precarity: PrecarityStatus,
        memberships: list[CommunityMembership] | None = None,
        community_states: dict[str, CommunityState] | None = None,
    ) -> ClassPosition:
        """Classify household with optional community filtration.

        Args:
            wealth_percentile: Wealth percentile 0-100.
            precarity: PrecarityStatus for proletariat/lumpen distinction.
            memberships: Optional community memberships for filtration.
            community_states: Optional community states for modifier lookup.

        Returns:
            ClassPosition after applying any filtration predicates.
        """
        effective_wealth = wealth_percentile
        effective_precarity = precarity

        if memberships:
            # Phase 4 will wire in filtration here
            from babylon.economics.melt.filtration import apply_filtration

            filtration_result = apply_filtration(
                wealth_percentile=wealth_percentile,
                precarity=precarity,
                memberships=memberships,
                community_states=community_states or {},
            )
            effective_wealth = filtration_result.effective_wealth_percentile
            effective_precarity = filtration_result.effective_precarity

        return self._base.classify_by_wealth_and_precarity(effective_wealth, effective_precarity)

    def classify_dual_criteria(
        self,
        wealth_percentile: float,
        precarity: PrecarityStatus,
        v_produced: float,
        v_reproduction: float,
        memberships: list[CommunityMembership] | None = None,
        community_states: dict[str, CommunityState] | None = None,
    ) -> DualCriteriaResult:
        """Compare accounting criterion vs wealth percentile classification.

        Args:
            wealth_percentile: Wealth percentile 0-100.
            precarity: PrecarityStatus.
            v_produced: Value produced by household.
            v_reproduction: Value required for household reproduction.
            memberships: Optional community memberships for filtration.
            community_states: Optional community states.

        Returns:
            DualCriteriaResult with agreement status and magnitude.
        """
        wealth_class = self.classify_with_filtration(
            wealth_percentile, precarity, memberships, community_states
        )
        accounting_class = _accounting_criterion(v_produced, v_reproduction)

        agrees = wealth_class == accounting_class
        magnitude = 0.0 if agrees else abs(v_produced - v_reproduction)

        return DualCriteriaResult(
            wealth_class=wealth_class,
            accounting_class=accounting_class,
            agrees=agrees,
            magnitude=magnitude,
        )


class FractalConsistencyResult(BaseModel):
    """Result of fractal consistency validation across county resolutions.

    Validates that the same ClassPosition enum and classification logic
    works at both metro and sub-county zoom levels (FR-009).

    Args:
        is_consistent: True if fractal pattern holds across all counties.
        proletariat_lumpen_share: PROLETARIAT+LUMPEN share per county.
        class_positions_present: Set of ClassPositions present per county.
        metro_distribution: Population-weighted metro-level distribution.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    is_consistent: bool
    proletariat_lumpen_share: dict[str, float]
    class_positions_present: dict[str, set[ClassPosition]]
    metro_distribution: dict[ClassPosition, float]


def validate_fractal_consistency(
    county_distributions: dict[str, dict[ClassPosition, float]],
) -> FractalConsistencyResult:
    """Validate fractal consistency across county-level class distributions.

    Checks that each county has all five class positions represented and
    that distributions sum to approximately 1.0. Computes metro-level
    aggregate as equal-weighted average across counties.

    Args:
        county_distributions: Per-county class position distributions
            mapping FIPS -> {ClassPosition -> population fraction}.

    Returns:
        FractalConsistencyResult with consistency status and metrics.
    """
    is_consistent = True
    proletariat_lumpen_share: dict[str, float] = {}
    class_positions_present: dict[str, set[ClassPosition]] = {}

    for fips, dist in county_distributions.items():
        # Check distribution sums to ~1.0
        total = sum(dist.values())
        if abs(total - 1.0) > 0.01:
            is_consistent = False

        # Record which class positions are present
        present = {cp for cp, share in dist.items() if share > 0.0}
        class_positions_present[fips] = present

        # Check all five positions present
        if len(present) < 5:
            is_consistent = False

        # Compute proletariat + lumpen share
        prol_lumpen = dist.get(ClassPosition.PROLETARIAT, 0.0) + dist.get(
            ClassPosition.LUMPENPROLETARIAT, 0.0
        )
        proletariat_lumpen_share[fips] = prol_lumpen

    # Compute metro aggregate (equal-weighted average)
    metro_distribution: dict[ClassPosition, float] = {}
    n_counties = len(county_distributions)
    if n_counties > 0:
        for cp in ClassPosition:
            total_share = sum(dist.get(cp, 0.0) for dist in county_distributions.values())
            metro_distribution[cp] = total_share / n_counties

    return FractalConsistencyResult(
        is_consistent=is_consistent,
        proletariat_lumpen_share=proletariat_lumpen_share,
        class_positions_present=class_positions_present,
        metro_distribution=metro_distribution,
    )


__all__ = [
    "DefaultUnifiedClassifier",
    "DualCriteriaResult",
    "FractalConsistencyResult",
    "UnifiedClassifier",
    "validate_fractal_consistency",
]
