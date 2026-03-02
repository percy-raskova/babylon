"""Structural selectivity function for institutions (Feature 040).

Determines action cost modifiers for Organizations housed within
an institution. Checks institution-level overrides first, then
falls back to apparatus-type defaults.

See Also:
    ``specs/040-institution-base-model/spec.md``: FR-007.
"""

from __future__ import annotations

from babylon.models.entities.institution import Institution
from babylon.models.enums import ActionType


def structural_selectivity(
    institution: Institution,
    action_type: ActionType,
    defaults: dict[str, dict[str, float]],
) -> float:
    """Compute the cost modifier for an action within an institution.

    Checks institution.action_modifiers first for an override. Falls
    back to defaults[apparatus_type][action_type] from InstitutionDefines.
    Returns 1.0 (no modifier) if no mapping found.

    Args:
        institution: The institution providing structural selectivity.
        action_type: The action type to look up.
        defaults: Default modifiers per ApparatusType, keyed by
            ApparatusType string values, sub-keyed by ActionType
            string values. Loaded from InstitutionDefines.default_action_modifiers.

    Returns:
        Cost multiplier: < 1.0 means cheaper, > 1.0 means more expensive.
    """
    # Check institution-level overrides first
    action_key = action_type.value
    if action_key in institution.action_modifiers:
        return institution.action_modifiers[action_key]

    # Fall back to apparatus-type defaults
    apparatus_key = institution.apparatus_type.value
    apparatus_defaults = defaults.get(apparatus_key, {})
    return apparatus_defaults.get(action_key, 1.0)
