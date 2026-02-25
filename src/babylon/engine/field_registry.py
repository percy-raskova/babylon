"""Field registry for extensible contradiction fields.

Dialectical Field Topology (Feature 002): The field registry provides a
mapping from field names to computation + normalization callables. Core
computation logic (gradient, Laplacian, derivatives, principal contradiction)
iterates over registered field names without hardcoding any.

Reference: FR-001 (extensible field set, field-name-agnostic core computation)
Reference: R-003 (contradiction field storage architecture)
Reference: R-007 (domain-specific normalization)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class FieldRegistryProtocol(Protocol):
    """Protocol for the open field registry.

    The registry maps field names to computation + normalization callables.
    Core computation logic MUST be field-name-agnostic.
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


# ─────────────────────────────────────────────────────────────────────
# Default field computation callables
# ─────────────────────────────────────────────────────────────────────


def compute_exploitation(node_attributes: dict[str, Any]) -> float:
    """Compute exploitation field from wealth deficit relative to subsistence.

    When wealth < subsistence, the worker is being exploited: the surplus
    value they produce exceeds what they receive. The ratio (subsistence - wealth)
    / subsistence captures this deficit as a fraction.

    Args:
        node_attributes: Node attributes dict with wealth, s_bio, s_class.

    Returns:
        Raw exploitation value >= 0.0. Higher means more exploited.
    """
    wealth = float(node_attributes.get("wealth", 0.0))
    subsistence = float(node_attributes.get("s_bio", 0.01)) + float(
        node_attributes.get("s_class", 0.0)
    )
    if wealth <= 0:
        return 5.0  # Maximum exploitation when destitute
    denominator = max(subsistence, 0.01)
    return max(0.0, (denominator - wealth) / denominator)


def compute_immiseration(node_attributes: dict[str, Any]) -> float:
    """Compute immiseration field from wealth decline rate.

    Immiseration captures the rate at which material conditions are
    worsening. Requires _previous_wealth injected from persistent_data.

    Args:
        node_attributes: Node attributes dict with wealth, _previous_wealth.

    Returns:
        Raw immiseration value >= 0.0. Higher means faster decline.
    """
    wealth = float(node_attributes.get("wealth", 0.0))
    prev_wealth = float(node_attributes.get("_previous_wealth", wealth))
    if prev_wealth <= 0:
        return 0.0
    decline = max(0.0, prev_wealth - wealth) / prev_wealth
    return decline


def compute_imperial_rent(node_attributes: dict[str, Any]) -> float:
    """Compute imperial rent field from unearned increment.

    The unearned_increment attribute represents the PPP bonus that forms
    the material basis of labor aristocracy — wealth received not from
    own labor but from imperial extraction.

    Args:
        node_attributes: Node attributes dict with unearned_increment.

    Returns:
        Raw imperial rent value >= 0.0.
    """
    return max(0.0, float(node_attributes.get("unearned_increment", 0.0)))


def compute_displacement(node_attributes: dict[str, Any]) -> float:
    """Compute displacement field from population change rate.

    Displacement captures forced population movement — evictions,
    gentrification, carceral removal. Requires _previous_population
    injected from persistent_data.

    Args:
        node_attributes: Node attributes dict with population, _previous_population.

    Returns:
        Raw displacement value. Positive = population loss (displacement).
    """
    pop = float(node_attributes.get("population", 1))
    prev_pop = float(node_attributes.get("_previous_population", pop))
    if prev_pop <= 0:
        return 0.0
    # Positive when population declines (displacement outward)
    return max(0.0, (prev_pop - pop) / prev_pop)


# ─────────────────────────────────────────────────────────────────────
# Default normalization callables
# ─────────────────────────────────────────────────────────────────────


def _normalize_linear_10(raw_value: float) -> float:
    """Normalize raw value to [0.0, 10.0] via linear scaling.

    Maps raw values in [0.0, 1.0] to [0.0, 10.0].
    Values outside this range are clamped.
    """
    return max(0.0, min(10.0, raw_value * 10.0))


def _normalize_imperial_rent(raw_value: float) -> float:
    """Normalize imperial rent to [0.0, 10.0].

    Uses log-like scaling: raw values can range widely, so we
    use a saturating function. For typical ranges (0-50), maps
    to reasonable field values.
    """
    if raw_value <= 0.0:
        return 0.0
    # Saturating: 10 * (1 - e^(-raw/10))
    import math

    return max(0.0, min(10.0, 10.0 * (1.0 - math.exp(-raw_value / 10.0))))


# ─────────────────────────────────────────────────────────────────────
# Concrete Implementation
# ─────────────────────────────────────────────────────────────────────


class DefaultFieldRegistry:
    """Concrete implementation of FieldRegistryProtocol.

    Maintains an ordered mapping of field names to (computation, normalization)
    callables. Registration order is preserved for deterministic iteration.
    """

    def __init__(self) -> None:
        self._fields: dict[
            str,
            tuple[Callable[[dict[str, Any]], float], Callable[[float], float]],
        ] = {}
        self._order: list[str] = []

    def register(
        self,
        name: str,
        computation: Callable[[dict[str, Any]], float],
        normalization: Callable[[float], float],
    ) -> None:
        """Register a new contradiction field.

        Args:
            name: Field identifier.
            computation: Callable that extracts raw value from node attributes.
            normalization: Callable that maps raw value to [0.0, 10.0].

        Raises:
            ValueError: If name is already registered.
        """
        if name in self._fields:
            msg = f"Field '{name}' is already registered"
            raise ValueError(msg)
        self._fields[name] = (computation, normalization)
        self._order.append(name)

    def get_field_names(self) -> list[str]:
        """Return all registered field names in registration order."""
        return list(self._order)

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
        if name not in self._fields:
            msg = f"Field '{name}' is not registered"
            raise KeyError(msg)
        computation, _normalization = self._fields[name]
        return computation(node_attributes)

    def normalize(self, name: str, raw_value: float) -> float:
        """Normalize a raw field value.

        Args:
            name: Registered field name.
            raw_value: Raw value to normalize.

        Returns:
            Normalized value in [0.0, 10.0].

        Raises:
            KeyError: If name is not registered.
        """
        if name not in self._fields:
            msg = f"Field '{name}' is not registered"
            raise KeyError(msg)
        _computation, normalization = self._fields[name]
        return normalization(raw_value)

    @classmethod
    def with_defaults(cls) -> DefaultFieldRegistry:
        """Factory that creates a registry with the four default fields.

        Default fields:
            - exploitation: Wealth deficit relative to subsistence
            - immiseration: Wealth decline rate
            - imperial_rent: Unearned increment (PPP bonus)
            - displacement: Population change rate

        Returns:
            DefaultFieldRegistry with four fields registered.
        """
        registry = cls()
        registry.register("exploitation", compute_exploitation, _normalize_linear_10)
        registry.register("immiseration", compute_immiseration, _normalize_linear_10)
        registry.register("imperial_rent", compute_imperial_rent, _normalize_imperial_rent)
        registry.register("displacement", compute_displacement, _normalize_linear_10)
        return registry
