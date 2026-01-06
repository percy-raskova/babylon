"""Tests for babylon.models.entities.territory.

TDD Red Phase: These tests define the contract for the Territory entity.
Territory is the Phase 3.5 node type - the spatial substrate of the simulation.

Sprint 3.5.2: Layer 0 - The Territorial Substrate.

Refactored with pytest.parametrize for Phase 4 of Unit Test Health Improvement Plan.
"""

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

from babylon.models.entities.territory import Territory
from babylon.models.enums import OperationalProfile, SectorType, TerritoryType

# Aliases for readability
TC = TestConstants

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
            heat=TC.Territory.MODERATE_HEAT,
            rent_level=TC.Territory.ELEVATED_RENT,
            population=TC.Territory.SMALL_POPULATION,
            under_eviction=True,
        )
        assert territory.host_id == "C001"
        assert territory.occupant_id == "C002"
        assert territory.profile == OperationalProfile.HIGH_PROFILE
        assert territory.heat == TC.Territory.MODERATE_HEAT
        assert territory.rent_level == TC.Territory.ELEVATED_RENT
        assert territory.population == TC.Territory.SMALL_POPULATION
        assert territory.under_eviction is True


# =============================================================================
# ID VALIDATION TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryIdValidation:
    """Territory ID must match pattern ^T[0-9]{3}$."""

    @pytest.mark.parametrize(
        "valid_id",
        ["T001", "T999", "T000", "T123"],
        ids=["t001", "t999", "t000", "t123"],
    )
    def test_valid_id(self, valid_id: str) -> None:
        """Valid territory IDs are accepted."""
        territory = Territory(
            id=valid_id,
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.id == valid_id

    @pytest.mark.parametrize(
        "invalid_id,reason",
        [
            ("t001", "lowercase"),
            ("C001", "wrong_prefix"),
            ("T01", "too_short"),
            ("T0001", "too_long"),
        ],
        ids=["lowercase", "wrong_prefix", "too_short", "too_long"],
    )
    def test_invalid_id(self, invalid_id: str, reason: str) -> None:
        """Invalid territory IDs are rejected: {reason}."""
        with pytest.raises(ValidationError):
            Territory(
                id=invalid_id,
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
            )


# =============================================================================
# DEFAULT VALUES TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryDefaults:
    """Territory should have sensible default values."""

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("profile", OperationalProfile.LOW_PROFILE),
            ("heat", TC.Territory.NO_HEAT),
            ("rent_level", TC.Territory.BASELINE_RENT),
            ("population", TC.Territory.EMPTY),
            ("host_id", None),
            ("occupant_id", None),
            ("under_eviction", False),
        ],
        ids=[
            "profile_low",
            "heat_zero",
            "rent_baseline",
            "population_zero",
            "host_none",
            "occupant_none",
            "not_under_eviction",
        ],
    )
    def test_defaults(self, attr: str, expected: object) -> None:
        """Territory has correct default values."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert getattr(territory, attr) == expected


# =============================================================================
# CONSTRAINED TYPE TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryConstrainedTypes:
    """Territory should validate constrained types."""

    @pytest.mark.parametrize(
        "field,valid_value",
        [
            ("heat", 0.0),
            ("heat", 1.0),
            ("rent_level", 0.0),
            ("rent_level", 100.0),
            ("population", 0),
            ("population", TC.Territory.LARGE_POPULATION),
        ],
        ids=[
            "heat_zero",
            "heat_one",
            "rent_zero",
            "rent_large",
            "population_zero",
            "population_large",
        ],
    )
    def test_accepts_valid_value(self, field: str, valid_value: object) -> None:
        """Territory accepts valid {field} value."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            **{field: valid_value},
        )
        assert getattr(territory, field) == valid_value

    @pytest.mark.parametrize(
        "field,invalid_value",
        [
            ("heat", -0.1),
            ("heat", 1.1),
            ("rent_level", -1.0),
            ("population", -1),
        ],
        ids=[
            "heat_negative",
            "heat_over_one",
            "rent_negative",
            "population_negative",
        ],
    )
    def test_rejects_invalid_value(self, field: str, invalid_value: object) -> None:
        """Territory rejects invalid {field} value."""
        with pytest.raises(ValidationError):
            Territory(
                id="T001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
                **{field: invalid_value},
            )


# =============================================================================
# COMPUTED PROPERTY TESTS
# =============================================================================


@pytest.mark.topology
class TestTerritoryClarityBonus:
    """Territory clarity_bonus property for recruitment effects."""

    @pytest.mark.parametrize(
        "profile,expected_bonus",
        [
            (OperationalProfile.LOW_PROFILE, 0.0),
            (OperationalProfile.HIGH_PROFILE, 0.3),
        ],
        ids=["low_profile_no_bonus", "high_profile_bonus"],
    )
    def test_clarity_bonus(self, profile: OperationalProfile, expected_bonus: float) -> None:
        """Profile {profile} gives {expected_bonus} clarity bonus."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            profile=profile,
        )
        assert territory.clarity_bonus == expected_bonus


@pytest.mark.topology
class TestTerritoryLiberation:
    """Territory is_liberated property for sovereign status."""

    @pytest.mark.parametrize(
        "host_id,occupant_id,expected",
        [
            (None, None, False),
            ("C001", "C002", False),
            (None, "C002", True),
        ],
        ids=["unoccupied", "with_host", "occupant_no_host_liberated"],
    )
    def test_is_liberated(
        self, host_id: str | None, occupant_id: str | None, expected: bool
    ) -> None:
        """Territory liberation status is correct."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            host_id=host_id,
            occupant_id=occupant_id,
        )
        assert territory.is_liberated is expected


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
            heat=TC.Territory.MODERATE_HEAT,
            rent_level=TC.Territory.ELEVATED_RENT,
            population=TC.Territory.SMALL_POPULATION,
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


# =============================================================================
# TERRITORY TYPE TESTS (Sprint 3.7: The Carceral Geography)
# =============================================================================


@pytest.mark.unit
class TestTerritoryTypeDefault:
    """Territory type defaults and validation tests."""

    def test_territory_type_defaults_to_core(self) -> None:
        """Territory type defaults to CORE (high value, low heat destination).

        Sprint 3.7: The Carceral Geography - Necropolitical Triad.
        Most territories are CORE by default - they are destinations for
        labor aristocracy, not containment zones.
        """
        territory = Territory(
            id="T001",
            name="Suburbs",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert territory.territory_type == TerritoryType.CORE


@pytest.mark.unit
class TestTerritorySinkNode:
    """Tests for is_sink_node property.

    Sprint 3.7: The Carceral Geography - Necropolitical Triad.
    Sink nodes are territories where displaced populations are routed.
    They have no economic value - only containment/elimination function.
    """

    @pytest.mark.parametrize(
        "territory_type,is_sink",
        [
            (TerritoryType.RESERVATION, True),
            (TerritoryType.PENAL_COLONY, True),
            (TerritoryType.CONCENTRATION_CAMP, True),
            (TerritoryType.CORE, False),
            (TerritoryType.PERIPHERY, False),
        ],
        ids=[
            "reservation_sink",
            "penal_colony_sink",
            "concentration_camp_sink",
            "core_not_sink",
            "periphery_not_sink",
        ],
    )
    def test_is_sink_node(self, territory_type: TerritoryType, is_sink: bool) -> None:
        """Territory type {territory_type} is_sink_node={is_sink}."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            territory_type=territory_type,
        )
        assert territory.is_sink_node is is_sink


# =============================================================================
# METABOLIC DYNAMICS TESTS (Slice 1.4)
# =============================================================================


@pytest.mark.topology
class TestTerritoryMetabolicDefaults:
    """Territory metabolic fields should have sensible defaults."""

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("biocapacity", TC.Territory.FULL_BIOCAPACITY),
            ("max_biocapacity", TC.Territory.FULL_BIOCAPACITY),
            ("regeneration_rate", TC.Territory.DEFAULT_REGENERATION),
            ("extraction_intensity", TC.Probability.ZERO),
        ],
        ids=[
            "biocapacity_full",
            "max_biocapacity_full",
            "regeneration_2pct",
            "extraction_zero",
        ],
    )
    def test_metabolic_defaults(self, attr: str, expected: object) -> None:
        """Territory has correct metabolic default values."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
        )
        assert getattr(territory, attr) == expected


@pytest.mark.topology
class TestTerritoryMetabolicConstraints:
    """Territory metabolic fields should be properly constrained."""

    @pytest.mark.parametrize(
        "field,valid_value",
        [
            ("biocapacity", 0.0),
            ("max_biocapacity", 0.0),
            ("regeneration_rate", 0.0),
            ("regeneration_rate", 1.0),
            ("extraction_intensity", 0.0),
            ("extraction_intensity", 1.0),
        ],
        ids=[
            "biocapacity_zero",
            "max_biocapacity_zero",
            "regeneration_zero",
            "regeneration_one",
            "extraction_zero",
            "extraction_one",
        ],
    )
    def test_accepts_valid_metabolic_value(self, field: str, valid_value: float) -> None:
        """Territory accepts valid {field} value."""
        territory = Territory(
            id="T001",
            name="Test",
            sector_type=SectorType.RESIDENTIAL,
            **{field: valid_value},
        )
        assert getattr(territory, field) == valid_value

    @pytest.mark.parametrize(
        "field,invalid_value",
        [
            ("biocapacity", -10.0),
            ("max_biocapacity", -50.0),
            ("regeneration_rate", -0.01),
            ("regeneration_rate", 1.1),
            ("extraction_intensity", -0.1),
            ("extraction_intensity", 1.5),
        ],
        ids=[
            "biocapacity_negative",
            "max_biocapacity_negative",
            "regeneration_negative",
            "regeneration_over_one",
            "extraction_negative",
            "extraction_over_one",
        ],
    )
    def test_rejects_invalid_metabolic_value(self, field: str, invalid_value: float) -> None:
        """Territory rejects invalid {field} value."""
        with pytest.raises(ValidationError):
            Territory(
                id="T001",
                name="Test",
                sector_type=SectorType.RESIDENTIAL,
                **{field: invalid_value},
            )
