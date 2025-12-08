"""Tests for OrganizationComponent.

TDD Red Phase: These tests define the contract for OrganizationComponent.
OrganizationComponent represents the organizational capacity of an entity:
- cohesion: Internal unity and coordination [0, 1] (Probability, default 0.1)
- cadre_level: Quality of organizational leadership [0, 1] (Probability, default 0.0)

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

from babylon.models.components.base import Component
from babylon.models.components.organization import OrganizationComponent

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.math
class TestOrganizationComponentCreation:
    """Test OrganizationComponent instantiation with required and default fields."""

    def test_creation_with_defaults(self) -> None:
        """Can create OrganizationComponent with default values."""
        component = OrganizationComponent()
        assert component.cohesion == 0.1
        assert component.cadre_level == 0.0

    def test_creation_with_custom_cohesion(self) -> None:
        """Can create OrganizationComponent with custom cohesion."""
        component = OrganizationComponent(cohesion=0.7)
        assert component.cohesion == 0.7
        assert component.cadre_level == 0.0

    def test_creation_with_custom_cadre_level(self) -> None:
        """Can create OrganizationComponent with custom cadre_level."""
        component = OrganizationComponent(cadre_level=0.5)
        assert component.cohesion == 0.1
        assert component.cadre_level == 0.5

    def test_creation_with_all_custom_values(self) -> None:
        """Can create OrganizationComponent with all custom values."""
        component = OrganizationComponent(
            cohesion=0.8,
            cadre_level=0.6,
        )
        assert component.cohesion == 0.8
        assert component.cadre_level == 0.6

    def test_creation_with_boundary_values_zero(self) -> None:
        """Can create OrganizationComponent at minimum boundaries."""
        component = OrganizationComponent(
            cohesion=0.0,
            cadre_level=0.0,
        )
        assert component.cohesion == 0.0
        assert component.cadre_level == 0.0

    def test_creation_with_boundary_values_one(self) -> None:
        """Can create OrganizationComponent at maximum boundaries."""
        component = OrganizationComponent(
            cohesion=1.0,
            cadre_level=1.0,
        )
        assert component.cohesion == 1.0
        assert component.cadre_level == 1.0

    def test_creation_highly_organized(self) -> None:
        """Can create highly organized entity (high cohesion, high cadre)."""
        component = OrganizationComponent(cohesion=0.9, cadre_level=0.9)
        assert component.cohesion == 0.9
        assert component.cadre_level == 0.9

    def test_creation_atomized(self) -> None:
        """Can create atomized entity (no cohesion, no cadres)."""
        component = OrganizationComponent(cohesion=0.0, cadre_level=0.0)
        assert component.cohesion == 0.0
        assert component.cadre_level == 0.0


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestOrganizationComponentValidation:
    """Test field constraints and validation rules."""

    def test_rejects_negative_cohesion(self) -> None:
        """Cohesion cannot be negative (Probability constraint)."""
        with pytest.raises(ValidationError):
            OrganizationComponent(cohesion=-0.1)

    def test_rejects_cohesion_greater_than_one(self) -> None:
        """Cohesion cannot exceed 1.0 (Probability constraint)."""
        with pytest.raises(ValidationError):
            OrganizationComponent(cohesion=1.1)

    def test_rejects_negative_cadre_level(self) -> None:
        """Cadre level cannot be negative (Probability constraint)."""
        with pytest.raises(ValidationError):
            OrganizationComponent(cadre_level=-0.1)

    def test_rejects_cadre_level_greater_than_one(self) -> None:
        """Cadre level cannot exceed 1.0 (Probability constraint)."""
        with pytest.raises(ValidationError):
            OrganizationComponent(cadre_level=1.1)

    def test_accepts_moderate_values(self) -> None:
        """Moderate values for both fields are valid."""
        component = OrganizationComponent(cohesion=0.3, cadre_level=0.4)
        assert component.cohesion == 0.3
        assert component.cadre_level == 0.4


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.math
class TestOrganizationComponentImmutability:
    """Test that OrganizationComponent is frozen/immutable."""

    def test_cannot_mutate_cohesion(self) -> None:
        """Cannot modify cohesion after creation."""
        component = OrganizationComponent(cohesion=0.5)
        with pytest.raises(ValidationError):
            component.cohesion = 0.9  # type: ignore[misc]

    def test_cannot_mutate_cadre_level(self) -> None:
        """Cannot modify cadre_level after creation."""
        component = OrganizationComponent(cadre_level=0.5)
        with pytest.raises(ValidationError):
            component.cadre_level = 0.9  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestOrganizationComponentSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """OrganizationComponent serializes to valid JSON."""
        component = OrganizationComponent(
            cohesion=0.5,
            cadre_level=0.3,
        )
        json_str = component.model_dump_json()
        assert "0.5" in json_str
        assert "0.3" in json_str

    def test_deserialize_from_json(self) -> None:
        """OrganizationComponent can be restored from JSON."""
        json_str = '{"cohesion": 0.5, "cadre_level": 0.3}'
        component = OrganizationComponent.model_validate_json(json_str)
        assert component.cohesion == 0.5
        assert component.cadre_level == 0.3

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        original = OrganizationComponent(
            cohesion=0.42,
            cadre_level=0.67,
        )
        json_str = original.model_dump_json()
        restored = OrganizationComponent.model_validate_json(json_str)

        assert restored.cohesion == pytest.approx(original.cohesion)
        assert restored.cadre_level == pytest.approx(original.cadre_level)

    def test_dict_conversion(self) -> None:
        """OrganizationComponent converts to dict for database storage."""
        component = OrganizationComponent(
            cohesion=0.5,
            cadre_level=0.3,
        )
        data = component.model_dump()

        assert data["cohesion"] == 0.5
        assert data["cadre_level"] == 0.3


# =============================================================================
# PROTOCOL COMPLIANCE TESTS
# =============================================================================


@pytest.mark.math
class TestOrganizationComponentProtocol:
    """Test that OrganizationComponent implements Component protocol."""

    def test_implements_component_protocol(self) -> None:
        """OrganizationComponent is a valid Component."""
        component = OrganizationComponent()
        assert isinstance(component, Component)

    def test_component_type_is_organization(self) -> None:
        """component_type returns 'organization'."""
        component = OrganizationComponent()
        assert component.component_type == "organization"

    def test_component_type_is_string(self) -> None:
        """component_type returns a string."""
        component = OrganizationComponent()
        assert isinstance(component.component_type, str)


# =============================================================================
# FIELD DESCRIPTION TESTS
# =============================================================================


@pytest.mark.math
class TestOrganizationComponentFieldDescriptions:
    """Test that all fields have descriptions."""

    def test_cohesion_has_description(self) -> None:
        """cohesion field has a description."""
        field_info = OrganizationComponent.model_fields["cohesion"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_cadre_level_has_description(self) -> None:
        """cadre_level field has a description."""
        field_info = OrganizationComponent.model_fields["cadre_level"]
        assert field_info.description is not None
        assert len(field_info.description) > 0
