"""Tests for SpatialComponent.

TDD Red Phase: These tests define the contract for SpatialComponent.
SpatialComponent represents the location and mobility of an entity:
- location_id: Geographic or topological location identifier (str, default "")
- mobility: Ability to relocate [0, 1] (Probability, default 0.5)

All tests verify:
1. Valid creation with defaults
2. Valid creation with custom values
3. Rejection of invalid values (out of bounds)
4. Frozen/immutable (raises on mutation)
5. JSON serialization round-trip
6. Implements Component protocol
"""

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

from babylon.models.components.base import Component
from babylon.models.components.spatial import SpatialComponent

TC = TestConstants

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.math
class TestSpatialComponentCreation:
    """Test SpatialComponent instantiation with required and default fields."""

    def test_creation_with_defaults(self) -> None:
        """Can create SpatialComponent with default values."""
        component = SpatialComponent()
        assert component.location_id == ""
        assert component.mobility == TC.Spatial.DEFAULT_MOBILITY

    def test_creation_with_custom_location_id(self) -> None:
        """Can create SpatialComponent with custom location_id."""
        component = SpatialComponent(location_id="region_001")
        assert component.location_id == "region_001"
        assert component.mobility == TC.Spatial.DEFAULT_MOBILITY

    def test_creation_with_custom_mobility(self) -> None:
        """Can create SpatialComponent with custom mobility."""
        component = SpatialComponent(mobility=TC.Spatial.HIGH_MOBILITY)
        assert component.location_id == ""
        assert component.mobility == TC.Spatial.HIGH_MOBILITY

    def test_creation_with_all_custom_values(self) -> None:
        """Can create SpatialComponent with all custom values."""
        component = SpatialComponent(
            location_id="core_industrial_zone",
            mobility=TC.Spatial.LOW_MOBILITY,
        )
        assert component.location_id == "core_industrial_zone"
        assert component.mobility == TC.Spatial.LOW_MOBILITY

    def test_creation_with_boundary_mobility_zero(self) -> None:
        """Can create SpatialComponent with mobility at minimum boundary."""
        component = SpatialComponent(mobility=0.0)
        assert component.mobility == 0.0

    def test_creation_with_boundary_mobility_one(self) -> None:
        """Can create SpatialComponent with mobility at maximum boundary."""
        component = SpatialComponent(mobility=1.0)
        assert component.mobility == 1.0

    def test_creation_with_various_location_ids(self) -> None:
        """Can create SpatialComponent with various location_id formats."""
        test_locations = [
            "L001",
            "region_north",
            "global/asia/china",
            "123",
            "node-42",
        ]
        for loc in test_locations:
            component = SpatialComponent(location_id=loc)
            assert component.location_id == loc


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestSpatialComponentValidation:
    """Test field constraints and validation rules."""

    def test_rejects_negative_mobility(self) -> None:
        """Mobility cannot be negative (Probability constraint)."""
        with pytest.raises(ValidationError):
            SpatialComponent(mobility=-0.1)

    def test_rejects_mobility_greater_than_one(self) -> None:
        """Mobility cannot exceed 1.0 (Probability constraint)."""
        with pytest.raises(ValidationError):
            SpatialComponent(mobility=1.1)

    def test_accepts_empty_location_id(self) -> None:
        """Empty string is valid for location_id."""
        component = SpatialComponent(location_id="")
        assert component.location_id == ""

    def test_accepts_long_location_id(self) -> None:
        """Long location_id strings are valid."""
        long_location = "region/subregion/area/zone/sector/block/unit"
        component = SpatialComponent(location_id=long_location)
        assert component.location_id == long_location


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.math
class TestSpatialComponentImmutability:
    """Test that SpatialComponent is frozen/immutable."""

    def test_cannot_mutate_location_id(self) -> None:
        """Cannot modify location_id after creation."""
        component = SpatialComponent(location_id="region_001")
        with pytest.raises(ValidationError):
            component.location_id = "region_002"  # type: ignore[misc]

    def test_cannot_mutate_mobility(self) -> None:
        """Cannot modify mobility after creation."""
        component = SpatialComponent(mobility=TC.Spatial.DEFAULT_MOBILITY)
        with pytest.raises(ValidationError):
            component.mobility = TC.Probability.EXTREME  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSpatialComponentSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """SpatialComponent serializes to valid JSON."""
        component = SpatialComponent(
            location_id="region_001",
            mobility=TC.Probability.HIGH,
        )
        json_str = component.model_dump_json()
        assert "region_001" in json_str
        assert "0.7" in json_str

    def test_deserialize_from_json(self) -> None:
        """SpatialComponent can be restored from JSON."""
        # JSON string literal with raw values (testing deserialization)
        json_str = '{"location_id": "region_001", "mobility": 0.7}'
        component = SpatialComponent.model_validate_json(json_str)
        assert component.location_id == "region_001"
        assert component.mobility == TC.Probability.HIGH

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        # Precision test value - kept inline to verify exact decimal preservation
        original = SpatialComponent(
            location_id="core/industrial/zone_42",
            mobility=0.35,
        )
        json_str = original.model_dump_json()
        restored = SpatialComponent.model_validate_json(json_str)

        assert restored.location_id == original.location_id
        assert restored.mobility == pytest.approx(original.mobility)

    def test_dict_conversion(self) -> None:
        """SpatialComponent converts to dict for database storage."""
        component = SpatialComponent(
            location_id="region_001",
            mobility=TC.Probability.HIGH,
        )
        data = component.model_dump()

        assert data["location_id"] == "region_001"
        assert data["mobility"] == TC.Probability.HIGH


# =============================================================================
# PROTOCOL COMPLIANCE TESTS
# =============================================================================


@pytest.mark.math
class TestSpatialComponentProtocol:
    """Test that SpatialComponent implements Component protocol."""

    def test_implements_component_protocol(self) -> None:
        """SpatialComponent is a valid Component."""
        component = SpatialComponent()
        assert isinstance(component, Component)

    def test_component_type_is_spatial(self) -> None:
        """component_type returns 'spatial'."""
        component = SpatialComponent()
        assert component.component_type == "spatial"

    def test_component_type_is_string(self) -> None:
        """component_type returns a string."""
        component = SpatialComponent()
        assert isinstance(component.component_type, str)


# =============================================================================
# FIELD DESCRIPTION TESTS
# =============================================================================


@pytest.mark.math
class TestSpatialComponentFieldDescriptions:
    """Test that all fields have descriptions."""

    def test_location_id_has_description(self) -> None:
        """location_id field has a description."""
        field_info = SpatialComponent.model_fields["location_id"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_mobility_has_description(self) -> None:
        """mobility field has a description."""
        field_info = SpatialComponent.model_fields["mobility"]
        assert field_info.description is not None
        assert len(field_info.description) > 0
