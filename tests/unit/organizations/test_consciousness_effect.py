"""Tests for consciousness effect formula (Feature 031, T020-T022).

Tests five-factor consciousness_effect(), derive_credibility(), and
aggregate_consciousness_effects(). Includes Detroit worked example.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import OrganizationDefines
from babylon.models.entities.organization import (
    Business,
    CivilSocietyOrg,
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
from babylon.organizations.consciousness import (
    aggregate_consciousness_effects,
    consciousness_effect,
    derive_credibility,
)
from babylon.organizations.types import AggregatedEffect, ConsciousnessDelta
from tests.constants import TestConstants

TC = TestConstants


class TestDeriveCredibility:
    """derive_credibility() per-subtype rules."""

    @pytest.mark.math
    def test_civil_society_uses_legitimacy(self) -> None:
        cso = CivilSocietyOrg(
            id="cso-001",
            name="Church",
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.RELIGIOUS,
            legitimacy=0.7,
        )
        defines = OrganizationDefines()
        assert derive_credibility(cso, defines) == pytest.approx(0.7)

    @pytest.mark.math
    def test_political_faction_uses_default(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="RWP",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
        )
        defines = OrganizationDefines()
        assert derive_credibility(pf, defines) == pytest.approx(
            TC.Organization.CREDIBILITY_DEFAULT_FACTION
        )

    @pytest.mark.math
    def test_state_apparatus_sovereign(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="DPD",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.MUNICIPAL,
            legal_standing=LegalStanding.SOVEREIGN,
        )
        defines = OrganizationDefines()
        assert derive_credibility(sa, defines) == pytest.approx(
            TC.Organization.CREDIBILITY_SOVEREIGN
        )

    @pytest.mark.math
    def test_state_apparatus_chartered(self) -> None:
        sa = StateApparatus(
            id="sa-001",
            name="MDOC",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.STATE,
            legal_standing=LegalStanding.CHARTERED,
        )
        defines = OrganizationDefines()
        assert derive_credibility(sa, defines) == pytest.approx(
            TC.Organization.CREDIBILITY_CHARTERED
        )

    @pytest.mark.math
    def test_state_apparatus_other_standing(self) -> None:
        """Non-SOVEREIGN/CHARTERED gets default 0.5."""
        sa = StateApparatus(
            id="sa-001",
            name="Secret",
            class_character=ClassCharacter.BOURGEOIS,
            jurisdiction=JurisdictionLevel.NATIONAL,
            legal_standing=LegalStanding.REGISTERED,
        )
        defines = OrganizationDefines()
        assert derive_credibility(sa, defines) == pytest.approx(0.5)

    @pytest.mark.math
    def test_business_uses_employment_share(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Auto",
            employment_count=5000,
        )
        defines = OrganizationDefines()
        # With community_workforce=None, defaults to 0.0
        assert derive_credibility(biz, defines) == pytest.approx(0.0)

    @pytest.mark.math
    def test_business_with_workforce(self) -> None:
        biz = Business(
            id="biz-001",
            name="Ford",
            class_character=ClassCharacter.BOURGEOIS,
            sector="Auto",
            employment_count=1500,
        )
        defines = OrganizationDefines()
        # 1500 / 10000 = 0.15
        cred = derive_credibility(biz, defines, community_workforce=10000)
        assert cred == pytest.approx(0.15)


class TestConsciousnessEffect:
    """consciousness_effect(): five-factor product formula."""

    @pytest.mark.math
    def test_revolutionary_positive_ci_delta(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="RWP",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
            cadre_level=0.7,
            cohesion=0.6,
            consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        )
        defines = OrganizationDefines()
        delta = consciousness_effect(pf, defines)
        # 0.15 × 0.7 × 0.6 × 0.5 = 0.0315
        assert isinstance(delta, ConsciousnessDelta)
        assert delta.collective_identity_delta == pytest.approx(TC.Organization.RWP_CI_DELTA)
        assert delta.tendency_pressure == ConsciousnessTendency.REVOLUTIONARY
        assert delta.tendency_magnitude == pytest.approx(abs(TC.Organization.RWP_CI_DELTA))

    @pytest.mark.math
    def test_liberal_negative_ci_delta(self) -> None:
        cso = CivilSocietyOrg(
            id="cso-001",
            name="FBC",
            class_character=ClassCharacter.PROLETARIAN,
            service_type=ServiceType.RELIGIOUS,
            legitimacy=0.7,
            cadre_level=0.3,
            cohesion=0.8,
            consciousness_tendency=ConsciousnessTendency.LIBERAL,
        )
        defines = OrganizationDefines()
        delta = consciousness_effect(cso, defines)
        # -0.05 × 0.3 × 0.8 × 0.7 = -0.0084
        assert delta.collective_identity_delta == pytest.approx(TC.Organization.CHURCH_CI_DELTA)
        assert delta.tendency_pressure == ConsciousnessTendency.LIBERAL
        assert delta.tendency_magnitude == pytest.approx(abs(TC.Organization.CHURCH_CI_DELTA))

    @pytest.mark.math
    def test_fascist_zero_ci_delta(self) -> None:
        """FASCIST tendency produces zero CI delta, non-zero tendency pressure."""
        pf = PoliticalFaction(
            id="pf-fasc",
            name="Patriot Front",
            class_character=ClassCharacter.LABOR_ARISTOCRATIC,
            ideology="White nationalism",
            cadre_level=0.5,
            cohesion=0.4,
            consciousness_tendency=ConsciousnessTendency.FASCIST,
        )
        defines = OrganizationDefines()
        delta = consciousness_effect(pf, defines)
        assert delta.collective_identity_delta == pytest.approx(0.0)
        assert delta.tendency_pressure == ConsciousnessTendency.FASCIST
        # magnitude = 0.10 × 0.5 × 0.4 × 0.5 = 0.01
        assert delta.tendency_magnitude == pytest.approx(0.01)

    @pytest.mark.math
    def test_zero_cohesion_short_circuit(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="Dead Org",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
            cadre_level=0.7,
            cohesion=0.0,
            consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        )
        defines = OrganizationDefines()
        delta = consciousness_effect(pf, defines)
        assert delta.collective_identity_delta == pytest.approx(0.0)
        assert delta.tendency_magnitude == pytest.approx(0.0)

    @pytest.mark.math
    def test_zero_cadre_short_circuit(self) -> None:
        pf = PoliticalFaction(
            id="pf-001",
            name="Leaderless",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
            cadre_level=0.0,
            cohesion=0.8,
            consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        )
        defines = OrganizationDefines()
        delta = consciousness_effect(pf, defines)
        assert delta.collective_identity_delta == pytest.approx(0.0)
        assert delta.tendency_magnitude == pytest.approx(0.0)

    @pytest.mark.math
    def test_source_org_id_matches(self) -> None:
        pf = PoliticalFaction(
            id="pf-rwp",
            name="RWP",
            class_character=ClassCharacter.PROLETARIAN,
            ideology="ML",
            cadre_level=0.5,
            cohesion=0.5,
            consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
        )
        defines = OrganizationDefines()
        delta = consciousness_effect(pf, defines)
        assert delta.source_org_id == "pf-rwp"


class TestAggregateConsciousnessEffects:
    """aggregate_consciousness_effects(): concurrent org effects on a community."""

    @pytest.mark.math
    def test_empty_deltas(self) -> None:
        result = aggregate_consciousness_effects([], current_ci=0.5)
        assert isinstance(result, AggregatedEffect)
        assert result.total_ci_delta == pytest.approx(0.0)
        assert result.dominant_tendency is None
        assert result.new_ci == pytest.approx(0.5)

    @pytest.mark.math
    def test_single_delta(self) -> None:
        delta = ConsciousnessDelta(
            collective_identity_delta=0.1,
            tendency_pressure=ConsciousnessTendency.REVOLUTIONARY,
            tendency_magnitude=0.1,
            source_org_id="pf-001",
        )
        result = aggregate_consciousness_effects([delta], current_ci=0.3)
        assert result.total_ci_delta == pytest.approx(0.1)
        assert result.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert result.new_ci == pytest.approx(0.4)

    @pytest.mark.math
    def test_clamped_upper_bound(self) -> None:
        delta = ConsciousnessDelta(
            collective_identity_delta=0.8,
            tendency_pressure=ConsciousnessTendency.REVOLUTIONARY,
            tendency_magnitude=0.8,
            source_org_id="pf-001",
        )
        result = aggregate_consciousness_effects([delta], current_ci=0.5)
        assert result.new_ci == pytest.approx(1.0)

    @pytest.mark.math
    def test_clamped_lower_bound(self) -> None:
        delta = ConsciousnessDelta(
            collective_identity_delta=-0.8,
            tendency_pressure=ConsciousnessTendency.LIBERAL,
            tendency_magnitude=0.8,
            source_org_id="cso-001",
        )
        result = aggregate_consciousness_effects([delta], current_ci=0.3)
        assert result.new_ci == pytest.approx(0.0)

    @pytest.mark.math
    def test_detroit_worked_example(self) -> None:
        """Full Detroit scenario from consciousness-effect-contract.md."""
        rwp_delta = ConsciousnessDelta(
            collective_identity_delta=TC.Organization.RWP_CI_DELTA,
            tendency_pressure=ConsciousnessTendency.REVOLUTIONARY,
            tendency_magnitude=abs(TC.Organization.RWP_CI_DELTA),
            source_org_id="pf-rwp",
        )
        church_delta = ConsciousnessDelta(
            collective_identity_delta=TC.Organization.CHURCH_CI_DELTA,
            tendency_pressure=ConsciousnessTendency.LIBERAL,
            tendency_magnitude=abs(TC.Organization.CHURCH_CI_DELTA),
            source_org_id="cso-fbc",
        )
        ford_delta = ConsciousnessDelta(
            collective_identity_delta=TC.Organization.FORD_CI_DELTA,
            tendency_pressure=ConsciousnessTendency.LIBERAL,
            tendency_magnitude=abs(TC.Organization.FORD_CI_DELTA),
            source_org_id="biz-ford",
        )

        result = aggregate_consciousness_effects(
            [rwp_delta, church_delta, ford_delta],
            current_ci=0.5,
        )

        assert result.total_ci_delta == pytest.approx(
            TC.Organization.DETROIT_TOTAL_CI_DELTA, abs=1e-6
        )
        assert result.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert result.new_ci == pytest.approx(
            0.5 + TC.Organization.DETROIT_TOTAL_CI_DELTA, abs=1e-6
        )

    @pytest.mark.math
    def test_dominant_tendency_strongest_wins(self) -> None:
        """Multiple tendencies compete — strongest weighted wins."""
        rev = ConsciousnessDelta(
            collective_identity_delta=0.05,
            tendency_pressure=ConsciousnessTendency.REVOLUTIONARY,
            tendency_magnitude=0.05,
            source_org_id="pf-001",
        )
        lib = ConsciousnessDelta(
            collective_identity_delta=-0.02,
            tendency_pressure=ConsciousnessTendency.LIBERAL,
            tendency_magnitude=0.02,
            source_org_id="cso-001",
        )
        result = aggregate_consciousness_effects([rev, lib], current_ci=0.5)
        assert result.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
