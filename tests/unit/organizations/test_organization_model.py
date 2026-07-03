"""Tests for Organization base model (Feature 031, T008).

Tests the 15-field base Organization model: creation, validation,
immutability, serialization, and field descriptions.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.organization import Organization
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    LegalStanding,
    OrgType,
)
from tests.constants import TestConstants

TC = TestConstants


class TestOrganizationCreation:
    """Organization base model creation with defaults and custom values."""

    @pytest.mark.math
    def test_create_minimal(self) -> None:
        """Minimal creation with required fields only."""
        org = Organization(
            id="org-001",
            name="Test Org",
            org_type=OrgType.POLITICAL_FACTION,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.id == "org-001"
        assert org.name == "Test Org"
        assert org.org_type == OrgType.POLITICAL_FACTION
        assert org.class_character == ClassCharacter.PROLETARIAN

    @pytest.mark.math
    def test_default_cohesion(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.cohesion == pytest.approx(TC.Organization.DEFAULT_COHESION)

    @pytest.mark.math
    def test_default_cadre_level(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.cadre_level == pytest.approx(TC.Organization.DEFAULT_CADRE)

    @pytest.mark.math
    def test_default_budget(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.budget == pytest.approx(TC.Organization.DEFAULT_BUDGET)

    @pytest.mark.math
    def test_default_legal_standing(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.legal_standing == LegalStanding.REGISTERED

    @pytest.mark.math
    def test_default_consciousness_tendency(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.consciousness_tendency == ConsciousnessTendency.LIBERAL

    @pytest.mark.math
    def test_default_territory_ids_empty(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.territory_ids == []

    @pytest.mark.math
    def test_default_heat(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.heat == pytest.approx(TC.Organization.DEFAULT_HEAT)

    @pytest.mark.math
    def test_default_is_institution(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.is_institution is False

    @pytest.mark.math
    def test_default_institutional_persistence_none(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.institutional_persistence is None

    @pytest.mark.math
    def test_default_member_node_ids_empty(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        assert org.member_node_ids == []

    @pytest.mark.math
    def test_create_with_all_fields(self) -> None:
        """Full creation with all 15 fields."""
        org = Organization(
            id="org-001",
            name="Detroit PD",
            org_type=OrgType.STATE_APPARATUS,
            class_character=ClassCharacter.BOURGEOIS,
            cohesion=0.7,
            cadre_level=0.5,
            budget=1000.0,
            legal_standing=LegalStanding.SOVEREIGN,
            consciousness_tendency=ConsciousnessTendency.LIBERAL,
            territory_ids=["t-001", "t-002"],
            headquarters_id="t-001",
            heat=0.3,
            is_institution=True,
            institutional_persistence=0.9,
            member_node_ids=["kf-001", "kf-002"],
        )
        assert org.id == "org-001"
        assert org.budget == pytest.approx(1000.0)
        assert org.territory_ids == ["t-001", "t-002"]
        assert org.headquarters_id == "t-001"
        assert org.is_institution is True
        assert org.institutional_persistence == pytest.approx(0.9)
        assert org.member_node_ids == ["kf-001", "kf-002"]


class TestOrganizationValidation:
    """Validation rules for Organization base model."""

    @pytest.mark.math
    def test_rejects_empty_id(self) -> None:
        with pytest.raises(ValidationError):
            Organization(
                id="",
                name="Test",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
            )

    @pytest.mark.math
    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            Organization(
                id="org-001",
                name="",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
            )

    @pytest.mark.math
    def test_rejects_negative_cohesion(self) -> None:
        with pytest.raises(ValidationError):
            Organization(
                id="org-001",
                name="Test",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
                cohesion=-0.1,
            )

    @pytest.mark.math
    def test_rejects_cohesion_above_one(self) -> None:
        with pytest.raises(ValidationError):
            Organization(
                id="org-001",
                name="Test",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
                cohesion=1.1,
            )

    @pytest.mark.math
    def test_rejects_negative_budget(self) -> None:
        with pytest.raises(ValidationError):
            Organization(
                id="org-001",
                name="Test",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
                budget=-10.0,
            )

    @pytest.mark.math
    def test_rejects_negative_heat(self) -> None:
        with pytest.raises(ValidationError):
            Organization(
                id="org-001",
                name="Test",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
                heat=-0.1,
            )

    @pytest.mark.math
    def test_headquarters_must_be_in_territory_ids(self) -> None:
        with pytest.raises(ValidationError, match="headquarters_id must be in territory_ids"):
            Organization(
                id="org-001",
                name="Test",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
                territory_ids=["t-001"],
                headquarters_id="t-999",
            )

    @pytest.mark.math
    def test_headquarters_none_always_valid(self) -> None:
        """headquarters_id=None is always valid."""
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
            territory_ids=["t-001"],
            headquarters_id=None,
        )
        assert org.headquarters_id is None

    @pytest.mark.math
    def test_institutional_persistence_requires_is_institution(self) -> None:
        with pytest.raises(
            ValidationError,
            match="institutional_persistence must be None when is_institution is False",
        ):
            Organization(
                id="org-001",
                name="Test",
                org_type=OrgType.CIVIL_SOCIETY,
                class_character=ClassCharacter.PROLETARIAN,
                is_institution=False,
                institutional_persistence=0.5,
            )

    @pytest.mark.math
    def test_institutional_persistence_valid_with_is_institution(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
            is_institution=True,
            institutional_persistence=0.8,
        )
        assert org.institutional_persistence == pytest.approx(0.8)

    @pytest.mark.math
    def test_accepts_boundary_cohesion_zero(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
            cohesion=0.0,
        )
        assert org.cohesion == pytest.approx(0.0)

    @pytest.mark.math
    def test_accepts_boundary_cohesion_one(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
            cohesion=1.0,
        )
        assert org.cohesion == pytest.approx(1.0)


class TestOrganizationImmutability:
    """Organization is frozen — all mutations must use model_copy."""

    @pytest.mark.math
    def test_cannot_mutate_cohesion(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
        )
        with pytest.raises(ValidationError):
            org.cohesion = 0.5  # type: ignore[misc]

    @pytest.mark.math
    def test_model_copy_produces_new_instance(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.CIVIL_SOCIETY,
            class_character=ClassCharacter.PROLETARIAN,
            cohesion=0.5,
        )
        new_org = org.model_copy(update={"cohesion": 0.8})
        assert new_org.cohesion == pytest.approx(0.8)
        assert org.cohesion == pytest.approx(0.5)  # Original unchanged


class TestOrganizationSerialization:
    """JSON serialization round-trip."""

    @pytest.mark.ledger
    def test_model_dump_json_round_trip(self) -> None:
        org = Organization(
            id="org-001",
            name="Test Org",
            org_type=OrgType.POLITICAL_FACTION,
            class_character=ClassCharacter.PROLETARIAN,
            cohesion=0.7,
        )
        json_str = org.model_dump_json()
        restored = Organization.model_validate_json(json_str)
        assert restored.id == org.id
        assert restored.cohesion == pytest.approx(org.cohesion)

    @pytest.mark.ledger
    def test_model_dump_dict(self) -> None:
        org = Organization(
            id="org-001",
            name="Test",
            org_type=OrgType.POLITICAL_FACTION,
            class_character=ClassCharacter.PROLETARIAN,
        )
        d = org.model_dump()
        assert d["id"] == "org-001"
        assert d["org_type"] == "political_faction"
        assert "cohesion" in d
