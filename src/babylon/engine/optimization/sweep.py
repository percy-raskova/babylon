"""1D range sweeps and 2D grid/landscape sweeps over :class:`GameDefines`.

Migrates the sweep algorithms previously duplicated across three tools onto
the optimization package core (:mod:`.params`, :mod:`.ranges`,
:mod:`.objectives`, :mod:`.runner_api`, :mod:`.backends.types`,
:mod:`.reproducibility`):

* ``tools/parameter_analysis.py`` (the ``sweep`` subcommand) — 1D sweep +
  summary CSV.
* ``tools/tune_parameters.py`` — 1D sweep + the "Playable Boundary" report
  (the highest swept value at which the periphery still survives at least
  ``_PLAYABLE_BOUNDARY_TARGET_TICKS`` ticks).
* ``tools/landscape_analysis.py`` — 2D grid sweep + matrix CSV.

The three tools' overlapping helpers (``parse_param_arg``, three
slightly-different ``start:end:step`` parsers, three copies of the
parameter-injection loop) are retired here in favor of the shared
:mod:`.ranges` grammar and :func:`~babylon.engine.optimization.runner_api.run`.
No argparse lives in this module — :func:`run_sweep` is the plain callable
entry point a future ``__main__`` CLI dispatches to.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict

from babylon.config.defines import GameDefines
from babylon.engine.optimization import ranges
from babylon.engine.optimization.backends.types import Result
from babylon.engine.optimization.objectives import Objective, carceral_objective
from babylon.engine.optimization.params import get_tunable_parameters, inject_parameter
from babylon.engine.optimization.reproducibility import ReproRecord, build_repro_record
from babylon.engine.optimization.runner_api import run as run_trial

#: Default simulation length for a 1D sweep point: 5200 ticks = 100 years
#: (1 tick = 1 week). Matches ``tools/shared.py::DEFAULT_MAX_TICKS`` — the
#: default both ``tools/parameter_analysis.py`` and ``tools/tune_parameters.py``
#: ultimately ran against.
DEFAULT_MAX_TICKS_1D: Final[int] = 5200

#: Default simulation length for a 2D grid cell: 52 ticks = 1 year.
#: Matches ``tools/landscape_analysis.py::DEFAULT_MAX_TICKS`` — grid sweeps
#: run ``len(values1) * len(values2)`` trials, so the per-cell budget is
#: deliberately far smaller than the 1D default.
DEFAULT_MAX_TICKS_2D: Final[int] = 52

#: Minimum ``ticks_survived`` for a swept value to count toward the
#: "Playable Boundary" (``tools/tune_parameters.py::format_results``).
_PLAYABLE_BOUNDARY_TARGET_TICKS: Final[int] = 25


class SweepPoint(BaseModel):
    """One 1D- or 2D-sweep sample: the swept value(s) plus its trial outcome.

    :ivar value: The swept value for a 1D sweep, or the first parameter's
        value for a 2D sweep (row coordinate).
    :ivar value2: The second parameter's value for a 2D sweep (column
        coordinate); ``None`` for a 1D sweep.
    :ivar result: The trial's normalized :class:`Result`.
    :ivar repro: The trial's :class:`ReproRecord` (replay receipt).
    :ivar score: The configured :class:`Objective`'s score for this trial.
    """

    model_config = ConfigDict(frozen=True)

    value: float
    value2: float | None
    result: Result
    repro: ReproRecord
    score: float


def _validate_param_path(param_path: str) -> None:
    """Fail fast if ``param_path`` is not a known tunable parameter.

    :param param_path: Dot-separated path like ``"economy.extraction_efficiency"``.
    :raises ValueError: If ``param_path`` is not in
        :func:`~babylon.engine.optimization.params.get_tunable_parameters`.
    """
    if param_path not in get_tunable_parameters():
        raise ValueError(
            f"{param_path!r} is not a known tunable parameter "
            "(see babylon.engine.optimization.params.get_tunable_parameters)"
        )


def _scope_label(backend: str, scope_name: str, scenario: str) -> str:
    """Pick the repro-record scope label matching what the backend actually used.

    :param backend: ``"headless"`` or ``"in_memory"``.
    :param scope_name: The headless scope label (ignored for ``in_memory``).
    :param scenario: The in-memory scenario name (ignored for ``headless``).
    :returns: Whichever label the selected backend actually consumed.
    """
    return scope_name if backend == "headless" else scenario


def sweep_1d(
    param_path: str,
    values: Sequence[float],
    *,
    max_ticks: int = DEFAULT_MAX_TICKS_1D,
    seed: int = 2010,
    backend: str = "headless",
    scope_name: str = "detroit-tri-county",
    scenario: str = "imperial_circuit",
    base_defines: GameDefines | None = None,
    objective: Objective = carceral_objective,
    validate: bool = True,
) -> list[SweepPoint]:
    """Sweep one parameter across ``values``, one trial per value.

    Migrated from ``tools/tune_parameters.py::run_sweep`` and
    ``tools/parameter_analysis.py::run_sweep`` — same one-trial-per-value
    loop, now dispatched through
    :func:`~babylon.engine.optimization.runner_api.run` instead of
    ``tools/shared.py::run_simulation``, with an :class:`Objective` score
    and a :class:`ReproRecord` attached to every sample.

    :param param_path: Dot-separated parameter path, e.g.
        ``"economy.extraction_efficiency"``.
    :param values: The values to inject, in order (see
        :func:`~babylon.engine.optimization.ranges.expand_range` to build
        this from a ``start:end:step`` spec).
    :param max_ticks: Maximum ticks per trial.
    :param seed: RNG seed threaded through every trial (Constitution III.7
        — every trial in the sweep uses the *same* seed, so any survival
        difference is attributable to the swept parameter, not noise).
    :param backend: ``"headless"`` or ``"in_memory"`` — forwarded to
        :func:`~babylon.engine.optimization.runner_api.run`.
    :param scope_name: Headless scope label. ``backend="headless"`` only.
    :param scenario: In-memory scenario name. ``backend="in_memory"`` only.
    :param base_defines: Base ``GameDefines`` to inject ``param_path`` into
        for each trial. Defaults to ``GameDefines()``.
    :param objective: Scores each trial's :class:`Result` into
        ``SweepPoint.score``.
    :param validate: If ``True`` (default), fail fast when ``param_path``
        is not a known tunable parameter, before running any trial.
    :returns: One :class:`SweepPoint` per value in ``values``, in order.
    :raises ValueError: If ``validate`` and ``param_path`` is unknown, or if
        ``param_path`` is invalid (propagated from
        :func:`~babylon.engine.optimization.params.inject_parameter`).
    """
    if validate:
        _validate_param_path(param_path)

    base = base_defines if base_defines is not None else GameDefines()
    scope_label = _scope_label(backend, scope_name, scenario)

    points: list[SweepPoint] = []
    for value in values:
        defines = inject_parameter(base, param_path, value)
        result = run_trial(
            defines,
            seed=seed,
            max_ticks=max_ticks,
            backend=backend,
            scope_name=scope_name,
            scenario=scenario,
        )
        repro = build_repro_record(result, scope_name=scope_label, max_ticks=max_ticks)
        points.append(
            SweepPoint(
                value=value,
                value2=None,
                result=result,
                repro=repro,
                score=objective(result),
            )
        )
    return points


def sweep_2d(
    param1: str,
    values1: Sequence[float],
    param2: str,
    values2: Sequence[float],
    *,
    max_ticks: int = DEFAULT_MAX_TICKS_2D,
    seed: int = 2010,
    backend: str = "headless",
    scope_name: str = "detroit-tri-county",
    scenario: str = "imperial_circuit",
    base_defines: GameDefines | None = None,
    objective: Objective = carceral_objective,
    validate: bool = True,
    progress: bool = True,
) -> list[list[SweepPoint]]:
    """Grid-sweep two parameters, one trial per ``(v1, v2)`` cell.

    Migrated from ``tools/landscape_analysis.py::run_landscape_sweep`` — same
    nested loop (``values1`` rows x ``values2`` columns), now dispatched
    through :func:`~babylon.engine.optimization.runner_api.run`.

    :param param1: First (row) parameter path.
    :param values1: Row values.
    :param param2: Second (column) parameter path.
    :param values2: Column values.
    :param max_ticks: Maximum ticks per trial. Defaults far lower than
        :func:`sweep_1d` (``52`` vs ``5200``) because a grid runs
        ``len(values1) * len(values2)`` trials.
    :param seed: RNG seed threaded through every trial.
    :param backend: ``"headless"`` or ``"in_memory"``.
    :param scope_name: Headless scope label. ``backend="headless"`` only.
    :param scenario: In-memory scenario name. ``backend="in_memory"`` only.
    :param base_defines: Base ``GameDefines`` both parameters are injected
        into. Defaults to ``GameDefines()``.
    :param objective: Scores each trial's :class:`Result` into
        ``SweepPoint.score``.
    :param validate: If ``True`` (default), fail fast when either parameter
        path is not a known tunable parameter.
    :param progress: If ``True`` (default), print a ``\\r``-updating
        progress line per cell (matches the original tool's console output).
    :returns: ``values1``-major, ``values2``-minor matrix of
        :class:`SweepPoint` — ``matrix[i][j]`` is the trial for
        ``(values1[i], values2[j])``.
    :raises ValueError: If ``validate`` and either parameter path is
        unknown, or if either path is invalid.
    """
    if validate:
        _validate_param_path(param1)
        _validate_param_path(param2)

    base = base_defines if base_defines is not None else GameDefines()
    scope_label = _scope_label(backend, scope_name, scenario)
    total_runs = len(values1) * len(values2)
    run_count = 0

    matrix: list[list[SweepPoint]] = []
    for v1 in values1:
        row: list[SweepPoint] = []
        for v2 in values2:
            run_count += 1
            defines = inject_parameter(base, param1, v1)
            defines = inject_parameter(defines, param2, v2)
            result = run_trial(
                defines,
                seed=seed,
                max_ticks=max_ticks,
                backend=backend,
                scope_name=scope_name,
                scenario=scenario,
            )
            repro = build_repro_record(result, scope_name=scope_label, max_ticks=max_ticks)
            row.append(
                SweepPoint(
                    value=v1,
                    value2=v2,
                    result=result,
                    repro=repro,
                    score=objective(result),
                )
            )
            if progress:
                print(
                    f"\r[{run_count}/{total_runs}] "
                    f"{param1}={v1:.3f}, {param2}={v2:.3f} -> {result.ticks_survived} ticks",
                    end="",
                    flush=True,
                )
        matrix.append(row)

    if progress:
        print()  # Newline after the last progress update.
    return matrix


def format_sweep_report(
    param_path: str,
    points: Sequence[SweepPoint],
    *,
    target_ticks: int = _PLAYABLE_BOUNDARY_TARGET_TICKS,
) -> str:
    """Render the "Playable Boundary" report table for a 1D sweep.

    Migrated verbatim (algorithm-wise) from
    ``tools/tune_parameters.py::format_results``: the boundary is the
    *highest* swept value at which the run still survives at least
    ``target_ticks`` — i.e. the most extreme coefficient before the game
    becomes unwinnable.

    :param param_path: The swept parameter's path (for the report header).
    :param points: The sweep's :class:`SweepPoint` list, in swept order.
    :param target_ticks: Minimum ``ticks_survived`` to count as "playable".
    :returns: Multi-line report string suitable for console output.
    """
    lines = [
        "",
        "=" * 70,
        "PARAMETER SWEEP RESULTS",
        "=" * 70,
        "",
        f"Parameter: {param_path}",
        f"{'Value':>10} | {'Ticks Survived':>15} | {'Max Tension':>12} | {'Outcome':>10}",
        "-" * 70,
    ]

    for point in points:
        lines.append(
            f"{point.value:>10.4f} | "
            f"{point.result.ticks_survived:>15} | "
            f"{point.result.max_tension:>12.4f} | "
            f"{point.result.outcome:>10}"
        )

    lines.append("-" * 70)
    lines.append("")

    survived_count = sum(1 for p in points if p.result.outcome == "SURVIVED")
    died_count = sum(1 for p in points if p.result.outcome == "DIED")
    lines.append(f"Summary: {survived_count} survived, {died_count} died out of {len(points)} runs")

    boundary_points = [p for p in points if p.result.ticks_survived >= target_ticks]
    if boundary_points:
        highest_surviving = max(boundary_points, key=lambda p: p.value)
        lines.append(
            f"Playable Boundary: {param_path} <= {highest_surviving.value:.4f} "
            f"(survives {highest_surviving.result.ticks_survived} ticks)"
        )
    else:
        lines.append(f"No parameter value found where periphery survives >= {target_ticks} ticks")

    lines.append("")
    return "\n".join(lines)


def write_sweep_csv(points: Sequence[SweepPoint], output_path: Path) -> None:
    """Write a 1D sweep's per-value summary CSV.

    Migrated from ``tools/parameter_analysis.py::write_csv`` /
    ``extract_sweep_summary``: one row per swept value, columns
    alphabetically sorted (``final_wealth``, ``max_tension``, ``outcome``,
    ``score``, ``ticks_survived``, ``value``) — the original tool's
    ``sorted(all_keys)`` behavior, extended with the ``score`` column this
    module adds from the configured :class:`Objective`.

    :param points: The sweep's :class:`SweepPoint` list.
    :param output_path: Destination CSV path; parent directories are created.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = [
        {
            "value": p.value,
            "ticks_survived": p.result.ticks_survived,
            "outcome": p.result.outcome,
            "max_tension": p.result.max_tension,
            "final_wealth": p.result.final_wealth,
            "score": p.score,
        }
        for p in points
    ]
    if not rows:
        with open(output_path, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=["value"]).writeheader()
        return
    fieldnames = sorted(rows[0].keys())
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_landscape_csv(
    param1: str,
    values1: Sequence[float],
    param2: str,
    values2: Sequence[float],
    matrix: Sequence[Sequence[SweepPoint]],
    output_path: Path,
) -> None:
    """Write a 2D sweep's matrix CSV: rows=``param1``, cols=``param2``, cells=ticks survived.

    Migrated verbatim from ``tools/landscape_analysis.py::write_matrix_csv``.

    :param param1: Row parameter's path (for the corner-cell label).
    :param values1: Row values, matching ``matrix``'s outer dimension.
    :param param2: Column parameter's path (for the corner-cell label).
    :param values2: Column values, matching ``matrix``'s inner dimension.
    :param matrix: ``sweep_2d``'s output.
    :param output_path: Destination CSV path; parent directories are created.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        header = [f"{param1}\\{param2}"] + [f"{v:.4f}" for v in values2]
        writer.writerow(header)
        for i, v1 in enumerate(values1):
            row_data = [f"{v1:.4f}"] + [str(cell.result.ticks_survived) for cell in matrix[i]]
            writer.writerow(row_data)


def run_sweep(
    *,
    param: str,
    param2: str | None = None,
    max_ticks: int | None = None,
    seed: int = 2010,
    backend: str = "headless",
    scope_name: str = "detroit-tri-county",
    scenario: str = "imperial_circuit",
    base_defines: GameDefines | None = None,
    objective: Objective = carceral_objective,
    output_csv: Path | None = None,
    report: bool = False,
) -> list[SweepPoint] | list[list[SweepPoint]]:
    """Dispatch to :func:`sweep_1d` or :func:`sweep_2d` from one CLI-facing call.

    The single entry point a future ``__main__`` CLI calls: it does the
    ``param``/``param2`` grammar parsing (via
    :func:`~babylon.engine.optimization.ranges.parse_range`) and picks 1D vs
    2D by whether ``param2`` was given, so the CLI layer stays a thin
    argument-collecting shim with no algorithm logic of its own.

    :param param: First (or only) swept parameter as
        ``"category.field=start:end:step"``.
    :param param2: Second swept parameter, same grammar. If given, dispatches
        to :func:`sweep_2d`; if ``None``, dispatches to :func:`sweep_1d`.
    :param max_ticks: Maximum ticks per trial. Defaults to
        :data:`DEFAULT_MAX_TICKS_1D` for a 1D sweep or
        :data:`DEFAULT_MAX_TICKS_2D` for a 2D sweep when ``None``.
    :param seed: RNG seed threaded through every trial.
    :param backend: ``"headless"`` or ``"in_memory"``.
    :param scope_name: Headless scope label. ``backend="headless"`` only.
    :param scenario: In-memory scenario name. ``backend="in_memory"`` only.
    :param base_defines: Base ``GameDefines`` to inject swept values into.
    :param objective: Scores each trial's :class:`Result`.
    :param output_csv: If given, writes the sweep's CSV artifact here (1D:
        :func:`write_sweep_csv`; 2D: :func:`write_landscape_csv`).
    :param report: If ``True``, prints :func:`format_sweep_report` after a
        1D sweep (ignored for a 2D sweep, which has no Playable Boundary
        concept).
    :returns: :func:`sweep_1d`'s or :func:`sweep_2d`'s result, so the caller
        can inspect trials beyond what was written to ``output_csv``.
    :raises ValueError: Propagated from :func:`~babylon.engine.optimization.ranges.parse_range`
        or from parameter validation in :func:`sweep_1d`/:func:`sweep_2d`.
    """
    param1_path, values1 = ranges.parse_range(param)

    if param2 is None:
        resolved_ticks = max_ticks if max_ticks is not None else DEFAULT_MAX_TICKS_1D
        points_1d = sweep_1d(
            param1_path,
            values1,
            max_ticks=resolved_ticks,
            seed=seed,
            backend=backend,
            scope_name=scope_name,
            scenario=scenario,
            base_defines=base_defines,
            objective=objective,
        )
        if output_csv is not None:
            write_sweep_csv(points_1d, output_csv)
        if report:
            print(format_sweep_report(param1_path, points_1d))
        return points_1d

    param2_path, values2 = ranges.parse_range(param2)
    resolved_ticks_2d = max_ticks if max_ticks is not None else DEFAULT_MAX_TICKS_2D
    matrix = sweep_2d(
        param1_path,
        values1,
        param2_path,
        values2,
        max_ticks=resolved_ticks_2d,
        seed=seed,
        backend=backend,
        scope_name=scope_name,
        scenario=scenario,
        base_defines=base_defines,
        objective=objective,
    )
    if output_csv is not None:
        write_landscape_csv(param1_path, values1, param2_path, values2, matrix, output_csv)
    return matrix


__all__ = [
    "DEFAULT_MAX_TICKS_1D",
    "DEFAULT_MAX_TICKS_2D",
    "SweepPoint",
    "sweep_1d",
    "sweep_2d",
    "format_sweep_report",
    "write_sweep_csv",
    "write_landscape_csv",
    "run_sweep",
]
