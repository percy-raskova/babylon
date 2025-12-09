"""Tests for babylon.engine.factories entity factory functions.

TDD Red Phase: These tests define the contract for create_proletariat()
and create_bourgeoisie() factory functions.

The factories provide convenient ways to create SocialClass entities
with sensible defaults for class simulation.
"""

import pytest

from babylon.models import SocialClass, SocialRole

# =============================================================================
# TEST CREATE_PROLETARIAT
# =============================================================================


@pytest.mark.unit
class TestCreateProletariat:
    """Tests for the create_proletariat() factory function."""

    def test_returns_social_class(self) -> None:
        """create_proletariat() returns a SocialClass instance."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        assert isinstance(result, SocialClass)

    def test_has_exploited_role(self) -> None:
        """create_proletariat() assigns PERIPHERY_PROLETARIAT role (exploited class)."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        assert result.role == SocialRole.PERIPHERY_PROLETARIAT

    def test_default_wealth_is_low(self) -> None:
        """create_proletariat() has default wealth of 0.5 (low wealth)."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        assert result.wealth == pytest.approx(0.5)

    def test_custom_wealth_override(self) -> None:
        """create_proletariat() accepts custom wealth parameter."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat(wealth=1.5)
        assert result.wealth == pytest.approx(1.5)

    def test_default_ideology_slightly_revolutionary(self) -> None:
        """create_proletariat() has default ideology of -0.3 (leaning revolutionary)."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        # IdeologicalProfile with class_consciousness=0.65 converts to legacy -0.3
        assert result.ideology.to_legacy_ideology() == pytest.approx(-0.3)

    def test_custom_ideology_override(self) -> None:
        """create_proletariat() accepts custom ideology parameter."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat(ideology=-0.8)
        # Legacy float -0.8 converts to IdeologicalProfile, then back
        assert result.ideology.to_legacy_ideology() == pytest.approx(-0.8)

    def test_default_organization_low(self) -> None:
        """create_proletariat() has default organization of 0.1 (10%)."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        assert result.organization == pytest.approx(0.1)

    def test_custom_organization_override(self) -> None:
        """create_proletariat() accepts custom organization parameter."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat(organization=0.5)
        assert result.organization == pytest.approx(0.5)

    def test_has_valid_id_pattern(self) -> None:
        """create_proletariat() generates valid ID matching ^C[0-9]{3}$ pattern."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        # ID should match the required pattern
        import re

        assert re.match(r"^C[0-9]{3}$", result.id) is not None

    def test_default_name(self) -> None:
        """create_proletariat() has sensible default name."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        assert result.name == "Proletariat"

    def test_custom_name_override(self) -> None:
        """create_proletariat() accepts custom name parameter."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat(name="Industrial Worker")
        assert result.name == "Industrial Worker"

    def test_custom_id_override(self) -> None:
        """create_proletariat() accepts custom id parameter."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat(id="C100")
        assert result.id == "C100"

    def test_default_subsistence_threshold(self) -> None:
        """create_proletariat() has subsistence threshold of 0.3."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        assert result.subsistence_threshold == pytest.approx(0.3)

    def test_default_repression_faced(self) -> None:
        """create_proletariat() has default repression_faced of 0.5."""
        from babylon.engine.factories import create_proletariat

        result = create_proletariat()
        assert result.repression_faced == pytest.approx(0.5)


# =============================================================================
# TEST CREATE_BOURGEOISIE
# =============================================================================


@pytest.mark.unit
class TestCreateBourgeoisie:
    """Tests for the create_bourgeoisie() factory function."""

    def test_returns_social_class(self) -> None:
        """create_bourgeoisie() returns a SocialClass instance."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        assert isinstance(result, SocialClass)

    def test_has_exploiter_role(self) -> None:
        """create_bourgeoisie() assigns CORE_BOURGEOISIE role (exploiter class)."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        assert result.role == SocialRole.CORE_BOURGEOISIE

    def test_default_wealth_is_high(self) -> None:
        """create_bourgeoisie() has default wealth of 10.0 (high wealth)."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        assert result.wealth == pytest.approx(10.0)

    def test_custom_wealth_override(self) -> None:
        """create_bourgeoisie() accepts custom wealth parameter."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie(wealth=50.0)
        assert result.wealth == pytest.approx(50.0)

    def test_default_ideology_reactionary(self) -> None:
        """create_bourgeoisie() has default ideology of 0.8 (leaning reactionary)."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        # IdeologicalProfile with class_consciousness=0.1 converts to legacy 0.8
        assert result.ideology.to_legacy_ideology() == pytest.approx(0.8)

    def test_custom_ideology_override(self) -> None:
        """create_bourgeoisie() accepts custom ideology parameter."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie(ideology=0.5)
        # Legacy float 0.5 converts to IdeologicalProfile, then back
        assert result.ideology.to_legacy_ideology() == pytest.approx(0.5)

    def test_default_organization_high(self) -> None:
        """create_bourgeoisie() has default organization of 0.7 (70% - well-organized)."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        assert result.organization == pytest.approx(0.7)

    def test_custom_organization_override(self) -> None:
        """create_bourgeoisie() accepts custom organization parameter."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie(organization=0.9)
        assert result.organization == pytest.approx(0.9)

    def test_has_valid_id_pattern(self) -> None:
        """create_bourgeoisie() generates valid ID matching ^C[0-9]{3}$ pattern."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        import re

        assert re.match(r"^C[0-9]{3}$", result.id) is not None

    def test_default_name(self) -> None:
        """create_bourgeoisie() has sensible default name."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        assert result.name == "Bourgeoisie"

    def test_custom_name_override(self) -> None:
        """create_bourgeoisie() accepts custom name parameter."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie(name="Finance Capital")
        assert result.name == "Finance Capital"

    def test_custom_id_override(self) -> None:
        """create_bourgeoisie() accepts custom id parameter."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie(id="C200")
        assert result.id == "C200"

    def test_default_subsistence_threshold_low(self) -> None:
        """create_bourgeoisie() has low subsistence threshold of 0.1."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        assert result.subsistence_threshold == pytest.approx(0.1)

    def test_default_repression_faced_low(self) -> None:
        """create_bourgeoisie() has low repression_faced of 0.1 (protected by state)."""
        from babylon.engine.factories import create_bourgeoisie

        result = create_bourgeoisie()
        assert result.repression_faced == pytest.approx(0.1)


# =============================================================================
# TEST FACTORY UNIQUENESS
# =============================================================================


@pytest.mark.unit
class TestFactoryUniqueness:
    """Tests for factory function ID generation."""

    def test_proletariat_and_bourgeoisie_have_different_default_ids(self) -> None:
        """Default IDs for proletariat and bourgeoisie should differ."""
        from babylon.engine.factories import create_bourgeoisie, create_proletariat

        proletariat = create_proletariat()
        bourgeoisie = create_bourgeoisie()
        assert proletariat.id != bourgeoisie.id

    def test_multiple_proletariat_calls_same_default_id(self) -> None:
        """Multiple calls to create_proletariat() without id param use same default."""
        from babylon.engine.factories import create_proletariat

        p1 = create_proletariat()
        p2 = create_proletariat()
        # Default ID should be deterministic
        assert p1.id == p2.id
