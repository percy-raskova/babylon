"""SublationRule — composable Aufhebung lifecycle abstraction.

Sublation (Aufhebung) is the fundamental mechanism through which
contradictions resolve into higher-order forms. In the Babylon engine,
this manifests as:

1. A **threshold predicate** — when has the dialectic's internal
   contradiction intensified enough to produce a qualitative leap?
2. A **successor factory** — what higher-order dialectic emerges?
3. A **governance relationship** — how does the successor govern
   the sublated dialectic's continued evolution?

Previously, each dialectic implemented its own ad-hoc ``sublate()``
override with duplicated boilerplate (threshold check, EmptyPole
construction, parent_id wiring). ``SublationRule`` extracts this
into a composable, declarative, testable structure.

Usage::

    from babylon.engine.dialectics.sublation import SublationRule

    rule = SublationRule(
        name="realization_crisis",
        threshold=lambda d: d.pole_a.commodity_overhang > THRESHOLD,
        successor_type="RealizationCrisisDialectic",
        successor_factory=lambda d: RealizationCrisisDialectic(
            pole_a=EmptyPole(), pole_b=EmptyPole(),
            weight=0.0, parent_id=d.id,
            tick_created=d.tick_updated, tick_updated=d.tick_updated,
        ),
    )

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: Base class with sublate().
    :mod:`babylon.engine.dialectics.tick`: tick() handles sublation events.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import Dialectic


class SublationRule(BaseModel):
    """A composable sublation specification.

    Encapsulates the three components of the Aufhebung lifecycle:

    1. ``threshold`` — predicate on the dialectic: when to sublate.
    2. ``successor_factory`` — callable producing the successor.
    3. ``name`` — human-readable identifier for debugging/events.

    The rule does NOT own the governance relationship; that is left
    to the sublated dialectic's ``step()`` method, which can use
    ``world.find_successor()`` to locate and read its governor.

    Attributes:
        name: Human-readable name for this sublation rule.
        threshold: Callable that takes a Dialectic and returns True
            when the sublation condition is met.
        successor_type: The type_tag of the successor dialectic.
        successor_factory: Callable that takes the predecessor
            dialectic and returns the successor instance.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str = Field(..., description="Human-readable rule name.")
    threshold: Callable[[Any], bool] = Field(..., description="Predicate: when to sublate.")
    successor_type: str = Field(..., description="type_tag of the successor dialectic.")
    successor_factory: Callable[[Any], Dialectic[Any, Any]] = Field(
        ..., description="Factory producing the successor from the predecessor."
    )

    def threshold_met(self, dialectic: Dialectic[Any, Any]) -> bool:
        """Evaluate the sublation threshold.

        Args:
            dialectic: The dialectic to test.

        Returns:
            True if the threshold condition is satisfied.
        """
        return self.threshold(dialectic)

    def create_successor(self, dialectic: Dialectic[Any, Any]) -> Dialectic[Any, Any]:
        """Create the successor dialectic.

        The successor is produced with ``parent_id`` wired to the
        predecessor's ``id``, establishing the containment relationship
        that ``WorldView.find_successor()`` can later resolve.

        Args:
            dialectic: The predecessor dialectic being sublated.

        Returns:
            A new Dialectic instance — the successor.
        """
        return self.successor_factory(dialectic)


__all__ = [
    "SublationRule",
]
