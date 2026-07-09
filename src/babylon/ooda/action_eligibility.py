"""Action eligibility checking for organizations (Feature 032).

Provides the 25x4 eligibility matrix mapping (OrgType, ActionType) pairs
to boolean availability, with special-case overrides for REPRESS, SURVEIL,
and ASSIMILATE.

See Also:
    ``specs/032-ooda-loop-system/contracts/action-resolution-contract.md``
"""

from __future__ import annotations

from typing import Any

from babylon.models.enums import ActionType, ConsciousnessTendency, OrgType

# --- 25x4 eligibility matrix ---
# True = org type can perform this action by default.
# Special cases (REPRESS, SURVEIL, ASSIMILATE) handled in check_eligibility().
_ELIGIBILITY_MAP: dict[tuple[str, str], bool] = {}

# Actions universally available to all org types
_UNIVERSAL_ACTIONS: frozenset[ActionType] = frozenset(
    {
        ActionType.RECRUIT,
        ActionType.ORGANIZE,
        ActionType.EDUCATE,
        ActionType.AGITATE,
        ActionType.PROPAGANDIZE,
        ActionType.FUNDRAISE,
        ActionType.PROTEST,
        ActionType.COUNTER_INTEL,
        ActionType.MAP_NETWORK,
        ActionType.PROPOSE_ALLIANCE,
        ActionType.DENOUNCE,
        ActionType.BUILD_INFRASTRUCTURE,
        # Player spatial verb (verb-dispatch engine): any org may relocate.
        ActionType.MOVE,
    }
)

for _org_type in OrgType:
    for _action in _UNIVERSAL_ACTIONS:
        _ELIGIBILITY_MAP[(_org_type.value, _action.value)] = True

# PROVIDE_SERVICE: all except Business
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.PROVIDE_SERVICE.value)] = (
        _org_type != OrgType.BUSINESS
    )

# EMPLOY: Business only
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.EMPLOY.value)] = _org_type == OrgType.BUSINESS

# STRIKE: PoliticalFaction and CivilSociety only
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.STRIKE.value)] = _org_type in {
        OrgType.POLITICAL_FACTION,
        OrgType.CIVIL_SOCIETY,
    }

# EXPROPRIATE: PoliticalFaction only by default
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.EXPROPRIATE.value)] = (
        _org_type == OrgType.POLITICAL_FACTION
    )

# REPRESS: StateApparatus only by default (special case adds violence_capacity)
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.REPRESS.value)] = (
        _org_type == OrgType.STATE_APPARATUS
    )

# SURVEIL: StateApparatus only by default (special case adds surveillance_capacity)
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.SURVEIL.value)] = (
        _org_type == OrgType.STATE_APPARATUS
    )

# INFILTRATE: StateApparatus only (no special cases)
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.INFILTRATE.value)] = (
        _org_type == OrgType.STATE_APPARATUS
    )

# ATTACK_INFRASTRUCTURE: StateApparatus and PoliticalFaction
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.ATTACK_INFRASTRUCTURE.value)] = _org_type in {
        OrgType.STATE_APPARATUS,
        OrgType.POLITICAL_FACTION,
    }

# ASSIMILATE: StateApparatus by default (special case for LIBERAL + institution)
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.ASSIMILATE.value)] = (
        _org_type == OrgType.STATE_APPARATUS
    )

# --- Spec-071 fascist action verbs ---
# POGROM: PoliticalFaction (the reactionary formation) can direct communal violence.
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.POGROM.value)] = (
        _org_type == OrgType.POLITICAL_FACTION
    )

# LOCKOUT: Business only (the employer withdraws wages/employment).
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.LOCKOUT.value)] = _org_type == OrgType.BUSINESS

# VIGILANTISM: PoliticalFaction and CivilSociety (extra-state reactionary civil formations).
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.VIGILANTISM.value)] = _org_type in {
        OrgType.POLITICAL_FACTION,
        OrgType.CIVIL_SOCIETY,
    }

# RED_BROWN_COUP: never a directly-selectable OODA action — it is auto-triggered
# by the FascistFactionSystem on majority LA defection. Present in the matrix
# (all-pairs contract) but False for every org type.
for _org_type in OrgType:
    _ELIGIBILITY_MAP[(_org_type.value, ActionType.RED_BROWN_COUP.value)] = False

# Freeze for immutability
ELIGIBILITY_MAP: dict[tuple[str, str], bool] = dict(_ELIGIBILITY_MAP)


def check_eligibility(
    org_type: OrgType | str,
    action_type: ActionType | str,
    org_attrs: dict[str, Any] | None = None,
) -> bool:
    """Check if an organization type can perform an action.

    Looks up the static eligibility matrix, then applies special-case
    overrides for REPRESS, SURVEIL, and ASSIMILATE.

    Args:
        org_type: Organization type (OrgType enum or string value).
        action_type: Action to check (ActionType enum or string value).
        org_attrs: Optional organization attributes dict for special cases.

    Returns:
        True if the organization is eligible for the action.
    """
    ot = org_type.value if isinstance(org_type, OrgType) else org_type
    at = action_type.value if isinstance(action_type, ActionType) else action_type
    attrs = org_attrs or {}

    # Base eligibility from matrix
    base = ELIGIBILITY_MAP.get((ot, at), False)

    # Special case: REPRESS — non-state orgs with violence_capacity
    if at == ActionType.REPRESS.value and not base and attrs.get("violence_capacity", 0) > 0:
        return True

    # Special case: SURVEIL — non-state orgs with surveillance_capacity
    if at == ActionType.SURVEIL.value and not base and attrs.get("surveillance_capacity", 0) > 0:
        return True

    # Special case: ASSIMILATE — LIBERAL + is_institution for non-state
    if (
        at == ActionType.ASSIMILATE.value
        and not base
        and ot in {OrgType.POLITICAL_FACTION.value, OrgType.CIVIL_SOCIETY.value}
    ):
        tendency = attrs.get("consciousness_tendency")
        is_institution = attrs.get("is_institution", False)
        if tendency == ConsciousnessTendency.LIBERAL.value and is_institution:
            return True

    return base


__all__ = [
    "ELIGIBILITY_MAP",
    "check_eligibility",
]
