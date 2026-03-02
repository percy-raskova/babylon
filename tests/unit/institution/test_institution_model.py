"""Unit tests for Institution entity models (Feature 040, Phase 2).

Tests cover:
- InternalBalanceOfForces: sum validator, hegemonic_fraction computed field
- ReproductionMechanism: reproduction_capacity computation
- SpawningBlueprint: construction
- InstitutionOrgRelation: defaults and constraints
- Institution: cross-field validators, frozen immutability
- Event types: FactionShiftEvent, ReproductionEvent, BonapartistModeEvent
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.models.entities.institution import (
    BonapartistModeEvent,
    FactionShiftEvent,
    InstitutionOrgRelation,
    InternalBalanceOfForces,
    ReproductionEvent,
    ReproductionMechanism,
    SpawningBlueprint,
)
from babylon.models.enums import (
    ApparatusType,
    ClassCharacter,
    ClassInscription,
    OrgType,
    RulingClassFraction,
    SocialFunction,
)

from .conftest import make_balance, make_institution, make_relation, make_reproduction

# =============================================================================
# InternalBalanceOfForces
# =============================================================================


class TestInternalBalanceOfForces:
    """Tests for the InternalBalanceOfForces model."""

    @pytest.mark.math
    def test_valid_weights(self) -> None:
        """Weights summing to 1.0 should be accepted."""
        b = make_balance()
        assert b.liberal_technocratic == 0.5
        assert b.revanchist_fascist == 0.3
        assert b.institutionalist_bonapartist == 0.2

    @pytest.mark.math
    def test_boundary_tolerance_low(self) -> None:
        """Weights summing to 0.99 should be accepted (tolerance)."""
        b = InternalBalanceOfForces(
            liberal_technocratic=0.49,
            revanchist_fascist=0.30,
            institutionalist_bonapartist=0.20,
        )
        assert b.liberal_technocratic == 0.49

    @pytest.mark.math
    def test_boundary_tolerance_high(self) -> None:
        """Weights summing to 1.01 should be accepted (tolerance)."""
        b = InternalBalanceOfForces(
            liberal_technocratic=0.51,
            revanchist_fascist=0.30,
            institutionalist_bonapartist=0.20,
        )
        assert b.liberal_technocratic == 0.51

    @pytest.mark.math
    def test_invalid_weights_too_high(self) -> None:
        """Weights summing to > 1.01 should be rejected."""
        with pytest.raises(ValidationError, match="sum to 1.0"):
            InternalBalanceOfForces(
                liberal_technocratic=0.6,
                revanchist_fascist=0.4,
                institutionalist_bonapartist=0.2,
            )

    @pytest.mark.math
    def test_invalid_weights_too_low(self) -> None:
        """Weights summing to < 0.99 should be rejected."""
        with pytest.raises(ValidationError, match="sum to 1.0"):
            InternalBalanceOfForces(
                liberal_technocratic=0.3,
                revanchist_fascist=0.2,
                institutionalist_bonapartist=0.2,
            )

    @pytest.mark.math
    def test_hegemonic_fraction_liberal(self) -> None:
        """Highest weight fraction should be hegemonic."""
        b = make_balance(
            liberal_technocratic=0.5,
            revanchist_fascist=0.3,
            institutionalist_bonapartist=0.2,
        )
        assert b.hegemonic_fraction == RulingClassFraction.LIBERAL_TECHNOCRATIC

    @pytest.mark.math
    def test_hegemonic_fraction_revanchist(self) -> None:
        """REVANCHIST should be hegemonic when it has highest weight."""
        b = make_balance(
            liberal_technocratic=0.2,
            revanchist_fascist=0.5,
            institutionalist_bonapartist=0.3,
        )
        assert b.hegemonic_fraction == RulingClassFraction.REVANCHIST_FASCIST

    @pytest.mark.math
    def test_hegemonic_fraction_bonapartist(self) -> None:
        """BONAPARTIST should be hegemonic when it has highest weight."""
        b = make_balance(
            liberal_technocratic=0.2,
            revanchist_fascist=0.3,
            institutionalist_bonapartist=0.5,
        )
        assert b.hegemonic_fraction == RulingClassFraction.INSTITUTIONALIST_BONAPARTIST

    @pytest.mark.math
    def test_frozen(self) -> None:
        """InternalBalanceOfForces must be immutable."""
        b = make_balance()
        with pytest.raises(ValidationError, match="frozen"):
            b.liberal_technocratic = 0.9  # type: ignore[misc]


# =============================================================================
# ReproductionMechanism
# =============================================================================


class TestReproductionMechanism:
    """Tests for the ReproductionMechanism model."""

    @pytest.mark.math
    def test_all_true_high_capacity(self) -> None:
        """All mechanisms active with high budget should yield high capacity."""
        r = make_reproduction()
        # (4/4)*0.7 + 0.8*0.3 = 0.7 + 0.24 = 0.94
        assert r.reproduction_capacity == pytest.approx(0.94)

    @pytest.mark.math
    def test_all_false_low_capacity(self) -> None:
        """No mechanisms with low budget should yield low capacity."""
        r = ReproductionMechanism(budget_independence=0.1)
        # (0/4)*0.7 + 0.1*0.3 = 0.0 + 0.03 = 0.03
        assert r.reproduction_capacity == pytest.approx(0.03)

    @pytest.mark.math
    def test_partial_mechanisms(self) -> None:
        """Partial mechanisms should yield intermediate capacity."""
        r = ReproductionMechanism(
            recruitment_pipeline=True,
            training_program=True,
            budget_independence=0.5,
        )
        # (2/4)*0.7 + 0.5*0.3 = 0.35 + 0.15 = 0.50
        assert r.reproduction_capacity == pytest.approx(0.50)

    @pytest.mark.math
    def test_frozen(self) -> None:
        """ReproductionMechanism must be immutable."""
        r = make_reproduction()
        with pytest.raises(ValidationError, match="frozen"):
            r.budget_independence = 0.0  # type: ignore[misc]


# =============================================================================
# SpawningBlueprint
# =============================================================================


class TestSpawningBlueprint:
    """Tests for the SpawningBlueprint model."""

    def test_construction(self) -> None:
        """SpawningBlueprint should construct with required fields."""
        bp = SpawningBlueprint(
            org_type=OrgType.STATE_APPARATUS,
            default_class_character=ClassCharacter.BOURGEOIS,
        )
        assert bp.org_type == OrgType.STATE_APPARATUS
        assert bp.base_attributes == {}

    def test_with_attributes(self) -> None:
        """SpawningBlueprint should accept base_attributes."""
        bp = SpawningBlueprint(
            org_type=OrgType.BUSINESS,
            default_class_character=ClassCharacter.BOURGEOIS,
            base_attributes={"sector": "automotive"},
        )
        assert bp.base_attributes["sector"] == "automotive"


# =============================================================================
# InstitutionOrgRelation
# =============================================================================


class TestInstitutionOrgRelation:
    """Tests for the InstitutionOrgRelation model."""

    def test_defaults(self) -> None:
        """Relation should have sensible defaults."""
        rel = InstitutionOrgRelation(
            institution_id="doj",
            organization_id="fbi",
        )
        assert rel.resource_provision == 0.0
        assert rel.legal_cover is False
        assert rel.factional_alignment is None

    def test_with_factional_alignment(self) -> None:
        """Relation should accept factional alignment."""
        rel = make_relation(
            factional_alignment=RulingClassFraction.LIBERAL_TECHNOCRATIC,
        )
        assert rel.factional_alignment == RulingClassFraction.LIBERAL_TECHNOCRATIC

    def test_frozen(self) -> None:
        """InstitutionOrgRelation must be immutable."""
        rel = make_relation()
        with pytest.raises(ValidationError, match="frozen"):
            rel.legal_cover = False  # type: ignore[misc]


# =============================================================================
# Institution
# =============================================================================


class TestInstitution:
    """Tests for the Institution model."""

    def test_construction_rsa(self) -> None:
        """RSA institution should construct with jurisdiction."""
        inst = make_institution()
        assert inst.apparatus_type == ApparatusType.RSA_JUDICIAL
        assert inst.jurisdiction == frozenset(["national"])

    def test_construction_isa_no_jurisdiction(self) -> None:
        """ISA institution should construct without jurisdiction."""
        inst = make_institution(
            id="dps",
            name="Detroit Public Schools",
            apparatus_type=ApparatusType.ISA_EDUCATIONAL,
            social_function=SocialFunction.EDUCATION,
            jurisdiction=None,
        )
        assert inst.jurisdiction is None

    def test_jurisdiction_rsa_only(self) -> None:
        """Non-RSA institution with jurisdiction should be rejected."""
        with pytest.raises(ValidationError, match="RSA_"):
            make_institution(
                apparatus_type=ApparatusType.ISA_EDUCATIONAL,
                social_function=SocialFunction.EDUCATION,
                jurisdiction=frozenset(["local"]),
            )

    def test_action_modifiers_positive(self) -> None:
        """Action modifiers must be > 0.0."""
        with pytest.raises(ValidationError, match="must be > 0.0"):
            make_institution(action_modifiers={"educate": 0.0})

    def test_action_modifiers_negative(self) -> None:
        """Action modifiers must be > 0.0."""
        with pytest.raises(ValidationError, match="must be > 0.0"):
            make_institution(action_modifiers={"educate": -0.5})

    def test_action_modifiers_valid(self) -> None:
        """Valid action modifiers should be accepted."""
        inst = make_institution(action_modifiers={"educate": 0.7, "repress": 2.0})
        assert inst.action_modifiers["educate"] == 0.7

    def test_default_class_inscription(self) -> None:
        """Default class inscription should be BOURGEOIS."""
        inst = make_institution()
        assert inst.class_inscription == ClassInscription.BOURGEOIS

    def test_frozen(self) -> None:
        """Institution must be immutable."""
        inst = make_institution()
        with pytest.raises(ValidationError, match="frozen"):
            inst.legitimacy = 0.0  # type: ignore[misc]

    def test_model_copy(self) -> None:
        """Institution should support immutable mutation via model_copy."""
        inst = make_institution()
        degraded = inst.model_copy(update={"housed_org_ids": []})
        assert degraded.housed_org_ids == []
        assert inst.housed_org_ids == ["fbi"]

    def test_frozenset_fields(self) -> None:
        """frozenset fields should be properly typed."""
        inst = make_institution()
        assert isinstance(inst.legal_authorities, frozenset)
        assert isinstance(inst.jurisdiction, frozenset)


# =============================================================================
# Event Types
# =============================================================================


class TestEventTypes:
    """Tests for institution event types."""

    def test_faction_shift_event(self) -> None:
        """FactionShiftEvent should construct correctly."""
        e = FactionShiftEvent(
            institution_id="doj",
            old_fraction=RulingClassFraction.LIBERAL_TECHNOCRATIC,
            new_fraction=RulingClassFraction.REVANCHIST_FASCIST,
            weights={"liberal_technocratic": 0.3, "revanchist_fascist": 0.5},
        )
        assert e.old_fraction == RulingClassFraction.LIBERAL_TECHNOCRATIC
        assert e.new_fraction == RulingClassFraction.REVANCHIST_FASCIST

    def test_reproduction_event(self) -> None:
        """ReproductionEvent should construct correctly."""
        bp = SpawningBlueprint(
            org_type=OrgType.STATE_APPARATUS,
            default_class_character=ClassCharacter.BOURGEOIS,
        )
        e = ReproductionEvent(
            institution_id="doj",
            spawned_org_type=OrgType.STATE_APPARATUS,
            blueprint=bp,
        )
        assert e.spawned_org_type == OrgType.STATE_APPARATUS

    def test_bonapartist_mode_event(self) -> None:
        """BonapartistModeEvent should construct correctly."""
        e = BonapartistModeEvent(
            institution_id="doj",
            bonapartist_weight=0.45,
        )
        assert e.bonapartist_weight == 0.45
