"""Tests for Component protocol.

TDD Red Phase: These tests define the contract for Component protocol.
The Component protocol is the base interface that all component types must implement.

The Component protocol defines:
1. A runtime-checkable interface for type checking
2. The component_type property returning a string identifier
3. Compatibility with Pydantic BaseModel for serialization

All concrete components (Material, Vitality, Spatial, Ideological, Organization)
must implement this protocol.
"""

import pytest

# These imports should fail until the protocol is implemented
from babylon.models.components.base import Component

# =============================================================================
# PROTOCOL DEFINITION TESTS
# =============================================================================


@pytest.mark.math
class TestComponentProtocol:
    """Test that Component is a valid runtime-checkable Protocol."""

    def test_protocol_exists(self) -> None:
        """Component protocol can be imported."""
        assert Component is not None

    def test_protocol_is_runtime_checkable(self) -> None:
        """Component protocol supports isinstance() checks."""

        # Protocol should be decorated with @runtime_checkable
        assert hasattr(Component, "__protocol_attrs__") or hasattr(
            Component, "_is_runtime_protocol"
        )

    def test_protocol_defines_component_type(self) -> None:
        """Component protocol requires component_type property."""
        # Check that component_type is part of the protocol's interface
        # For runtime_checkable protocols, we check __protocol_attrs__
        assert "component_type" in dir(Component) or hasattr(Component, "component_type")


# =============================================================================
# PROTOCOL COMPLIANCE TESTS
# =============================================================================


@pytest.mark.math
class TestProtocolCompliance:
    """Test that classes can properly implement the Component protocol."""

    def test_compliant_class_passes_isinstance(self) -> None:
        """A class with component_type property passes isinstance check."""
        from pydantic import BaseModel, ConfigDict

        class ValidComponent(BaseModel):
            """A valid component implementation."""

            model_config = ConfigDict(frozen=True)

            @property
            def component_type(self) -> str:
                """Return the component type identifier."""
                return "valid"

        instance = ValidComponent()
        assert isinstance(instance, Component)

    def test_noncompliant_class_fails_isinstance(self) -> None:
        """A class without component_type fails isinstance check."""
        from pydantic import BaseModel, ConfigDict

        class InvalidComponent(BaseModel):
            """A component missing the required property."""

            model_config = ConfigDict(frozen=True)

        instance = InvalidComponent()
        assert not isinstance(instance, Component)

    def test_component_type_must_return_string(self) -> None:
        """component_type property must return a string."""
        from pydantic import BaseModel, ConfigDict

        class TypedComponent(BaseModel):
            """A component with typed component_type."""

            model_config = ConfigDict(frozen=True)

            @property
            def component_type(self) -> str:
                """Return the component type identifier."""
                return "typed"

        instance = TypedComponent()
        result = instance.component_type
        assert isinstance(result, str)
        assert result == "typed"


# =============================================================================
# INTEGRATION WITH PYDANTIC TESTS
# =============================================================================


@pytest.mark.math
class TestPydanticIntegration:
    """Test that Component protocol works with Pydantic models."""

    def test_component_can_be_frozen(self) -> None:
        """Component implementations can be immutable."""
        from pydantic import BaseModel, ConfigDict, ValidationError

        class FrozenComponent(BaseModel):
            """An immutable component."""

            model_config = ConfigDict(frozen=True)
            value: float = 0.0

            @property
            def component_type(self) -> str:
                """Return the component type identifier."""
                return "frozen"

        instance = FrozenComponent(value=1.0)
        with pytest.raises(ValidationError):
            instance.value = 2.0  # type: ignore[misc]

    def test_component_can_serialize_to_json(self) -> None:
        """Component implementations serialize to JSON."""
        from pydantic import BaseModel, ConfigDict

        class SerializableComponent(BaseModel):
            """A serializable component."""

            model_config = ConfigDict(frozen=True)
            value: float = 0.0

            @property
            def component_type(self) -> str:
                """Return the component type identifier."""
                return "serializable"

        instance = SerializableComponent(value=42.0)
        json_str = instance.model_dump_json()
        assert "42.0" in json_str or "42" in json_str

    def test_component_can_deserialize_from_json(self) -> None:
        """Component implementations deserialize from JSON."""
        from pydantic import BaseModel, ConfigDict

        class DeserializableComponent(BaseModel):
            """A deserializable component."""

            model_config = ConfigDict(frozen=True)
            value: float = 0.0

            @property
            def component_type(self) -> str:
                """Return the component type identifier."""
                return "deserializable"

        json_str = '{"value": 42.0}'
        instance = DeserializableComponent.model_validate_json(json_str)
        assert instance.value == 42.0

    def test_component_preserves_values_on_round_trip(self) -> None:
        """Component values survive JSON round-trip."""
        from pydantic import BaseModel, ConfigDict

        class RoundTripComponent(BaseModel):
            """A component for round-trip testing."""

            model_config = ConfigDict(frozen=True)
            wealth: float = 0.0
            probability: float = 0.5

            @property
            def component_type(self) -> str:
                """Return the component type identifier."""
                return "roundtrip"

        original = RoundTripComponent(wealth=100.0, probability=0.75)
        json_str = original.model_dump_json()
        restored = RoundTripComponent.model_validate_json(json_str)

        assert restored.wealth == pytest.approx(original.wealth)
        assert restored.probability == pytest.approx(original.probability)
