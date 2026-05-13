"""Per-tick atomic transaction envelope.

Spec 062 — FR-008a + data-model.md §2.6. Every tick produces exactly one
:class:`PerTickTransactionEnvelope`; the envelope is the atomic unit of
persistence. :meth:`PostgresRuntime.persist_tick_atomic` writes the whole
envelope in one Postgres transaction or rolls back if any insert fails.

See Also:
    ``specs/062-cross-scale-integration/contracts/persistence.yaml``.
    :mod:`babylon.persistence.audit_models`: :class:`ConservationAuditRow`.
    :mod:`babylon.persistence.hex_state`: :class:`DynamicHexState`.
    :mod:`babylon.persistence.external_node`: :class:`ExternalNode`.
    :mod:`babylon.economics.boundary_flow_register`:
        :class:`BoundaryFlowRegisterRow`.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from babylon.economics.boundary_flow_register import BoundaryFlowRegisterRow
from babylon.persistence.audit_models import ConservationAuditRow
from babylon.persistence.external_node import ExternalNode
from babylon.persistence.hex_state import DynamicHexState


class PerTickTransactionEnvelope(BaseModel):
    """Atomic unit of per-tick persistence.

    Holds every row produced during one tick that must commit together:
    hex states, external-node states, boundary-register rows, and audit-log
    rows. A single ``determinism_hash`` value is shared across all rows in
    the tick (GATE-1 / Constitution III.7).

    The envelope is frozen — once handed to
    :meth:`PostgresRuntime.persist_tick_atomic` it cannot be mutated.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    hex_state_rows: list[DynamicHexState] = Field(default_factory=list)
    external_node_rows: list[ExternalNode] = Field(default_factory=list)
    boundary_register_rows: list[BoundaryFlowRegisterRow] = Field(default_factory=list)
    audit_log_rows: list[ConservationAuditRow] = Field(default_factory=list)
    determinism_hash: str = Field(min_length=64, max_length=64)


__all__ = ["PerTickTransactionEnvelope"]
