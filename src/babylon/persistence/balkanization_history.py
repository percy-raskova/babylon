"""Spec-070 audit-row writers for CLAIMS / INFLUENCES mutations
(FR-046 + R-005).

These functions append rows to ``balkanization_claims_audit`` /
``balkanization_influences_audit`` (defined in migration 0025). They
are the *only* sanctioned write path for those tables — direct INSERTs
elsewhere violate Constitution II.11 (Subsystem Table Ownership).

OBSERVER-mode mutations (FR-049) MUST pass ``observer_mutation=True``
so the audit row is flagged. CAMPAIGN-mode + system-internal mutations
default to ``observer_mutation=False``.

Each writer is post-tick: invoked from inside a system's tick AFTER
the GraphProtocol mutation has been applied. The Postgres write is
deferred to the per-tick flush (per spec-062 two-phase persistence
boundary FR-008a).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

if TYPE_CHECKING:  # pragma: no cover - import-only
    from psycopg_pool import ConnectionPool


Operation = Literal["CREATE", "UPDATE", "DELETE"]


@dataclass(frozen=True)
class ClaimsAuditRow:
    """Per FR-046 + audit_row.schema.json ClaimsAuditRow."""

    session_id: UUID
    tick: int
    sovereign_id: str
    territory_id: str
    operation: Operation
    control_level: float
    fiscal_status: str
    legal_status: str
    recognition_level: float
    observer_mutation: bool


@dataclass(frozen=True)
class InfluencesAuditRow:
    """Per FR-046 + audit_row.schema.json InfluencesAuditRow."""

    session_id: UUID
    tick: int
    faction_id: str
    territory_id: str
    operation: Operation
    influence_level: float
    support_type: str
    cadre_count: int
    sympathizer_count: int
    observer_mutation: bool


_INSERT_CLAIMS_AUDIT_SQL = """
INSERT INTO balkanization_claims_audit (
    session_id, tick, sovereign_id, territory_id, operation,
    control_level, fiscal_status, legal_status, recognition_level,
    observer_mutation
)
VALUES (
    %(session_id)s, %(tick)s, %(sovereign_id)s, %(territory_id)s,
    %(operation)s, %(control_level)s, %(fiscal_status)s,
    %(legal_status)s, %(recognition_level)s, %(observer_mutation)s
)
"""

_INSERT_INFLUENCES_AUDIT_SQL = """
INSERT INTO balkanization_influences_audit (
    session_id, tick, faction_id, territory_id, operation,
    influence_level, support_type, cadre_count, sympathizer_count,
    observer_mutation
)
VALUES (
    %(session_id)s, %(tick)s, %(faction_id)s, %(territory_id)s,
    %(operation)s, %(influence_level)s, %(support_type)s,
    %(cadre_count)s, %(sympathizer_count)s, %(observer_mutation)s
)
"""


def record_claims_mutation(
    pool: ConnectionPool,
    row: ClaimsAuditRow,
) -> None:
    """Append a single CLAIMS-mutation audit row.

    Args:
        pool: psycopg ConnectionPool from the runtime ServiceContainer.
        row: Audit row payload.
    """

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            _INSERT_CLAIMS_AUDIT_SQL,
            {
                "session_id": row.session_id,
                "tick": row.tick,
                "sovereign_id": row.sovereign_id,
                "territory_id": row.territory_id,
                "operation": row.operation,
                "control_level": row.control_level,
                "fiscal_status": row.fiscal_status,
                "legal_status": row.legal_status,
                "recognition_level": row.recognition_level,
                "observer_mutation": row.observer_mutation,
            },
        )


def record_influences_mutation(
    pool: ConnectionPool,
    row: InfluencesAuditRow,
) -> None:
    """Append a single INFLUENCES-mutation audit row.

    Args:
        pool: psycopg ConnectionPool from the runtime ServiceContainer.
        row: Audit row payload.
    """

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            _INSERT_INFLUENCES_AUDIT_SQL,
            {
                "session_id": row.session_id,
                "tick": row.tick,
                "faction_id": row.faction_id,
                "territory_id": row.territory_id,
                "operation": row.operation,
                "influence_level": row.influence_level,
                "support_type": row.support_type,
                "cadre_count": row.cadre_count,
                "sympathizer_count": row.sympathizer_count,
                "observer_mutation": row.observer_mutation,
            },
        )


__all__ = [
    "ClaimsAuditRow",
    "InfluencesAuditRow",
    "Operation",
    "record_claims_mutation",
    "record_influences_mutation",
]
