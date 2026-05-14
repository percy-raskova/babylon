"""Build summary.json — terminal aggregates + audit log + performance.

Spec: 064-headless-sim-runner (T026).

The summary follows ``contracts/summary_json_schema.yaml``. Top-level
keys:

* ``schema_version`` — locked literal "1.0"
* ``run_metadata`` — session id, exit reason, ticks, year, seed, scope
* ``terminal_state`` — aggregates at the final completed tick
* ``external_node_flows`` — per-external-node summed flow magnitudes
* ``county_terminal_snapshot`` — per-county terminal state (delta-vs-init)
* ``conservation_audit`` — projection of conservation_audit_log rows
* ``performance`` — wallclock breakdown
* ``end_game_event`` (optional) — present when exit_reason == early_terminated
* ``error`` (optional) — present when exit_reason == errored

The builder is decoupled from Postgres: callers feed it pre-shaped
inputs. Postgres-backed runs query the relevant views/tables and pass
the rows in; unit tests pass synthetic fixtures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from babylon.engine.headless_runner.models import (
    AuditEntry,
    ExitReason,
    PerformanceBreakdown,
    SimulationRunConfig,
)


def build_summary(
    *,
    config: SimulationRunConfig,
    session_id: str,
    exit_reason: ExitReason,
    ticks_completed: int,
    wallclock_start: datetime,
    wallclock_end: datetime,
    terminal_state: dict[str, Any],
    external_node_flows: list[dict[str, Any]],
    county_terminal_snapshot: list[dict[str, Any]],
    conservation_audit: list[AuditEntry],
    performance: PerformanceBreakdown,
    end_game_event: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the summary payload as a plain dict.

    Args:
        config: The driving :class:`SimulationRunConfig`.
        session_id: UUID string for this run.
        exit_reason: How the run terminated.
        ticks_completed: Number of fully-persisted ticks (≤ config.ticks).
        wallclock_start: Run start time (UTC).
        wallclock_end: Run end time (UTC).
        terminal_state: Aggregates at the final completed tick (counties_alive,
            total_population, total_v/c/s/k, mean ideology axes, etc.).
        external_node_flows: One entry per external node (canada, china,
            rest_of_usa) with summed inflows/outflows.
        county_terminal_snapshot: Per-county terminal row + delta-vs-initial.
        conservation_audit: Conservation-invariant violations from spec-062.
        performance: Wallclock attribution model.
        end_game_event: Present iff exit_reason == EARLY_TERMINATED.
        error: Present iff exit_reason == ERRORED.

    Returns:
        Dict ready to be JSON-encoded as summary.json.
    """
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "run_metadata": {
            "session_id": session_id,
            "exit_reason": exit_reason.value,
            "ticks_requested": config.ticks,
            "ticks_completed": ticks_completed,
            "start_year": config.start_year,
            "seed": config.random_seed,
            "scope_name": config.scope_name,
            "scope_fips": sorted(config.scope_fips),
            "external_node_ids": sorted(config.external_node_ids),
            "wallclock_start": _iso_utc(wallclock_start),
            "wallclock_end": _iso_utc(wallclock_end),
        },
        "terminal_state": terminal_state,
        "external_node_flows": external_node_flows,
        "county_terminal_snapshot": county_terminal_snapshot,
        "conservation_audit": [_audit_to_dict(a) for a in conservation_audit],
        "performance": performance.model_dump(),
    }

    if end_game_event is not None:
        payload["end_game_event"] = end_game_event
    if error is not None:
        payload["error"] = error

    return payload


def _audit_to_dict(audit: AuditEntry) -> dict[str, Any]:
    return {
        "tick": audit.tick,
        "invariant_name": audit.invariant_name,
        "severity": audit.severity,
        "details": dict(audit.details),
    }


def _iso_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


__all__ = ["build_summary"]
