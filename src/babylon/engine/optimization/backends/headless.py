"""Headless Postgres-backed optimization trial backend.

Wraps :func:`babylon.engine.headless_runner.run` — a real, Postgres-backed
simulation session — and reshapes its :class:`SimulationRunResult` into the
optimization package's :class:`~babylon.engine.optimization.backends.types.Result`
contract.

Field extraction mirrors ``tools/shared.py::run_simulation`` (the pre-package
implementation), with one deliberate fix: the RNG seed is threaded through as
a genuine per-trial parameter (``seed``) rather than read off
``getattr(defines, "rng_seed", 2010)`` — ``GameDefines`` has no ``rng_seed``
field, so the old code was silently always falling back to the ``2010``
default regardless of what a caller intended.

.. note::
   **Known upstream limitation (out of scope for this phase):**
   :meth:`EventCapture._extract_event_type` (headless_runner/event_capture.py)
   probes captured events for an ``event_type`` attribute, but the kernel
   ``Event`` dataclass (``babylon.kernel.event_bus.Event``) names that field
   ``type``. Every engine-published event therefore falls through to the
   ``event.__class__.__name__`` branch (``"Event"``) rather than surfacing
   its real :class:`~babylon.models.enums.events.EventType` value. This
   backend still matches against the *documented* ``event_type`` contract
   (as the correct consumer would), so phase-milestone detection will read
   as all-``None`` until that upstream bug is fixed — an honest degradation
   per Constitution III.11, not a fabricated milestone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from babylon.config.defines import GameDefines
from babylon.engine.optimization.backends.types import Result
from babylon.models.enums.events import EventType

# Maps Result.phase_milestones key -> the EventType value that signals it.
_MILESTONE_EVENT_TYPES: dict[str, str] = {
    "superwage_crisis": EventType.SUPERWAGE_CRISIS.value,
    "class_decomposition": EventType.CLASS_DECOMPOSITION.value,
    "control_ratio_crisis": EventType.CONTROL_RATIO_CRISIS.value,
    "terminal_decision": EventType.TERMINAL_DECISION.value,
}


def _extract_final_wealth(final_state: Any) -> float:
    """Sum terminal-tick entity wealth as a coarse aggregate proxy."""
    if final_state is None or not hasattr(final_state, "entities"):
        return 0.0
    return sum(float(e.wealth) for e in final_state.entities.values())


def _extract_max_tension(*, artifact_dir: Path | None, final_state: Any) -> float:
    """Prefer the SQL-backed cross-tick max from ``summary.json``.

    Falls back to the terminal in-memory snapshot's relationships when the
    artifact is absent or degraded (mirrors ``tools/shared.py::run_simulation``).
    """
    max_tension = 0.0
    if artifact_dir is not None:
        summary_path = artifact_dir / "summary.json"
        if summary_path.exists():
            try:
                summary_payload = json.loads(summary_path.read_text())
                terminal_state = summary_payload.get("terminal_state", {})
                max_tension = float(terminal_state.get("max_tension") or 0.0)
            except (OSError, ValueError, json.JSONDecodeError):
                max_tension = 0.0
    if max_tension == 0.0 and final_state is not None and hasattr(final_state, "relationships"):
        max_tension = max(
            (float(getattr(r, "tension", 0.0)) for r in final_state.relationships),
            default=0.0,
        )
    return max_tension


def _extract_phase_milestones(
    events: tuple[dict[str, Any], ...],
) -> tuple[dict[str, int | None], str | None]:
    """Scan captured events for the first tick of each Track-A milestone.

    :param events: ``SimulationRunResult.events`` — dicts shaped
        ``{"tick", "event_type", "entity_ids", "severity", "details"}``.
    :returns: ``(phase_milestones, terminal_outcome)``.
    """
    phase_milestones: dict[str, int | None] = dict.fromkeys(_MILESTONE_EVENT_TYPES)
    terminal_outcome: str | None = None
    for ev in events:
        ev_type = ev.get("event_type")
        ev_tick = ev.get("tick")
        for legacy_key, type_value in _MILESTONE_EVENT_TYPES.items():
            if ev_type == type_value and phase_milestones[legacy_key] is None:
                phase_milestones[legacy_key] = ev_tick
        if ev_type == EventType.TERMINAL_DECISION.value and terminal_outcome is None:
            details = ev.get("details")
            terminal_outcome = details.get("outcome") if isinstance(details, dict) else None
    return phase_milestones, terminal_outcome


def run_headless(
    defines: GameDefines,
    seed: int,
    max_ticks: int,
    scope_fips: frozenset[str],
    scope_name: str,
    output_dir: Path,
) -> Result:
    """Run one trial via the headless Postgres-backed runner.

    :param defines: The (possibly swept) ``GameDefines`` for this trial.
        Threaded to :func:`babylon.engine.headless_runner.run` via
        ``SimulationRunConfig.defines`` — see the plumbing fix in
        ``runner._resolve_defines``.
    :param seed: RNG seed for this trial (``SimulationRunConfig.random_seed``).
    :param max_ticks: Maximum ticks to run.
    :param scope_fips: County FIPS codes in scope.
    :param scope_name: Predefined or custom scope label (recorded, not
        re-resolved — the caller already resolved ``scope_fips``).
    :param output_dir: Directory for the run's artifact bundle.
    :returns: Backend-normalized :class:`Result`.
    """
    from babylon.engine.headless_runner import run as headless_run
    from babylon.engine.headless_runner.models import ExitReason, SimulationRunConfig
    from babylon.engine.headless_runner.runner import _defines_hash

    config = SimulationRunConfig(
        ticks=max_ticks,
        random_seed=seed,
        scope_name=scope_name,
        scope_fips=scope_fips,
        output_dir=output_dir,
        defines=defines,
    )
    result = headless_run(config)

    final_state = result.final_world_state
    final_wealth = _extract_final_wealth(final_state)
    max_tension = _extract_max_tension(artifact_dir=result.artifact_dir, final_state=final_state)
    phase_milestones, terminal_outcome = _extract_phase_milestones(result.events)

    return Result(
        ticks_survived=result.ticks_completed,
        outcome="SURVIVED" if result.exit_reason == ExitReason.COMPLETED else "DIED",
        max_tension=max_tension,
        final_wealth=final_wealth,
        phase_milestones=phase_milestones,
        terminal_outcome=terminal_outcome,
        defines_hash=_defines_hash(defines),
        rng_seed=seed,
        backend="headless",
        extra={
            "session_id": str(result.session_id),
            "artifact_dir": str(result.artifact_dir) if result.artifact_dir else None,
            "exit_reason": result.exit_reason.value,
        },
    )


__all__ = ["run_headless"]
