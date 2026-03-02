"""Unit tests for RSA institution scenarios (Feature 040, US1).

Validates:
- SC-001: DOJ instantiation with FBI housed, persistence after org destruction
- SC-006: Multiple conflicting orgs in same institution
- Degradation-not-destruction: empty housed_org_ids preserves institution
"""

from __future__ import annotations

import pytest

from babylon.models.enums import (
    ApparatusType,
    RulingClassFraction,
    SocialFunction,
)

from .conftest import make_institution, make_relation


class TestRSAInstantiation:
    """SC-001: DOJ as RSA_JUDICIAL with FBI housed."""

    def test_doj_apparatus_type(self) -> None:
        """DOJ should be RSA_JUDICIAL."""
        doj = make_institution()
        assert doj.apparatus_type == ApparatusType.RSA_JUDICIAL

    def test_doj_persistence_attributes(self) -> None:
        """DOJ should have persistence attributes within valid range."""
        doj = make_institution()
        assert 0.0 <= doj.formalization_level <= 1.0
        assert 0.0 <= doj.institutional_inertia <= 1.0
        assert 0.0 <= doj.legitimacy <= 1.0
        assert doj.formalization_level == 0.95
        assert doj.institutional_inertia == 0.8

    def test_doj_territory_footprint(self) -> None:
        """DOJ should report territory_ids for its footprint."""
        doj = make_institution()
        assert doj.territory_ids == ["us_national"]

    def test_doj_jurisdiction(self) -> None:
        """DOJ should have jurisdiction set for RSA type."""
        doj = make_institution()
        assert doj.jurisdiction == frozenset(["national"])

    def test_doj_housed_org(self) -> None:
        """DOJ should house the FBI organization."""
        doj = make_institution()
        assert "fbi" in doj.housed_org_ids

    def test_doj_spawning_blueprint(self) -> None:
        """DOJ should have a spawning blueprint for replacement orgs."""
        doj = make_institution()
        assert len(doj.spawning_blueprints) == 1
        bp = doj.spawning_blueprints[0]
        assert bp.org_type.value == "state_apparatus"

    @pytest.mark.math
    def test_doj_reproduction_capacity_high(self) -> None:
        """DOJ with full reproduction should have capacity > 0.8."""
        doj = make_institution()
        assert doj.reproduction.reproduction_capacity > 0.8


class TestConflictingOrgs:
    """SC-006: Multiple conflicting orgs in same institution."""

    def test_multiple_housed_orgs(self) -> None:
        """Institution should accept multiple housed org IDs."""
        doj = make_institution(
            housed_org_ids=["fbi_civil_rights", "fbi_counterintel"],
        )
        assert len(doj.housed_org_ids) == 2

    def test_conflicting_factional_alignments(self) -> None:
        """Separate relations can have different factional alignments."""
        rel_liberal = make_relation(
            organization_id="fbi_civil_rights",
            factional_alignment=RulingClassFraction.LIBERAL_TECHNOCRATIC,
        )
        rel_revanchist = make_relation(
            organization_id="fbi_counterintel",
            factional_alignment=RulingClassFraction.REVANCHIST_FASCIST,
        )
        assert rel_liberal.factional_alignment != rel_revanchist.factional_alignment
        assert rel_liberal.institution_id == rel_revanchist.institution_id


class TestDegradationNotDestruction:
    """SC-001 continuation: Destroying housed orgs degrades but doesn't destroy."""

    def test_remove_all_housed_orgs(self) -> None:
        """Removing all housed orgs should yield empty list but institution persists."""
        doj = make_institution()
        degraded = doj.model_copy(update={"housed_org_ids": []})

        # Institution persists
        assert degraded.id == "doj"
        assert degraded.housed_org_ids == []

        # Social function intact
        assert degraded.social_function == SocialFunction.ADJUDICATION

        # Legal authorities intact
        assert "federal_prosecution" in degraded.legal_authorities

        # Fixed assets intact
        assert degraded.territory_ids == ["us_national"]

        # Reproduction capacity intact
        assert degraded.reproduction.reproduction_capacity > 0.0

    def test_degraded_institution_can_reference_blueprint(self) -> None:
        """Degraded institution should still have spawning blueprints."""
        doj = make_institution()
        degraded = doj.model_copy(update={"housed_org_ids": []})
        assert len(degraded.spawning_blueprints) == 1

    def test_military_rsa_persistence(self) -> None:
        """RSA_MILITARY should persist with territory footprint."""
        military = make_institution(
            id="us_army",
            name="US Army",
            apparatus_type=ApparatusType.RSA_MILITARY,
            social_function=SocialFunction.MILITARY_DEFENSE,
            territory_ids=["fort_knox", "fort_bragg"],
            jurisdiction=frozenset(["national"]),
        )
        assert military.apparatus_type == ApparatusType.RSA_MILITARY
        assert len(military.territory_ids) == 2
