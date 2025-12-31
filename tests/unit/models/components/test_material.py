"""Tests for MaterialComponent.

TDD Red Phase: These tests define the contract for MaterialComponent.
MaterialComponent represents the material conditions of an entity:
- wealth: Economic resources (Currency, default 10.0)
- resources: Available material resources (Currency, default 0.0)
- means_of_production: Control over productive apparatus (Probability, default 0.0)

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
from babylon.models.components.material import MaterialComponent

TC = TestConstants

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.math
class TestMaterialComponentCreation:
    """Test MaterialComponent instantiation with required and default fields."""

    def test_creation_with_defaults(self) -> None:
        """Can create MaterialComponent with default values."""
        component = MaterialComponent()
        assert component.wealth == TC.Wealth.DEFAULT_WEALTH
        assert component.resources == TC.Wealth.DESTITUTE
        assert component.means_of_production == TC.Probability.ZERO

    def test_creation_with_custom_wealth(self) -> None:
        """Can create MaterialComponent with custom wealth."""
        component = MaterialComponent(wealth=TC.Wealth.SIGNIFICANT)
        assert component.wealth == TC.Wealth.SIGNIFICANT
        assert component.resources == TC.Wealth.DESTITUTE
        assert component.means_of_production == TC.Probability.ZERO

    def test_creation_with_custom_resources(self) -> None:
        """Can create MaterialComponent with custom resources."""
        component = MaterialComponent(resources=TC.Wealth.MODEST)
        assert component.wealth == TC.Wealth.DEFAULT_WEALTH
        assert component.resources == TC.Wealth.MODEST
        assert component.means_of_production == TC.Probability.ZERO

    def test_creation_with_custom_means_of_production(self) -> None:
        """Can create MaterialComponent with custom means_of_production."""
        component = MaterialComponent(means_of_production=TC.Probability.VERY_HIGH)
        assert component.wealth == TC.Wealth.DEFAULT_WEALTH
        assert component.resources == TC.Wealth.DESTITUTE
        assert component.means_of_production == TC.Probability.VERY_HIGH

    def test_creation_with_all_custom_values(self) -> None:
        """Can create MaterialComponent with all custom values."""
        component = MaterialComponent(
            wealth=TC.Wealth.HIGH,
            resources=TC.Wealth.SUBSTANTIAL,
            means_of_production=TC.Probability.EXTREME,
        )
        assert component.wealth == TC.Wealth.HIGH
        assert component.resources == TC.Wealth.SUBSTANTIAL
        assert component.means_of_production == TC.Probability.EXTREME

    def test_creation_with_zero_values(self) -> None:
        """Can create MaterialComponent with zero values."""
        component = MaterialComponent(
            wealth=0.0,
            resources=0.0,
            means_of_production=0.0,
        )
        assert component.wealth == 0.0
        assert component.resources == 0.0
        assert component.means_of_production == 0.0

    def test_creation_with_boundary_means_of_production(self) -> None:
        """Can create MaterialComponent with means_of_production at boundaries."""
        # Minimum boundary
        component_min = MaterialComponent(means_of_production=0.0)
        assert component_min.means_of_production == 0.0

        # Maximum boundary
        component_max = MaterialComponent(means_of_production=1.0)
        assert component_max.means_of_production == 1.0


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestMaterialComponentValidation:
    """Test field constraints and validation rules."""

    def test_rejects_negative_wealth(self) -> None:
        """Wealth cannot be negative (Currency constraint)."""
        with pytest.raises(ValidationError):
            MaterialComponent(wealth=-1.0)

    def test_rejects_negative_resources(self) -> None:
        """Resources cannot be negative (Currency constraint)."""
        with pytest.raises(ValidationError):
            MaterialComponent(resources=-1.0)

    def test_rejects_negative_means_of_production(self) -> None:
        """Means of production cannot be negative (Probability constraint)."""
        with pytest.raises(ValidationError):
            MaterialComponent(means_of_production=-0.1)

    def test_rejects_means_of_production_greater_than_one(self) -> None:
        """Means of production cannot exceed 1.0 (Probability constraint)."""
        with pytest.raises(ValidationError):
            MaterialComponent(means_of_production=1.1)

    def test_accepts_large_wealth(self) -> None:
        """Large wealth values are valid."""
        component = MaterialComponent(wealth=TC.Wealth.LARGE)
        assert component.wealth == TC.Wealth.LARGE

    def test_accepts_large_resources(self) -> None:
        """Large resources values are valid."""
        component = MaterialComponent(resources=TC.Wealth.LARGE)
        assert component.resources == TC.Wealth.LARGE


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.math
class TestMaterialComponentImmutability:
    """Test that MaterialComponent is frozen/immutable."""

    def test_cannot_mutate_wealth(self) -> None:
        """Cannot modify wealth after creation."""
        component = MaterialComponent(wealth=TC.Wealth.SIGNIFICANT)
        with pytest.raises(ValidationError):
            component.wealth = TC.Wealth.SUBSTANTIAL  # type: ignore[misc]

    def test_cannot_mutate_resources(self) -> None:
        """Cannot modify resources after creation."""
        component = MaterialComponent(resources=TC.Wealth.MODEST)
        with pytest.raises(ValidationError):
            component.resources = TC.Wealth.SIGNIFICANT  # type: ignore[misc]

    def test_cannot_mutate_means_of_production(self) -> None:
        """Cannot modify means_of_production after creation."""
        component = MaterialComponent(means_of_production=TC.Probability.MIDPOINT)
        with pytest.raises(ValidationError):
            component.means_of_production = TC.Probability.EXTREME  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestMaterialComponentSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """MaterialComponent serializes to valid JSON."""
        component = MaterialComponent(
            wealth=TC.Wealth.SIGNIFICANT,
            resources=TC.Wealth.MODEST,
            means_of_production=TC.Probability.HIGH,
        )
        json_str = component.model_dump_json()
        assert "100" in json_str
        assert "50" in json_str
        assert "0.7" in json_str

    def test_deserialize_from_json(self) -> None:
        """MaterialComponent can be restored from JSON."""
        # JSON string literal with raw values (testing deserialization)
        json_str = '{"wealth": 100.0, "resources": 50.0, "means_of_production": 0.7}'
        component = MaterialComponent.model_validate_json(json_str)
        assert component.wealth == TC.Wealth.SIGNIFICANT
        assert component.resources == TC.Wealth.MODEST
        assert component.means_of_production == TC.Probability.HIGH

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        # Precision test values - kept inline to verify exact decimal preservation
        original = MaterialComponent(
            wealth=123.45,
            resources=67.89,
            means_of_production=0.42,
        )
        json_str = original.model_dump_json()
        restored = MaterialComponent.model_validate_json(json_str)

        assert restored.wealth == pytest.approx(original.wealth)
        assert restored.resources == pytest.approx(original.resources)
        assert restored.means_of_production == pytest.approx(original.means_of_production)

    def test_dict_conversion(self) -> None:
        """MaterialComponent converts to dict for database storage."""
        component = MaterialComponent(
            wealth=TC.Wealth.SIGNIFICANT,
            resources=TC.Wealth.MODEST,
            means_of_production=TC.Probability.HIGH,
        )
        data = component.model_dump()

        assert data["wealth"] == TC.Wealth.SIGNIFICANT
        assert data["resources"] == TC.Wealth.MODEST
        assert data["means_of_production"] == TC.Probability.HIGH


# =============================================================================
# PROTOCOL COMPLIANCE TESTS
# =============================================================================


@pytest.mark.math
class TestMaterialComponentProtocol:
    """Test that MaterialComponent implements Component protocol."""

    def test_implements_component_protocol(self) -> None:
        """MaterialComponent is a valid Component."""
        component = MaterialComponent()
        assert isinstance(component, Component)

    def test_component_type_is_material(self) -> None:
        """component_type returns 'material'."""
        component = MaterialComponent()
        assert component.component_type == "material"

    def test_component_type_is_string(self) -> None:
        """component_type returns a string."""
        component = MaterialComponent()
        assert isinstance(component.component_type, str)


# =============================================================================
# FIELD DESCRIPTION TESTS
# =============================================================================


@pytest.mark.math
class TestMaterialComponentFieldDescriptions:
    """Test that all fields have descriptions."""

    def test_wealth_has_description(self) -> None:
        """wealth field has a description."""
        field_info = MaterialComponent.model_fields["wealth"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_resources_has_description(self) -> None:
        """resources field has a description."""
        field_info = MaterialComponent.model_fields["resources"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_means_of_production_has_description(self) -> None:
        """means_of_production field has a description."""
        field_info = MaterialComponent.model_fields["means_of_production"]
        assert field_info.description is not None
        assert len(field_info.description) > 0
