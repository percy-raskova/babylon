"""Tests for IdeologicalComponent.

TDD Red Phase: These tests define the contract for IdeologicalComponent.
IdeologicalComponent represents the political alignment and adherence of an entity:
- alignment: Position on revolutionary-reactionary spectrum [-1, 1] (Ideology, default 0.0)
- adherence: Strength of ideological commitment [0, 1] (Probability, default 0.5)

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
        assert component.alignment == 0.0
        assert component.adherence == 0.5

    def test_creation_with_custom_alignment(self) -> None:
        """Can create IdeologicalComponent with custom alignment."""
        component = IdeologicalComponent(alignment=-0.7)
        assert component.alignment == -0.7
        assert component.adherence == 0.5

    def test_creation_with_custom_adherence(self) -> None:
        """Can create IdeologicalComponent with custom adherence."""
        component = IdeologicalComponent(adherence=0.9)
        assert component.alignment == 0.0
        assert component.adherence == 0.9

    def test_creation_with_all_custom_values(self) -> None:
        """Can create IdeologicalComponent with all custom values."""
        component = IdeologicalComponent(
            alignment=0.5,
            adherence=0.8,
        )
        assert component.alignment == 0.5
        assert component.adherence == 0.8

    def test_creation_revolutionary_boundary(self) -> None:
        """Can create IdeologicalComponent at revolutionary boundary."""
        component = IdeologicalComponent(alignment=-1.0)
        assert component.alignment == -1.0

    def test_creation_reactionary_boundary(self) -> None:
        """Can create IdeologicalComponent at reactionary boundary."""
        component = IdeologicalComponent(alignment=1.0)
        assert component.alignment == 1.0

    def test_creation_with_adherence_boundaries(self) -> None:
        """Can create IdeologicalComponent with adherence at boundaries."""
        # Minimum adherence
        component_min = IdeologicalComponent(adherence=0.0)
        assert component_min.adherence == 0.0

        # Maximum adherence
        component_max = IdeologicalComponent(adherence=1.0)
        assert component_max.adherence == 1.0

    def test_creation_full_revolutionary_committed(self) -> None:
        """Can create fully revolutionary with full commitment."""
        component = IdeologicalComponent(alignment=-1.0, adherence=1.0)
        assert component.alignment == -1.0
        assert component.adherence == 1.0

    def test_creation_full_reactionary_committed(self) -> None:
        """Can create fully reactionary with full commitment."""
        component = IdeologicalComponent(alignment=1.0, adherence=1.0)
        assert component.alignment == 1.0
        assert component.adherence == 1.0


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.math
class TestIdeologicalComponentValidation:
    """Test field constraints and validation rules."""

    def test_rejects_alignment_below_negative_one(self) -> None:
        """Alignment cannot be less than -1.0 (Ideology constraint)."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(alignment=-1.1)

    def test_rejects_alignment_above_one(self) -> None:
        """Alignment cannot exceed 1.0 (Ideology constraint)."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(alignment=1.1)

    def test_rejects_negative_adherence(self) -> None:
        """Adherence cannot be negative (Probability constraint)."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(adherence=-0.1)

    def test_rejects_adherence_greater_than_one(self) -> None:
        """Adherence cannot exceed 1.0 (Probability constraint)."""
        with pytest.raises(ValidationError):
            IdeologicalComponent(adherence=1.1)

    def test_accepts_neutral_alignment(self) -> None:
        """Neutral alignment (0.0) is valid."""
        component = IdeologicalComponent(alignment=0.0)
        assert component.alignment == 0.0

    def test_accepts_moderate_values(self) -> None:
        """Moderate values for both fields are valid."""
        component = IdeologicalComponent(alignment=-0.3, adherence=0.6)
        assert component.alignment == -0.3
        assert component.adherence == 0.6


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.math
class TestIdeologicalComponentImmutability:
    """Test that IdeologicalComponent is frozen/immutable."""

    def test_cannot_mutate_alignment(self) -> None:
        """Cannot modify alignment after creation."""
        component = IdeologicalComponent(alignment=-0.5)
        with pytest.raises(ValidationError):
            component.alignment = 0.5  # type: ignore[misc]

    def test_cannot_mutate_adherence(self) -> None:
        """Cannot modify adherence after creation."""
        component = IdeologicalComponent(adherence=0.5)
        with pytest.raises(ValidationError):
            component.adherence = 0.9  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestIdeologicalComponentSerialization:
    """Test JSON serialization for Ledger (SQLite) storage."""

    def test_serialize_to_json(self) -> None:
        """IdeologicalComponent serializes to valid JSON."""
        component = IdeologicalComponent(
            alignment=-0.5,
            adherence=0.7,
        )
        json_str = component.model_dump_json()
        assert "-0.5" in json_str
        assert "0.7" in json_str

    def test_deserialize_from_json(self) -> None:
        """IdeologicalComponent can be restored from JSON."""
        json_str = '{"alignment": -0.5, "adherence": 0.7}'
        component = IdeologicalComponent.model_validate_json(json_str)
        assert component.alignment == -0.5
        assert component.adherence == 0.7

    def test_round_trip_preserves_values(self) -> None:
        """JSON round-trip preserves all field values."""
        original = IdeologicalComponent(
            alignment=0.42,
            adherence=0.67,
        )
        json_str = original.model_dump_json()
        restored = IdeologicalComponent.model_validate_json(json_str)

        assert restored.alignment == pytest.approx(original.alignment)
        assert restored.adherence == pytest.approx(original.adherence)

    def test_dict_conversion(self) -> None:
        """IdeologicalComponent converts to dict for database storage."""
        component = IdeologicalComponent(
            alignment=-0.5,
            adherence=0.7,
        )
        data = component.model_dump()

        assert data["alignment"] == -0.5
        assert data["adherence"] == 0.7


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

    def test_alignment_has_description(self) -> None:
        """alignment field has a description."""
        field_info = IdeologicalComponent.model_fields["alignment"]
        assert field_info.description is not None
        assert len(field_info.description) > 0

    def test_adherence_has_description(self) -> None:
        """adherence field has a description."""
        field_info = IdeologicalComponent.model_fields["adherence"]
        assert field_info.description is not None
        assert len(field_info.description) > 0
