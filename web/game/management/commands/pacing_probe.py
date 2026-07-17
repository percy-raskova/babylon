"""Management command: headless null-play pacing probe (spec-116 Task 6).

Runs the engine's real ``step()`` loop on a chosen scenario, entirely
in-memory (no Postgres, no ``EngineBridge``, no DB writes), while an
:class:`~babylon.engine.observers.EndgameDetector` observes every tick.
This is the instrument for spec-116's DECLARED CEREMONY #1 — calibrating
the fixed-horizon campaign's pacing (when, if ever, a recognized endgame
pattern locks in under null play) against the five recognizer axes.

Usage::

    python manage.py pacing_probe --scenario us --ticks 5200 --seed 0 \\
        --report /tmp/pacing-us.json

The JSON report shape::

    {
        "scenario": "us",
        "ticks_completed": 5200,
        "first_recognition": {"revolutionary_victory": null, ...},
        "final_pattern": null,
        "axis_curves": {"revolutionary_victory": [[26, 0.1], ...], ...},
        "event_type_counts": {"surplus_extraction": 5200, ...}
    }

No wall-clock timestamp is included in the report body (Constitution
III.7 determinism) — wall-clock cost is recorded by the operator running
the probe, not by the instrument itself.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand, CommandError

from babylon.config.defines import GameDefines
from babylon.engine.observers import EndgameDetector
from babylon.engine.simulation_engine import step
from babylon.models.config import SimulationConfig

if TYPE_CHECKING:
    from babylon.models.world_state import WorldState

# The five recognizer axes — must equal EndgameDetector.axis_progress()'s key set
# (pinned by the Step 1 test's set-equality assertion).
AXES: tuple[str, ...] = (
    "revolutionary_victory",
    "ecological_collapse",
    "fascist_consolidation",
    "red_ogv",
    "fragmented_collapse",
)
SAMPLE_EVERY: int = 26  # curve sampling cadence in ticks (half a year); a reporting
# choice — numerically equal to pattern_lock_ticks by
# coincidence, deliberately NOT read from defines

_MIN_TICKS: int = 1
_MAX_TICKS: int = 10000


def _ticks_type(value: str) -> int:
    """Argparse ``type=`` validator bounding ``--ticks`` to ``[1, 10000]``.

    The bound is what makes the probe's per-tick loop provably finite
    (Power-of-10 rule 2): the loop runs ``range(1, ticks + 1)`` over this
    already-validated, statically-bounded value.

    Args:
        value: Raw ``--ticks`` string from argparse.

    Returns:
        The parsed tick count.

    Raises:
        argparse.ArgumentTypeError: If ``value`` is not an int, or falls
            outside ``[1, 10000]``.
    """
    try:
        ticks = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--ticks must be an integer, got {value!r}") from exc
    if not (_MIN_TICKS <= ticks <= _MAX_TICKS):
        raise argparse.ArgumentTypeError(
            f"--ticks must be in [{_MIN_TICKS}, {_MAX_TICKS}], got {ticks}"
        )
    return ticks


@dataclass
class ProbeResult:
    """In-memory result of one :func:`run_probe` invocation.

    Attributes:
        ticks_completed: Number of ticks actually run (equals the
            requested ``ticks`` unless the loop is changed to break early
            in the future — today it never does).
        first_recognition: Per-axis first tick at which
            ``EndgameDetector.recognized_pattern`` equaled that axis, or
            ``None`` if it never did.
        final_pattern: The recognized pattern's ``GameOutcome.value`` at
            the final tick, or ``None``.
        axis_curves: Per-axis ``[tick, progress]`` samples, taken every
            :data:`SAMPLE_EVERY` ticks (plus the final tick).
        event_counts: Histogram of ``str(event.event_type)`` across every
            tick's ``WorldState.events``.
    """

    ticks_completed: int
    first_recognition: dict[str, int | None]
    final_pattern: str | None
    axis_curves: dict[str, list[list[float]]]
    event_counts: Counter[str]


def run_probe(scenario: str, ticks: int, seed: int) -> ProbeResult:
    """Run the headless null-play probe and return its in-memory result.

    Builds the scenario's initial state via the same bridge helper the
    web session path uses (:func:`game.engine_bridge._build_initial_state_for_scenario`,
    which includes spec-070 balkanization seeding), then advances it
    ``ticks`` times with :func:`~babylon.engine.simulation_engine.step`
    while an :class:`~babylon.engine.observers.EndgameDetector` observes.
    No actions are submitted (null play) and no persistence layer is
    touched.

    Args:
        scenario: Scenario identifier or alias (resolved by
            ``_build_initial_state_for_scenario``).
        ticks: Number of ticks to run (already bounded by :func:`_ticks_type`
            when invoked via the CLI).
        seed: Deterministic RNG seed for the run's ``SimulationConfig``.

    Returns:
        The completed :class:`ProbeResult`.

    Raises:
        ValueError: If ``scenario`` does not resolve to a registered
            scenario (propagated from ``_build_initial_state_for_scenario``).
    """
    from game.engine_bridge import _build_initial_state_for_scenario

    state: WorldState = _build_initial_state_for_scenario(scenario)
    defines = GameDefines.load_default()
    sim_config = SimulationConfig(rng_seed=seed)
    detector = EndgameDetector(defines=defines)
    detector.on_simulation_start(state, sim_config)

    persistent: dict[str, Any] = {}
    first_recognition: dict[str, int | None] = dict.fromkeys(AXES)
    curves: dict[str, list[list[float]]] = {axis: [] for axis in AXES}
    event_counts: Counter[str] = Counter()
    ticks_completed = 0

    for tick in range(1, ticks + 1):
        previous = state
        state = step(state, sim_config, persistent, defines)
        detector.on_tick(previous, state)
        ticks_completed = tick

        for event in state.events:
            event_counts[str(event.event_type)] += 1

        progress = detector.axis_progress()
        pattern = detector.recognized_pattern
        if pattern is not None and first_recognition[pattern.value] is None:
            first_recognition[pattern.value] = tick

        if tick % SAMPLE_EVERY == 0 or tick == ticks:
            for axis, value in progress.items():
                curves[axis].append([tick, round(value, 4)])

    final_pattern = detector.recognized_pattern.value if detector.recognized_pattern else None
    return ProbeResult(
        ticks_completed=ticks_completed,
        first_recognition=first_recognition,
        final_pattern=final_pattern,
        axis_curves=curves,
        event_counts=event_counts,
    )


class Command(BaseCommand):
    """Headless null-play pacing probe over the web scenario path."""

    help = (
        "Run a headless null-play simulation and report EndgameDetector axis "
        "pacing (spec-116 ceremony instrument, Task 6)."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--scenario",
            type=str,
            default="us",
            help="Scenario name or alias (default: us, the spec-116 gate-1 scenario)",
        )
        parser.add_argument(
            "--ticks",
            type=_ticks_type,
            default=5200,
            help="Number of ticks to run, bounded to [1, 10000] (default: 5200 = 100 years)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=0,
            help="Deterministic RNG seed (default: 0)",
        )
        parser.add_argument(
            "--report",
            type=str,
            required=True,
            help="Path to write the JSON report to",
        )

    def handle(self, *_args: object, **options: Any) -> None:
        scenario: str = options["scenario"]
        ticks: int = options["ticks"]
        seed: int = options["seed"]
        report_path = Path(options["report"])

        try:
            result = run_probe(scenario, ticks, seed)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        report_data: dict[str, Any] = {
            "scenario": scenario,
            "ticks_completed": result.ticks_completed,
            "first_recognition": result.first_recognition,
            "final_pattern": result.final_pattern,
            "axis_curves": result.axis_curves,
            "event_type_counts": dict(result.event_counts),
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_data, indent=2, sort_keys=True))

        self._print_summary(scenario, ticks, seed, result)
        self.stdout.write(self.style.SUCCESS(f"Report written to {report_path}"))

    def _print_summary(
        self,
        scenario: str,
        ticks: int,
        seed: int,
        result: ProbeResult,
    ) -> None:
        """Print a human-readable pacing summary table to stdout.

        Args:
            scenario: Scenario identifier used for the run.
            ticks: Requested tick count.
            seed: RNG seed used for the run.
            result: The completed :class:`ProbeResult`.
        """
        self.stdout.write(
            f"Scenario: {scenario}  ticks: {result.ticks_completed}/{ticks}  seed: {seed}"
        )
        self.stdout.write(f"Final pattern: {result.final_pattern or '(none)'}")
        self.stdout.write(f"{'axis':<24}{'first_recognition':>20}{'final_progress':>16}")
        for axis in AXES:
            first = result.first_recognition[axis]
            first_str = str(first) if first is not None else "-"
            curve = result.axis_curves[axis]
            final_progress = curve[-1][1] if curve else 0.0
            self.stdout.write(f"{axis:<24}{first_str:>20}{final_progress:>16.4f}")
        top_events = result.event_counts.most_common(5)
        self.stdout.write(f"Event types: {len(result.event_counts)} distinct; top 5: {top_events}")
