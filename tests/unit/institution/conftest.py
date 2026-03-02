"""Test fixtures and factory helpers for institution unit tests (Feature 040)."""

from __future__ import annotations

from typing import Any

from babylon.models.entities.institution import (
    Institution,
    InstitutionOrgRelation,
    InternalBalanceOfForces,
    ReproductionMechanism,
    SpawningBlueprint,
)
from babylon.models.enums import (
    ApparatusType,
    ClassCharacter,
    ClassInscription,
    LifecyclePhase,
    OrgType,
    SocialFunction,
)


def make_balance(**overrides: Any) -> InternalBalanceOfForces:
    """Create an InternalBalanceOfForces with Detroit DOJ defaults.

    Args:
        **overrides: Fields to override on the default balance.

    Returns:
        Frozen InternalBalanceOfForces instance.
    """
    defaults: dict[str, Any] = {
        "liberal_technocratic": 0.5,
        "revanchist_fascist": 0.3,
        "institutionalist_bonapartist": 0.2,
        "internal_contestation": 0.3,
    }
    defaults.update(overrides)
    return InternalBalanceOfForces(**defaults)


def make_reproduction(**overrides: Any) -> ReproductionMechanism:
    """Create a ReproductionMechanism with sensible defaults.

    Args:
        **overrides: Fields to override.

    Returns:
        Frozen ReproductionMechanism instance.
    """
    defaults: dict[str, Any] = {
        "recruitment_pipeline": True,
        "training_program": True,
        "succession_protocol": True,
        "budget_independence": 0.8,
        "legal_self_perpetuation": True,
    }
    defaults.update(overrides)
    return ReproductionMechanism(**defaults)


def make_institution(**overrides: Any) -> Institution:
    """Create an Institution with DOJ defaults.

    Args:
        **overrides: Fields to override on the default Institution.

    Returns:
        Frozen Institution instance.
    """
    defaults: dict[str, Any] = {
        "id": "doj",
        "name": "Department of Justice",
        "apparatus_type": ApparatusType.RSA_JUDICIAL,
        "social_function": SocialFunction.ADJUDICATION,
        "class_inscription": ClassInscription.BOURGEOIS,
        "internal_balance": make_balance(),
        "budget": 1_000_000.0,
        "legal_authorities": frozenset(["federal_prosecution", "civil_rights_enforcement"]),
        "personnel_capacity": 500,
        "formalization_level": 0.95,
        "institutional_inertia": 0.8,
        "legitimacy": 0.7,
        "housed_org_ids": ["fbi"],
        "territory_ids": ["us_national"],
        "jurisdiction": frozenset(["national"]),
        "reproduction": make_reproduction(),
        "spawning_blueprints": [
            SpawningBlueprint(
                org_type=OrgType.STATE_APPARATUS,
                default_class_character=ClassCharacter.BOURGEOIS,
                base_attributes={"jurisdiction": "national", "violence_capacity": 0.3},
            ),
        ],
    }
    defaults.update(overrides)
    return Institution(**defaults)


def make_isa_institution(**overrides: Any) -> Institution:
    """Create an ISA_EDUCATIONAL institution with Detroit Public Schools defaults.

    Args:
        **overrides: Fields to override.

    Returns:
        Frozen Institution instance.
    """
    defaults: dict[str, Any] = {
        "id": "detroit_public_schools",
        "name": "Detroit Public Schools",
        "apparatus_type": ApparatusType.ISA_EDUCATIONAL,
        "social_function": SocialFunction.EDUCATION,
        "class_inscription": ClassInscription.CONTESTED,
        "internal_balance": make_balance(
            liberal_technocratic=0.6,
            revanchist_fascist=0.2,
            institutionalist_bonapartist=0.2,
        ),
        "budget": 500_000.0,
        "personnel_capacity": 3000,
        "legitimacy": 0.5,
        "territory_ids": ["detroit_h3_001", "detroit_h3_002"],
        "lifecycle_function": LifecyclePhase.D_DEPENDENT,
        "reproduction": make_reproduction(budget_independence=0.3),
    }
    defaults.update(overrides)
    return Institution(**defaults)


def make_relation(**overrides: Any) -> InstitutionOrgRelation:
    """Create an InstitutionOrgRelation with sensible defaults.

    Args:
        **overrides: Fields to override.

    Returns:
        Frozen InstitutionOrgRelation instance.
    """
    defaults: dict[str, Any] = {
        "institution_id": "doj",
        "organization_id": "fbi",
        "resource_provision": 0.5,
        "legal_cover": True,
        "legitimacy_transfer": 0.6,
        "action_oversight": 0.3,
    }
    defaults.update(overrides)
    return InstitutionOrgRelation(**defaults)
