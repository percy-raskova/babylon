"""RED phase: Tests for @derived decorator and derivation registry.

Spec 040 Discipline 2: Derived values are never stored.
The @derived decorator marks a function as a derivation — a computation
that produces a value from primitives. The registry tracks all derivations
for documentation and enforcement.
"""

from __future__ import annotations

# These imports will fail until the module exists
from babylon.derivations.decorator import derived
from babylon.derivations.registry import DerivedRegistry
from babylon.models.world_state import WorldState


class TestDerivedDecorator:
    """Verify @derived marks functions as derivations."""

    def test_derived_decorator_marks_function(self) -> None:
        """@derived sets _is_derived and _derives_name on the function."""

        @derived(name="test_metric")
        def compute_test(state: WorldState) -> float:
            return 0.0

        assert getattr(compute_test, "_is_derived", False) is True
        assert getattr(compute_test, "_derives_name", None) == "test_metric"

    def test_derived_function_is_callable(self) -> None:
        """Decorated function remains callable with correct result."""
        state = WorldState(tick=0)

        @derived(name="tick_squared")
        def compute_tick_squared(state: WorldState) -> int:
            return state.tick**2

        assert compute_tick_squared(state) == 0

    def test_derived_decorator_registers_in_registry(self) -> None:
        """@derived auto-registers in the global DerivedRegistry."""
        registry = DerivedRegistry()

        @derived(name="registered_metric", registry=registry)
        def compute_registered(state: WorldState) -> float:
            return 42.0

        assert "registered_metric" in registry
        assert registry["registered_metric"] is compute_registered


class TestDerivedRegistry:
    """Verify DerivedRegistry tracks all derivations."""

    def test_registry_is_iterable(self) -> None:
        """Registry supports iteration over registered derivations."""
        registry = DerivedRegistry()

        @derived(name="a", registry=registry)
        def compute_a(state: WorldState) -> float:
            return 1.0

        @derived(name="b", registry=registry)
        def compute_b(state: WorldState) -> float:
            return 2.0

        names = list(registry)
        assert "a" in names
        assert "b" in names

    def test_registry_rejects_duplicate_names(self) -> None:
        """Registry raises on duplicate derivation names."""
        import pytest

        registry = DerivedRegistry()

        @derived(name="unique", registry=registry)
        def compute_first(state: WorldState) -> float:
            return 1.0

        with pytest.raises(ValueError, match="already registered"):

            @derived(name="unique", registry=registry)
            def compute_second(state: WorldState) -> float:
                return 2.0
