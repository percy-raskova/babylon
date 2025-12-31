"""Tests for VitalityComponent.

TDD Red Phase: These tests define the contract for VitalityComponent.
VitalityComponent represents the population and survival needs of an entity:
- population: Size of the population (Currency, default 1.0)
- subsistence_needs: Resources needed for survival (Currency, default 5.0)

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
from babylon.models.components.vitality import VitalityComponent

TC = TestConstants

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.math
class TestVitalityComponentCreation:
    """Test VitalityComponent instantiation with required and default fields."""

    def test_creation_with_defaults(self) -> None:
        """Can create VitalityComponent with default values."""
        component = VitalityComponent()
        assert component.population == TC.Vitality.DEFAULT_POPULATION
        assert component.subsistence_needs == TC.Vitality.DEFAULT_SUBSISTENCE

    def test_creation_with_custom_population(self) -> None:
        """Can create VitalityComponent with custom population."""
        component = VitalityComponent(population=TC.Vitality.SMALL)
        assert component.population == TC.Vitality.SMALL
        assert component.subsistence_needs == TC.Vitality.DEFAULT_SUBSISTENCE

    def test_creation_with_custom_subsistence_needs(self) -> None:
        """Can create VitalityComponent with custom subsistence_needs."""
        component = VitalityComponent(subsistence_needs=TC.Vitality.HIGH_SUBSISTENCE)
        assert component.population == TC.Vitality.DEFAULT_POPULATION
        assert component.subsistence_needs == TC.Vitality.HIGH_SUBSISTENCE

    def test_creation_with_all_custom_values(self) -> None:
        """Can create VitalityComponent with all custom values."""
        component = VitalityComponent(
            population=TC.Vitality.MEDIUM,
            subsistence_needs=TC.Vitality.ELEVATED_SUBSISTENCE,
        )
        assert component.population == TC.Vitality.MEDIUM
        assert component.subsistence_needs == TC.Vitality.ELEVATED_SUBSISTENCE

    def test_creation_with_zero_values(self) -> None:
        """Can create VitalityComponent with zero values."""
        # Boundary values kept inline (type contract test)
        component = VitalityComponent(
            population=0.0,
            subsistence_needs=0.0,
        )
        assert component.population == 0.0
        assert component.subsistence_needs == 0.0

    def test_creation_with_fractional_values(self) -> None:
        """Can create VitalityComponent with fractional values."""
        component = VitalityComponent(
            population=TC.Vitality.FRACTIONAL,
            subsistence_needs=TC.Vitality.LOW_SUBSISTENCE,
        )
        assert component.population == TC.Vitality.FRACTIONAL
        assert component.subsistence_needs == TC.Vitality.LOW_SUBSISTENCE


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestVitalityComponentValidation:
    """Test field constraints and validation rules."""

    def test_rejects_negative_population(self) -> None:
        """Population cannot be negative (Currency constraint)."""
        with pytest.raises(ValidationError):
            VitalityComponent(population=-1.0)

    def test_rejects_negative_subsistence_needs(self) -> None:
        """Subsistence needs cannot be negative (Currency constraint)."""
        with pytest.raises(ValidationError):
            VitalityComponent(subsistence_needs=-1.0)

    def test_accepts_large_population(self) -> None:
        """Large population values are valid."""
        component = VitalityComponent(population=TC.Vitality.LARGE)
        assert component.population == TC.Vitality.LARGE

    def test_accepts_large_subsistence_needs(self) -> None:
        """Large subsistence_needs values are valid."""
        component = VitalityComponent(subsistence_needs=TC.Wealth.LARGE)
        assert component.subsistence_needs == TC.Wealth.LARGE


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.math
class TestVitalityComponentImmutability:
    """Test that VitalityComponent is frozen/immutable."""

    def test_cannot_mutate_population(self) -> None:
        """Cannot modify population after creation."""
        component = VitalityComponent(population=TC.Wealth.SIGNIFICANT)
        with pytest.raises(ValidationError):
            component.population = TC.Wealth.SUBSTANTIAL  # type: ignore[misc]

    def test_cannot_mutate_subsistence_needs(self) -> None:
        """Cannot modify subsistence_needs after creation."""
        component = VitalityComponent(subsistence_needs=TC.Vitality.HIGH_SUBSISTENCE)
        with pytest.raises(ValidationError):
            component.subsistence_needs = TC.Vitality.DOUBLED_SUBSISTENCE  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestVitalityComponentSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """VitalityComponent serializes to valid JSON."""
        component = VitalityComponent(
            population=TC.Wealth.SIGNIFICANT,
            subsistence_needs=TC.Vitality.ELEVATED_SUBSISTENCE,
        )
        json_str = component.model_dump_json()
        assert "100" in json_str
        assert "8" in json_str

    def test_deserialize_from_json(self) -> None:
        """VitalityComponent can be restored from JSON."""
        # JSON string literal with raw values (testing deserialization)
        json_str = '{"population": 100.0, "subsistence_needs": 8.0}'
        component = VitalityComponent.model_validate_json(json_str)
        assert component.population == TC.Wealth.SIGNIFICANT
        assert component.subsistence_needs == TC.Vitality.ELEVATED_SUBSISTENCE

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        # Precision test values - kept inline to verify exact decimal preservation
        original = VitalityComponent(
            population=123.45,
            subsistence_needs=67.89,
        )
        json_str = original.model_dump_json()
        restored = VitalityComponent.model_validate_json(json_str)

        assert restored.population == pytest.approx(original.population)
        assert restored.subsistence_needs == pytest.approx(original.subsistence_needs)

    def test_dict_conversion(self) -> None:
        """VitalityComponent converts to dict for database storage."""
        component = VitalityComponent(
            population=TC.Wealth.SIGNIFICANT,
            subsistence_needs=TC.Vitality.ELEVATED_SUBSISTENCE,
        )
        data = component.model_dump()

        assert data["population"] == TC.Wealth.SIGNIFICANT
        assert data["subsistence_needs"] == TC.Vitality.ELEVATED_SUBSISTENCE


# =============================================================================
# PROTOCOL COMPLIANCE TESTS
# =============================================================================


@pytest.mark.math
class TestVitalityComponentProtocol:
    """Test that VitalityComponent implements Component protocol."""

    def test_implements_component_protocol(self) -> None:
        """VitalityComponent is a valid Component."""
        component = VitalityComponent()
        assert isinstance(component, Component)

    def test_component_type_is_vitality(self) -> None:
        """component_type returns 'vitality'."""
        component = VitalityComponent()
        assert component.component_type == "vitality"

    def test_component_type_is_string(self) -> None:
        """component_type returns a string."""
        component = VitalityComponent()
        assert isinstance(component.component_type, str)


# =============================================================================
# FIELD DESCRIPTION TESTS
# =============================================================================


@pytest.mark.math
class TestVitalityComponentFieldDescriptions:
    """Test that all fields have descriptions."""

    def test_population_has_description(self) -> None:
        """population field has a description."""
        field_info = VitalityComponent.model_fields["population"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_subsistence_needs_has_description(self) -> None:
        """subsistence_needs field has a description."""
        field_info = VitalityComponent.model_fields["subsistence_needs"]
        assert field_info.description is not None
        assert len(field_info.description) > 0
