"""Result type for total functions with explicit error channels.

Spec 040, Discipline 2: Systems return ``Result[WorldState, TransitionError]``.
Exceptions are reserved for programmer errors (shape mismatches, missing nodes).
Expected failures go through the ``Result`` channel.

Usage::

    from babylon.engine.result import Ok, Err, Result

    def step(state: WorldState) -> Result[WorldState, TransitionError]:
        if wealth < 0:
            return Err(NegativeCapitalStock(node_id="C001", field="wealth", value=wealth))
        return Ok(state.model_copy(update={"tick": state.tick + 1}))
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Ok[T]:  # noqa: UP046 — requires Python 3.12+ syntax
    """Success variant of Result.

    Holds the successful value from a system step.

    Args:
        value: The successful result value.
    """

    value: T

    def is_ok(self) -> bool:
        """Return True — this is a success variant."""
        return True

    def is_err(self) -> bool:
        """Return False — this is not an error variant."""
        return False

    def unwrap(self) -> T:
        """Return the contained value.

        Returns:
            The success value.
        """
        return self.value

    def map(self, fn: Callable[[T], U]) -> Ok[U]:
        """Apply fn to the contained value.

        Args:
            fn: Function to apply to the success value.

        Returns:
            New Ok with transformed value.
        """
        return Ok(fn(self.value))


@dataclass(frozen=True)
class Err[E]:  # noqa: UP046 — requires Python 3.12+ syntax
    """Error variant of Result.

    Holds a modeled failure from a system step.

    Args:
        error: The error describing what went wrong.
    """

    error: E

    def is_ok(self) -> bool:
        """Return False — this is not a success variant."""
        return False

    def is_err(self) -> bool:
        """Return True — this is an error variant."""
        return True

    def unwrap(self) -> None:
        """Raise ValueError — cannot unwrap an Err.

        Raises:
            ValueError: Always, with the error message.
        """
        raise ValueError(str(self.error))

    def map(self, _fn: Callable[..., object]) -> Err[E]:
        """Pass through — errors are not transformed by map.

        Args:
            _fn: Ignored function.

        Returns:
            Self unchanged.
        """
        return self


Result = Ok[T] | Err[E]
"""Type alias for the Result union.

A ``Result[T, E]`` is either ``Ok[T]`` (success) or ``Err[E]`` (modeled failure).
"""
