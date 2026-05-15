"""Pydantic entities for the headless simulation runner.

Spec: 064-headless-sim-runner (data-model.md §1)

All models are frozen Pydantic 2.x per project standard. The set:

* :class:`ExitReason` — discrete run-terminal states
* :class:`SimulationRunConfig` — full input description of one run
* :class:`PerformanceBreakdown` — wallclock attribution
* :class:`AuditEntry` — projection of one conservation_audit_log row
* :class:`TraceRow` — one row of trace.csv
* :class:`SimulationRunResult` — return value of :func:`runner.run`
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_FIPS5_RE = re.compile(r"^\d{5}$")


class ExitReason(StrEnum):
    """Run-terminal state discriminator.

    Mapped to CLI exit codes per ``contracts/cli_contract.yaml``:

    * ``COMPLETED`` → exit 0
    * ``EARLY_TERMINATED`` → exit 0 (valid end-game)
    * ``USER_INTERRUPTED`` → exit 130
    * ``ERRORED`` → exit 1
    """

    COMPLETED = "completed"
    EARLY_TERMINATED = "early_terminated"
    USER_INTERRUPTED = "user_interrupted"
    ERRORED = "errored"


class SimulationRunConfig(BaseModel):
    """Frozen, hashable description of a single headless run.

    Constructed from CLI flags + defaults; persisted into the manifest's
    ``deterministic_inputs`` section.
    """

    model_config = ConfigDict(frozen=True)

    ticks: int = Field(default=1000, ge=1, le=100_000)
    start_year: int = Field(default=2010, ge=1900, le=2100)
    random_seed: int = Field(default=2010)

    scope_name: str = Field(default="michigan-canada")
    scope_fips: frozenset[str] = Field(...)
    external_node_ids: frozenset[str] = Field(default=frozenset({"canada"}))

    sqlite_reference_path: Path = Field(
        default=Path("data/sqlite/marxist-data-3NF.sqlite"),
    )
    output_dir: Path = Field(...)
    defines_overlay_path: Path | None = Field(default=None)

    dry_run: bool = Field(default=False)
    verbose: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    # Spec-065 additions
    strict: bool = Field(
        default=False,
        description=(
            "When True, the runner exits with code 1 on first "
            "conservation_audit_log row with severity='alarm'. The "
            "qa:e2e-regression mise task enables this; ad-hoc runs "
            "default to False (informational audit log only)."
        ),
    )
    endgame_detector: str | None = Field(
        default=None,
        description=(
            "Optional dotted import path to an EndgameDetector instance "
            "(e.g., babylon.engine.observer.ImperialCollapseDetector). "
            "When set, the runner polls the detector at end of every "
            "tick; on positive return the loop halts and exit_reason "
            "becomes 'early_terminated'."
        ),
    )

    @field_validator("scope_fips")
    @classmethod
    def _validate_fips(cls, value: frozenset[str]) -> frozenset[str]:
        if not value:
            raise ValueError("scope_fips must be non-empty")
        bad = [f for f in value if not _FIPS5_RE.match(f)]
        if bad:
            raise ValueError(f"scope_fips contains non-5-digit codes: {sorted(bad)[:5]}")
        return value


class PerformanceBreakdown(BaseModel):
    """Wallclock attribution for SC-002 verification."""

    model_config = ConfigDict(frozen=True)

    total_wallclock_sec: float = Field(ge=0.0)
    session_init_sec: float = Field(ge=0.0)
    hex_hydration_sec: float = Field(ge=0.0)
    tick_loop_sec: float = Field(ge=0.0)
    artifact_emission_sec: float = Field(ge=0.0)
    per_tick_median_ms: float = Field(ge=0.0)
    per_tick_p99_ms: float = Field(ge=0.0)
    per_tick_max_ms: float = Field(ge=0.0)
    # Spec-065 T074: per-engine-system wallclock (empty until engine wires up).
    per_system_ms: dict[str, float] = Field(default_factory=dict)


class AuditEntry(BaseModel):
    """Projection of one row from spec-062 ``conservation_audit_log``."""

    model_config = ConfigDict(frozen=True)

    tick: int = Field(ge=0)
    invariant_name: str
    severity: Literal["info", "warning", "error", "critical"]
    details: dict[str, Any] = Field(default_factory=dict)


class TraceRow(BaseModel):
    """One row of ``trace.csv``.

    Column ordering matches ``contracts/trace_csv_schema.yaml`` and the
    SQL view ``view_runtime_trace_emission``. CSV serialization writes
    ``""`` for ``None`` per FR-008.
    """

    model_config = ConfigDict(frozen=True)

    tick: int
    simulated_year: float
    entity_id: str
    entity_kind: Literal["county", "external", "national", "hex_aggregate"]

    v: float | None = None
    c: float | None = None
    s: float | None = None
    k: float | None = None

    p_acquiescence: float | None = None
    p_revolution: float | None = None
    ideology_r: float | None = None
    ideology_l: float | None = None
    ideology_f: float | None = None

    surveillance_coupling: float | None = None
    internet_access_pct: float | None = None
    biocapacity_stock: float | None = None
    energy_stock: float | None = None
    raw_material_stock: float | None = None

    profit_rate: float | None = None
    exploitation_rate: float | None = None

    population: int | None = None
    employment_proxy: float | None = None


class SimulationRunResult(BaseModel):
    """Return value of :func:`babylon.engine.headless_runner.run`."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    session_id: UUID
    config: SimulationRunConfig
    ticks_completed: int = Field(ge=0)
    exit_reason: ExitReason
    end_game_tick: int | None = None
    end_game_condition: str | None = None

    wallclock_start: datetime
    wallclock_end: datetime
    performance: PerformanceBreakdown

    conservation_audit: tuple[AuditEntry, ...] = Field(default_factory=tuple)

    trace_rows: Iterator[TraceRow] | None = None
    artifact_dir: Path | None = None

    # Spec-065 additions
    events: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    final_world_state: Any = Field(default=None)
