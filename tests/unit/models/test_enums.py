"""Tests for babylon.models.enums.

TDD Red Phase: These tests define the contract for our enum types.
Each enum must:
1. Be a StrEnum (serialize to lowercase strings for JSON)
2. Have all expected values
3. Be constructible from string values
4. Reject invalid values
"""

import pytest

from babylon.models.enums import (
    EdgeType,
    IntensityLevel,
    ResolutionType,
    SocialRole,
)


@pytest.mark.math
class TestSocialRole:
    """SocialRole: Class position in the world system.

    Based on MLM-TW theory:
    - core_bourgeoisie: Owns means of production in imperial core
    - periphery_proletariat: Sells labor in exploited periphery
    - labor_aristocracy: Core workers benefiting from imperial rent
    - petty_bourgeoisie: Small owners, professionals
    - lumpenproletariat: Outside formal economy
    """

    def test_all_expected_roles_exist(self) -> None:
        """All MLM-TW class categories are defined."""
        assert hasattr(SocialRole, "CORE_BOURGEOISIE")
        assert hasattr(SocialRole, "PERIPHERY_PROLETARIAT")
        assert hasattr(SocialRole, "LABOR_ARISTOCRACY")
        assert hasattr(SocialRole, "PETTY_BOURGEOISIE")
        assert hasattr(SocialRole, "LUMPENPROLETARIAT")

    def test_roles_serialize_to_lowercase_strings(self) -> None:
        """Roles serialize to snake_case for JSON compatibility."""
        assert SocialRole.CORE_BOURGEOISIE.value == "core_bourgeoisie"
        assert SocialRole.PERIPHERY_PROLETARIAT.value == "periphery_proletariat"
        assert SocialRole.LABOR_ARISTOCRACY.value == "labor_aristocracy"
        assert SocialRole.PETTY_BOURGEOISIE.value == "petty_bourgeoisie"
        assert SocialRole.LUMPENPROLETARIAT.value == "lumpenproletariat"

    def test_role_constructible_from_string(self) -> None:
        """Can construct enum from its string value."""
        role = SocialRole("periphery_proletariat")
        assert role == SocialRole.PERIPHERY_PROLETARIAT

    def test_invalid_role_raises_value_error(self) -> None:
        """Unknown roles are rejected with ValueError."""
        with pytest.raises(ValueError):
            SocialRole("middle_class")  # Not a valid MLM-TW category

        with pytest.raises(ValueError):
            SocialRole("working_class")  # Too vague for MLM-TW

    def test_role_is_string_subclass(self) -> None:
        """SocialRole values can be used as strings."""
        role = SocialRole.CORE_BOURGEOISIE
        assert isinstance(role, str)
        assert role == "core_bourgeoisie"

    def test_role_count(self) -> None:
        """Exactly 5 social roles defined."""
        assert len(SocialRole) == 5


@pytest.mark.math
class TestEdgeType:
    """EdgeType: Nature of relationships between entities.

    The fundamental relationship types:
    - exploitation: Value extraction (imperial rent flow)
    - solidarity: Mutual support (class consciousness)
    - repression: State violence against class
    - competition: Market rivalry
    """

    def test_all_expected_edge_types_exist(self) -> None:
        """All relationship types are defined."""
        assert hasattr(EdgeType, "EXPLOITATION")
        assert hasattr(EdgeType, "SOLIDARITY")
        assert hasattr(EdgeType, "REPRESSION")
        assert hasattr(EdgeType, "COMPETITION")

    def test_edge_types_serialize_to_lowercase(self) -> None:
        """Edge types serialize to snake_case for JSON."""
        assert EdgeType.EXPLOITATION.value == "exploitation"
        assert EdgeType.SOLIDARITY.value == "solidarity"
        assert EdgeType.REPRESSION.value == "repression"
        assert EdgeType.COMPETITION.value == "competition"

    def test_edge_type_constructible_from_string(self) -> None:
        """Can construct from string value."""
        edge = EdgeType("exploitation")
        assert edge == EdgeType.EXPLOITATION

    def test_invalid_edge_type_raises(self) -> None:
        """Unknown edge types are rejected."""
        with pytest.raises(ValueError):
            EdgeType("friendship")  # Not a structural relationship

    def test_edge_type_count(self) -> None:
        """Exactly 4 edge types defined."""
        assert len(EdgeType) == 4


@pytest.mark.math
class TestIntensityLevel:
    """IntensityLevel: Contradiction/tension intensity.

    From dormant (not yet manifest) to critical (rupture imminent):
    - dormant: Contradiction exists but not active
    - low: Minor tensions
    - medium: Noticeable conflict
    - high: Serious crisis
    - critical: Rupture imminent
    """

    def test_all_intensity_levels_exist(self) -> None:
        """All intensity levels defined."""
        assert hasattr(IntensityLevel, "DORMANT")
        assert hasattr(IntensityLevel, "LOW")
        assert hasattr(IntensityLevel, "MEDIUM")
        assert hasattr(IntensityLevel, "HIGH")
        assert hasattr(IntensityLevel, "CRITICAL")

    def test_intensity_levels_serialize_to_lowercase(self) -> None:
        """Intensity levels serialize to lowercase for JSON."""
        assert IntensityLevel.DORMANT.value == "dormant"
        assert IntensityLevel.LOW.value == "low"
        assert IntensityLevel.MEDIUM.value == "medium"
        assert IntensityLevel.HIGH.value == "high"
        assert IntensityLevel.CRITICAL.value == "critical"

    def test_intensity_constructible_from_string(self) -> None:
        """Can construct from string value."""
        level = IntensityLevel("high")
        assert level == IntensityLevel.HIGH

    def test_invalid_intensity_raises(self) -> None:
        """Unknown intensity levels are rejected."""
        with pytest.raises(ValueError):
            IntensityLevel("extreme")  # Not a valid level

    def test_intensity_level_count(self) -> None:
        """Exactly 5 intensity levels defined."""
        assert len(IntensityLevel) == 5

    def test_intensity_levels_are_ordered_conceptually(self) -> None:
        """Levels follow logical ordering (for documentation)."""
        # This tests that we have the right semantic ordering
        levels = [
            IntensityLevel.DORMANT,
            IntensityLevel.LOW,
            IntensityLevel.MEDIUM,
            IntensityLevel.HIGH,
            IntensityLevel.CRITICAL,
        ]
        # All values exist and are distinct
        assert len(set(levels)) == 5


@pytest.mark.math
class TestResolutionType:
    """ResolutionType: How contradictions resolve.

    Three possible outcomes:
    - synthesis: Dialectical resolution (new unity of opposites)
    - rupture: Revolutionary break (system change)
    - suppression: Forced dormancy (contradiction remains)
    """

    def test_all_resolution_types_exist(self) -> None:
        """All resolution types defined."""
        assert hasattr(ResolutionType, "SYNTHESIS")
        assert hasattr(ResolutionType, "RUPTURE")
        assert hasattr(ResolutionType, "SUPPRESSION")

    def test_resolution_types_serialize_to_lowercase(self) -> None:
        """Resolution types serialize to lowercase for JSON."""
        assert ResolutionType.SYNTHESIS.value == "synthesis"
        assert ResolutionType.RUPTURE.value == "rupture"
        assert ResolutionType.SUPPRESSION.value == "suppression"

    def test_resolution_constructible_from_string(self) -> None:
        """Can construct from string value."""
        resolution = ResolutionType("rupture")
        assert resolution == ResolutionType.RUPTURE

    def test_invalid_resolution_raises(self) -> None:
        """Unknown resolution types are rejected."""
        with pytest.raises(ValueError):
            ResolutionType("compromise")  # Not a dialectical outcome

    def test_resolution_type_count(self) -> None:
        """Exactly 3 resolution types defined."""
        assert len(ResolutionType) == 3
