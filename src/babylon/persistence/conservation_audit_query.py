"""Read facade for the ``conservation_audit_log`` table (Spec 062, T069).

Per ``contracts/audit_log.yaml#ConservationAuditQuery``. The audit log is
append-only (Postgres GRANT enforcement); this module only provides
``SELECT`` access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from babylon.persistence.audit_models import AuditSeverity, ConservationAuditRow

if TYPE_CHECKING:
    from babylon.persistence import PostgresRuntime


_FETCH_BASE = """
SELECT session_id, tick, scale, invariant_name,
       computed_value, expected_value, residual,
       severity, determinism_hash, created_at_utc
FROM conservation_audit_log
WHERE session_id = %(session_id)s
"""

_COUNT_BY_SEVERITY = """
SELECT severity, COUNT(*)
FROM conservation_audit_log
WHERE session_id = %(session_id)s
  AND (%(tick_lo)s IS NULL OR tick >= %(tick_lo)s)
  AND (%(tick_hi)s IS NULL OR tick <= %(tick_hi)s)
GROUP BY severity
"""


class ConservationAuditQuery:
    """Read-only typed-protocol facade for audit-log queries."""

    def __init__(self, runtime: PostgresRuntime) -> None:
        self._runtime = runtime

    def fetch(
        self,
        *,
        session_id: UUID,
        tick: int | None = None,
        scale: str | None = None,
        invariant_name: str | None = None,
        severity: AuditSeverity | str | None = None,
        limit: int | None = None,
    ) -> list[ConservationAuditRow]:
        """Return rows matching the filters (all optional).

        Ordering: ``ORDER BY tick ASC, invariant_name ASC``.
        """
        sql_parts = [_FETCH_BASE]
        params: dict[str, object] = {"session_id": str(session_id)}

        if tick is not None:
            sql_parts.append("AND tick = %(tick)s")
            params["tick"] = tick
        if scale is not None:
            sql_parts.append("AND scale = %(scale)s")
            params["scale"] = scale
        if invariant_name is not None:
            sql_parts.append("AND invariant_name = %(invariant_name)s")
            params["invariant_name"] = invariant_name
        if severity is not None:
            sql_parts.append("AND severity = %(severity)s")
            params["severity"] = severity.value if isinstance(severity, AuditSeverity) else severity

        sql_parts.append("ORDER BY tick ASC, invariant_name ASC")
        if limit is not None:
            sql_parts.append("LIMIT %(limit)s")
            params["limit"] = limit

        sql = "\n".join(sql_parts)
        with self._runtime._pool.connection() as conn:  # noqa: SLF001
            rows = conn.execute(sql, params).fetchall()
        return [
            ConservationAuditRow(
                session_id=r[0],
                tick=r[1],
                scale=r[2],
                invariant_name=r[3],
                computed_value=r[4],
                expected_value=r[5],
                residual=r[6],
                severity=AuditSeverity(r[7]),
                determinism_hash=r[8],
                created_at_utc=r[9],
            )
            for r in rows
        ]

    def count_by_severity(
        self,
        session_id: UUID,
        tick_range: tuple[int, int] | None = None,
    ) -> dict[str, int]:
        """Returns ``{'ok': N, 'warn': N, 'alarm': N}`` for the requested range.

        Missing severities are returned with value 0 so the result has a
        fixed three-key shape.
        """
        lo, hi = (None, None) if tick_range is None else tick_range
        params = {
            "session_id": str(session_id),
            "tick_lo": lo,
            "tick_hi": hi,
        }
        with self._runtime._pool.connection() as conn:  # noqa: SLF001
            rows = conn.execute(_COUNT_BY_SEVERITY, params).fetchall()
        counts: dict[str, int] = {"ok": 0, "warn": 0, "alarm": 0}
        for sev, count in rows:
            counts[sev] = count
        return counts


__all__ = ["ConservationAuditQuery"]
