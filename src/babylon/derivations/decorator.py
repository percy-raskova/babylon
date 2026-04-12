"""@derived decorator for marking derivation functions.

Spec 040 Discipline 2: Derived values are never stored.
The @derived decorator marks a function as a derivation and optionally
registers it in a DerivedRegistry.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from babylon.derivations.registry import DerivedRegistry

F = TypeVar("F", bound=Callable[..., Any])


def derived(
    name: str,
    registry: DerivedRegistry | None = None,
) -> Callable[[F], F]:
    """Mark a function as a derived computation.

    Sets ``_is_derived = True`` and ``_derives_name = name`` on the
    decorated function. Optionally registers it in a DerivedRegistry.

    Args:
        name: Unique name for this derivation.
        registry: Optional registry to auto-register in.

    Returns:
        Decorator that marks and optionally registers the function.

    Example::

        @derived(name="total_wealth")
        def compute_total_wealth(state):
            return sum(e.wealth for e in state.entities.values())

        assert compute_total_wealth._is_derived is True
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        wrapper._is_derived = True  # type: ignore[attr-defined]
        wrapper._derives_name = name  # type: ignore[attr-defined]

        if registry is not None:
            registry.register(name, wrapper)

        return wrapper  # type: ignore[return-value]

    return decorator
