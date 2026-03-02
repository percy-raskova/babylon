"""Tests for ClassSystemDefines solidarity matrix (Feature 038, US3).

Feature: 038-unified-class-system
TDD Phase: RED then GREEN

Tests cover:
- T028: get_base_solidarity symmetry (BC-010), known pair values, unknown pair returns 0.0
"""

from __future__ import annotations

import pytest
from tests.constants import ClassSystemDefaults

from babylon.config.defines import ClassSystemDefines, GameDefines

CS = ClassSystemDefaults()


class TestGetBaseSolidarity:
    """T028: get_base_solidarity matrix tests."""

    @pytest.mark.unit
    def test_proletariat_pair_value(self) -> None:
        """Two PROLETARIAT agents get base_solidarity=0.80."""
        defines = ClassSystemDefines()
        result = defines.get_base_solidarity("PROLETARIAT", "PROLETARIAT")
        assert result == pytest.approx(CS.SOLIDARITY_PROL_PROL)

    @pytest.mark.unit
    def test_bourgeoisie_proletariat_value(self) -> None:
        """BOURGEOISIE-PROLETARIAT pair gets base_solidarity=0.00."""
        defines = ClassSystemDefines()
        result = defines.get_base_solidarity("BOURGEOISIE", "PROLETARIAT")
        assert result == pytest.approx(CS.SOLIDARITY_BOURG_PROL)

    @pytest.mark.unit
    def test_symmetry(self) -> None:
        """get_base_solidarity(A, B) == get_base_solidarity(B, A) for all pairs."""
        defines = ClassSystemDefines()
        class_names = [
            "BOURGEOISIE",
            "PETIT_BOURGEOISIE",
            "LABOR_ARISTOCRACY",
            "PROLETARIAT",
            "LUMPENPROLETARIAT",
        ]
        for i, class_a in enumerate(class_names):
            for class_b in class_names[i:]:
                forward = defines.get_base_solidarity(class_a, class_b)
                reverse = defines.get_base_solidarity(class_b, class_a)
                assert forward == reverse, (
                    f"Asymmetry: get({class_a}, {class_b})={forward} "
                    f"!= get({class_b}, {class_a})={reverse}"
                )

    @pytest.mark.unit
    def test_unknown_pair_returns_zero(self) -> None:
        """Unknown class name returns 0.0."""
        defines = ClassSystemDefines()
        assert defines.get_base_solidarity("UNKNOWN", "PROLETARIAT") == 0.0
        assert defines.get_base_solidarity("PROLETARIAT", "UNKNOWN") == 0.0
        assert defines.get_base_solidarity("UNKNOWN", "UNKNOWN") == 0.0

    @pytest.mark.unit
    def test_all_diagonal_entries_positive(self) -> None:
        """Same-class pairs have positive solidarity (intra-class cohesion)."""
        defines = ClassSystemDefines()
        class_names = [
            "BOURGEOISIE",
            "PETIT_BOURGEOISIE",
            "LABOR_ARISTOCRACY",
            "PROLETARIAT",
            "LUMPENPROLETARIAT",
        ]
        for name in class_names:
            value = defines.get_base_solidarity(name, name)
            assert value > 0.0, f"{name}-{name} should be positive, got {value}"

    @pytest.mark.unit
    def test_class_proximity_ordering(self) -> None:
        """Adjacent classes have higher solidarity than distant ones."""
        defines = ClassSystemDefines()
        # PROLETARIAT-LUMPEN > BOURGEOISIE-LUMPEN
        prol_lumpen = defines.get_base_solidarity("PROLETARIAT", "LUMPENPROLETARIAT")
        bourg_lumpen = defines.get_base_solidarity("BOURGEOISIE", "LUMPENPROLETARIAT")
        assert prol_lumpen > bourg_lumpen

    @pytest.mark.unit
    def test_game_defines_integration(self) -> None:
        """GameDefines().class_system.get_base_solidarity works end-to-end."""
        defines = GameDefines()
        result = defines.class_system.get_base_solidarity("PROLETARIAT", "PROLETARIAT")
        assert result == pytest.approx(0.80)

    @pytest.mark.unit
    def test_matrix_bounds_validation(self) -> None:
        """All matrix entries must be in [0.0, 1.0]."""
        defines = ClassSystemDefines()
        for outer_key, inner_dict in defines.base_class_solidarity.items():
            for inner_key, value in inner_dict.items():
                assert 0.0 <= value <= 1.0, (
                    f"Matrix entry [{outer_key}][{inner_key}]={value} out of bounds"
                )

    @pytest.mark.unit
    def test_matrix_has_15_unique_entries(self) -> None:
        """Upper-triangle matrix has exactly 15 entries (5+4+3+2+1)."""
        defines = ClassSystemDefines()
        total = sum(len(inner) for inner in defines.base_class_solidarity.values())
        assert total == 15
