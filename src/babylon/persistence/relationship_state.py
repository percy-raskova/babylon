"""Pydantic model for spec-065 per-tick relationship-state rows.

One frozen row model corresponding to migration 0024
(``dynamic_relationship_state``). Stores per-tick dyadic edges
(EXPLOITATION, SOLIDARITY, WAGES, etc.) between SocialClass entities so
:func:`summary.json`-grade aggregates like ``max_tension`` can be
computed via SQL across all persisted ticks (spec-065 T080).

The bridge writes 0 rows per tick in the spec-065 first cut (the
in-memory ``WorldState.relationships`` is currently empty — relationship
dynamics flip on with spec-066's engine integration). The Postgres
table + envelope field + this model are the durable surface for those
rows when the engine starts publishing them.

See Also:
    ``src/babylon/persistence/migrations/0024_dynamic_relationship_state.sql``
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["DynamicRelationshipState"]


class DynamicRelationshipState(BaseModel):
    """One row of ``dynamic_relationship_state`` (migration 0024).

    Owner: ``ContradictionSystem`` + ``SolidaritySystem`` (per
    Constitution II.11). Primary key:
    ``(session_id, tick, source_node_id, target_node_id, edge_type)``.

    Spec-065 T080: the bridge converts ``WorldState.relationships`` to
    these rows in :meth:`WorldStateBridge.persist_tick`. The
    ``max_tension`` summary metric is computed by SQL aggregation of
    these rows across all ticks in a session.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    source_node_id: str = Field(min_length=1, max_length=64)
    target_node_id: str = Field(min_length=1, max_length=64)
    edge_type: str = Field(min_length=1, max_length=32)
    tension: float = Field(ge=0.0, le=1.0)
    solidarity: float = Field(default=0.0, ge=0.0, le=1.0)
