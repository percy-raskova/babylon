"""Development-only parameter sweeps over the frozen Python reference simulation.

Provides sweep algorithms on the development-only analysis package core
(:mod:`.params`, :mod:`.ranges`,
:mod:`.objectives`, :mod:`.runner_api`, :mod:`.backends.types`,
:mod:`.reproducibility`). It supports a 1D summary, a sampled-playability
report, and a 2D landscape matrix through one shared range grammar.
No argparse lives in this module — :func:`run_sweep` is the plain callable
entry point the package CLI dispatches to.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from tools.devtools.sim_analysis import ranges
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.objectives import Objective, carceral_objective
from tools.devtools.sim_analysis.params import (
    ParameterValue,
    get_tunable_parameters,
    inject_parameter,
)
from tools.devtools.sim_analysis.reproducibility import ReproRecord, build_repro_record
from tools.devtools.sim_analysis.runner_api import run as run_trial

from babylon.config.defines import GameDefines, canonical_defines_hash

#: Default simulation length for a 1D sweep point: 5200 ticks = 100 years
#: (1 tick = 1 week). This is the canonical long-horizon default for the
#: retained in-memory optimizer.
DEFAULT_MAX_TICKS_1D: Final[int] = 5200

#: Default simulation length for a 2D grid cell: 52 ticks = 1 year.
#: Grid sweeps run ``len(values1) * len(values2)`` trials, so the per-cell
#: budget is deliberately far smaller than the 1D default.
DEFAULT_MAX_TICKS_2D: Final[int] = 52

#: Hard ceiling for one sweep invocation. This matches the sensitivity
#: runner's global-analysis ceiling and prevents two individually valid
#: million-point ranges from producing a catastrophic Cartesian product.
MAX_SWEEP_EVALUATIONS: Final[int] = 2048

#: Upper bound on aggregate simulated ticks in one sweep. Evaluation count
#: alone is insufficient when callers can also choose an arbitrary horizon.
MAX_SWEEP_TICK_EVALUATIONS: Final[int] = 5_000_000

#: Minimum ``ticks_survived`` for a swept value to count as a sampled survivor.
_PLAYABLE_BOUNDARY_TARGET_TICKS: Final[int] = 25


class SweepPoint(BaseModel):
    """One 1D- or 2D-sweep sample: the swept value(s) plus its trial outcome.

    :ivar value: The swept value for a 1D sweep, or the first parameter's
        value for a 2D sweep (row coordinate).
    :ivar value2: The second parameter's value for a 2D sweep (column
        coordinate); ``None`` for a 1D sweep.
    :ivar result: The trial's normalized :class:`Result`.
    :ivar repro: The trial's :class:`ReproRecord` (verification receipt).
    :ivar score: The configured :class:`Objective`'s score for this trial.
    """

    model_config = ConfigDict(frozen=True, strict=True, allow_inf_nan=False)

    value: ParameterValue
    value2: ParameterValue | None
    result: Result
    repro: ReproRecord
    score: float

    @model_validator(mode="after")
    def validate_result_receipt_alignment(self) -> Self:
        """Reject non-finite results and receipts that describe another trial."""
        _validate_point_result_receipt(self)
        return self


class SweepManifest1D(BaseModel):
    """Versioned replay-input artifact for a one-dimensional sweep."""

    model_config = ConfigDict(frozen=True, strict=True, allow_inf_nan=False)

    schema_id: Literal["babylon.sim-analysis.sweep-1d.v1"] = Field(
        default="babylon.sim-analysis.sweep-1d.v1",
        alias="schema",
    )
    base_defines: GameDefines
    base_defines_hash: str
    parameter_path: str
    values: tuple[ParameterValue, ...]
    seed: int
    backend: str
    scenario: str
    max_ticks: int = Field(ge=1)
    objective: str
    points: tuple[SweepPoint, ...]

    @model_validator(mode="after")
    def validate_replay_inputs(self) -> Self:
        """Bind each ordered point to the retained base coefficient payload."""
        base = self.base_defines
        _validate_run_config(
            max_ticks=self.max_ticks,
            seed=self.seed,
            backend=self.backend,
            scenario=self.scenario,
        )
        _validate_sweep_workload(len(self.values), max_ticks=self.max_ticks)
        if not self.objective.strip():
            raise ValueError("objective identity must not be empty")
        if canonical_defines_hash(base) != self.base_defines_hash:
            raise ValueError("base_defines_hash does not match the retained base_defines payload")
        if len(self.values) != len(self.points):
            raise ValueError("1D sweep values and points must have identical lengths")
        if not self.points:
            raise ValueError("1D sweep manifests require at least one point")
        for value, point in zip(self.values, self.points, strict=True):
            _validate_manifest_point(
                point,
                expected_value=value,
                expected_value2=None,
                expected_defines=inject_parameter(base, self.parameter_path, value),
                seed=self.seed,
                backend=self.backend,
                scenario=self.scenario,
                max_ticks=self.max_ticks,
            )
        return self


class SweepManifest2D(BaseModel):
    """Versioned replay-input artifact for a two-dimensional grid sweep."""

    model_config = ConfigDict(frozen=True, strict=True, allow_inf_nan=False)

    schema_id: Literal["babylon.sim-analysis.sweep-2d.v1"] = Field(
        default="babylon.sim-analysis.sweep-2d.v1",
        alias="schema",
    )
    base_defines: GameDefines
    base_defines_hash: str
    parameter1_path: str
    values1: tuple[ParameterValue, ...]
    parameter2_path: str
    values2: tuple[ParameterValue, ...]
    seed: int
    backend: str
    scenario: str
    max_ticks: int = Field(ge=1)
    objective: str
    matrix: tuple[tuple[SweepPoint, ...], ...]

    @model_validator(mode="after")
    def validate_replay_inputs(self) -> Self:
        """Bind every matrix coordinate to its retained coefficient inputs."""
        base = self.base_defines
        if self.parameter1_path == self.parameter2_path:
            raise ValueError("2D sweep parameter paths must be distinct")
        _validate_run_config(
            max_ticks=self.max_ticks,
            seed=self.seed,
            backend=self.backend,
            scenario=self.scenario,
        )
        _validate_sweep_workload(
            len(self.values1) * len(self.values2),
            max_ticks=self.max_ticks,
        )
        if not self.objective.strip():
            raise ValueError("objective identity must not be empty")
        if canonical_defines_hash(base) != self.base_defines_hash:
            raise ValueError("base_defines_hash does not match the retained base_defines payload")
        if len(self.values1) != len(self.matrix):
            raise ValueError("2D sweep values1 and matrix rows must have identical lengths")
        if not self.values1 or not self.values2:
            raise ValueError("2D sweep manifests require a non-empty grid")
        for value1, row in zip(self.values1, self.matrix, strict=True):
            if len(self.values2) != len(row):
                raise ValueError("every 2D sweep matrix row must align with values2")
            for value2, point in zip(self.values2, row, strict=True):
                defines = inject_parameter(base, self.parameter1_path, value1)
                defines = inject_parameter(defines, self.parameter2_path, value2)
                _validate_manifest_point(
                    point,
                    expected_value=value1,
                    expected_value2=value2,
                    expected_defines=defines,
                    seed=self.seed,
                    backend=self.backend,
                    scenario=self.scenario,
                    max_ticks=self.max_ticks,
                )
        return self


def _same_parameter_value(left: ParameterValue, right: ParameterValue) -> bool:
    """Compare value and native numeric type (``1`` is not replay-equal to ``1.0``)."""
    return type(left) is type(right) and left == right


def _validate_point_result_receipt(point: SweepPoint) -> None:
    """Reject non-finite results and receipts that describe another trial."""
    for name, value in (
        ("result.max_tension", point.result.max_tension),
        ("result.final_wealth", point.result.final_wealth),
        ("score", point.score),
    ):
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite, got: {value!r}")

    aligned_fields = (
        ("defines_hash", point.result.defines_hash, point.repro.defines_hash),
        ("rng_seed", point.result.rng_seed, point.repro.rng_seed),
        ("backend", point.result.backend, point.repro.backend),
        ("ticks_survived", point.result.ticks_survived, point.repro.ticks_survived),
        ("outcome", point.result.outcome, point.repro.outcome),
        ("terminal_outcome", point.result.terminal_outcome, point.repro.terminal_outcome),
    )
    for name, result_value, receipt_value in aligned_fields:
        if result_value != receipt_value:
            raise ValueError(
                f"result {name} does not match its verification receipt: "
                f"{result_value!r} != {receipt_value!r}"
            )


def _validate_manifest_point(
    point: SweepPoint,
    *,
    expected_value: ParameterValue,
    expected_value2: ParameterValue | None,
    expected_defines: GameDefines,
    seed: int,
    backend: str,
    scenario: str,
    max_ticks: int,
) -> None:
    """Validate one point against its grid coordinate and run configuration."""
    _validate_point_result_receipt(point)
    if not _same_parameter_value(point.value, expected_value):
        raise ValueError("sweep point value does not align with its configured value")
    if expected_value2 is None:
        if point.value2 is not None:
            raise ValueError("1D sweep points must not have a second value")
    elif point.value2 is None or not _same_parameter_value(point.value2, expected_value2):
        raise ValueError("sweep point value2 does not align with its configured value")

    expected_hash = canonical_defines_hash(expected_defines)
    if point.result.defines_hash != expected_hash or point.repro.defines_hash != expected_hash:
        raise ValueError("sweep point hash does not match its replay-input coefficient payload")
    if point.result.rng_seed != seed or point.repro.rng_seed != seed:
        raise ValueError("sweep point seed does not match the sweep run configuration")
    if point.result.backend != backend or point.repro.backend != backend:
        raise ValueError("sweep point backend does not match the sweep run configuration")
    if point.repro.scenario != scenario:
        raise ValueError("sweep point scenario does not match the sweep run configuration")
    if point.repro.max_ticks != max_ticks:
        raise ValueError("sweep point max_ticks does not match the sweep run configuration")


def _validate_param_path(param_path: str) -> None:
    """Fail fast if ``param_path`` is not a known tunable parameter.

    :param param_path: Dot-separated path like ``"economy.extraction_efficiency"``.
    :raises ValueError: If ``param_path`` is not in
        :func:`~tools.devtools.sim_analysis.params.get_tunable_parameters`.
    """
    if param_path not in get_tunable_parameters():
        raise ValueError(
            f"{param_path!r} is not a known tunable parameter "
            "(see tools.devtools.sim_analysis.params.get_tunable_parameters)"
        )


def _validate_sweep_workload(evaluations: int, *, max_ticks: int) -> None:
    """Reject empty or accidentally unbounded sweeps before any trial starts."""
    if not 1 <= evaluations <= MAX_SWEEP_EVALUATIONS:
        raise ValueError(
            f"sweep workload must be 1..{MAX_SWEEP_EVALUATIONS} evaluations; "
            f"requested {evaluations}"
        )
    tick_evaluations = evaluations * max_ticks
    if tick_evaluations > MAX_SWEEP_TICK_EVALUATIONS:
        raise ValueError(
            "sweep workload exceeds the tick budget: "
            f"{evaluations} evaluations * {max_ticks} max_ticks = {tick_evaluations}; "
            f"limit {MAX_SWEEP_TICK_EVALUATIONS}"
        )


def _validate_run_config(*, max_ticks: int, seed: int, backend: str, scenario: str) -> None:
    """Validate shared run inputs before dispatching the first simulation."""
    if type(max_ticks) is not int or max_ticks < 1:
        raise ValueError(f"max_ticks must be a positive integer, got: {max_ticks!r}")
    if type(seed) is not int:
        raise ValueError(f"seed must be an integer, got: {seed!r}")
    if backend != "in_memory":
        raise ValueError(f"Unknown backend {backend!r}; expected 'in_memory'")
    if not scenario.strip():
        raise ValueError("scenario must not be empty")


def sweep_1d(
    param_path: str,
    values: Sequence[ParameterValue],
    *,
    max_ticks: int = DEFAULT_MAX_TICKS_1D,
    seed: int = 2010,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    base_defines: GameDefines | None = None,
    objective: Objective = carceral_objective,
    validate: bool = True,
) -> list[SweepPoint]:
    """Sweep one parameter across ``values``, one trial per value.

    Each trial uses :func:`~tools.devtools.sim_analysis.runner_api.run` and
    carries an :class:`Objective` score plus a :class:`ReproRecord`.

    :param param_path: Dot-separated parameter path, e.g.
        ``"economy.extraction_efficiency"``.
    :param values: The values to inject, in order (see
        :func:`~tools.devtools.sim_analysis.ranges.expand_range` to build
        this from a ``start:end:step`` spec).
    :param max_ticks: Maximum ticks per trial.
    :param seed: RNG seed threaded through every trial (Constitution III.7
        — every trial in the sweep uses the *same* seed, so any survival
        difference is attributable to the swept parameter, not noise).
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param base_defines: Base ``GameDefines`` to inject ``param_path`` into
        for each trial. Defaults to ``GameDefines()``.
    :param objective: Scores each trial's :class:`Result` into
        ``SweepPoint.score``.
    :param validate: If ``True`` (default), fail fast when ``param_path``
        is not a known tunable parameter, before running any trial.
    :returns: One :class:`SweepPoint` per value in ``values``, in order.
    :raises ValueError: If ``validate`` and ``param_path`` is unknown, or if
        ``param_path`` is invalid (propagated from
        :func:`~tools.devtools.sim_analysis.params.inject_parameter`).
    """
    if validate:
        _validate_param_path(param_path)
    _validate_run_config(max_ticks=max_ticks, seed=seed, backend=backend, scenario=scenario)
    _validate_sweep_workload(len(values), max_ticks=max_ticks)

    base = base_defines if base_defines is not None else GameDefines()
    points: list[SweepPoint] = []
    for value in values:
        defines = inject_parameter(base, param_path, value)
        result = run_trial(
            defines,
            seed=seed,
            max_ticks=max_ticks,
            backend=backend,
            scenario=scenario,
        )
        repro = build_repro_record(result, scenario=scenario, max_ticks=max_ticks)
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
    values1: Sequence[ParameterValue],
    param2: str,
    values2: Sequence[ParameterValue],
    *,
    max_ticks: int = DEFAULT_MAX_TICKS_2D,
    seed: int = 2010,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    base_defines: GameDefines | None = None,
    objective: Objective = carceral_objective,
    validate: bool = True,
    progress: bool = True,
) -> list[list[SweepPoint]]:
    """Grid-sweep two parameters, one trial per ``(v1, v2)`` cell.

    The nested loop uses ``values1`` rows and ``values2`` columns, with each
    trial dispatched through :func:`~tools.devtools.sim_analysis.runner_api.run`.

    :param param1: First (row) parameter path.
    :param values1: Row values.
    :param param2: Second (column) parameter path.
    :param values2: Column values.
    :param max_ticks: Maximum ticks per trial. Defaults far lower than
        :func:`sweep_1d` (``52`` vs ``5200``) because a grid runs
        ``len(values1) * len(values2)`` trials.
    :param seed: RNG seed threaded through every trial.
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
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
        unknown, if either path is invalid, or if both axes name the same
        parameter.
    """
    if param1 == param2:
        raise ValueError("2D sweep parameter paths must be distinct")
    if validate:
        _validate_param_path(param1)
        _validate_param_path(param2)

    total_runs = len(values1) * len(values2)
    _validate_run_config(max_ticks=max_ticks, seed=seed, backend=backend, scenario=scenario)
    _validate_sweep_workload(total_runs, max_ticks=max_ticks)

    base = base_defines if base_defines is not None else GameDefines()
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
                scenario=scenario,
            )
            repro = build_repro_record(result, scenario=scenario, max_ticks=max_ticks)
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
    """Render the sampled-playability report table for a 1D sweep.

    The report identifies the *highest sampled value* whose run survives at
    least ``target_ticks``. It deliberately does not infer a monotonic boundary:
    arbitrary parameters may produce non-monotonic responses.

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
            f"Highest sampled value meeting target: {param_path} = "
            f"{highest_surviving.value:.4f} "
            f"(survives {highest_surviving.result.ticks_survived} ticks)"
        )
    else:
        lines.append(f"No parameter value found where periphery survives >= {target_ticks} ticks")

    lines.append("")
    return "\n".join(lines)


def write_sweep_csv(points: Sequence[SweepPoint], output_path: Path) -> None:
    """Write a 1D sweep's per-value summary CSV.

    Writes one row per swept value, with alphabetically sorted columns:
    ``defines_hash``, ``final_wealth``, ``max_tension``, ``outcome``,
    ``rng_seed``, ``score``, ``terminal_outcome``, ``ticks_survived``, and
    ``value``. The hash and seed make the CSV useful for inspection, while
    the adjacent JSON manifest remains the durable replay-input artifact.

    :param points: The sweep's :class:`SweepPoint` list.
    :param output_path: Destination CSV path; parent directories are created.
    """
    _prepare_output_file(output_path)
    rows: list[dict[str, Any]] = [
        {
            "value": p.value,
            "defines_hash": p.repro.defines_hash,
            "rng_seed": p.repro.rng_seed,
            "ticks_survived": p.result.ticks_survived,
            "outcome": p.result.outcome,
            "terminal_outcome": p.result.terminal_outcome,
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
    values1: Sequence[ParameterValue],
    param2: str,
    values2: Sequence[ParameterValue],
    matrix: Sequence[Sequence[SweepPoint]],
    output_path: Path,
) -> None:
    """Write a 2D sweep's matrix CSV: rows=``param1``, cols=``param2``, cells=ticks survived.

    :param param1: Row parameter's path (for the corner-cell label).
    :param values1: Row values, matching ``matrix``'s outer dimension.
    :param param2: Column parameter's path (for the corner-cell label).
    :param values2: Column values, matching ``matrix``'s inner dimension.
    :param matrix: ``sweep_2d``'s output.
    :param output_path: Destination CSV path; parent directories are created.
    """
    if len(values1) != len(matrix):
        raise ValueError("values1 and matrix rows must have identical lengths")
    if any(len(values2) != len(row) for row in matrix):
        raise ValueError("every matrix row must align with values2")
    _prepare_output_file(output_path)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        header = [f"{param1}\\{param2}"] + [f"{v:.4f}" for v in values2]
        writer.writerow(header)
        for i, v1 in enumerate(values1):
            row_data = [f"{v1:.4f}"] + [str(cell.result.ticks_survived) for cell in matrix[i]]
            writer.writerow(row_data)


def _objective_id(objective: Objective) -> str:
    """Return an import-oriented identity for a configured objective callable."""
    module = getattr(objective, "__module__", "<unknown>")
    qualname = getattr(objective, "__qualname__", getattr(objective, "__name__", "<unknown>"))
    return f"{module}:{qualname}"


def _prepare_output_file(output_path: Path) -> None:
    """Create an output parent while rejecting paths that name directories."""
    _validate_output_file(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)


def _validate_output_file(output_path: Path) -> None:
    """Reject an invalid output target without changing the filesystem."""
    if output_path.exists() and output_path.is_dir():
        raise ValueError(f"analysis output path is a directory: {output_path}")
    for parent in output_path.parents:
        if parent.exists():
            if not parent.is_dir():
                raise ValueError(f"analysis output parent is not a directory: {parent}")
            break


def _resolve_output_paths(
    output_csv: Path | None,
    manifest_path: Path | None,
) -> tuple[Path | None, Path | None]:
    """Resolve defaults and preflight all sweep outputs before any trial."""
    resolved_manifest = manifest_path
    if resolved_manifest is None and output_csv is not None:
        try:
            resolved_manifest = output_csv.with_suffix(".manifest.json")
        except ValueError as exc:
            raise ValueError(f"cannot derive manifest path from CSV path: {output_csv}") from exc

    output_paths = [path for path in (output_csv, resolved_manifest) if path is not None]
    canonical_paths = [path.resolve() for path in output_paths]
    if len(set(canonical_paths)) != len(canonical_paths):
        raise ValueError("sweep CSV and manifest output paths must be distinct")
    for index, left in enumerate(canonical_paths):
        for right in canonical_paths[index + 1 :]:
            if left in right.parents or right in left.parents:
                raise ValueError("sweep output paths must not contain one another")
    for output_path in output_paths:
        _validate_output_file(output_path)
    return output_csv, resolved_manifest


def _write_strict_manifest(
    manifest: SweepManifest1D | SweepManifest2D,
    output_path: Path,
) -> None:
    """Serialize one validated manifest as standards-compliant JSON."""
    _prepare_output_file(output_path)
    payload = json.dumps(
        manifest.model_dump(mode="json", by_alias=True),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
    output_path.write_text(f"{payload}\n", encoding="utf-8")


def write_sweep_manifest_1d(
    *,
    base_defines: GameDefines,
    param_path: str,
    values: Sequence[ParameterValue],
    seed: int,
    backend: str,
    scenario: str,
    max_ticks: int,
    objective: Objective,
    points: Sequence[SweepPoint],
    output_path: Path,
) -> None:
    """Write a strict, versioned replay-input manifest for a 1D sweep."""
    manifest = SweepManifest1D(
        base_defines=base_defines,
        base_defines_hash=canonical_defines_hash(base_defines),
        parameter_path=param_path,
        values=tuple(values),
        seed=seed,
        backend=backend,
        scenario=scenario,
        max_ticks=max_ticks,
        objective=_objective_id(objective),
        points=tuple(points),
    )
    _write_strict_manifest(manifest, output_path)


def write_sweep_manifest_2d(
    *,
    base_defines: GameDefines,
    param1: str,
    values1: Sequence[ParameterValue],
    param2: str,
    values2: Sequence[ParameterValue],
    seed: int,
    backend: str,
    scenario: str,
    max_ticks: int,
    objective: Objective,
    matrix: Sequence[Sequence[SweepPoint]],
    output_path: Path,
) -> None:
    """Write a strict, versioned replay-input manifest for a 2D sweep."""
    manifest = SweepManifest2D(
        base_defines=base_defines,
        base_defines_hash=canonical_defines_hash(base_defines),
        parameter1_path=param1,
        values1=tuple(values1),
        parameter2_path=param2,
        values2=tuple(values2),
        seed=seed,
        backend=backend,
        scenario=scenario,
        max_ticks=max_ticks,
        objective=_objective_id(objective),
        matrix=tuple(tuple(row) for row in matrix),
    )
    _write_strict_manifest(manifest, output_path)


def run_sweep(
    *,
    param: str,
    param2: str | None = None,
    max_ticks: int | None = None,
    seed: int = 2010,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    base_defines: GameDefines | None = None,
    objective: Objective = carceral_objective,
    output_csv: Path | None = None,
    manifest_path: Path | None = None,
    report: bool = False,
) -> list[SweepPoint] | list[list[SweepPoint]]:
    """Dispatch to :func:`sweep_1d` or :func:`sweep_2d` from one CLI-facing call.

    The single entry point a future ``__main__`` CLI calls: it does the
    ``param``/``param2`` grammar parsing (via
    :func:`~tools.devtools.sim_analysis.ranges.parse_range`) and picks 1D vs
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
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param base_defines: Base ``GameDefines`` to inject swept values into.
    :param objective: Scores each trial's :class:`Result`.
    :param output_csv: If given, writes the sweep's CSV artifact here (1D:
        :func:`write_sweep_csv`; 2D: :func:`write_landscape_csv`).
    :param manifest_path: Replay-input JSON artifact path. When omitted and
        ``output_csv`` is present, defaults to the CSV path with a
        ``.manifest.json`` suffix. May be supplied without a CSV for a
        manifest-only run.
    :param report: If ``True``, prints :func:`format_sweep_report` after a
        1D sweep (ignored for a 2D sweep, which has no sampled-playability
        report).
    :returns: :func:`sweep_1d`'s or :func:`sweep_2d`'s result, so the caller
        can inspect trials beyond what was written to ``output_csv``.
    :raises ValueError: Propagated from :func:`~tools.devtools.sim_analysis.ranges.parse_range`
        or from parameter validation in :func:`sweep_1d`/:func:`sweep_2d`.
    """
    resolved_csv, resolved_manifest = _resolve_output_paths(output_csv, manifest_path)
    param1_path, values1 = ranges.parse_range(param)
    base = base_defines if base_defines is not None else GameDefines()

    if param2 is None:
        resolved_ticks = max_ticks if max_ticks is not None else DEFAULT_MAX_TICKS_1D
        points_1d = sweep_1d(
            param1_path,
            values1,
            max_ticks=resolved_ticks,
            seed=seed,
            backend=backend,
            scenario=scenario,
            base_defines=base,
            objective=objective,
        )
        if resolved_csv is not None:
            write_sweep_csv(points_1d, resolved_csv)
        if resolved_manifest is not None:
            write_sweep_manifest_1d(
                base_defines=base,
                param_path=param1_path,
                values=values1,
                seed=seed,
                backend=backend,
                scenario=scenario,
                max_ticks=resolved_ticks,
                objective=objective,
                points=points_1d,
                output_path=resolved_manifest,
            )
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
        scenario=scenario,
        base_defines=base,
        objective=objective,
    )
    if resolved_csv is not None:
        write_landscape_csv(param1_path, values1, param2_path, values2, matrix, resolved_csv)
    if resolved_manifest is not None:
        write_sweep_manifest_2d(
            base_defines=base,
            param1=param1_path,
            values1=values1,
            param2=param2_path,
            values2=values2,
            seed=seed,
            backend=backend,
            scenario=scenario,
            max_ticks=resolved_ticks_2d,
            objective=objective,
            matrix=matrix,
            output_path=resolved_manifest,
        )
    return matrix


__all__ = [
    "DEFAULT_MAX_TICKS_1D",
    "DEFAULT_MAX_TICKS_2D",
    "MAX_SWEEP_EVALUATIONS",
    "MAX_SWEEP_TICK_EVALUATIONS",
    "SweepPoint",
    "SweepManifest1D",
    "SweepManifest2D",
    "sweep_1d",
    "sweep_2d",
    "format_sweep_report",
    "write_sweep_csv",
    "write_landscape_csv",
    "write_sweep_manifest_1d",
    "write_sweep_manifest_2d",
    "run_sweep",
]
