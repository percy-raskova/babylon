"""Invariant protocol and concrete invariants for the simulation engine.

Spec 040, Discipline 1: Invariants as First-Class Objects.

Every invariant in the constitution becomes an object implementing the
``Invariant`` protocol. Systems declare which invariants they preserve,
and the test harness checks them automatically via Hypothesis.

Usage::

    from babylon.engine.invariants import NonNegativeWealth, Invariant

    class VolumeOneProduction:
        invariants: ClassVar[list[Invariant]] = [NonNegativeWealth()]

        def step(self, state: WorldState) -> Result[WorldState, TransitionError]:
            ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from babylon.models.world_state import WorldState


@dataclass(frozen=True)
class InvariantResult:
    """Outcome of an invariant check.

    Use factory methods ``InvariantResult.ok()`` and ``InvariantResult.violated(msg)``
    rather than constructing directly.

    Attributes:
        passed: True if the invariant holds, False if violated.
        msg: Descriptive message (empty on success, diagnosis on failure).
    """

    passed: bool
    msg: str = ""

    @property
    def ok(self) -> bool:
        """Whether the invariant check passed."""
        return self.passed

    @classmethod
    def success(cls) -> InvariantResult:
        """Create a passing result.

        Returns:
            InvariantResult with passed=True.
        """
        return cls(passed=True, msg="")

    @classmethod
    def violated(cls, msg: str) -> InvariantResult:
        """Create a failing result with a diagnosis message.

        Args:
            msg: Description of the invariant violation.

        Returns:
            InvariantResult with passed=False.
        """
        return cls(passed=False, msg=msg)


@runtime_checkable
class Invariant(Protocol):
    """Protocol for simulation invariants.

    Every constitution invariant becomes an object implementing this protocol.
    Systems declare which invariants they preserve via a class-level list.
    The test harness runs declared invariants on (pre, post) state pairs.
    """

    @property
    def name(self) -> str:
        """Unique identifier for this invariant."""
        ...

    def check(self, pre: WorldState, post: WorldState) -> InvariantResult:
        """Verify the invariant holds between pre and post states.

        Args:
            pre: WorldState before system step.
            post: WorldState after system step.

        Returns:
            InvariantResult indicating pass or violation.
        """
        ...


class NonNegativeWealth:
    """No entity has negative wealth after a system step.

    This invariant checks all social_class entities in the post-state
    and fails if any have wealth < 0.
    """

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "non_negative_wealth"

    def check(self, _pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that no entity wealth is negative.

        Args:
            _pre: WorldState before step (unused for this invariant).
            post: WorldState after step.

        Returns:
            InvariantResult — violated if any entity has wealth < 0.
        """
        for entity_id, entity in post.entities.items():
            if entity.wealth < 0:
                return InvariantResult.violated(
                    f"Entity {entity_id} has negative wealth: {entity.wealth:.6f}"
                )
        return InvariantResult.success()


class HeatNonNegativity:
    """Territory heat fields must be >= 0 everywhere.

    Heat represents state repressive attention. Negative heat
    is physically meaningless.
    """

    @property
    def name(self) -> str:
        """Invariant identifier."""
        return "heat_non_negativity"

    def check(self, _pre: WorldState, post: WorldState) -> InvariantResult:
        """Check that no territory has negative heat.

        Args:
            _pre: WorldState before step (unused for this invariant).
            post: WorldState after step.

        Returns:
            InvariantResult — violated if any territory has heat < 0.
        """
        for territory_id, territory in post.territories.items():
            if territory.heat < 0:
                return InvariantResult.violated(
                    f"Territory {territory_id} has negative heat: {territory.heat:.6f}"
                )
        return InvariantResult.success()
