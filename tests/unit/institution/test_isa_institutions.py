"""Unit tests for ISA institution scenarios (Feature 040, US2).

Validates:
- SC-002: ISA_EDUCATIONAL (Detroit Public Schools) with structural selectivity
- SC-004: ISA_RELIGIOUS (Catholic Church) with community embeddedness
- ISA-specific model properties and lifecycle
"""

from __future__ import annotations

import pytest

from babylon.models.enums import (
    ApparatusType,
    ClassInscription,
    LifecyclePhase,
    SocialFunction,
)

from .conftest import make_institution, make_isa_institution


class TestISAEducational:
    """SC-002: Detroit Public Schools as ISA_EDUCATIONAL."""

    def test_apparatus_type(self) -> None:
        """DPS should be ISA_EDUCATIONAL."""
        dps = make_isa_institution()
        assert dps.apparatus_type == ApparatusType.ISA_EDUCATIONAL

    def test_social_function(self) -> None:
        """DPS should have EDUCATION social function."""
        dps = make_isa_institution()
        assert dps.social_function == SocialFunction.EDUCATION

    def test_class_inscription_contested(self) -> None:
        """DPS should have CONTESTED class inscription."""
        dps = make_isa_institution()
        assert dps.class_inscription == ClassInscription.CONTESTED

    def test_lifecycle_dependent(self) -> None:
        """DPS should be in D_DEPENDENT lifecycle phase."""
        dps = make_isa_institution()
        assert dps.lifecycle_function == LifecyclePhase.D_DEPENDENT

    def test_low_budget_independence(self) -> None:
        """DPS reproduction should have low budget independence."""
        dps = make_isa_institution()
        assert dps.reproduction.budget_independence == 0.3

    def test_no_jurisdiction(self) -> None:
        """ISA should have no jurisdiction (RSA-only field)."""
        dps = make_isa_institution()
        assert dps.jurisdiction is None

    def test_territory_footprint(self) -> None:
        """DPS should have multiple territory IDs."""
        dps = make_isa_institution()
        assert len(dps.territory_ids) == 2

    @pytest.mark.math
    def test_reproduction_capacity(self) -> None:
        """DPS reproduction capacity reflects low budget independence."""
        dps = make_isa_institution()
        # 4 bools true => 4/4 = 1.0, budget_independence = 0.3
        # capacity = 1.0 * 0.7 + 0.3 * 0.3 = 0.79
        expected = 1.0 * 0.7 + 0.3 * 0.3
        assert abs(dps.reproduction.reproduction_capacity - expected) < 1e-6


class TestISAReligious:
    """SC-004: Catholic Church as ISA_RELIGIOUS."""

    def test_isa_religious_apparatus_type(self) -> None:
        """Catholic Church should be ISA_RELIGIOUS."""
        church = make_institution(
            id="catholic_church",
            name="Catholic Church",
            apparatus_type=ApparatusType.ISA_RELIGIOUS,
            social_function=SocialFunction.WORSHIP,
            class_inscription=ClassInscription.CONTESTED,
            jurisdiction=None,
            territory_ids=["T001", "T002", "T003"],
        )
        assert church.apparatus_type == ApparatusType.ISA_RELIGIOUS

    def test_isa_religious_social_function(self) -> None:
        """Catholic Church should have WORSHIP social function."""
        church = make_institution(
            id="catholic_church",
            name="Catholic Church",
            apparatus_type=ApparatusType.ISA_RELIGIOUS,
            social_function=SocialFunction.WORSHIP,
            class_inscription=ClassInscription.CONTESTED,
            jurisdiction=None,
        )
        assert church.social_function == SocialFunction.WORSHIP

    def test_isa_religious_no_jurisdiction(self) -> None:
        """ISA_RELIGIOUS should not have jurisdiction."""
        church = make_institution(
            id="catholic_church",
            name="Catholic Church",
            apparatus_type=ApparatusType.ISA_RELIGIOUS,
            social_function=SocialFunction.WORSHIP,
            class_inscription=ClassInscription.CONTESTED,
            jurisdiction=None,
        )
        assert church.jurisdiction is None

    def test_isa_religious_broad_territory(self) -> None:
        """Catholic Church should span multiple territories."""
        church = make_institution(
            id="catholic_church",
            name="Catholic Church",
            apparatus_type=ApparatusType.ISA_RELIGIOUS,
            social_function=SocialFunction.WORSHIP,
            class_inscription=ClassInscription.CONTESTED,
            jurisdiction=None,
            territory_ids=["T001", "T002", "T003"],
        )
        assert len(church.territory_ids) == 3


class TestISAFamilyAndCommunications:
    """Additional ISA subtypes for coverage."""

    def test_isa_communications(self) -> None:
        """ISA_COMMUNICATIONS should have COMMUNICATION social function."""
        media = make_institution(
            id="fox_news",
            name="Fox News",
            apparatus_type=ApparatusType.ISA_COMMUNICATIONS,
            social_function=SocialFunction.COMMUNICATION,
            class_inscription=ClassInscription.BOURGEOIS,
            jurisdiction=None,
        )
        assert media.apparatus_type == ApparatusType.ISA_COMMUNICATIONS
        assert media.social_function == SocialFunction.COMMUNICATION

    def test_isa_family(self) -> None:
        """ISA_FAMILY should be valid apparatus type."""
        family = make_institution(
            id="nuclear_family_norm",
            name="Nuclear Family Norm",
            apparatus_type=ApparatusType.ISA_FAMILY,
            social_function=SocialFunction.CARE,
            class_inscription=ClassInscription.CONTESTED,
            jurisdiction=None,
        )
        assert family.apparatus_type == ApparatusType.ISA_FAMILY


class TestISAModifications:
    """ISA institutions with custom overrides."""

    def test_isa_with_custom_action_modifiers(self) -> None:
        """ISA institution can override action modifiers."""
        school = make_isa_institution(
            action_modifiers={"educate": 0.5, "recruit": 0.6},
        )
        assert school.action_modifiers == {"educate": 0.5, "recruit": 0.6}

    def test_isa_with_liberal_hegemony(self) -> None:
        """ISA with liberal-dominated balance reports LIBERAL hegemonic fraction."""
        from babylon.models.enums import RulingClassFraction

        school = make_isa_institution()
        assert school.internal_balance.hegemonic_fraction == (
            RulingClassFraction.LIBERAL_TECHNOCRATIC
        )
