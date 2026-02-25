"""Contract: Field Registry for extensible contradiction fields.

This is a design contract, not production code. It defines the interface
that the implementation must satisfy.

Reference: FR-001 (extensible field set, field-name-agnostic core computation)
Reference: R-003 (contradiction field storage architecture)
Reference: R-007 (domain-specific normalization)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FieldComputation(Protocol):
    """Protocol for a single field's computation function.

    Each registered field provides a callable that extracts
    a raw value from node attributes (economic calculator outputs).
    """

    def __call__(self, node_attributes: dict[str, Any]) -> float:
        """Compute raw field value from node economic attributes.

        Args:
            node_attributes: Dict of node attributes from GraphProtocol.

        Returns:
            Raw (pre-normalization) field value.
        """
        ...


@runtime_checkable
class FieldNormalization(Protocol):
    """Protocol for a single field's normalization function.

    Maps raw value to [0.0, 10.0] using domain-specific bounds.
    """

    def __call__(self, raw_value: float) -> float:
        """Normalize raw value to [0.0, 10.0].

        Args:
            raw_value: Pre-normalization value from FieldComputation.

        Returns:
            Normalized value clamped to [0.0, 10.0].
        """
        ...


class FieldRegistryProtocol(Protocol):
    """Protocol for the open field registry.

    The registry maps field names to computation + normalization callables.
    Core computation logic (gradient, Laplacian, derivatives, principal
    contradiction) MUST be field-name-agnostic — it iterates over
    registered field names without hardcoding any.

    Contract:
        - register() adds a new field without touching computation code
        - get_field_names() returns all registered field names
        - compute() returns raw value for a field at a node
        - normalize() returns normalized value for a field
    """

    def register(
        self,
        name: str,
        computation: Callable[[dict[str, Any]], float],
        normalization: Callable[[float], float],
    ) -> None:
        """Register a new contradiction field.

        Args:
            name: Field identifier (e.g., "exploitation", "immiseration").
            computation: Callable that extracts raw value from node attributes.
            normalization: Callable that maps raw value to [0.0, 10.0].

        Raises:
            ValueError: If name is already registered.
        """
        ...

    def get_field_names(self) -> list[str]:
        """Return all registered field names in registration order."""
        ...

    def compute(self, name: str, node_attributes: dict[str, Any]) -> float:
        """Compute raw field value for a named field.

        Args:
            name: Registered field name.
            node_attributes: Node attributes dict.

        Returns:
            Raw field value.

        Raises:
            KeyError: If name is not registered.
        """
        ...

    def normalize(self, name: str, raw_value: float) -> float:
        """Normalize a raw field value using the field's normalization function.

        Args:
            name: Registered field name.
            raw_value: Raw value to normalize.

        Returns:
            Normalized value in [0.0, 10.0].

        Raises:
            KeyError: If name is not registered.
        """
        ...
