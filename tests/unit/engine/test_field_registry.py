"""Tests for the FieldRegistry (Feature 002 - Dialectical Field Topology).

TDD RED phase: These tests define the contract for FieldRegistryProtocol
and DefaultFieldRegistry.

Reference: specs/002-dialectical-field-topology/contracts/field_registry.py
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.field_registry import DefaultFieldRegistry

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _identity_computation(node_attributes: dict[str, Any]) -> float:
    """Return wealth directly as raw field value."""
    return float(node_attributes.get("wealth", 0.0))


def _linear_normalization(raw_value: float) -> float:
    """Simple linear normalization to [0.0, 10.0]."""
    return max(0.0, min(10.0, raw_value))


def _squared_computation(node_attributes: dict[str, Any]) -> float:
    """Return squared wealth as raw field value."""
    w = float(node_attributes.get("wealth", 0.0))
    return w * w


# ─────────────────────────────────────────────────────────────────────
# TEST: DefaultFieldRegistry - Registration
# ─────────────────────────────────────────────────────────────────────


class TestFieldRegistryRegistration:
    """Registration behavior for DefaultFieldRegistry."""

    def test_register_single_field(self) -> None:
        """Registering a single field adds it to the registry."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        assert registry.get_field_names() == ["exploitation"]

    def test_register_multiple_fields_preserves_order(self) -> None:
        """Fields are returned in registration order."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        registry.register("immiseration", _squared_computation, _linear_normalization)
        registry.register("imperial_rent", _identity_computation, _linear_normalization)
        assert registry.get_field_names() == [
            "exploitation",
            "immiseration",
            "imperial_rent",
        ]

    def test_register_duplicate_name_raises(self) -> None:
        """Registering the same name twice raises ValueError."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("exploitation", _squared_computation, _linear_normalization)

    def test_empty_registry_has_no_fields(self) -> None:
        """Empty registry returns empty list."""
        registry = DefaultFieldRegistry()
        assert registry.get_field_names() == []


# ─────────────────────────────────────────────────────────────────────
# TEST: DefaultFieldRegistry - Computation
# ─────────────────────────────────────────────────────────────────────


class TestFieldRegistryComputation:
    """Computation behavior for DefaultFieldRegistry."""

    def test_compute_returns_raw_value(self) -> None:
        """Compute calls the registered computation callable."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        result = registry.compute("exploitation", {"wealth": 7.5})
        assert result == 7.5

    def test_compute_unregistered_field_raises(self) -> None:
        """Computing an unregistered field raises KeyError."""
        registry = DefaultFieldRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.compute("nonexistent", {"wealth": 1.0})

    def test_compute_with_missing_attributes_returns_default(self) -> None:
        """Computation handles missing attributes via .get() defaults."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        result = registry.compute("exploitation", {})
        assert result == 0.0


# ─────────────────────────────────────────────────────────────────────
# TEST: DefaultFieldRegistry - Normalization
# ─────────────────────────────────────────────────────────────────────


class TestFieldRegistryNormalization:
    """Normalization behavior for DefaultFieldRegistry."""

    def test_normalize_within_bounds(self) -> None:
        """Normalize maps value within [0.0, 10.0]."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        assert registry.normalize("exploitation", 5.0) == 5.0

    def test_normalize_clamps_high(self) -> None:
        """Normalize clamps values above 10.0."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        assert registry.normalize("exploitation", 15.0) == 10.0

    def test_normalize_clamps_low(self) -> None:
        """Normalize clamps values below 0.0."""
        registry = DefaultFieldRegistry()
        registry.register("exploitation", _identity_computation, _linear_normalization)
        assert registry.normalize("exploitation", -3.0) == 0.0

    def test_normalize_unregistered_field_raises(self) -> None:
        """Normalizing an unregistered field raises KeyError."""
        registry = DefaultFieldRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.normalize("nonexistent", 5.0)


# ─────────────────────────────────────────────────────────────────────
# TEST: DefaultFieldRegistry - Default Fields
# ─────────────────────────────────────────────────────────────────────


class TestFieldRegistryDefaults:
    """Default field registration via with_defaults() factory."""

    def test_with_defaults_registers_four_fields(self) -> None:
        """Factory registers exploitation, immiseration, imperial_rent, displacement."""
        registry = DefaultFieldRegistry.with_defaults()
        names = registry.get_field_names()
        assert "exploitation" in names
        assert "immiseration" in names
        assert "imperial_rent" in names
        assert "displacement" in names
        assert len(names) == 4

    def test_default_exploitation_computation(self) -> None:
        """Exploitation field computes from wealth and subsistence."""
        registry = DefaultFieldRegistry.with_defaults()
        # Destitute worker: wealth = 0 → high exploitation
        raw = registry.compute("exploitation", {"wealth": 0.0, "s_bio": 5.0})
        assert raw > 0.0

    def test_default_exploitation_normalization_in_bounds(self) -> None:
        """Exploitation normalization output is in [0.0, 10.0]."""
        registry = DefaultFieldRegistry.with_defaults()
        raw = registry.compute("exploitation", {"wealth": 0.0, "s_bio": 5.0})
        normalized = registry.normalize("exploitation", raw)
        assert 0.0 <= normalized <= 10.0

    def test_default_immiseration_no_change(self) -> None:
        """Immiseration is 0 when wealth hasn't declined."""
        registry = DefaultFieldRegistry.with_defaults()
        raw = registry.compute("immiseration", {"wealth": 10.0, "_previous_wealth": 10.0})
        assert raw == 0.0

    def test_default_immiseration_wealth_decline(self) -> None:
        """Immiseration is positive when wealth declines."""
        registry = DefaultFieldRegistry.with_defaults()
        raw = registry.compute("immiseration", {"wealth": 5.0, "_previous_wealth": 10.0})
        assert raw > 0.0

    def test_default_imperial_rent_from_unearned(self) -> None:
        """Imperial rent field reads from unearned_increment."""
        registry = DefaultFieldRegistry.with_defaults()
        raw = registry.compute("imperial_rent", {"unearned_increment": 3.5})
        assert raw == 3.5

    def test_default_displacement_no_change(self) -> None:
        """Displacement is 0 when population hasn't changed."""
        registry = DefaultFieldRegistry.with_defaults()
        raw = registry.compute(
            "displacement",
            {"population": 1000, "_previous_population": 1000},
        )
        assert raw == 0.0

    def test_default_displacement_population_loss(self) -> None:
        """Displacement is positive when population declines."""
        registry = DefaultFieldRegistry.with_defaults()
        raw = registry.compute(
            "displacement",
            {"population": 800, "_previous_population": 1000},
        )
        assert raw > 0.0
