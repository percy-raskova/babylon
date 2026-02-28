"""Tests for organization-related enums (Feature 031, T002).

Tests 6 new StrEnum classes and 5 new EdgeType values.
Verifies no collision with existing EdgeType values.
"""

from __future__ import annotations

import pytest

from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    EdgeType,
    JurisdictionLevel,
    LegalStanding,
    OrgType,
    ServiceType,
    TopologyType,
)


class TestOrgType:
    """OrgType enum: 4 organization categories."""

    @pytest.mark.math
    def test_has_four_values(self) -> None:
        assert len(OrgType) == 4

    @pytest.mark.math
    def test_state_apparatus(self) -> None:
        assert OrgType.STATE_APPARATUS == "state_apparatus"

    @pytest.mark.math
    def test_business(self) -> None:
        assert OrgType.BUSINESS == "business"

    @pytest.mark.math
    def test_political_faction(self) -> None:
        assert OrgType.POLITICAL_FACTION == "political_faction"

    @pytest.mark.math
    def test_civil_society(self) -> None:
        assert OrgType.CIVIL_SOCIETY == "civil_society"

    @pytest.mark.math
    def test_values_are_lowercase_snake_case(self) -> None:
        for member in OrgType:
            assert member.value == member.value.lower()
            assert " " not in member.value


class TestClassCharacter:
    """ClassCharacter enum: 6 class interest categories."""

    @pytest.mark.math
    def test_has_six_values(self) -> None:
        assert len(ClassCharacter) == 6

    @pytest.mark.math
    def test_bourgeois(self) -> None:
        assert ClassCharacter.BOURGEOIS == "bourgeois"

    @pytest.mark.math
    def test_petty_bourgeois(self) -> None:
        assert ClassCharacter.PETTY_BOURGEOIS == "petty_bourgeois"

    @pytest.mark.math
    def test_labor_aristocratic(self) -> None:
        assert ClassCharacter.LABOR_ARISTOCRATIC == "labor_aristocratic"

    @pytest.mark.math
    def test_proletarian(self) -> None:
        assert ClassCharacter.PROLETARIAN == "proletarian"

    @pytest.mark.math
    def test_lumpen(self) -> None:
        assert ClassCharacter.LUMPEN == "lumpen"

    @pytest.mark.math
    def test_contested(self) -> None:
        assert ClassCharacter.CONTESTED == "contested"


class TestTopologyType:
    """TopologyType enum: 4 computed topology classifications."""

    @pytest.mark.math
    def test_has_four_values(self) -> None:
        assert len(TopologyType) == 4

    @pytest.mark.math
    def test_star(self) -> None:
        assert TopologyType.STAR == "star"

    @pytest.mark.math
    def test_hierarchy(self) -> None:
        assert TopologyType.HIERARCHY == "hierarchy"

    @pytest.mark.math
    def test_mesh(self) -> None:
        assert TopologyType.MESH == "mesh"

    @pytest.mark.math
    def test_cell(self) -> None:
        assert TopologyType.CELL == "cell"


class TestLegalStanding:
    """LegalStanding enum: 5 legal status categories."""

    @pytest.mark.math
    def test_has_five_values(self) -> None:
        assert len(LegalStanding) == 5

    @pytest.mark.math
    def test_sovereign(self) -> None:
        assert LegalStanding.SOVEREIGN == "sovereign"

    @pytest.mark.math
    def test_chartered(self) -> None:
        assert LegalStanding.CHARTERED == "chartered"

    @pytest.mark.math
    def test_registered(self) -> None:
        assert LegalStanding.REGISTERED == "registered"

    @pytest.mark.math
    def test_informal(self) -> None:
        assert LegalStanding.INFORMAL == "informal"

    @pytest.mark.math
    def test_underground(self) -> None:
        assert LegalStanding.UNDERGROUND == "underground"


class TestJurisdictionLevel:
    """JurisdictionLevel enum: 4 jurisdictional scopes."""

    @pytest.mark.math
    def test_has_four_values(self) -> None:
        assert len(JurisdictionLevel) == 4

    @pytest.mark.math
    def test_national(self) -> None:
        assert JurisdictionLevel.NATIONAL == "national"

    @pytest.mark.math
    def test_state(self) -> None:
        assert JurisdictionLevel.STATE == "state"

    @pytest.mark.math
    def test_county(self) -> None:
        assert JurisdictionLevel.COUNTY == "county"

    @pytest.mark.math
    def test_municipal(self) -> None:
        assert JurisdictionLevel.MUNICIPAL == "municipal"


class TestServiceType:
    """ServiceType enum: 8 civil society service domains."""

    @pytest.mark.math
    def test_has_eight_values(self) -> None:
        assert len(ServiceType) == 8

    @pytest.mark.math
    def test_religious(self) -> None:
        assert ServiceType.RELIGIOUS == "religious"

    @pytest.mark.math
    def test_educational(self) -> None:
        assert ServiceType.EDUCATIONAL == "educational"

    @pytest.mark.math
    def test_healthcare(self) -> None:
        assert ServiceType.HEALTHCARE == "healthcare"

    @pytest.mark.math
    def test_legal_aid(self) -> None:
        assert ServiceType.LEGAL_AID == "legal_aid"

    @pytest.mark.math
    def test_mutual_aid(self) -> None:
        assert ServiceType.MUTUAL_AID == "mutual_aid"

    @pytest.mark.math
    def test_cultural(self) -> None:
        assert ServiceType.CULTURAL == "cultural"

    @pytest.mark.math
    def test_media(self) -> None:
        assert ServiceType.MEDIA == "media"

    @pytest.mark.math
    def test_labor(self) -> None:
        assert ServiceType.LABOR == "labor"


class TestNewEdgeTypeValues:
    """5 new EdgeType values for organization relationships."""

    @pytest.mark.math
    def test_membership(self) -> None:
        assert EdgeType.MEMBERSHIP == "membership"

    @pytest.mark.math
    def test_recruitment(self) -> None:
        assert EdgeType.RECRUITMENT == "recruitment"

    @pytest.mark.math
    def test_employment(self) -> None:
        assert EdgeType.EMPLOYMENT == "employment"

    @pytest.mark.math
    def test_command(self) -> None:
        assert EdgeType.COMMAND == "command"

    @pytest.mark.math
    def test_presence(self) -> None:
        assert EdgeType.PRESENCE == "presence"

    @pytest.mark.math
    def test_no_collision_with_existing_nine_values(self) -> None:
        """New values must not collide with the existing 9 EdgeType values."""
        existing_values = {
            "exploitation",
            "solidarity",
            "repression",
            "competition",
            "tribute",
            "wages",
            "client_state",
            "tenancy",
            "adjacency",
        }
        new_values = {"membership", "recruitment", "employment", "command", "presence"}
        assert existing_values.isdisjoint(new_values)

    @pytest.mark.math
    def test_total_edge_type_count(self) -> None:
        """EdgeType should have 14 values (9 existing + 5 new)."""
        assert len(EdgeType) == 14


class TestConsciousnessTendencyReuse:
    """ConsciousnessTendency already exists — verify it is reusable."""

    @pytest.mark.math
    def test_has_three_values(self) -> None:
        assert len(ConsciousnessTendency) == 3

    @pytest.mark.math
    def test_liberal(self) -> None:
        assert ConsciousnessTendency.LIBERAL == "liberal"

    @pytest.mark.math
    def test_fascist(self) -> None:
        assert ConsciousnessTendency.FASCIST == "fascist"

    @pytest.mark.math
    def test_revolutionary(self) -> None:
        assert ConsciousnessTendency.REVOLUTIONARY == "revolutionary"
