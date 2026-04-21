"""World, Morphism, and WorldEvent — the v2 dialectical graph.

Replaces the Embedded Trinity (Ledger / Topology / Archive) with a
single coherent structure. The graph isn't separate from the dialectics —
it's how they're wired into the tick engine's data flow.

A morphism ``feeds(d1, d2)`` means ``d2.step()`` reads from
``d1.observe()``. A morphism ``contains(d1, d2)`` means ``d1`` is one
of ``d2``'s poles (nesting).

See Also:
    :class:`babylon.engine.dialectics.base.Dialectic`: The fundamental type.
    :mod:`babylon.engine.dialectics.tick`: The pure tick function.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from babylon.engine.dialectics.base import TickInputs

# ===========================================================================
# Morphism — typed relationship between two dialectics
# ===========================================================================


class Morphism(BaseModel):
    """A typed relationship between two dialectics.

    The five canonical relation types:

    - ``feeds``: d2.step() reads from d1.observe()
    - ``constrains``: d1 limits d2's state space
    - ``transforms``: d1's output becomes d2's input prices
    - ``contains``: d1 is one of d2's poles (nesting)
    - ``antagonizes``: d1 and d2 are mutually antagonistic

    Attributes:
        id: Unique identifier for this morphism.
        source_id: UUID of the source dialectic.
        target_id: UUID of the target dialectic.
        relation: Relationship type string.
        weight: Coupling strength.
        metadata: Optional additional data for the relationship.
        tick_created: Tick when this morphism was created.
        tick_destroyed: Tick when this morphism was destroyed (None if live).
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    relation: str
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    tick_created: int = 0
    tick_destroyed: int | None = None


# ===========================================================================
# WorldEvent — event recording
# ===========================================================================


class WorldEvent(BaseModel):
    """An event generated during a tick.

    Events include sublations, crises, ruptures, and player actions.
    The narrative field is populated by the LLM layer (optional).

    Attributes:
        id: Auto-incrementing identifier.
        event_type: Type of event (sublation, crisis, rupture, player_action).
        dialectic_id: UUID of the dialectic that generated this event.
        payload: Arbitrary data associated with the event.
        narrative: LLM-generated prose description (optional).
    """

    model_config = ConfigDict(frozen=True)

    event_type: str
    dialectic_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    narrative: str | None = None


# ===========================================================================
# World — the tick-level world state
# ===========================================================================


class World(BaseModel):
    """The complete world state at a given tick.

    This is the single structure that replaces the Embedded Trinity
    (Ledger / Topology / Archive). It holds all dialectics, their
    morphism wiring, and events generated during the current tick.

    Attributes:
        tick: Current simulation tick.
        dialectics: Map of UUID to Dialectic instance.
        morphisms: List of Morphism edges wiring the dialectical graph.
        events: List of WorldEvent records for this tick.
        sublated_ids: Set of dialectic IDs that have been sublated
                      (replaced by successors). These are excluded from
                      live queries.
    """

    model_config = ConfigDict(frozen=True)

    tick: int = 0
    dialectics: dict[UUID, Any] = Field(default_factory=dict)
    morphisms: list[Morphism] = Field(default_factory=list)
    events: list[WorldEvent] = Field(default_factory=list)
    sublated_ids: frozenset[UUID] = Field(default_factory=frozenset)

    def get_by_type(self, type_tag: str) -> dict[UUID, Any]:
        """Filter dialectics by their type_tag.

        Args:
            type_tag: The type discriminator to filter by.

        Returns:
            Dict of UUID → Dialectic matching the given type_tag.
        """
        return {uid: d for uid, d in self.dialectics.items() if d.type_tag == type_tag}

    def get_inputs_for(self, target_id: UUID) -> TickInputs:
        """Compute TickInputs for a target dialectic from morphism graph.

        Collects ``observe()`` output from all source dialectics that
        have a ``feeds`` morphism targeting ``target_id``.

        Args:
            target_id: UUID of the dialectic receiving inputs.

        Returns:
            TickInputs with upstream observations populated.
        """
        upstream: dict[UUID, dict[str, Any]] = {}
        for m in self.morphisms:
            if m.target_id == target_id and m.relation == "feeds":
                source = self.dialectics.get(m.source_id)
                if source is not None:
                    upstream[m.source_id] = source.observe()
        return TickInputs(upstream=upstream)

    def get_one_or_none(self, type_tag: str) -> Any | None:
        """Return a single dialectic matching the given type_tag, or None.

        This is the defensive accessor for cyclical composition. When a
        dialectic needs to read state from a peer that may or may not exist
        (e.g. ConsumptionDialectic reading ProductionDialectic), it uses
        ``get_one_or_none`` instead of assuming the peer is present.

        If multiple dialectics of the same type exist, returns the first
        found (iteration order).

        Args:
            type_tag: The type discriminator to search for.

        Returns:
            The first matching Dialectic, or None if none exist.
        """
        for d in self.dialectics.values():
            if d.type_tag == type_tag:
                return d
        return None

    def get_live_dialectics(self) -> dict[UUID, Any]:
        """Return all dialectics that have not been sublated.

        Sublated dialectics are preserved in the ``dialectics`` dict
        for history, but excluded from live queries.

        Returns:
            Dict of UUID → Dialectic for all non-sublated instances.
        """
        return {uid: d for uid, d in self.dialectics.items() if uid not in self.sublated_ids}
