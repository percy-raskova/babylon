"""Dialectic[A, B] — the fundamental primitive of Babylon v2.

A Dialectic is a 5-tuple ``D = (A, Ā, w, T, σ)``:

- ``A, Ā`` are typed states — the two poles.
- ``w ∈ [-1, 1]`` is the principal aspect weight.
- ``T`` is the motion operator (implemented as :meth:`step`).
- ``σ`` is the sublation predicate (implemented as :meth:`sublate`).

The engine enforces three universal invariants on every Dialectic at every
tick: weight ∈ [-1, 1], type stability across motion, and that ``step``
returns a Dialectic of the declared type.

See Also:
    :mod:`babylon.engine.dialectics.volume_1`: Concrete V1 dialectics.
    :mod:`babylon.engine.dialectics.world`: World graph model.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# ===========================================================================
# Type variables for generic poles
# ===========================================================================

A = TypeVar("A", bound=BaseModel)
B = TypeVar("B", bound=BaseModel)


# ===========================================================================
# Supporting types for step() interface
# ===========================================================================


class TickInputs(BaseModel):
    """Upstream dialectic outputs feeding into this tick.

    This carries the ``ε`` term from the formal definition — the output
    of upstream dialectics in the morphism graph that feed into this
    dialectic's motion law.

    Attributes:
        upstream: Mapping of source dialectic ID to its ``observe()`` output.
    """

    model_config = ConfigDict(frozen=True)

    upstream: dict[UUID, dict[str, Any]] = Field(
        default_factory=dict,
        description="Mapping of source dialectic ID to its observe() output.",
    )


class WorldView(BaseModel):
    """Read-only projection of the World for context access.

    Provides the ``World`` term from the formal definition — read-only
    access to the rest of the graph for context during ``step()``.

    Attributes:
        tick: Current simulation tick.
        dialectics: Read-only view of all live dialectics by ID.
    """

    model_config = ConfigDict(frozen=True)

    tick: int = Field(..., description="Current simulation tick.")
    dialectics: dict[UUID, Any] = Field(
        default_factory=dict,
        description="Read-only view of all live dialectics by ID.",
    )


# ===========================================================================
# The Dialectic primitive
# ===========================================================================


class Dialectic(BaseModel, Generic[A, B]):  # noqa: UP046 — Pydantic requires Generic syntax
    """The fundamental type of the Babylon v2 engine.

    Every world object is a Dialectic. The simulation is the time-evolution
    of a graph of dialectics under their motion laws.

    Subclasses must:
    - Set ``type_tag`` as a class-level string (discriminator for serialization).
    - Implement ``step()`` — the motion law T.
    - Optionally override ``sublate()``, ``observe()``, ``invariants()``.

    The model is frozen (immutable). ``step()`` returns a *new* Dialectic;
    it never mutates in place.

    Attributes:
        id: Unique identifier for this dialectic instance.
        type_tag: Discriminator string set by each subclass.
        pole_a: The first pole (typed state A).
        pole_b: The second pole (typed state B / Ā).
        weight: Principal aspect weight ∈ [-1, 1]. <0 = pole A dominant,
                0 = equilibrium, >0 = pole B dominant.
        parent_id: UUID of the predecessor if this was produced by sublation.
        tick_created: Tick when this dialectic was first instantiated.
        tick_updated: Tick when this dialectic was last stepped.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    type_tag: str  # Set by subclass as a class variable or field default
    pole_a: A
    pole_b: B
    weight: float = Field(..., ge=-1.0, le=1.0)
    parent_id: UUID | None = None
    tick_created: int
    tick_updated: int

    @abstractmethod
    def step(self, inputs: TickInputs, world: WorldView) -> Dialectic[A, B]:
        """Motion law T.

        Must return a new Dialectic of the *same concrete type*.
        The engine checks type stability as a universal invariant.

        Args:
            inputs: Upstream dialectic outputs for this tick.
            world: Read-only view of the full world graph.

        Returns:
            A new Dialectic instance (same type) representing the next state.
        """

    def sublate(self) -> Dialectic[Any, Any] | None:
        """Sublation predicate σ.

        Returns a successor dialectic when the contradiction resolves into
        a higher-order form, or ``None`` if no sublation occurs.

        The default implementation returns ``None`` (no sublation).

        Returns:
            Successor Dialectic, or None.
        """
        return None

    def observe(self) -> dict[str, Any]:
        """Project onto a measurement basis.

        Used by the frontend, analytics, and the morphism graph to
        read this dialectic's state without accessing internals.

        Returns:
            Dictionary with at minimum: id, type, weight, principal_aspect.
        """
        return {
            "id": str(self.id),
            "type": self.type_tag,
            "weight": self.weight,
            "principal_aspect": "A" if self.weight < 0 else "B",
        }

    def invariants(self) -> list[str]:
        """Return list of violated invariants for this tick.

        An empty list means the dialectic is in a valid state.
        Subclasses should override to add domain-specific invariants
        (conservation of labor content, etc.).

        Returns:
            List of invariant violation descriptions. Empty = valid.
        """
        return []
