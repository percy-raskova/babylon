"""Tests for IdeologicalComponent.

TDD Red Phase: These tests define the contract for IdeologicalComponent.
IdeologicalComponent represents the George Jackson Model of ideological state:
- class_consciousness: Relationship to Capital [0, 1] (default 0.0)
- national_identity: Relationship to State [0, 1] (default 0.5)
- agitation: Raw political energy [0, inf) (default 0.0) - NO UPPER BOUND

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
from babylon.models.components.ideological import IdeologicalComponent

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.math
class TestIdeologicalComponentCreation:
    """Test IdeologicalComponent instantiation with required and default fields."""

    def test_creation_with_defaults(self) -> None:
        """Can create IdeologicalComponent with default values."""
        component = IdeologicalComponent()
        assert component.class_consciousness == 0.0
        assert component.national_identity == 0.5
        assert component.agitation == 0.0

    def test_creation_with_custom_class_consciousness(self) -> None:
        """Can create IdeologicalComponent with custom class_consciousness."""
        component = IdeologicalComponent(class_consciousness=0.7)
        assert component.class_consciousness == 0.7
        assert component.national_identity == 0.5
        assert component.agitation == 0.0

    def test_creation_with_custom_national_identity(self) -> None:
        """Can create IdeologicalComponent with custom national_identity."""
        component = IdeologicalComponent(national_identity=0.9)
        assert component.class_consciousness == 0.0
        assert component.national_identity == 0.9
        assert component.agitation == 0.0

    def test_creation_with_custom_agitation(self) -> None:
        """Can create IdeologicalComponent with custom agitation."""
        component = IdeologicalComponent(agitation=2.5)
        assert component.class_consciousness == 0.0
        assert component.national_identity == 0.5
        assert component.agitation == 2.5

    def test_creation_with_all_custom_values(self) -> None:
        """Can create IdeologicalComponent with all custom values."""
        component = IdeologicalComponent(
            class_consciousness=0.8,
            national_identity=0.3,
            agitation=1.5,
        )
        assert component.class_consciousness == 0.8
        assert component.national_identity == 0.3
        assert component.agitation == 1.5

    def test_creation_revolutionary_boundary(self) -> None:
        """Can create IdeologicalComponent at revolutionary boundary (class_consciousness=1.0)."""
        component = IdeologicalComponent(class_consciousness=1.0)
        assert component.class_consciousness == 1.0

    def test_creation_false_consciousness_boundary(self) -> None:
        """Can create IdeologicalComponent at false consciousness boundary (class_consciousness=0.0)."""
        component = IdeologicalComponent(class_consciousness=0.0)
        assert component.class_consciousness == 0.0

    def test_creation_internationalist_boundary(self) -> None:
        """Can create IdeologicalComponent at internationalist boundary (national_identity=0.0)."""
        component = IdeologicalComponent(national_identity=0.0)
        assert component.national_identity == 0.0

    def test_creation_fascist_boundary(self) -> None:
        """Can create IdeologicalComponent at fascist boundary (national_identity=1.0)."""
        component = IdeologicalComponent(national_identity=1.0)
        assert component.national_identity == 1.0

    def test_creation_with_agitation_zero(self) -> None:
        """Can create IdeologicalComponent with zero agitation (no crisis energy)."""
        component = IdeologicalComponent(agitation=0.0)
        assert component.agitation == 0.0

    def test_creation_with_high_agitation(self) -> None:
        """Can create IdeologicalComponent with high agitation (crisis conditions).

        Agitation has NO upper bound - it accumulates during wage crises.
        """
        component = IdeologicalComponent(agitation=100.0)
        assert component.agitation == 100.0

    def test_creation_full_revolutionary_internationalist(self) -> None:
        """Can create fully revolutionary internationalist profile."""
        component = IdeologicalComponent(
            class_consciousness=1.0,
            national_identity=0.0,
            agitation=5.0,
        )
        assert component.class_consciousness == 1.0
        assert component.national_identity == 0.0
        assert component.agitation == 5.0

    def test_creation_false_consciousness_fascist(self) -> None:
        """Can create false consciousness fascist profile."""
        component = IdeologicalComponent(
            class_consciousness=0.0,
            national_identity=1.0,
            agitation=3.0,
        )
        assert component.class_consciousness == 0.0
        assert component.national_identity == 1.0
        assert component.agitation == 3.0


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestIdeologicalComponentValidation:
    """Test field constraints and validation rules."""

    def test_rejects_negative_class_consciousness(self) -> None:
        """class_consciousness cannot be negative."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(class_consciousness=-0.1)

    def test_rejects_class_consciousness_above_one(self) -> None:
        """class_consciousness cannot exceed 1.0."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(class_consciousness=1.1)

    def test_rejects_negative_national_identity(self) -> None:
        """national_identity cannot be negative."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(national_identity=-0.1)

    def test_rejects_national_identity_above_one(self) -> None:
        """national_identity cannot exceed 1.0."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(national_identity=1.1)

    def test_rejects_negative_agitation(self) -> None:
        """agitation cannot be negative."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(agitation=-0.1)

    def test_accepts_agitation_above_one(self) -> None:
        """agitation CAN exceed 1.0 - it has no upper bound."""
        component = IdeologicalComponent(agitation=5.0)
        assert component.agitation == 5.0

    def test_accepts_very_high_agitation(self) -> None:
        """agitation can be arbitrarily large (accumulated crisis energy)."""
        component = IdeologicalComponent(agitation=1000.0)
        assert component.agitation == 1000.0

    def test_accepts_neutral_values(self) -> None:
        """Neutral/moderate values for all fields are valid."""
        component = IdeologicalComponent(
            class_consciousness=0.5,
            national_identity=0.5,
            agitation=0.5,
        )
        assert component.class_consciousness == 0.5
        assert component.national_identity == 0.5
        assert component.agitation == 0.5


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.math
class TestIdeologicalComponentImmutability:
    """Test that IdeologicalComponent is frozen/immutable."""

    def test_cannot_mutate_class_consciousness(self) -> None:
        """Cannot modify class_consciousness after creation."""
        component = IdeologicalComponent(class_consciousness=0.5)
        with pytest.raises(ValidationError):
            component.class_consciousness = 0.9  # type: ignore[misc]

    def test_cannot_mutate_national_identity(self) -> None:
        """Cannot modify national_identity after creation."""
        component = IdeologicalComponent(national_identity=0.5)
        with pytest.raises(ValidationError):
            component.national_identity = 0.9  # type: ignore[misc]

    def test_cannot_mutate_agitation(self) -> None:
        """Cannot modify agitation after creation."""
        component = IdeologicalComponent(agitation=1.0)
        with pytest.raises(ValidationError):
            component.agitation = 5.0  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestIdeologicalComponentSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """IdeologicalComponent serializes to valid JSON."""
        component = IdeologicalComponent(
            class_consciousness=0.8,
            national_identity=0.3,
            agitation=2.5,
        )
        json_str = component.model_dump_json()
        assert "0.8" in json_str
        assert "0.3" in json_str
        assert "2.5" in json_str

    def test_deserialize_from_json(self) -> None:
        """IdeologicalComponent can be restored from JSON."""
        json_str = '{"class_consciousness": 0.8, "national_identity": 0.3, "agitation": 2.5}'
        component = IdeologicalComponent.model_validate_json(json_str)
        assert component.class_consciousness == 0.8
        assert component.national_identity == 0.3
        assert component.agitation == 2.5

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        original = IdeologicalComponent(
            class_consciousness=0.42,
            national_identity=0.67,
            agitation=3.14,
        )
        json_str = original.model_dump_json()
        restored = IdeologicalComponent.model_validate_json(json_str)

        assert restored.class_consciousness == pytest.approx(original.class_consciousness)
        assert restored.national_identity == pytest.approx(original.national_identity)
        assert restored.agitation == pytest.approx(original.agitation)

    def test_dict_conversion(self) -> None:
        """IdeologicalComponent converts to dict for database storage."""
        component = IdeologicalComponent(
            class_consciousness=0.8,
            national_identity=0.3,
            agitation=2.5,
        )
        data = component.model_dump()

        assert data["class_consciousness"] == 0.8
        assert data["national_identity"] == 0.3
        assert data["agitation"] == 2.5


# =============================================================================
# PROTOCOL COMPLIANCE TESTS
# =============================================================================


@pytest.mark.math
class TestIdeologicalComponentProtocol:
    """Test that IdeologicalComponent implements Component protocol."""

    def test_implements_component_protocol(self) -> None:
        """IdeologicalComponent is a valid Component."""
        component = IdeologicalComponent()
        assert isinstance(component, Component)

    def test_component_type_is_ideological(self) -> None:
        """component_type returns 'ideological'."""
        component = IdeologicalComponent()
        assert component.component_type == "ideological"

    def test_component_type_is_string(self) -> None:
        """component_type returns a string."""
        component = IdeologicalComponent()
        assert isinstance(component.component_type, str)


# =============================================================================
# FIELD DESCRIPTION TESTS
# =============================================================================


@pytest.mark.math
class TestIdeologicalComponentFieldDescriptions:
    """Test that all fields have descriptions."""

    def test_class_consciousness_has_description(self) -> None:
        """class_consciousness field has a description."""
        field_info = IdeologicalComponent.model_fields["class_consciousness"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_national_identity_has_description(self) -> None:
        """national_identity field has a description."""
        field_info = IdeologicalComponent.model_fields["national_identity"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_agitation_has_description(self) -> None:
        """agitation field has a description."""
        field_info = IdeologicalComponent.model_fields["agitation"]
        assert field_info.description is not None
        assert len(field_info.description) > 0
