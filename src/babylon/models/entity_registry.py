"""Entity ID registry - single source of truth for entity ID mappings.

This module provides canonical mappings between SocialRole enums and entity IDs,
eliminating hardcoded magic strings like "C001", "C002", etc. throughout the codebase.

Usage:
    from babylon.models.entity_registry import (
        PERIPHERY_WORKER_ID,
        COMPRADOR_ID,
        role_to_entity_id,
        get_slot_name,
    )

See Also:
    :class:`babylon.models.enums.SocialRole` for the enum definitions
    :doc:`/ai-docs/decisions.yaml` for ADR context
"""

from __future__ import annotations

from typing import Final

from babylon.models.enums import SocialRole

# =============================================================================
# ENTITY ID CONSTANTS
# =============================================================================

PERIPHERY_WORKER_ID: Final[str] = "C001"
"""Periphery Worker (P_w) - exploited proletariat in the global South."""

COMPRADOR_ID: Final[str] = "C002"
"""Comprador (P_c) - local bourgeoisie collaborating with imperialism."""

CORE_BOURGEOISIE_ID: Final[str] = "C003"
"""Core Bourgeoisie (C_b) - metropolitan capitalist class."""

LABOR_ARISTOCRACY_ID: Final[str] = "C004"
"""Labor Aristocracy (C_w) - privileged workers in the imperial core."""

# Terminal Crisis Dynamics entities (Sprint 3.X)
CARCERAL_ENFORCER_ID: Final[str] = "C005"
"""Carceral Enforcer - guards, cops, prison staff (repressive apparatus)."""

INTERNAL_PROLETARIAT_ID: Final[str] = "C006"
"""Internal Proletariat - core workers outside LA (precariat, unemployed, incarcerated)."""

# =============================================================================
# ROLE TO ENTITY ID MAPPING
# =============================================================================

ROLE_TO_ENTITY_ID: Final[dict[SocialRole, str]] = {
    SocialRole.PERIPHERY_PROLETARIAT: PERIPHERY_WORKER_ID,
    SocialRole.COMPRADOR_BOURGEOISIE: COMPRADOR_ID,
    SocialRole.CORE_BOURGEOISIE: CORE_BOURGEOISIE_ID,
    SocialRole.LABOR_ARISTOCRACY: LABOR_ARISTOCRACY_ID,
    SocialRole.CARCERAL_ENFORCER: CARCERAL_ENFORCER_ID,
    SocialRole.INTERNAL_PROLETARIAT: INTERNAL_PROLETARIAT_ID,
}
"""Maps SocialRole enum values to canonical entity IDs."""

ENTITY_ID_TO_ROLE: Final[dict[str, SocialRole]] = {
    entity_id: role for role, entity_id in ROLE_TO_ENTITY_ID.items()
}
"""Inverse mapping: entity IDs to SocialRole enum values."""

# =============================================================================
# ENTITY SLOT NAMES (for CSV/metrics output)
# =============================================================================

ENTITY_SLOT_NAMES: Final[dict[str, str]] = {
    PERIPHERY_WORKER_ID: "p_w",  # Periphery Worker
    COMPRADOR_ID: "p_c",  # Comprador
    CORE_BOURGEOISIE_ID: "c_b",  # Core Bourgeoisie
    LABOR_ARISTOCRACY_ID: "c_w",  # Labor Aristocracy (Core Worker)
    CARCERAL_ENFORCER_ID: "c_e",  # Carceral Enforcer
    INTERNAL_PROLETARIAT_ID: "i_p",  # Internal Proletariat
}
"""Maps entity IDs to short slot names used in CSV columns and metrics."""

# =============================================================================
# ENTITY ID GROUPINGS
# =============================================================================

METRICS_ENTITY_IDS: Final[list[str]] = [
    PERIPHERY_WORKER_ID,
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    LABOR_ARISTOCRACY_ID,
]
"""Entity IDs tracked in metrics observer (active during normal simulation).

These are the four canonical entities in the imperial circuit scenario.
Terminal crisis entities (C005, C006) are excluded as they only become
active during class decomposition events.
"""

TERMINAL_CRISIS_ENTITY_IDS: Final[list[str]] = [
    CARCERAL_ENFORCER_ID,
    INTERNAL_PROLETARIAT_ID,
]
"""Entity IDs for terminal crisis dynamics (dormant until class decomposition)."""

ALL_ENTITY_IDS: Final[list[str]] = [
    PERIPHERY_WORKER_ID,
    COMPRADOR_ID,
    CORE_BOURGEOISIE_ID,
    LABOR_ARISTOCRACY_ID,
    CARCERAL_ENFORCER_ID,
    INTERNAL_PROLETARIAT_ID,
]
"""All entity IDs including terminal crisis entities."""


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def role_to_entity_id(role: SocialRole) -> str:
    """Convert a SocialRole enum to its canonical entity ID.

    Args:
        role: SocialRole enum value

    Returns:
        Entity ID string (e.g., "C001")

    Raises:
        KeyError: If the role has no entity ID mapping (e.g., LUMPENPROLETARIAT)

    Example:
        >>> role_to_entity_id(SocialRole.PERIPHERY_PROLETARIAT)
        'C001'
    """
    return ROLE_TO_ENTITY_ID[role]


def entity_id_to_role(entity_id: str) -> SocialRole:
    """Convert an entity ID to its SocialRole enum.

    Args:
        entity_id: Entity ID string (e.g., "C001")

    Returns:
        SocialRole enum value

    Raises:
        KeyError: If the entity ID is not recognized

    Example:
        >>> entity_id_to_role("C001")
        <SocialRole.PERIPHERY_PROLETARIAT: 'periphery_proletariat'>
    """
    return ENTITY_ID_TO_ROLE[entity_id]


def get_slot_name(entity_id: str) -> str:
    """Get the short slot name for an entity ID.

    Slot names are used for CSV column prefixes and metrics keys.

    Args:
        entity_id: Entity ID string (e.g., "C001")

    Returns:
        Short slot name (e.g., "p_w")

    Raises:
        KeyError: If the entity ID is not recognized

    Example:
        >>> get_slot_name("C001")
        'p_w'
    """
    return ENTITY_SLOT_NAMES[entity_id]


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Entity ID constants
    "PERIPHERY_WORKER_ID",
    "COMPRADOR_ID",
    "CORE_BOURGEOISIE_ID",
    "LABOR_ARISTOCRACY_ID",
    "CARCERAL_ENFORCER_ID",
    "INTERNAL_PROLETARIAT_ID",
    # Mappings
    "ROLE_TO_ENTITY_ID",
    "ENTITY_ID_TO_ROLE",
    "ENTITY_SLOT_NAMES",
    # Groupings
    "METRICS_ENTITY_IDS",
    "TERMINAL_CRISIS_ENTITY_IDS",
    "ALL_ENTITY_IDS",
    # Utility functions
    "role_to_entity_id",
    "entity_id_to_role",
    "get_slot_name",
]
