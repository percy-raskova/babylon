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
    EventType,
    IntensityLevel,
    OperationalProfile,
    ResolutionType,
    SectorType,
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
        """Exactly 6 social roles defined (includes COMPRADOR_BOURGEOISIE)."""
        assert len(SocialRole) == 6


@pytest.mark.math
class TestEdgeType:
    """EdgeType: Nature of relationships between entities.

    The fundamental relationship types:
    - exploitation: Value extraction (imperial rent flow)
    - solidarity: Mutual support (class consciousness)
    - repression: State violence against class
    - competition: Market rivalry
    - tribute: Value flow from periphery comprador to core (15% cut)
    - wages: Core bourgeoisie paying core workers (super-wages)
    - client_state: Imperial subsidy to maintain client state stability
    """

    def test_all_expected_edge_types_exist(self) -> None:
        """All relationship types are defined."""
        assert hasattr(EdgeType, "EXPLOITATION")
        assert hasattr(EdgeType, "SOLIDARITY")
        assert hasattr(EdgeType, "REPRESSION")
        assert hasattr(EdgeType, "COMPETITION")

    def test_imperial_circuit_edge_types_exist(self) -> None:
        """Imperial circuit edge types for 4-node model (Sprint 3.4.1)."""
        assert hasattr(EdgeType, "TRIBUTE")
        assert hasattr(EdgeType, "WAGES")
        assert hasattr(EdgeType, "CLIENT_STATE")

    def test_edge_types_serialize_to_lowercase(self) -> None:
        """Edge types serialize to snake_case for JSON."""
        assert EdgeType.EXPLOITATION.value == "exploitation"
        assert EdgeType.SOLIDARITY.value == "solidarity"
        assert EdgeType.REPRESSION.value == "repression"
        assert EdgeType.COMPETITION.value == "competition"

    def test_imperial_circuit_edge_types_serialize(self) -> None:
        """Imperial circuit edge types serialize to snake_case for JSON."""
        assert EdgeType.TRIBUTE.value == "tribute"
        assert EdgeType.WAGES.value == "wages"
        assert EdgeType.CLIENT_STATE.value == "client_state"

    def test_edge_type_constructible_from_string(self) -> None:
        """Can construct from string value."""
        edge = EdgeType("exploitation")
        assert edge == EdgeType.EXPLOITATION

    def test_imperial_circuit_edge_types_constructible(self) -> None:
        """Imperial circuit edge types can be constructed from strings."""
        assert EdgeType("tribute") == EdgeType.TRIBUTE
        assert EdgeType("wages") == EdgeType.WAGES
        assert EdgeType("client_state") == EdgeType.CLIENT_STATE

    def test_invalid_edge_type_raises(self) -> None:
        """Unknown edge types are rejected."""
        with pytest.raises(ValueError):
            EdgeType("friendship")  # Not a structural relationship

    def test_edge_type_count(self) -> None:
        """Exactly 9 edge types defined (4 original + 3 imperial circuit + 2 territory)."""
        assert len(EdgeType) == 9

    def test_territory_edge_types_exist(self) -> None:
        """Territory edge types for Layer 0 (Sprint 3.5.1).

        TENANCY: Occupant -> Territory (who uses the space)
        ADJACENCY: Territory -> Territory (spatial connectivity)
        """
        assert hasattr(EdgeType, "TENANCY")
        assert hasattr(EdgeType, "ADJACENCY")

    def test_territory_edge_types_serialize(self) -> None:
        """Territory edge types serialize to snake_case for JSON."""
        assert EdgeType.TENANCY.value == "tenancy"
        assert EdgeType.ADJACENCY.value == "adjacency"

    def test_territory_edge_types_constructible(self) -> None:
        """Territory edge types can be constructed from strings."""
        assert EdgeType("tenancy") == EdgeType.TENANCY
        assert EdgeType("adjacency") == EdgeType.ADJACENCY


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


@pytest.mark.math
class TestEventType:
    """EventType: Types of simulation events for the narrative layer.

    Event types published to EventBus on significant state changes:
    - surplus_extraction: Imperial rent extracted (Phase 1)
    - imperial_subsidy: Wealth converted to suppression to stabilize client state (Phase 4)
    - solidarity_awakening: Periphery worker enters active struggle (Sprint 3.4.2)
    - consciousness_transmission: Consciousness transmitted via solidarity edge (Sprint 3.4.2)
    - mass_awakening: Target crosses mass awakening threshold (Sprint 3.4.2)
    """

    def test_surplus_extraction_exists(self) -> None:
        """SURPLUS_EXTRACTION event type exists (Phase 1)."""
        assert hasattr(EventType, "SURPLUS_EXTRACTION")
        assert EventType.SURPLUS_EXTRACTION.value == "surplus_extraction"

    def test_imperial_subsidy_exists(self) -> None:
        """IMPERIAL_SUBSIDY event type exists (Sprint 3.4.1 Phase 4)."""
        assert hasattr(EventType, "IMPERIAL_SUBSIDY")
        assert EventType.IMPERIAL_SUBSIDY.value == "imperial_subsidy"

    def test_solidarity_awakening_exists(self) -> None:
        """SOLIDARITY_AWAKENING event type exists (Sprint 3.4.2).

        Emitted when a periphery worker's consciousness crosses the
        activation threshold (0.3), entering active struggle.
        """
        assert hasattr(EventType, "SOLIDARITY_AWAKENING")
        assert EventType.SOLIDARITY_AWAKENING.value == "solidarity_awakening"

    def test_consciousness_transmission_exists(self) -> None:
        """CONSCIOUSNESS_TRANSMISSION event type exists (Sprint 3.4.2).

        Emitted when consciousness flows from active struggle (periphery)
        to passive consumer (core) via a SOLIDARITY edge.
        """
        assert hasattr(EventType, "CONSCIOUSNESS_TRANSMISSION")
        assert EventType.CONSCIOUSNESS_TRANSMISSION.value == "consciousness_transmission"

    def test_mass_awakening_exists(self) -> None:
        """MASS_AWAKENING event type exists (Sprint 3.4.2).

        Emitted when a target's consciousness crosses the mass awakening
        threshold (0.6), indicating revolutionary potential in the core.
        """
        assert hasattr(EventType, "MASS_AWAKENING")
        assert EventType.MASS_AWAKENING.value == "mass_awakening"

    def test_event_type_constructible_from_string(self) -> None:
        """Can construct EventType from string value."""
        assert EventType("surplus_extraction") == EventType.SURPLUS_EXTRACTION
        assert EventType("imperial_subsidy") == EventType.IMPERIAL_SUBSIDY
        assert EventType("solidarity_awakening") == EventType.SOLIDARITY_AWAKENING
        assert EventType("consciousness_transmission") == EventType.CONSCIOUSNESS_TRANSMISSION
        assert EventType("mass_awakening") == EventType.MASS_AWAKENING

    def test_invalid_event_type_raises(self) -> None:
        """Unknown event types are rejected."""
        with pytest.raises(ValueError):
            EventType("random_event")

    def test_event_type_count(self) -> None:
        """Exactly 9 event types defined (2 original + 3 solidarity + 1 dynamic balance + 3 agency layer)."""
        assert len(EventType) == 9


# =============================================================================
# LAYER 0 TERRITORY ENUMS (Sprint 3.5.1)
# =============================================================================


@pytest.mark.math
class TestOperationalProfile:
    """OperationalProfile: The stance system for territory visibility.

    Sprint 3.5.1: Layer 0 - The Territorial Substrate.
    Profile determines the trade-off between safety and recruitment:
    - low_profile: Safe from eviction, low recruitment (opaque)
    - high_profile: High recruitment, high heat (transparent)
    """

    def test_all_profiles_exist(self) -> None:
        """All operational profiles are defined."""
        assert hasattr(OperationalProfile, "LOW_PROFILE")
        assert hasattr(OperationalProfile, "HIGH_PROFILE")

    def test_profiles_serialize_to_lowercase(self) -> None:
        """Profiles serialize to snake_case for JSON."""
        assert OperationalProfile.LOW_PROFILE.value == "low_profile"
        assert OperationalProfile.HIGH_PROFILE.value == "high_profile"

    def test_profile_constructible_from_string(self) -> None:
        """Can construct from string value."""
        assert OperationalProfile("low_profile") == OperationalProfile.LOW_PROFILE
        assert OperationalProfile("high_profile") == OperationalProfile.HIGH_PROFILE

    def test_invalid_profile_raises(self) -> None:
        """Unknown profiles are rejected."""
        with pytest.raises(ValueError):
            OperationalProfile("stealth")  # Not a valid profile

        with pytest.raises(ValueError):
            OperationalProfile("hidden")  # Not a valid profile

    def test_profile_is_string_subclass(self) -> None:
        """OperationalProfile values can be used as strings."""
        profile = OperationalProfile.LOW_PROFILE
        assert isinstance(profile, str)
        assert profile == "low_profile"

    def test_profile_count(self) -> None:
        """Exactly 2 operational profiles defined."""
        assert len(OperationalProfile) == 2


@pytest.mark.math
class TestSectorType:
    """SectorType: Strategic sector categories for territories.

    Sprint 3.5.1: Layer 0 - The Territorial Substrate.
    Sector types determine the economic and social character of territories:
    - industrial: Factories, warehouses, production
    - residential: Housing, neighborhoods
    - commercial: Shops, markets, services
    - university: Educational institutions, intellectuals
    - docks: Ports, logistics, trade
    - government: State buildings, bureaucracy
    """

    def test_all_sector_types_exist(self) -> None:
        """All sector types are defined."""
        assert hasattr(SectorType, "INDUSTRIAL")
        assert hasattr(SectorType, "RESIDENTIAL")
        assert hasattr(SectorType, "COMMERCIAL")
        assert hasattr(SectorType, "UNIVERSITY")
        assert hasattr(SectorType, "DOCKS")
        assert hasattr(SectorType, "GOVERNMENT")

    def test_sector_types_serialize_to_lowercase(self) -> None:
        """Sector types serialize to snake_case for JSON."""
        assert SectorType.INDUSTRIAL.value == "industrial"
        assert SectorType.RESIDENTIAL.value == "residential"
        assert SectorType.COMMERCIAL.value == "commercial"
        assert SectorType.UNIVERSITY.value == "university"
        assert SectorType.DOCKS.value == "docks"
        assert SectorType.GOVERNMENT.value == "government"

    def test_sector_type_constructible_from_string(self) -> None:
        """Can construct from string value."""
        assert SectorType("industrial") == SectorType.INDUSTRIAL
        assert SectorType("residential") == SectorType.RESIDENTIAL
        assert SectorType("commercial") == SectorType.COMMERCIAL
        assert SectorType("university") == SectorType.UNIVERSITY
        assert SectorType("docks") == SectorType.DOCKS
        assert SectorType("government") == SectorType.GOVERNMENT

    def test_invalid_sector_type_raises(self) -> None:
        """Unknown sector types are rejected."""
        with pytest.raises(ValueError):
            SectorType("suburb")  # Not a valid sector type

        with pytest.raises(ValueError):
            SectorType("rural")  # Not a valid sector type

    def test_sector_type_is_string_subclass(self) -> None:
        """SectorType values can be used as strings."""
        sector = SectorType.UNIVERSITY
        assert isinstance(sector, str)
        assert sector == "university"

    def test_sector_type_count(self) -> None:
        """Exactly 6 sector types defined."""
        assert len(SectorType) == 6
