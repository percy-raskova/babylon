"""Tests for babylon.models.entities.territory.

TDD Red Phase: These tests define the contract for the Territory entity.
Territory is the Phase 3.5 node type - the spatial substrate of the simulation.

Sprint 3.5.2: Layer 0 - The Territorial Substrate.
"""

import pytest
from pydantic import ValidationError

from babylon.models.entities.territory import Territory
from babylon.models.enums import OperationalProfile, SectorType

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryCreation:
    """Territory should be createable with valid data."""

    def test_minimal_creation(self) -> None:
        """Can create Territory with only required fields."""
        territory = Territory(
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
        )
        assert territory.id == "T001"
        assert territory.name == "University District"
        assert territory.sector_type == SectorType.UNIVERSITY

    def test_full_creation(self) -> None:
        """Can create Territory with all fields."""
        territory = Territory(
            id="T002",
            name="Industrial Zone",
            sector_type=SectorType.INDUSTRIAL,
            host_id="C001",
            occupant_id="C002",
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.5,
            rent_level=2.0,
            population=1000,
            under_eviction=True,
        )
        assert territory.host_id == "C001"
        assert territory.occupant_id == "C002"
        assert territory.profile == OperationalProfile.HIGH_PROFILE
        assert territory.heat == 0.5
        assert territory.rent_level == 2.0
        assert territory.population == 1000
        assert territory.under_eviction is True


# =============================================================================
# ID VALIDATION TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryIdValidation:
    """Territory ID must match pattern ^T[0-9]{3}$."""

    def test_valid_id_t001(self) -> None:
        """T001 is a valid territory ID."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.id == "T001"

    def test_valid_id_t999(self) -> None:
        """T999 is a valid territory ID."""
        territory = Territory(
            id="T999",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.id == "T999"

    def test_invalid_id_lowercase(self) -> None:
        """Lowercase 't' is invalid."""
        with pytest.raises(ValidationError):
            Territory(
                id="t001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
            )

    def test_invalid_id_wrong_prefix(self) -> None:
        """Wrong prefix is invalid (must be T, not C)."""
        with pytest.raises(ValidationError):
            Territory(
                id="C001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
            )

    def test_invalid_id_too_short(self) -> None:
        """Too few digits is invalid."""
        with pytest.raises(ValidationError):
            Territory(
                id="T01",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
            )

    def test_invalid_id_too_long(self) -> None:
        """Too many digits is invalid."""
        with pytest.raises(ValidationError):
            Territory(
                id="T0001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
            )


# =============================================================================
# DEFAULT VALUES TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryDefaults:
    """Territory should have sensible default values."""

    def test_profile_defaults_to_low(self) -> None:
        """Profile defaults to LOW_PROFILE (safe, low recruitment)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.profile == OperationalProfile.LOW_PROFILE

    def test_heat_defaults_to_zero(self) -> None:
        """Heat defaults to 0.0 (no state attention)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.heat == 0.0

    def test_rent_level_defaults_to_one(self) -> None:
        """Rent level defaults to 1.0 (baseline)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.rent_level == 1.0

    def test_population_defaults_to_zero(self) -> None:
        """Population defaults to 0."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.population == 0

    def test_host_id_defaults_to_none(self) -> None:
        """Host ID defaults to None (no legal sovereign)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.host_id is None

    def test_occupant_id_defaults_to_none(self) -> None:
        """Occupant ID defaults to None (no de facto occupant)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.occupant_id is None

    def test_under_eviction_defaults_to_false(self) -> None:
        """Under eviction defaults to False."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.under_eviction is False


# =============================================================================
# CONSTRAINED TYPE TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryConstrainedTypes:
    """Territory should validate constrained types."""

    def test_heat_accepts_zero(self) -> None:
        """Heat of 0.0 is valid (no attention)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            heat=0.0,
        )
        assert territory.heat == 0.0

    def test_heat_accepts_one(self) -> None:
        """Heat of 1.0 is valid (maximum attention)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            heat=1.0,
        )
        assert territory.heat == 1.0

    def test_heat_rejects_negative(self) -> None:
        """Negative heat is invalid."""
        with pytest.raises(ValidationError):
            Territory(
                id="T001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
                heat=-0.1,
            )

    def test_heat_rejects_greater_than_one(self) -> None:
        """Heat > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            Territory(
                id="T001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
                heat=1.1,
            )

    def test_rent_level_accepts_zero(self) -> None:
        """Rent level of 0.0 is valid (free)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            rent_level=0.0,
        )
        assert territory.rent_level == 0.0

    def test_rent_level_accepts_large(self) -> None:
        """Large rent level is valid."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            rent_level=100.0,
        )
        assert territory.rent_level == 100.0

    def test_rent_level_rejects_negative(self) -> None:
        """Negative rent level is invalid."""
        with pytest.raises(ValidationError):
            Territory(
                id="T001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
                rent_level=-1.0,
            )

    def test_population_accepts_zero(self) -> None:
        """Population of 0 is valid (empty)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            population=0,
        )
        assert territory.population == 0

    def test_population_accepts_large(self) -> None:
        """Large population is valid."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            population=1000000,
        )
        assert territory.population == 1000000

    def test_population_rejects_negative(self) -> None:
        """Negative population is invalid."""
        with pytest.raises(ValidationError):
            Territory(
                id="T001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
                population=-1,
            )


# =============================================================================
# COMPUTED PROPERTY TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryClarityBonus:
    """Territory clarity_bonus property for recruitment effects."""

    def test_low_profile_no_clarity_bonus(self) -> None:
        """LOW_PROFILE gives 0.0 clarity bonus (safe but boring)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.LOW_PROFILE,
        )
        assert territory.clarity_bonus == 0.0

    def test_high_profile_clarity_bonus(self) -> None:
        """HIGH_PROFILE gives 0.3 clarity bonus (attracts cadre)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            profile=OperationalProfile.HIGH_PROFILE,
        )
        assert territory.clarity_bonus == 0.3


@pytest.mark.topology
class TestTerritoryLiberation:
    """Territory is_liberated property for sovereign status."""

    def test_unoccupied_not_liberated(self) -> None:
        """Territory with no occupant is not liberated."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            host_id=None,
            occupant_id=None,
        )
        assert territory.is_liberated is False

    def test_with_host_not_liberated(self) -> None:
        """Territory with host is not liberated (still under sovereignty)."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            host_id="C001",
            occupant_id="C002",
        )
        assert territory.is_liberated is False

    def test_occupant_no_host_is_liberated(self) -> None:
        """Territory with occupant but no host IS liberated."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            host_id=None,
            occupant_id="C002",
        )
        assert territory.is_liberated is True


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritorySerialization:
    """Territory should serialize correctly for save/load."""

    def test_json_round_trip(self) -> None:
        """Territory survives JSON round-trip."""
        original = Territory(
            id="T001",
            name="University District",
            sector_type=SectorType.UNIVERSITY,
            host_id="C001",
            occupant_id="C002",
            profile=OperationalProfile.HIGH_PROFILE,
            heat=0.5,
            rent_level=1.5,
            population=5000,
            under_eviction=True,
        )
        json_str = original.model_dump_json()
        restored = Territory.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.sector_type == original.sector_type
        assert restored.host_id == original.host_id
        assert restored.occupant_id == original.occupant_id
        assert restored.profile == original.profile
        assert restored.heat == pytest.approx(original.heat)
        assert restored.rent_level == pytest.approx(original.rent_level)
        assert restored.population == original.population
        assert restored.under_eviction == original.under_eviction

    def test_dict_round_trip(self) -> None:
        """Territory survives dict round-trip."""
        original = Territory(
            id="T001",
            name="Docks",
            sector_type=SectorType.DOCKS,
            heat=0.3,
        )
        data = original.model_dump()
        restored = Territory.model_validate(data)

        assert restored.id == original.id
        assert restored.sector_type == original.sector_type
        assert restored.heat == original.heat

    def test_enums_serialize_as_strings(self) -> None:
        """Enums serialize to string values for JSON compatibility."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.GOVERNMENT,
            profile=OperationalProfile.LOW_PROFILE,
        )
        data = territory.model_dump()

        assert data["sector_type"] == "government"
        assert data["profile"] == "low_profile"
