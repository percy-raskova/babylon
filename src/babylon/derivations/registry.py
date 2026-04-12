"""DerivedRegistry for tracking derivation functions.

Spec 040 Discipline 2: All derived computations are tracked in a
registry for documentation, enforcement, and introspection.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any


class DerivedRegistry:
    """Registry of derived computations.

    Tracks all functions decorated with @derived, ensuring uniqueness
    and providing iteration/lookup capabilities.

    Example::

        registry = DerivedRegistry()

        @derived(name="total_wealth", registry=registry)
        def compute_total_wealth(state):
            return sum(e.wealth for e in state.entities.values())

        assert "total_wealth" in registry
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._derivations: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        """Register a derivation function.

        Args:
            name: Unique derivation name.
            func: The derivation function.

        Raises:
            ValueError: If name is already registered.
        """
        if name in self._derivations:
            msg = f"Derivation '{name}' already registered"
            raise ValueError(msg)
        self._derivations[name] = func

    def __contains__(self, name: str) -> bool:
        """Check if a derivation is registered."""
        return name in self._derivations

    def __getitem__(self, name: str) -> Callable[..., Any]:
        """Get a derivation function by name."""
        return self._derivations[name]

    def __iter__(self) -> Iterator[str]:
        """Iterate over registered derivation names."""
        return iter(self._derivations)

    def __len__(self) -> int:
        """Number of registered derivations."""
        return len(self._derivations)
