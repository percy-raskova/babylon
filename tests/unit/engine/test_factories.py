"""Tests for babylon.engine.factories entity factory functions.

TDD Red Phase: These tests define the contract for create_proletariat()
and create_bourgeoisie() factory functions.

The factories provide convenient ways to create SocialClass entities
with sensible defaults for class simulation.

Refactored with pytest.parametrize for Phase 4 of Unit Test Health Improvement Plan.
"""

import re

import pytest

from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.models import SocialClass, SocialRole

# =============================================================================
# TEST CREATE_PROLETARIAT
# =============================================================================


@pytest.mark.unit
class TestCreateProletariat:
    """Tests for the create_proletariat() factory function."""

    def test_returns_social_class(self) -> None:
        """create_proletariat() returns a SocialClass instance."""
        result = create_proletariat()
        assert isinstance(result, SocialClass)

    @pytest.mark.parametrize(
        "attr,expected,use_approx",
        [
            ("role", SocialRole.PERIPHERY_PROLETARIAT, False),
            ("wealth", 0.5, True),
            ("organization", 0.1, True),
            ("subsistence_threshold", 0.3, True),
            ("repression_faced", 0.5, True),
            ("name", "Proletariat", False),
        ],
        ids=[
            "exploited_role",
            "low_wealth",
            "low_organization",
            "subsistence_threshold",
            "repression_faced",
            "default_name",
        ],
    )
    def test_proletariat_defaults(self, attr: str, expected: object, use_approx: bool) -> None:
        """create_proletariat() has correct default values."""
        result = create_proletariat()
        actual = getattr(result, attr)
        if use_approx:
            assert actual == pytest.approx(expected)
        else:
            assert actual == expected

    def test_default_ideology_slightly_revolutionary(self) -> None:
        """create_proletariat() has default ideology of -0.3 (leaning revolutionary)."""
        result = create_proletariat()
        # IdeologicalProfile with class_consciousness=0.65 converts to legacy -0.3
        assert result.ideology.to_legacy_ideology() == pytest.approx(-0.3)

    def test_has_valid_id_pattern(self) -> None:
        """create_proletariat() generates valid ID matching ^C[0-9]{3}$ pattern."""
        result = create_proletariat()
        assert re.match(r"^C[0-9]{3}$", result.id) is not None

    @pytest.mark.parametrize(
        "kwarg,value,attr,use_approx",
        [
            ({"wealth": 1.5}, 1.5, "wealth", True),
            ({"ideology": -0.8}, -0.8, None, True),  # Special handling for ideology
            ({"organization": 0.5}, 0.5, "organization", True),
            ({"name": "Industrial Worker"}, "Industrial Worker", "name", False),
            ({"id": "C100"}, "C100", "id", False),
        ],
        ids=[
            "custom_wealth",
            "custom_ideology",
            "custom_organization",
            "custom_name",
            "custom_id",
        ],
    )
    def test_proletariat_custom_override(
        self, kwarg: dict, value: object, attr: str | None, use_approx: bool
    ) -> None:
        """create_proletariat() accepts custom parameter overrides."""
        result = create_proletariat(**kwarg)
        # attr=None means ideology, which needs to_legacy_ideology() conversion
        actual = result.ideology.to_legacy_ideology() if attr is None else getattr(result, attr)
        if use_approx:
            assert actual == pytest.approx(value)
        else:
            assert actual == value


# =============================================================================
# TEST CREATE_BOURGEOISIE
# =============================================================================


@pytest.mark.unit
class TestCreateBourgeoisie:
    """Tests for the create_bourgeoisie() factory function."""

    def test_returns_social_class(self) -> None:
        """create_bourgeoisie() returns a SocialClass instance."""
        result = create_bourgeoisie()
        assert isinstance(result, SocialClass)

    @pytest.mark.parametrize(
        "attr,expected,use_approx",
        [
            ("role", SocialRole.CORE_BOURGEOISIE, False),
            ("wealth", 10.0, True),
            ("organization", 0.7, True),
            ("subsistence_threshold", 0.1, True),
            ("repression_faced", 0.1, True),
            ("name", "Bourgeoisie", False),
        ],
        ids=[
            "exploiter_role",
            "high_wealth",
            "high_organization",
            "low_subsistence",
            "low_repression",
            "default_name",
        ],
    )
    def test_bourgeoisie_defaults(self, attr: str, expected: object, use_approx: bool) -> None:
        """create_bourgeoisie() has correct default values."""
        result = create_bourgeoisie()
        actual = getattr(result, attr)
        if use_approx:
            assert actual == pytest.approx(expected)
        else:
            assert actual == expected

    def test_default_ideology_reactionary(self) -> None:
        """create_bourgeoisie() has default ideology of 0.8 (leaning reactionary)."""
        result = create_bourgeoisie()
        # IdeologicalProfile with class_consciousness=0.1 converts to legacy 0.8
        assert result.ideology.to_legacy_ideology() == pytest.approx(0.8)

    def test_has_valid_id_pattern(self) -> None:
        """create_bourgeoisie() generates valid ID matching ^C[0-9]{3}$ pattern."""
        result = create_bourgeoisie()
        assert re.match(r"^C[0-9]{3}$", result.id) is not None

    @pytest.mark.parametrize(
        "kwarg,value,attr,use_approx",
        [
            ({"wealth": 50.0}, 50.0, "wealth", True),
            ({"ideology": 0.5}, 0.5, None, True),  # Special handling for ideology
            ({"organization": 0.9}, 0.9, "organization", True),
            ({"name": "Finance Capital"}, "Finance Capital", "name", False),
            ({"id": "C200"}, "C200", "id", False),
        ],
        ids=[
            "custom_wealth",
            "custom_ideology",
            "custom_organization",
            "custom_name",
            "custom_id",
        ],
    )
    def test_bourgeoisie_custom_override(
        self, kwarg: dict, value: object, attr: str | None, use_approx: bool
    ) -> None:
        """create_bourgeoisie() accepts custom parameter overrides."""
        result = create_bourgeoisie(**kwarg)
        # attr=None means ideology, which needs to_legacy_ideology() conversion
        actual = result.ideology.to_legacy_ideology() if attr is None else getattr(result, attr)
        if use_approx:
            assert actual == pytest.approx(value)
        else:
            assert actual == value


# =============================================================================
# TEST FACTORY UNIQUENESS
# =============================================================================


@pytest.mark.unit
class TestFactoryUniqueness:
    """Tests for factory function ID generation."""

    def test_proletariat_and_bourgeoisie_have_different_default_ids(self) -> None:
        """Default IDs for proletariat and bourgeoisie should differ."""
        proletariat = create_proletariat()
        bourgeoisie = create_bourgeoisie()
        assert proletariat.id != bourgeoisie.id

    def test_multiple_proletariat_calls_same_default_id(self) -> None:
        """Multiple calls to create_proletariat() without id param use same default."""
        p1 = create_proletariat()
        p2 = create_proletariat()
        # Default ID should be deterministic
        assert p1.id == p2.id
