"""Fast in-memory optimization trial backend (legacy engine path).

Drives the pre-Postgres, pure in-memory engine — the same tick-loop shape
as ``tools/regression_test.py``'s ``_run_scenario_ticks`` — via
:func:`babylon.engine.scenarios.create_imperial_circuit_scenario` /
:func:`babylon.engine.scenarios.create_two_node_scenario` +
:func:`babylon.engine.simulation_engine.step`.

Unlike the headless backend, this path genuinely honors injected
``GameDefines`` today: ``step()`` accepts the caller's ``defines`` on every
tick call, no coefficient plumbing is degraded. It also runs the full
``_DEFAULT_SYSTEMS`` chain internally (``simulation_engine._DEFAULT_ENGINE``)
and returns each tick's typed Pydantic events on ``WorldState.events``, so
Track-A phase-milestone detection is real here (not a documented gap as in
the headless backend) — ``WorldState.events`` is per-tick, not cumulative
(a tick with no events is ``[]``), so milestones are accumulated across the
loop in this module, first-occurrence only.
"""

from __future__ import annotations

from typing import Any

from babylon.config.defines import GameDefines
from babylon.engine.optimization.backends.types import Result
from babylon.models.entity_registry import PERIPHERY_WORKER_ID
from babylon.models.enums.events import EventType
from babylon.models.events import TerminalDecisionEvent

# Maps Result.phase_milestones key -> the EventType that signals it.
_MILESTONE_EVENT_TYPES: dict[str, EventType] = {
    "superwage_crisis": EventType.SUPERWAGE_CRISIS,
    "class_decomposition": EventType.CLASS_DECOMPOSITION,
    "control_ratio_crisis": EventType.CONTROL_RATIO_CRISIS,
    "terminal_decision": EventType.TERMINAL_DECISION,
}

_SCENARIO_FACTORIES = ("imperial_circuit", "two_node")


def _build_scenario(scenario: str) -> tuple[Any, Any, GameDefines]:
    """Resolve a scenario name to its ``(WorldState, SimulationConfig, GameDefines)``.

    :raises ValueError: If ``scenario`` is not a recognized name.
    """
    if scenario == "imperial_circuit":
        from babylon.engine.scenarios import create_imperial_circuit_scenario

        return create_imperial_circuit_scenario()
    if scenario == "two_node":
        from babylon.engine.scenarios import create_two_node_scenario

        return create_two_node_scenario()
    raise ValueError(f"Unknown scenario {scenario!r}; expected one of: {_SCENARIO_FACTORIES}")


def _max_exploitation_tension(state: Any) -> float:
    """Maximum tension across all relationships in one WorldState snapshot."""
    max_tension = 0.0
    for rel in state.relationships:
        if hasattr(rel, "tension"):
            max_tension = max(max_tension, rel.tension)
    return max_tension


def _scan_tick_events(
    events: list[Any],
    phase_milestones: dict[str, int | None],
    terminal_outcome: str | None,
) -> str | None:
    """Update ``phase_milestones`` in place with this tick's first-occurrences.

    :returns: The (possibly updated) ``terminal_outcome``.
    """
    for ev in events:
        ev_type = getattr(ev, "event_type", None)
        ev_tick = getattr(ev, "tick", None)
        for legacy_key, type_value in _MILESTONE_EVENT_TYPES.items():
            if ev_type == type_value and phase_milestones[legacy_key] is None:
                phase_milestones[legacy_key] = ev_tick
        if terminal_outcome is None and isinstance(ev, TerminalDecisionEvent):
            terminal_outcome = ev.outcome
    return terminal_outcome


def run_in_memory(
    defines: GameDefines,
    seed: int,
    max_ticks: int,
    scenario: str = "imperial_circuit",
) -> Result:
    """Run one trial via the fast in-memory legacy engine path.

    :param defines: The (possibly swept) ``GameDefines`` for this trial —
        passed to ``step()`` on every tick.
    :param seed: RNG seed for this trial. Threaded onto the scenario's
        ``SimulationConfig.rng_seed`` (Constitution III.7). Stochastic
        Systems resolve their RNG via
        :func:`babylon.kernel.system_base.resolve_rng`, which reads
        ``services.rng`` (never populated on this path, same as the
        headless backend) with a tick-derived fallback — never the
        process-global ``random`` module either way.
    :param max_ticks: Maximum ticks to run before declaring survival.
    :param scenario: One of ``"imperial_circuit"`` or ``"two_node"``.
    :returns: Backend-normalized :class:`Result`.
    """
    from babylon.engine.headless_runner.runner import _defines_hash
    from babylon.engine.simulation_engine import step

    state, sim_config, _base_defines = _build_scenario(scenario)
    sim_config = sim_config.model_copy(update={"rng_seed": seed})
    persistent_context: dict[str, Any] = {}

    phase_milestones: dict[str, int | None] = dict.fromkeys(_MILESTONE_EVENT_TYPES)
    terminal_outcome: str | None = None
    max_tension = _max_exploitation_tension(state)
    ticks_survived = 0
    died = False

    for tick in range(1, max_ticks + 1):
        state = step(state, sim_config, persistent_context, defines)
        ticks_survived = tick
        max_tension = max(max_tension, _max_exploitation_tension(state))
        terminal_outcome = _scan_tick_events(state.events, phase_milestones, terminal_outcome)

        periphery_worker = state.entities.get(PERIPHERY_WORKER_ID)
        if periphery_worker is not None and not periphery_worker.active:
            died = True
            break

    return Result(
        ticks_survived=ticks_survived,
        outcome="DIED" if died else "SURVIVED",
        max_tension=max_tension,
        final_wealth=sum(float(e.wealth) for e in state.entities.values()),
        phase_milestones=phase_milestones,
        terminal_outcome=terminal_outcome,
        defines_hash=_defines_hash(defines),
        rng_seed=seed,
        backend="in_memory",
        extra={"scenario": scenario},
    )


__all__ = ["run_in_memory"]
