"""Discrete ownership transitions for land tenure (Feature 043).

Defines discrete state machine transitions for HexTenureComposition
that drive macroscopic class structure changes (e.g., LA to Proletariat)
through endogenous property relations rather than static demographic proxies.

These transitions are intended to be invoked by tension-driven events.

Also provides the equity threshold test (FR-005 of spec 038) that
determines whether owner-occupants have meaningful equity to constitute
Labor Aristocracy membership.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.domain.economics.substrate.types import HexEconomicState, HexTenureComposition
from babylon.models.enums import SocialRole

if TYPE_CHECKING:
    from babylon.config.defines import ClassSystemDefines


def apply_foreclosure(
    state: HexEconomicState,
    fraction_lost: float,
    to_rental: bool = False,
) -> HexEconomicState:
    """Apply a foreclosure event to a hex.

    Financial default processes structurally dispossess the Labor Aristocracy
    of their property equity, converting them into Proletariat/Lumpenproletariat.
    The foreclosed property either becomes vacant/abandoned or transitions
    to a rental property owned by commercial landlords.

    Args:
        state: Current hex economic state.
        fraction_lost: Fraction of total hex area lost to foreclosure.
        to_rental: If True, rentiers buy up the property (residential_rental).
                   If False, property sits vacant (vacant_abandoned).

    Returns:
        Updated HexEconomicState with mutated tenure composition.
    """
    if not state.tenure_composition:
        return state

    tenure = state.tenure_composition
    # Clamp the lost fraction so we don't drop below 0
    actual_lost = min(tenure.residential_owner_occupied, max(0.0, fraction_lost))

    if actual_lost <= 0.0:
        return state

    updates = {
        "residential_owner_occupied": tenure.residential_owner_occupied - actual_lost,
    }

    if to_rental:
        updates["residential_rental"] = tenure.residential_rental + actual_lost
    else:
        updates["vacant_abandoned"] = tenure.vacant_abandoned + actual_lost

    new_tenure = tenure.model_copy(update=updates)
    return state.model_copy(update={"tenure_composition": new_tenure})


def apply_purchase(state: HexEconomicState, fraction_gained: float) -> HexEconomicState:
    """Apply a purchase event to a hex.

    Proletariat acquires residential property overcoming the meaningful equity
    threshold, thereby transitioning to the Labor Aristocracy. This typically
    converts rental property to owner-occupied property.

    Args:
        state: Current hex economic state.
        fraction_gained: Fraction of total hex area purchased for owner-occupancy.

    Returns:
        Updated HexEconomicState.
    """
    if not state.tenure_composition:
        return state

    tenure = state.tenure_composition
    # Clamp the gained fraction so we don't drop rental below 0
    actual_gained = min(tenure.residential_rental, max(0.0, fraction_gained))

    if actual_gained <= 0.0:
        return state

    new_tenure = tenure.model_copy(
        update={
            "residential_owner_occupied": tenure.residential_owner_occupied + actual_gained,
            "residential_rental": tenure.residential_rental - actual_gained,
        }
    )
    return state.model_copy(update={"tenure_composition": new_tenure})


def apply_abandonment(state: HexEconomicState, fraction_abandoned: float) -> HexEconomicState:
    """Apply an abandonment event to a hex.

    Tax delinquency or severe structural obsolescence leading to capital flight.
    This converts residential or commercial property directly to vacant space.
    Affects both owner-occupied and rental properties proportionally.

    Args:
        state: Current hex economic state.
        fraction_abandoned: Target fraction of residential property to abandon.

    Returns:
        Updated HexEconomicState.
    """
    if not state.tenure_composition:
        return state

    tenure = state.tenure_composition
    # Sum of susceptible residential properties
    total_res = tenure.residential_owner_occupied + tenure.residential_rental

    if total_res <= 0.0:
        return state

    # Clamp the fraction
    actual_abandoned = min(total_res, max(0.0, fraction_abandoned))
    if actual_abandoned <= 0.0:
        return state

    # Distribute proportionally
    prop_owner = tenure.residential_owner_occupied / total_res
    prop_rental = tenure.residential_rental / total_res

    lost_owner = actual_abandoned * prop_owner
    lost_rental = actual_abandoned * prop_rental

    new_tenure = tenure.model_copy(
        update={
            "residential_owner_occupied": tenure.residential_owner_occupied - lost_owner,
            "residential_rental": tenure.residential_rental - lost_rental,
            "vacant_abandoned": tenure.vacant_abandoned + actual_abandoned,
        }
    )
    return state.model_copy(update={"tenure_composition": new_tenure})


def evaluate_class_shares(
    tenure: HexTenureComposition,
    equity_threshold_met: bool = True,
) -> dict[SocialRole, float]:
    """Evaluate class position shares purely from the endogenous property relations.

    Feature 043 explicitly maps Property Type -> Class Position.
    Redundant storage of class position is forbidden; we derive it dynamically.

    Args:
        tenure: The current tenure composition of the hex.
        equity_threshold_met: If true, owner-occupants have meaningful equity and
                              qualify as Labor Aristocracy. If false, they are
                              functionally Proletariat despite nominal title.

    Returns:
        Mapping of SocialRole to the land fraction backing that population.
    """
    shares = {
        SocialRole.LABOR_ARISTOCRACY: 0.0,
        SocialRole.INTERNAL_PROLETARIAT: 0.0,
        SocialRole.LUMPENPROLETARIAT: 0.0,
        SocialRole.CORE_BOURGEOISIE: 0.0,
    }

    # Owner-occupied: LA if equity met, otherwise Proletariat
    if equity_threshold_met:
        shares[SocialRole.LABOR_ARISTOCRACY] += tenure.residential_owner_occupied
    else:
        shares[SocialRole.INTERNAL_PROLETARIAT] += tenure.residential_owner_occupied

    # Rental property (Tenants) -> Proletariat
    shares[SocialRole.INTERNAL_PROLETARIAT] += tenure.residential_rental

    # Commercial / Industrial property -> Bourgeoisie / PB
    # For now we group into CORE_BOURGEOISIE and potentially Petitor depending on scale
    shares[SocialRole.CORE_BOURGEOISIE] += tenure.commercial + tenure.industrial

    # Vacant/Abandoned -> Lumpenproletariat / highly precarious Proletariat
    shares[SocialRole.LUMPENPROLETARIAT] += tenure.vacant_abandoned

    # Note: Public and Trust land might represent state/collective ownership.
    # Excluded from direct individual household class roles for this simplified breakdown.

    return shares


def check_equity_threshold(
    state: HexEconomicState,
    defines: ClassSystemDefines | None = None,
) -> bool:
    """Test whether a hex's owner-occupants have meaningful equity.

    Implements FR-005 of spec 038 (as amended by spec 043):
    ``equity_factor`` serves as an absolute threshold test on the
    equity ratio, NOT a population-level numeric scaler.

    The equity ratio is defined as::

        equity_ratio = s / (c + v + s)

    This measures the fraction of total output captured as surplus,
    which serves as a proxy for the appreciation / equity accumulation
    trajectory of the hex's property base. Owner-occupants in a hex
    where this ratio exceeds the threshold have a material stake in
    the property system sufficient to constitute LA.

    Args:
        state: Hex economic state (must have tenure_composition).
        defines: ClassSystemDefines with equity_factor threshold.
            Uses GameDefines defaults if None.

    Returns:
        True if owner-occupants meet the meaningful equity threshold,
        False otherwise (including when tenure_composition is absent).
    """
    if state.tenure_composition is None:
        return False

    if defines is None:
        from babylon.config.defines import ClassSystemDefines as _CSD

        defines = _CSD()

    total_output = state.constant_capital + state.variable_capital + state.surplus_value
    if total_output <= 0.0:
        return False

    equity_ratio = state.surplus_value / total_output
    return equity_ratio >= defines.equity_factor
