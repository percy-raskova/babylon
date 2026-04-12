"""Transition error types for the simulation engine.

Spec 040, Discipline 2: Closed union of known failure modes.

``TransitionError`` is a union of all modeled failure types that a system
step can produce. These represent expected domain failures — negative capital,
insufficient labor hours, missing organizations — not programmer errors.

Exceptions (``assert``, ``KeyError``) remain for "this should be unreachable."
``Result[WorldState, TransitionError]`` for "this is a modeled outcome."
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NegativeCapitalStock:
    """A node's capital stock went negative after a system step.

    Args:
        node_id: The entity that has negative capital.
        field: Which field went negative (e.g., ``"wealth"``).
        value: The negative value.
    """

    node_id: str
    field: str
    value: float

    def __str__(self) -> str:
        return f"NegativeCapitalStock({self.node_id}.{self.field}={self.value:.6f})"


@dataclass(frozen=True)
class InsufficientLaborHours:
    """A production plan requires more labor hours than available.

    Args:
        node_id: The entity that lacks labor hours.
        required: Hours needed for the production run.
        available: Hours actually available.
    """

    node_id: str
    required: float
    available: float

    def __str__(self) -> str:
        return (
            f"InsufficientLaborHours({self.node_id}: "
            f"required={self.required:.2f}, available={self.available:.2f})"
        )


@dataclass(frozen=True)
class MissingOrganization:
    """An action references an organization that does not exist in state.

    Args:
        org_id: The organization ID that was not found.
    """

    org_id: str

    def __str__(self) -> str:
        return f"MissingOrganization({self.org_id})"


@dataclass(frozen=True)
class InfeasibleMigration:
    """A migration between territories is not possible.

    Args:
        node_id: The entity attempting migration.
        from_territory: Source territory ID.
        to_territory: Target territory ID.
        reason: Why the migration is infeasible.
    """

    node_id: str
    from_territory: str
    to_territory: str
    reason: str

    def __str__(self) -> str:
        return (
            f"InfeasibleMigration({self.node_id}: "
            f"{self.from_territory} -> {self.to_territory}, {self.reason})"
        )


@dataclass(frozen=True)
class ConservationViolation:
    """A conservation law was violated (defensive check before invariant harness).

    Args:
        invariant_name: Name of the conservation invariant.
        expected: Expected value (pre-step total or delta).
        actual: Actual value observed post-step.
        tolerance: The tolerance that was exceeded.
    """

    invariant_name: str
    expected: float
    actual: float
    tolerance: float

    def __str__(self) -> str:
        return (
            f"ConservationViolation({self.invariant_name}: "
            f"expected={self.expected:.6e}, actual={self.actual:.6e}, "
            f"tol={self.tolerance:.0e})"
        )


TransitionError = (
    NegativeCapitalStock
    | InsufficientLaborHours
    | MissingOrganization
    | InfeasibleMigration
    | ConservationViolation
)
"""Closed union of all modeled transition failures.

Systems return ``Result[WorldState, TransitionError]`` to signal expected
failures without raising exceptions.
"""
