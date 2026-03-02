"""Unit tests for structural selectivity function (Feature 040, US2).

Validates:
- SC-002: ISA_EDUCATIONAL default modifiers applied
- SC-007: Institution-level override takes precedence over defaults
- Fallback to 1.0 when no mapping found
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines, InstitutionDefines
from babylon.institution.selectivity import structural_selectivity
from babylon.models.enums import ActionType, ApparatusType

from .conftest import make_institution, make_isa_institution


class TestDefaultModifiers:
    """Structural selectivity falls back to apparatus-type defaults."""

    def test_rsa_judicial_surveil_cheaper(self) -> None:
        """RSA_JUDICIAL should make SURVEIL cheaper (< 1.0)."""
        doj = make_institution()
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(doj, ActionType.SURVEIL, defaults)
        assert modifier == 0.5

    def test_rsa_judicial_repress_expensive(self) -> None:
        """RSA_JUDICIAL should make REPRESS more expensive (> 1.0)."""
        doj = make_institution()
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(doj, ActionType.REPRESS, defaults)
        assert modifier == 1.2

    def test_isa_educational_educate_cheaper(self) -> None:
        """SC-002: ISA_EDUCATIONAL should make EDUCATE cheaper."""
        school = make_isa_institution()
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(school, ActionType.EDUCATE, defaults)
        assert modifier == 0.7

    def test_isa_educational_repress_expensive(self) -> None:
        """SC-002: ISA_EDUCATIONAL should make REPRESS very expensive."""
        school = make_isa_institution()
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(school, ActionType.REPRESS, defaults)
        assert modifier == 2.0

    def test_isa_educational_recruit_cheaper(self) -> None:
        """ISA_EDUCATIONAL should make RECRUIT cheaper."""
        school = make_isa_institution()
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(school, ActionType.RECRUIT, defaults)
        assert modifier == 0.8


class TestUnmappedFallback:
    """Actions without any mapping return 1.0 (no modifier)."""

    def test_unmapped_action_returns_one(self) -> None:
        """An action not in defaults or overrides should return 1.0."""
        doj = make_institution()
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(doj, ActionType.FUNDRAISE, defaults)
        assert modifier == 1.0

    def test_unmapped_apparatus_type_returns_one(self) -> None:
        """An apparatus type not in defaults should return 1.0."""
        inst = make_institution(
            apparatus_type=ApparatusType.ISA_LEGAL,
            jurisdiction=None,
        )
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(inst, ActionType.REPRESS, defaults)
        # isa_legal has empty dict => fallback to 1.0
        assert modifier == 1.0


class TestInstitutionOverride:
    """SC-007: Institution-level overrides take precedence."""

    def test_override_replaces_default(self) -> None:
        """Institution action_modifiers override should replace default."""
        # DOJ RSA_JUDICIAL default for SURVEIL is 0.5
        # Override to 0.9
        doj = make_institution(action_modifiers={"surveil": 0.9})
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(doj, ActionType.SURVEIL, defaults)
        assert modifier == 0.9

    def test_override_for_new_action(self) -> None:
        """Institution can add modifiers for actions not in defaults."""
        doj = make_institution(action_modifiers={"fundraise": 0.3})
        defaults = InstitutionDefines().default_action_modifiers
        modifier = structural_selectivity(doj, ActionType.FUNDRAISE, defaults)
        assert modifier == 0.3

    def test_override_only_applies_to_specified(self) -> None:
        """Override for one action doesn't affect other actions."""
        doj = make_institution(action_modifiers={"surveil": 0.9})
        defaults = InstitutionDefines().default_action_modifiers
        # REPRESS should still come from defaults
        modifier = structural_selectivity(doj, ActionType.REPRESS, defaults)
        assert modifier == 1.2


class TestGameDefinesIntegration:
    """Defaults loaded from GameDefines match InstitutionDefines."""

    @pytest.mark.math
    def test_gamedefines_provides_correct_defaults(self) -> None:
        """GameDefines().institution.default_action_modifiers should work."""
        defines = GameDefines()
        school = make_isa_institution()
        modifier = structural_selectivity(
            school,
            ActionType.EDUCATE,
            defines.institution.default_action_modifiers,
        )
        assert modifier == 0.7
