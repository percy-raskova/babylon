"""Community filtration predicates for unified class system (Feature 038).

This module implements community-specific filtration predicates that modify
classification inputs based on hyperedge memberships (FR-003, FR-004).

Four community types trigger filtration:
- FIRST_NATIONS: trust_land_discount on effective wealth
- INCARCERATED: precarity override to EXCLUDED
- UNDOCUMENTED: documentation_exclusion_factor + precarity floor PRECARIOUS
- DISABLED: reproduction_cost_modifier from CommunityState

Composition rule (FR-004): each predicate evaluates independently against
original inputs; the most restrictive composite result is used.

Feature: 038-unified-class-system
Date: 2026-03-01
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.config.defines import ClassSystemDefines, GameDefines
from babylon.economics.melt.types import PrecarityStatus
from babylon.models.entities.community import CommunityMembership, CommunityState
from babylon.models.enums import CommunityType

# Precarity severity ordering: higher value = more severe
_PRECARITY_SEVERITY: dict[PrecarityStatus, int] = {
    PrecarityStatus.STABLE: 0,
    PrecarityStatus.PRECARIOUS: 1,
    PrecarityStatus.MARGINALLY_ATTACHED: 2,
    PrecarityStatus.EXCLUDED: 3,
}


def precarity_severity(status: PrecarityStatus) -> int:
    """Return integer severity of a PrecarityStatus.

    Args:
        status: PrecarityStatus to evaluate.

    Returns:
        Integer severity (0=STABLE, 1=PRECARIOUS, 2=MARGINALLY_ATTACHED, 3=EXCLUDED).
    """
    return _PRECARITY_SEVERITY[status]


class FiltrationResult(BaseModel):
    """Result of applying community filtration predicates.

    Args:
        original_wealth_percentile: Input wealth percentile before filtration.
        effective_wealth_percentile: Wealth percentile after filtration.
        original_precarity: Input precarity before filtration.
        effective_precarity: Precarity after filtration.
        applied_predicates: Names of filtration predicates that fired.
        most_restrictive_community: CommunityType that produced most restrictive result.
    """

    model_config = ConfigDict(frozen=True)

    original_wealth_percentile: float = Field(ge=0.0, le=100.0)
    effective_wealth_percentile: float = Field(ge=0.0, le=100.0)
    original_precarity: PrecarityStatus
    effective_precarity: PrecarityStatus
    applied_predicates: list[str] = Field(default_factory=list)
    most_restrictive_community: CommunityType | None = Field(default=None)

    @model_validator(mode="after")
    def _validate_filtration_direction(self) -> FiltrationResult:
        """Ensure filtration only reduces effective values."""
        if self.effective_wealth_percentile > self.original_wealth_percentile:
            msg = (
                f"effective_wealth_percentile ({self.effective_wealth_percentile}) "
                f"> original_wealth_percentile ({self.original_wealth_percentile})"
            )
            raise ValueError(msg)
        orig_sev = precarity_severity(self.original_precarity)
        eff_sev = precarity_severity(self.effective_precarity)
        if eff_sev < orig_sev:
            msg = (
                f"effective_precarity ({self.effective_precarity.name}, severity={eff_sev}) "
                f"is less severe than original ({self.original_precarity.name}, severity={orig_sev})"
            )
            raise ValueError(msg)
        return self


def _apply_first_nations(
    wealth: float,
    precarity: PrecarityStatus,
    defines: ClassSystemDefines,
) -> tuple[float, PrecarityStatus, str]:
    """FIRST_NATIONS: apply trust_land_discount to effective wealth.

    Args:
        wealth: Original wealth percentile.
        precarity: Original precarity status.
        defines: ClassSystemDefines for trust_land_discount.

    Returns:
        Tuple of (effective_wealth, effective_precarity, predicate_name).
    """
    return (
        wealth * defines.trust_land_discount,
        precarity,
        "FIRST_NATIONS_trust_land",
    )


def _apply_incarcerated(
    wealth: float,
    precarity: PrecarityStatus,
) -> tuple[float, PrecarityStatus, str]:
    """INCARCERATED: override precarity to EXCLUDED.

    Args:
        wealth: Original wealth percentile (unchanged).
        precarity: Original precarity status (overridden).

    Returns:
        Tuple of (effective_wealth, EXCLUDED, predicate_name).
    """
    _ = precarity  # Always overridden
    return (wealth, PrecarityStatus.EXCLUDED, "INCARCERATED_exclusion")


def _apply_undocumented(
    wealth: float,
    precarity: PrecarityStatus,
    defines: ClassSystemDefines,
) -> tuple[float, PrecarityStatus, str]:
    """UNDOCUMENTED: apply documentation_exclusion_factor + precarity floor.

    Args:
        wealth: Original wealth percentile.
        precarity: Original precarity status.
        defines: ClassSystemDefines for documentation_exclusion_factor.

    Returns:
        Tuple of (effective_wealth, effective_precarity, predicate_name).
    """
    effective_wealth = wealth * defines.documentation_exclusion_factor
    # Precarity floor: at least PRECARIOUS
    if precarity_severity(precarity) < precarity_severity(PrecarityStatus.PRECARIOUS):
        effective_precarity = PrecarityStatus.PRECARIOUS
    else:
        effective_precarity = precarity
    return (effective_wealth, effective_precarity, "UNDOCUMENTED_exclusion")


def _apply_disabled(
    wealth: float,
    precarity: PrecarityStatus,
    community_states: dict[str, CommunityState],
) -> tuple[float, PrecarityStatus, str]:
    """DISABLED: apply reproduction_cost_modifier from CommunityState.

    Args:
        wealth: Original wealth percentile.
        precarity: Original precarity status.
        community_states: Keyed by community_type.value for modifier lookup.

    Returns:
        Tuple of (effective_wealth, effective_precarity, predicate_name).
    """
    state = community_states.get(CommunityType.DISABLED.value)
    if state is not None and state.reproduction_cost_modifier > 0.0:
        effective_wealth = wealth / state.reproduction_cost_modifier
    else:
        effective_wealth = wealth
    return (effective_wealth, precarity, "DISABLED_reproduction_cost")


# Map of community types to their filtration predicate applicators
_FILTRATION_TYPES: frozenset[CommunityType] = frozenset(
    {
        CommunityType.FIRST_NATIONS,
        CommunityType.INCARCERATED,
        CommunityType.UNDOCUMENTED,
        CommunityType.DISABLED,
    }
)


def apply_filtration(
    wealth_percentile: float,
    precarity: PrecarityStatus,
    memberships: list[CommunityMembership],
    community_states: dict[str, CommunityState],
    defines: ClassSystemDefines | None = None,
) -> FiltrationResult:
    """Apply community filtration predicates to classification inputs.

    Each predicate is evaluated independently against original inputs.
    The most restrictive composite result (lowest wealth, highest precarity
    severity) is used. FIRST_NATIONS always overrides SETTLER interpretation.

    Args:
        wealth_percentile: Input wealth percentile 0-100.
        precarity: Input PrecarityStatus.
        memberships: Community memberships to evaluate.
        community_states: Community states for modifier lookup.
        defines: ClassSystemDefines for coefficients (uses defaults if None).

    Returns:
        FiltrationResult with effective values after filtration.
    """
    if defines is None:
        defines = GameDefines().class_system

    # Collect which filtration-triggering community types are present
    active_types: set[CommunityType] = set()
    for m in memberships:
        if m.community_type in _FILTRATION_TYPES:
            active_types.add(m.community_type)

    # No filtration-triggering memberships -> identity
    if not active_types:
        return FiltrationResult(
            original_wealth_percentile=wealth_percentile,
            effective_wealth_percentile=wealth_percentile,
            original_precarity=precarity,
            effective_precarity=precarity,
        )

    # Evaluate each predicate independently against original inputs
    predicate_results: list[tuple[float, PrecarityStatus, str, CommunityType]] = []

    if CommunityType.FIRST_NATIONS in active_types:
        w, p, name = _apply_first_nations(wealth_percentile, precarity, defines)
        predicate_results.append((w, p, name, CommunityType.FIRST_NATIONS))

    if CommunityType.INCARCERATED in active_types:
        w, p, name = _apply_incarcerated(wealth_percentile, precarity)
        predicate_results.append((w, p, name, CommunityType.INCARCERATED))

    if CommunityType.UNDOCUMENTED in active_types:
        w, p, name = _apply_undocumented(wealth_percentile, precarity, defines)
        predicate_results.append((w, p, name, CommunityType.UNDOCUMENTED))

    if CommunityType.DISABLED in active_types:
        w, p, name = _apply_disabled(wealth_percentile, precarity, community_states)
        predicate_results.append((w, p, name, CommunityType.DISABLED))

    # Composite: most restrictive (lowest wealth, highest precarity severity)
    min_wealth = wealth_percentile
    max_precarity = precarity
    applied_names: list[str] = []
    most_restrictive: CommunityType | None = None
    min_wealth_community: CommunityType | None = None

    for w, p, name, ctype in predicate_results:
        applied_names.append(name)
        if w < min_wealth:
            min_wealth = w
            min_wealth_community = ctype
        if precarity_severity(p) > precarity_severity(max_precarity):
            max_precarity = p

    # Most restrictive community: whichever produced lowest wealth
    # (precarity override is binary so we track wealth as primary differentiator)
    most_restrictive = min_wealth_community

    return FiltrationResult(
        original_wealth_percentile=wealth_percentile,
        effective_wealth_percentile=min_wealth,
        original_precarity=precarity,
        effective_precarity=max_precarity,
        applied_predicates=applied_names,
        most_restrictive_community=most_restrictive,
    )


__all__ = [
    "FiltrationResult",
    "apply_filtration",
    "precarity_severity",
]
