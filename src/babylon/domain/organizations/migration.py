"""Legacy migration for factions.json and institutions.json (Feature 031, T031).

Converts legacy JSON records into typed Organization subtypes per the R8
mapping table in research.md. One-time migration — no runtime backward
compatibility layer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from babylon.models.entities.organization import (
    CivilSocietyOrg,
    OrganizationType,
    PoliticalFaction,
    StateApparatus,
)
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    JurisdictionLevel,
    LegalStanding,
    ServiceType,
)

logger = logging.getLogger(__name__)

# Ideology → ConsciousnessTendency mapping (R8)
_IDEOLOGY_TENDENCY: dict[str, ConsciousnessTendency] = {
    "Fascism": ConsciousnessTendency.FASCIST,
    "Liberal Democracy": ConsciousnessTendency.LIBERAL,
    "Marxism-Leninism": ConsciousnessTendency.REVOLUTIONARY,
    "Marxism-Leninism-Maoism": ConsciousnessTendency.REVOLUTIONARY,
}

# Institution type → service_type mapping for CivilSocietyOrg
_INST_TYPE_SERVICE: dict[str, ServiceType] = {
    "Cultural": ServiceType.MEDIA,
    "Economic": ServiceType.LABOR,
    "Religious": ServiceType.RELIGIOUS,
    "Educational": ServiceType.EDUCATIONAL,
}

# Institution types that map to StateApparatus
_STATE_TYPES = {"State", "Legal"}

# Institutions to drop (not organizations per Constitution I.16)
_DROP_NAMES = {"Systemic Racism"}


def migrate_faction(faction_data: dict[str, Any]) -> PoliticalFaction:
    """Migrate a legacy faction JSON record to PoliticalFaction.

    Args:
        faction_data: Raw dict from factions.json.

    Returns:
        PoliticalFaction with mapped fields.
    """
    ideology = faction_data["ideology"]
    tendency = _IDEOLOGY_TENDENCY.get(ideology, ConsciousnessTendency.LIBERAL)

    return PoliticalFaction(
        id=faction_data["id"],
        name=faction_data["name"],
        class_character=ClassCharacter.PROLETARIAN,
        ideology=ideology,
        consciousness_tendency=tendency,
    )


def migrate_institution(inst_data: dict[str, Any]) -> OrganizationType | None:
    """Migrate a legacy institution JSON record to Organization subtype.

    Args:
        inst_data: Raw dict from institutions.json.

    Returns:
        Organization subtype, or None if institution should be dropped.
    """
    name = inst_data["name"]
    inst_type = inst_data["type"]

    # Drop non-organizations (Systemic Racism per Constitution I.16)
    if name in _DROP_NAMES:
        logger.info(
            "Dropping '%s' — not an organization (social relation per Constitution I.16)",
            name,
        )
        return None

    inst_id = inst_data["id"]

    # State/Legal → StateApparatus
    if inst_type in _STATE_TYPES:
        jurisdiction = (
            JurisdictionLevel.NATIONAL if inst_type == "State" else JurisdictionLevel.STATE
        )
        return StateApparatus(
            id=inst_id,
            name=name,
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=jurisdiction,
            legal_standing=LegalStanding.SOVEREIGN,
        )

    # Cultural/Economic/Religious/Educational → CivilSocietyOrg
    service_type = _INST_TYPE_SERVICE.get(inst_type)
    if service_type is not None:
        return CivilSocietyOrg(
            id=inst_id,
            name=name,
            class_character=ClassCharacter.PROLETARIAN,
            service_type=service_type,
            consciousness_tendency=ConsciousnessTendency.LIBERAL,
        )

    msg = f"Unknown institution type '{inst_type}' for '{name}'"
    raise ValueError(msg)


def migrate_all(
    factions_path: Path,
    institutions_path: Path,
) -> dict[str, OrganizationType]:
    """Batch migrate all legacy factions and institutions.

    Args:
        factions_path: Path to factions.json.
        institutions_path: Path to institutions.json.

    Returns:
        Dict of organization ID to Organization subtype.
    """
    result: dict[str, OrganizationType] = {}

    with factions_path.open() as f:
        factions_data = json.load(f)
    for faction_data in factions_data["factions"]:
        faction = migrate_faction(faction_data)
        result[faction.id] = faction

    with institutions_path.open() as f:
        institutions_data = json.load(f)
    for inst_data in institutions_data["institutions"]:
        inst_org = migrate_institution(inst_data)
        if inst_org is not None:
            result[inst_org.id] = inst_org

    logger.info("Migrated %d organizations from legacy data", len(result))
    return result
