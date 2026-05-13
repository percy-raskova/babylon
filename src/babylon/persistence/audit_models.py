"""Conservation-audit Pydantic models.

Spec 062, data-model.md §2.4. The per-tick audit log records one row per
``(scale, invariant)`` evaluation; severity is graded ``ok | warn | alarm``
against :attr:`babylon.config.defines.EconomyDefines.epsilon_conservation`
(FR-046). Every row in the same tick carries the same
:attr:`ConservationAuditRow.determinism_hash` (GATE-1 / Constitution III.7).

See Also:
    ``specs/062-cross-scale-integration/contracts/audit_log.yaml``.
    :mod:`babylon.persistence.conservation_audit`: end-of-tick auditor.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditSeverity(StrEnum):
    """Three-level severity grade for a conservation audit row.

    OK:    |residual| <= epsilon_conservation (FR-046).
    WARN:  epsilon_conservation < |residual| <= 1e-6.
    ALARM: |residual| > 1e-6  →  emit ConservationAlarmEvent (FR-047).
    """

    OK = "ok"
    WARN = "warn"
    ALARM = "alarm"


class ConservationAuditRow(BaseModel):
    """One audit-log row for a (tick, scale, invariant) triple.

    Attributes:
        session_id: Owning session UUID.
        tick: Simulation tick (>= 0).
        scale: One of ``hex``, ``county``, ``state``, ``national``,
            ``global_phi``, or ``per_stage``.
        invariant_name: Stable identifier (see ``audit_log.yaml#invariant_name``).
        computed_value: Engine-computed quantity for this invariant.
        expected_value: Reference quantity (sum, balance, identity).
        residual: ``computed_value - expected_value`` (sign-preserving).
        severity: :class:`AuditSeverity` per FR-046 thresholds.
        determinism_hash: SHA-256 hex of canonical-JSON(tick + sorted
            hex_state + action list + rng_seed). Same value for every
            row in this tick (GATE-1).
        created_at_utc: Wall-clock timestamp of the audit evaluation.
    """

    model_config = ConfigDict(frozen=True)

    session_id: UUID
    tick: int = Field(ge=0)
    scale: str = Field(min_length=1, max_length=32)
    invariant_name: str = Field(min_length=1, max_length=128)
    computed_value: float
    expected_value: float
    residual: float
    severity: AuditSeverity
    determinism_hash: str = Field(min_length=64, max_length=64)
    created_at_utc: datetime


__all__ = ["AuditSeverity", "ConservationAuditRow"]
