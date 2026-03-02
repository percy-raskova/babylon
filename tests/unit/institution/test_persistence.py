"""Unit tests for social function persistence (Feature 040, US6).

Validates:
- SC-011: Institutions persist as long as social function is needed
- Degradation without destruction
- Social function immutability
"""

from __future__ import annotations

from babylon.models.enums import (
    ApparatusType,
    SocialFunction,
)

from .conftest import make_institution, make_isa_institution


class TestSocialFunctionPersistence:
    """Institutions persist via social function, not housed orgs."""

    def test_social_function_survives_org_removal(self) -> None:
        """Social function should survive removal of all housed orgs."""
        doj = make_institution()
        degraded = doj.model_copy(update={"housed_org_ids": []})
        assert degraded.social_function == SocialFunction.ADJUDICATION

    def test_apparatus_type_survives_org_removal(self) -> None:
        """Apparatus type should survive removal of all housed orgs."""
        doj = make_institution()
        degraded = doj.model_copy(update={"housed_org_ids": []})
        assert degraded.apparatus_type == ApparatusType.RSA_JUDICIAL

    def test_legal_authorities_survive_org_removal(self) -> None:
        """Legal authorities should survive removal of all housed orgs."""
        doj = make_institution()
        degraded = doj.model_copy(update={"housed_org_ids": []})
        assert "federal_prosecution" in degraded.legal_authorities

    def test_territory_survives_org_removal(self) -> None:
        """Territory footprint should survive removal of all housed orgs."""
        doj = make_institution()
        degraded = doj.model_copy(update={"housed_org_ids": []})
        assert len(degraded.territory_ids) > 0


class TestFormalizationAndInertia:
    """Institutional persistence attributes."""

    def test_high_formalization(self) -> None:
        """Highly formalized institutions resist change."""
        doj = make_institution()
        assert doj.formalization_level == 0.95

    def test_high_inertia(self) -> None:
        """High-inertia institutions maintain continuity."""
        doj = make_institution()
        assert doj.institutional_inertia == 0.8

    def test_formalization_range(self) -> None:
        """Formalization must be in [0, 1]."""
        inst = make_institution(formalization_level=0.0)
        assert inst.formalization_level == 0.0
        inst2 = make_institution(formalization_level=1.0)
        assert inst2.formalization_level == 1.0

    def test_inertia_range(self) -> None:
        """Institutional inertia must be in [0, 1]."""
        inst = make_institution(institutional_inertia=0.0)
        assert inst.institutional_inertia == 0.0


class TestBlueprintPersistence:
    """Spawning blueprints survive degradation."""

    def test_blueprints_survive_empty_orgs(self) -> None:
        """Blueprints should persist even with no housed orgs."""
        doj = make_institution()
        degraded = doj.model_copy(update={"housed_org_ids": []})
        assert len(degraded.spawning_blueprints) == 1

    def test_isa_without_blueprints(self) -> None:
        """ISA institutions may not have spawning blueprints."""
        school = make_isa_institution()
        assert len(school.spawning_blueprints) == 0


class TestLegitimacyPersistence:
    """Legitimacy survives structural changes."""

    def test_legitimacy_preserved(self) -> None:
        """Legitimacy should be preserved through model_copy."""
        doj = make_institution(legitimacy=0.9)
        updated = doj.model_copy(update={"housed_org_ids": ["new_org"]})
        assert updated.legitimacy == 0.9

    def test_legitimacy_range(self) -> None:
        """Legitimacy must be in [0, 1]."""
        inst = make_institution(legitimacy=0.0)
        assert inst.legitimacy == 0.0
        inst2 = make_institution(legitimacy=1.0)
        assert inst2.legitimacy == 1.0
