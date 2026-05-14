"""Append-only register of cross-boundary flows per tick.

Spec 062 — FR-040 / R2. Each row is one dyadic ``source -> dest`` flow with
the ID-space discriminator pair (``source_kind``, ``dest_kind``) per the
data-model.md §2.3 schema. Per Constitution II.9 (Morphism as Dyadic
Relation), no n-ary structures are introduced.

Buffered writes are flushed into the
:class:`babylon.persistence.envelope.PerTickTransactionEnvelope` so that all
rows commit atomically with the rest of the tick (FR-008a).

See Also:
    ``specs/062-cross-scale-integration/contracts/boundary_register.yaml``.
    :mod:`babylon.persistence.migrations.0013_boundary_flow_register`.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.node_kinds import BoundaryEdgeKind, NodeKind


class BoundaryFlowRegisterRow(BaseModel):
    """One row of the ``boundary_flow_register`` table.

    Per the R2 schema, both endpoints carry a discriminator enum
    (:class:`NodeKind`) so a single row can represent any pair from
    ``{hex, county, state, national, external}``. Magnitude is signed:
    positive means flow in the declared ``source -> dest`` direction.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    source_node_id: str = Field(min_length=1, max_length=64)
    source_kind: NodeKind
    dest_node_id: str = Field(min_length=1, max_length=64)
    dest_kind: NodeKind
    flow_type: BoundaryEdgeKind
    magnitude: float


class BoundaryFlowRegister:
    """In-memory buffer + facade for the boundary_flow_register table.

    Rows are appended during the economics-stage of a tick. At end-of-tick
    the buffer is folded into the :class:`PerTickTransactionEnvelope` and
    cleared. The Postgres-side facade
    (:meth:`PostgresRuntime.persist_tick_atomic`) commits the rows inside
    the per-tick transaction (FR-008a).

    The buffer is per-instance (not module-global) so multiple sessions
    advancing in parallel cannot leak rows into each other.
    """

    def __init__(self) -> None:
        self._buffer: list[BoundaryFlowRegisterRow] = []

    def record(
        self,
        *,
        session_id: UUID,
        tick: int,
        source_node_id: str,
        source_kind: NodeKind,
        dest_node_id: str,
        dest_kind: NodeKind,
        flow_type: BoundaryEdgeKind,
        magnitude: float,
    ) -> None:
        """Append one row to the in-memory buffer."""
        self._buffer.append(
            BoundaryFlowRegisterRow(
                session_id=session_id,
                tick=tick,
                source_node_id=source_node_id,
                source_kind=source_kind,
                dest_node_id=dest_node_id,
                dest_kind=dest_kind,
                flow_type=flow_type,
                magnitude=magnitude,
            )
        )

    def flush(self) -> list[BoundaryFlowRegisterRow]:
        """Return the buffered rows and clear the buffer.

        Called once per tick by the engine envelope builder. After flush()
        returns the buffer is empty.
        """
        rows = self._buffer
        self._buffer = []
        return rows

    def query(
        self,
        *,
        session_id: UUID | None = None,
        tick: int | None = None,
        source_kind: NodeKind | None = None,
        source_node_id: str | None = None,
        dest_kind: NodeKind | None = None,
        dest_node_id: str | None = None,
        flow_type: BoundaryEdgeKind | None = None,
    ) -> list[BoundaryFlowRegisterRow]:
        """In-memory filter helper.

        Use the Postgres facade for cross-tick / post-commit queries; this
        method only sees the current-tick buffered rows. All filters
        optional; None matches anything.
        """

        def matches(row: BoundaryFlowRegisterRow) -> bool:
            return (
                (session_id is None or row.session_id == session_id)
                and (tick is None or row.tick == tick)
                and (source_kind is None or row.source_kind == source_kind)
                and (source_node_id is None or row.source_node_id == source_node_id)
                and (dest_kind is None or row.dest_kind == dest_kind)
                and (dest_node_id is None or row.dest_node_id == dest_node_id)
                and (flow_type is None or row.flow_type == flow_type)
            )

        return [row for row in self._buffer if matches(row)]

    def buffered_count(self) -> int:
        """Number of rows currently in the buffer (for diagnostics)."""
        return len(self._buffer)


__all__ = [
    "BoundaryFlowRegisterRow",
    "BoundaryFlowRegister",
    # Re-export so the typical `from boundary_flow_register import *`
    # callsites get the enums too.
    "BoundaryEdgeKind",
    "NodeKind",
]
