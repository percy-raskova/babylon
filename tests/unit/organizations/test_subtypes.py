"""Tests for Organization subtypes and discriminated union (Feature 031, T009).

Tests StateApparatus, Business, PoliticalFaction, CivilSocietyOrg subtypes
and the OrganizationType discriminated union dispatch.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from babylon.models.entities.organization import (
    Business,
    CivilSocietyOrg,
    Organization,
    OrganizationType,
    PoliticalFaction,
    StateApparatus,
)
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    JurisdictionLevel,
    LegalStanding,
    OrgType,
    ServiceType,
)
from tests.constants import TestConstants

TC = TestConstants


class TestStateApparatus:
    """StateApparatus subtype-specific fields and defaults."""

    @pytest.mark.math
    def test_create_minimal(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="Detroit PD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert sa.org_type == OrgType.STATE_APPARATUS
        assert sa.jurisdiction == JurisdictionLevel.MUNICIPAL

    @pytest.mark.math
    def test_default_legal_standing_sovereign(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert sa.legal_standing == LegalStanding.SOVEREIGN

    @pytest.mark.math
    def test_default_violence_capacity(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert sa.violence_capacity == pytest.approx(0.0)

    @pytest.mark.math
    def test_default_surveillance_capacity(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert sa.surveillance_capacity == pytest.approx(0.0)

    @pytest.mark.math
    def test_has_intel_methodology(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert sa.intel_methodology is not None
        assert sa.intel_methodology.observation_ceiling == pytest.approx(0.2)

    @pytest.mark.math
    def test_is_subclass_of_organization(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert isinstance(sa, Organization)

    @pytest.mark.math
    def test_rejects_negative_violence_capacity(self) -> None:
        with pytest.raises(ValidationError):
            StateApparatus(
                id="sa-001",
                name="DPD",
                class_character=ClassCharacter.BOURGEOIS,
                jurisdiction=JurisdictionLevel.MUNICIPAL,
                violence_capacity=-0.1,
            )

    @pytest.mark.math
    def test_default_faction_balance_is_none(self) -> None:
        """None gates the org onto the legacy static priority queue."""
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert sa.faction_balance is None

    @pytest.mark.math
    def test_default_rng_seed_is_none(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
        )
        assert sa.rng_seed is None

    @pytest.mark.math
    def test_faction_balance_round_trips_through_model_dump(self) -> None:
        """Feature 039's ``_try_state_ai_dispatch`` reads faction_balance back
        off graph node attrs as a plain dict (``**org.model_dump()``) and
        reconstructs it with ``FactionBalance(**faction_data)`` — this must
        survive that dict round trip byte-for-byte on the primitive fields.
        """
        from babylon.models.entities.state_apparatus_ai import FactionBalance

        balance = FactionBalance(
            finance_capital=0.3,
            security_state=0.5,
            settler_populist=0.2,
            stability=0.6,
            legitimacy=0.5,
        )
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
            faction_balance=balance,
            rng_seed=0,
        )
        dumped = sa.model_dump()
        assert dumped["faction_balance"]["finance_capital"] == pytest.approx(0.3)
        assert dumped["faction_balance"]["security_state"] == pytest.approx(0.5)
        assert dumped["rng_seed"] == 0

        reconstructed = FactionBalance(**dumped["faction_balance"])
        assert reconstructed.finance_capital == pytest.approx(0.3)
        assert reconstructed.security_state == pytest.approx(0.5)
        assert reconstructed.settler_populist == pytest.approx(0.2)


class TestBusiness:
    """Business subtype-specific fields and defaults."""

    @pytest.mark.math
    def test_create_minimal(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford Motor Company",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Automotive Manufacturing",
        )
        assert biz.org_type == OrgType.BUSINESS
        assert biz.sector == "Automotive Manufacturing"

    @pytest.mark.math
    def test_default_employment_count(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Auto",
        )
        assert biz.employment_count == 0

    @pytest.mark.math
    def test_default_surplus_extraction_rate(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Auto",
        )
        assert biz.surplus_extraction_rate == pytest.approx(0.0)

    @pytest.mark.math
    def test_default_revenue(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Auto",
        )
        assert biz.revenue == pytest.approx(0.0)

    @pytest.mark.math
    def test_custom_employment_count(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Auto",
            employment_count=TC.Organization.FORD_EMPLOYMENT_COUNT,
        )
        assert biz.employment_count == TC.Organization.FORD_EMPLOYMENT_COUNT

    @pytest.mark.math
    def test_rejects_negative_employment_count(self) -> None:
        with pytest.raises(ValidationError):
            Business(
                id="biz-001",
                name="Ford",
                class_character=ClassCharacter.BOURGEOIS,
                sector="Auto",
                employment_count=-1,
            )

    @pytest.mark.math
    def test_rejects_empty_sector(self) -> None:
        with pytest.raises(ValidationError):
            Business(
                id="biz-001",
                name="Ford",
                class_character=ClassCharacter.BOURGEOIS,
                sector="",
            )

    @pytest.mark.math
    def test_is_subclass_of_organization(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Auto",
        )
        assert isinstance(biz, Organization)


class TestPoliticalFaction:
    """PoliticalFaction subtype-specific fields and defaults."""

    @pytest.mark.math
    def test_create_minimal(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="Revolutionary Workers Party",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="Marxism-Leninism",
        )
        assert pf.org_type == OrgType.POLITICAL_FACTION
        assert pf.ideology == "Marxism-Leninism"

    @pytest.mark.math
    def test_default_is_player(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="RWP",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
        )
        assert pf.is_player is False

    @pytest.mark.math
    def test_default_relationship_to_player(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="RWP",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
        )
        assert pf.relationship_to_player == "neutral"

    @pytest.mark.math
    def test_rejects_empty_ideology(self) -> None:
        with pytest.raises(ValidationError):
            PoliticalFaction(
                id="pf-001",
                name="RWP",
                class_character=ClassCharacter.PROLETARIAN,
                ideology="",
            )

    @pytest.mark.math
    def test_is_subclass_of_organization(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="RWP",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
        )
        assert isinstance(pf, Organization)


class TestCivilSocietyOrg:
    """CivilSocietyOrg subtype-specific fields and defaults."""

    @pytest.mark.math
    def test_create_minimal(self) -> None:
        cso = CivilSocietyOrg(
            id="cso-001",
            name="First Baptist Church",
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.RELIGIOUS,
        )
        assert cso.org_type == OrgType.CIVIL_SOCIETY
        assert cso.service_type == ServiceType.RELIGIOUS

    @pytest.mark.math
    def test_default_legitimacy(self) -> None:
        cso = CivilSocietyOrg(
            id="cso-001",
            name="FBC",
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.RELIGIOUS,
        )
        assert cso.legitimacy == pytest.approx(TC.Organization.DEFAULT_LEGITIMACY)

    @pytest.mark.math
    def test_custom_legitimacy(self) -> None:
        cso = CivilSocietyOrg(
            id="cso-001",
            name="FBC",
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.RELIGIOUS,
            legitimacy=TC.Organization.CHURCH_LEGITIMACY,
        )
        assert cso.legitimacy == pytest.approx(TC.Organization.CHURCH_LEGITIMACY)

    @pytest.mark.math
    def test_rejects_negative_legitimacy(self) -> None:
        with pytest.raises(ValidationError):
            CivilSocietyOrg(
                id="cso-001",
                name="FBC",
                class_character=ClassCharacter.PROLETARIAN,
                service_type=ServiceType.RELIGIOUS,
                legitimacy=-0.1,
            )

    @pytest.mark.math
    def test_is_subclass_of_organization(self) -> None:
        cso = CivilSocietyOrg(
            id="cso-001",
            name="FBC",
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.RELIGIOUS,
        )
        assert isinstance(cso, Organization)


class TestDiscriminatedUnion:
    """OrganizationType discriminated union dispatch."""

    @pytest.mark.math
    def test_dispatches_state_apparatus(self) -> None:
        adapter = TypeAdapter(OrganizationType)
        data = {
            "id": "sa-001",
            "name": "DPD",
            "org_type": "state_apparatus",
            "class_character": "bourgeois",
            "jurisdiction": "municipal",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, StateApparatus)

    @pytest.mark.math
    def test_dispatches_business(self) -> None:
        adapter = TypeAdapter(OrganizationType)
        data = {
            "id": "biz-001",
            "name": "Ford",
            "org_type": "business",
            "class_character": "bourgeois",
            "sector": "Auto",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, Business)

    @pytest.mark.math
    def test_dispatches_political_faction(self) -> None:
        adapter = TypeAdapter(OrganizationType)
        data = {
            "id": "pf-001",
            "name": "RWP",
            "org_type": "political_faction",
            "class_character": "proletarian",
            "ideology": "ML",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, PoliticalFaction)

    @pytest.mark.math
    def test_dispatches_civil_society(self) -> None:
        adapter = TypeAdapter(OrganizationType)
        data = {
            "id": "cso-001",
            "name": "FBC",
            "org_type": "civil_society",
            "class_character": "proletarian",
            "service_type": "religious",
        }
        result = adapter.validate_python(data)
        assert isinstance(result, CivilSocietyOrg)

    @pytest.mark.math
    def test_rejects_unknown_org_type(self) -> None:
        adapter = TypeAdapter(OrganizationType)
        data = {
            "id": "x-001",
            "name": "Unknown",
            "org_type": "unknown_type",
            "class_character": "proletarian",
        }
        with pytest.raises(ValidationError):
            adapter.validate_python(data)

    @pytest.mark.math
    def test_all_subtypes_share_base_fields(self) -> None:
        """All subtypes have the 15 base Organization fields."""
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
            consciousness_tendency=ConsciousnessTendency.FASCIST,
        )
        assert sa.consciousness_tendency == ConsciousnessTendency.FASCIST
        assert sa.cohesion == pytest.approx(TC.Organization.DEFAULT_COHESION)
