"""Development-only Monte Carlo analysis of the frozen Python reference simulation.

Trials execute through :func:`tools.devtools.sim_analysis.runner_api.run`,
so the per-sample RNG seed reaches the retained in-memory simulation. The
statistical core uses a deterministic
per-sample seed sequence drawn from one base seed, mean/std/95% CI
aggregation with the scipy-optional t/z-distribution logic — is unchanged
from the original tool.

Usage (programmatic; argparse lives in the package ``__main__``, not here)::

    from tools.devtools.sim_analysis.monte_carlo import run_monte_carlo

    artifact = run_monte_carlo(n_samples=100, base_seed=42)
    print(artifact.stats.survival_rate)

See Also:
    :doc:`/ai/tooling.yaml` monte_carlo section.
"""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field
from tools.devtools.sim_analysis import runner_api
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.objectives import Objective, carceral_objective
from tools.devtools.sim_analysis.params import inject_parameters
from tools.devtools.sim_analysis.ranges import parse_override
from tools.devtools.sim_analysis.reproducibility import ReproRecord, build_repro_record

from babylon.config.defines import GameDefines, canonical_defines_hash

# Try to import scipy for t-distribution CI, fall back to normal approximation.
try:
    from scipy import stats as _scipy_stats  # type: ignore[import-untyped]

    HAS_SCIPY = True
except ImportError:  # pragma: no cover - exercised only in scipy-less envs
    _scipy_stats = None
    HAS_SCIPY = False

# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_SAMPLES: Final[int] = 100
"""Default sample count for an exploratory Monte Carlo run."""

DEFAULT_MAX_TICKS: Final[int] = 5200
"""Default simulation length: 5200 ticks = 100 years (1 tick = 1 week)."""

MAX_SAMPLES: Final[int] = 10_000
MAX_TICKS: Final[int] = 5_200
MAX_TICK_EVALUATIONS: Final[int] = 52_000_000
"""Hard preflight bounds for an explicitly requested Monte Carlo campaign."""

DEFAULT_OUTPUT: Final[str] = "results/monte_carlo.csv"
"""Default CSV output path, relative to the invoking process's cwd."""

CONFIDENCE_LEVEL: Final[float] = 0.95
"""Confidence level used for the ticks-survived interval."""

_SEED_UPPER_BOUND: Final[int] = 2**31 - 1
"""Exclusive-ish upper bound for generated per-sample seeds (fits a 32-bit signed int)."""


# =============================================================================
# DATA SHAPES
# =============================================================================


class SampleResult(BaseModel):
    """One Monte Carlo sample's outcome.

    :ivar sample_id: 1-indexed sample number within the run.
    :ivar seed: The per-sample RNG seed drawn from the base-seed sequence.
    :ivar ticks_survived: Ticks the trial completed before death or ``max_ticks``.
    :ivar outcome: ``"SURVIVED"`` or ``"DIED"``.
    :ivar max_tension: Maximum EXPLOITATION-edge tension observed.
    :ivar final_wealth: Terminal-tick wealth/value aggregate.
    :ivar objective_score: This sample's score under the run's :class:`~tools.devtools.sim_analysis.objectives.Objective`.
    """

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    sample_id: int = Field(ge=1)
    seed: int
    ticks_survived: int = Field(ge=0)
    outcome: str
    max_tension: float
    final_wealth: float
    objective_score: float


class AggregateStats(BaseModel):
    """Aggregate statistics across all samples in one Monte Carlo run."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    n_samples: int = Field(ge=1)
    n_survived: int = Field(ge=0)
    n_died: int = Field(ge=0)
    survival_rate: float

    ticks_mean: float
    ticks_std: float
    ticks_ci_lower: float
    ticks_ci_upper: float

    tension_mean: float
    tension_std: float

    wealth_mean: float
    wealth_std: float

    objective_mean: float
    objective_std: float


class MonteCarloArtifact(BaseModel):
    """Full output of one Monte Carlo run: samples, stats, and repro receipts.

    :ivar samples: Every sample's :class:`SampleResult`, in run order.
    :ivar stats: Cross-sample :class:`AggregateStats`.
    :ivar repro_records: One verification receipt per sample, in the same
        order as ``samples``. The receipt hash is intentionally
        non-invertible; ``manifest_path`` retains the full coefficient and
        run-input payload needed to replay against the same source revision.
    :ivar csv_path: Where the per-sample + summary CSV was written.
    :ivar report_path: Where the markdown report was written, or ``None`` if
        no report was requested.
    """

    model_config = ConfigDict(frozen=True)

    samples: tuple[SampleResult, ...]
    stats: AggregateStats
    repro_records: tuple[ReproRecord, ...]
    csv_path: Path
    manifest_path: Path
    report_path: Path | None = None


class MonteCarloManifest(BaseModel):
    """Durable coefficient inputs and outputs for one Monte Carlo run."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    schema_id: Literal["babylon.sim-analysis.monte-carlo.v1"] = Field(
        default="babylon.sim-analysis.monte-carlo.v1",
        alias="schema",
    )
    base_defines: dict[str, object]
    defines_hash: str
    parameter_overrides: dict[str, int | float]
    base_seed: int | None
    backend: str
    scenario: str
    max_ticks: int = Field(ge=1)
    objective: str
    samples: tuple[SampleResult, ...]
    stats: AggregateStats
    repro_records: tuple[ReproRecord, ...]


# =============================================================================
# STATISTICS
# =============================================================================


def calculate_confidence_interval(
    data: list[float],
    confidence: float = CONFIDENCE_LEVEL,
) -> tuple[float, float]:
    """Calculate a confidence interval, preferring the t-distribution.

    :param data: Sample values.
    :param confidence: Confidence level (default 0.95 for a 95% CI).
    :returns: ``(lower_bound, upper_bound)``. ``(0.0, 0.0)`` if ``len(data) < 2``.
    """
    n = len(data)
    if n < 2:
        return (0.0, 0.0)

    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    std = variance**0.5

    # Use t-distribution for small samples, fall back to z-score approximation
    # when scipy is unavailable.
    if HAS_SCIPY and _scipy_stats is not None:
        t_critical = float(_scipy_stats.t.ppf((1 + confidence) / 2, n - 1))
    else:
        t_critical = 1.96 if n > 30 else 2.0

    margin = t_critical * (std / (n**0.5))
    return (mean - margin, mean + margin)


def _mean_and_std(data: list[float]) -> tuple[float, float]:
    """Sample mean and (n-1)-denominator standard deviation.

    :param data: Non-empty list of values.
    :returns: ``(mean, std)``. ``std`` is ``0.0`` if ``len(data) < 2``.
    """
    n = len(data)
    mean = sum(data) / n
    if n < 2:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    return mean, variance**0.5


def aggregate(samples: list[SampleResult]) -> AggregateStats:
    """Reduce per-sample results to cross-sample :class:`AggregateStats`.

    :param samples: Non-empty list of :class:`SampleResult`.
    :returns: The computed :class:`AggregateStats`.
    :raises ValueError: If ``samples`` is empty.
    """
    n_samples = len(samples)
    if n_samples == 0:
        raise ValueError("aggregate() requires at least one sample")

    ticks_data = [s.ticks_survived for s in samples]
    tension_data = [s.max_tension for s in samples]
    wealth_data = [s.final_wealth for s in samples]
    objective_data = [s.objective_score for s in samples]

    n_survived = sum(1 for s in samples if s.outcome == "SURVIVED")

    ticks_mean, ticks_std = _mean_and_std([float(t) for t in ticks_data])
    tension_mean, tension_std = _mean_and_std(tension_data)
    wealth_mean, wealth_std = _mean_and_std(wealth_data)
    objective_mean, objective_std = _mean_and_std(objective_data)

    ci_lower, ci_upper = calculate_confidence_interval([float(t) for t in ticks_data])

    return AggregateStats(
        n_samples=n_samples,
        n_survived=n_survived,
        n_died=n_samples - n_survived,
        survival_rate=n_survived / n_samples,
        ticks_mean=ticks_mean,
        ticks_std=ticks_std,
        ticks_ci_lower=ci_lower,
        ticks_ci_upper=ci_upper,
        tension_mean=tension_mean,
        tension_std=tension_std,
        wealth_mean=wealth_mean,
        wealth_std=wealth_std,
        objective_mean=objective_mean,
        objective_std=objective_std,
    )


# =============================================================================
# TRIAL EXECUTION
# =============================================================================


def run_trials(
    n_samples: int,
    defines: GameDefines,
    *,
    max_ticks: int = DEFAULT_MAX_TICKS,
    base_seed: int | None = None,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    progress: bool = True,
) -> tuple[list[SampleResult], list[ReproRecord]]:
    """Run N replications sequentially through :func:`runner_api.run`.

    Per-sample seeds are drawn from a local :class:`random.Random` seeded
    with ``base_seed`` (``None`` draws from OS entropy, matching the
    original tool's "no seed given" behavior) — the same deterministic
    seed *sequence* the pre-package tool produced, but without mutating the
    process-global :mod:`random` module.

    :param n_samples: Number of samples to run.
    :param defines: Base ``GameDefines`` (already carrying any parameter
        overrides) shared across all samples; only the RNG seed varies.
    :param max_ticks: Maximum ticks per sample.
    :param base_seed: Base random seed for reproducibility (``None`` = random).
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param objective: Scoring function applied to each trial's :class:`Result`.
    :param progress: Print progress lines to stdout.
    :returns: ``(samples, repro_records)``, both in run order and the same length.
    """
    rng = random.Random(base_seed)
    samples: list[SampleResult] = []
    repro_records: list[ReproRecord] = []

    if progress:
        print(f"Running {n_samples} Monte Carlo samples...")
        print(f"  Max ticks per sample: {max_ticks}")
        print(f"  Backend: {backend}")
        if base_seed is not None:
            print(f"  Base seed: {base_seed}")
        print()

    for i in range(n_samples):
        sample_seed = rng.randint(0, _SEED_UPPER_BOUND)

        result: Result = runner_api.run(
            defines,
            seed=sample_seed,
            max_ticks=max_ticks,
            backend=backend,
            scenario=scenario,
        )

        samples.append(
            SampleResult(
                sample_id=i + 1,
                seed=sample_seed,
                ticks_survived=result.ticks_survived,
                outcome=result.outcome,
                max_tension=result.max_tension,
                final_wealth=result.final_wealth,
                objective_score=objective(result),
            )
        )
        repro_records.append(build_repro_record(result, scenario=scenario, max_ticks=max_ticks))

        if progress and ((i + 1) % max(1, n_samples // 10) == 0 or i == n_samples - 1):
            pct = 100 * (i + 1) // n_samples
            print(f"\r  [{i + 1}/{n_samples}] {pct}% complete", end="", flush=True)

    if progress:
        print()  # Newline after progress

    return samples, repro_records


# =============================================================================
# OUTPUT ARTIFACTS
# =============================================================================


def write_csv(
    samples: list[SampleResult],
    stats: AggregateStats,
    repro_records: list[ReproRecord],
    output_path: Path,
) -> None:
    """Write per-sample results + summary statistics to CSV.

    :param samples: Per-sample results.
    :param stats: Cross-sample :class:`AggregateStats`.
    :param repro_records: Verification receipts in the same order as
        ``samples``.
    :param output_path: Path to write the CSV.
    :raises ValueError: If samples and receipts do not align.
    """
    if len(samples) != len(repro_records):
        raise ValueError("samples and repro_records must have identical lengths")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(
            [
                "sample_id",
                "seed",
                "defines_hash",
                "ticks_survived",
                "outcome",
                "max_tension",
                "final_wealth",
                "objective_score",
            ]
        )

        for s, record in zip(samples, repro_records, strict=True):
            if s.seed != record.rng_seed:
                raise ValueError(
                    f"sample {s.sample_id} seed does not match its verification receipt"
                )
            writer.writerow(
                [
                    s.sample_id,
                    s.seed,
                    record.defines_hash,
                    s.ticks_survived,
                    s.outcome,
                    f"{s.max_tension:.6f}",
                    f"{s.final_wealth:.6f}",
                    f"{s.objective_score:.6f}",
                ]
            )

        writer.writerow([])  # Blank row before summary

        writer.writerow(["# Summary Statistics"])
        writer.writerow(["n_samples", stats.n_samples])
        writer.writerow(["n_survived", stats.n_survived])
        writer.writerow(["n_died", stats.n_died])
        writer.writerow(["survival_rate", f"{stats.survival_rate:.4f}"])
        writer.writerow(["ticks_mean", f"{stats.ticks_mean:.2f}"])
        writer.writerow(["ticks_std", f"{stats.ticks_std:.2f}"])
        writer.writerow(["ticks_ci_lower", f"{stats.ticks_ci_lower:.2f}"])
        writer.writerow(["ticks_ci_upper", f"{stats.ticks_ci_upper:.2f}"])
        writer.writerow(["tension_mean", f"{stats.tension_mean:.4f}"])
        writer.writerow(["tension_std", f"{stats.tension_std:.4f}"])
        writer.writerow(["wealth_mean", f"{stats.wealth_mean:.4f}"])
        writer.writerow(["wealth_std", f"{stats.wealth_std:.4f}"])
        writer.writerow(["objective_mean", f"{stats.objective_mean:.4f}"])
        writer.writerow(["objective_std", f"{stats.objective_std:.4f}"])


def _objective_id(objective: Objective) -> str:
    """Return an import-oriented identity for an objective callable."""
    module = getattr(objective, "__module__", "<unknown>")
    qualname = getattr(objective, "__qualname__", getattr(objective, "__name__", "<unknown>"))
    return f"{module}:{qualname}"


def write_manifest(
    *,
    defines: GameDefines,
    overrides: Mapping[str, int | float],
    base_seed: int | None,
    backend: str,
    scenario: str,
    max_ticks: int,
    objective: Objective,
    samples: list[SampleResult],
    stats: AggregateStats,
    repro_records: list[ReproRecord],
    output_path: Path,
) -> None:
    """Write the replay-input Monte Carlo JSON artifact.

    The full validated ``GameDefines`` payload is stored once, while each
    sample retains its exact derived seed and outcome. JSON encoding rejects
    non-finite values rather than writing the non-standard ``NaN`` or
    ``Infinity`` tokens.
    """
    if len(samples) != len(repro_records):
        raise ValueError("samples and repro_records must have identical lengths")
    if not repro_records:
        raise ValueError("Monte Carlo manifests require at least one trial receipt")
    defines_hashes = {record.defines_hash for record in repro_records}
    if len(defines_hashes) != 1:
        raise ValueError("Monte Carlo receipts must bind one coefficient snapshot")
    defines_hash = next(iter(defines_hashes))
    expected_hash = canonical_defines_hash(defines)
    if defines_hash != expected_hash:
        raise ValueError("Monte Carlo receipt hash does not match the retained defines payload")

    manifest = MonteCarloManifest(
        base_defines=defines.model_dump(mode="json"),
        defines_hash=defines_hash,
        parameter_overrides=dict(overrides),
        base_seed=base_seed,
        backend=backend,
        scenario=scenario,
        max_ticks=max_ticks,
        objective=_objective_id(objective),
        samples=tuple(samples),
        stats=stats,
        repro_records=tuple(repro_records),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        manifest.model_dump(mode="json", by_alias=True),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
    output_path.write_text(f"{payload}\n", encoding="utf-8")


def format_report(
    stats: AggregateStats,
    *,
    base_seed: int | None = None,
    backend: str = "in_memory",
) -> str:
    """Format a markdown report for one Monte Carlo run.

    :param stats: Cross-sample :class:`AggregateStats`.
    :param base_seed: Base random seed used (``None`` if not set).
    :param backend: Backend the run executed against.
    :returns: Markdown report string.
    """
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    seed_info = f"Base Seed: {base_seed}" if base_seed is not None else "Base Seed: (random)"

    ci_width = stats.ticks_ci_upper - stats.ticks_ci_lower

    return f"""# Monte Carlo Uncertainty Quantification Report

**Generated**: {timestamp}
**Samples**: {stats.n_samples}
**Backend**: {backend}
**{seed_info}**

## Survival Outcomes

| Metric | Value |
|--------|-------|
| Survived | {stats.n_survived} ({100 * stats.survival_rate:.1f}%) |
| Died | {stats.n_died} ({100 * (1 - stats.survival_rate):.1f}%) |

## Ticks Survived

| Statistic | Value |
|-----------|-------|
| Mean | {stats.ticks_mean:.2f} |
| Std Dev | {stats.ticks_std:.2f} |
| 95% CI | [{stats.ticks_ci_lower:.2f}, {stats.ticks_ci_upper:.2f}] |
| CI Width | {ci_width:.2f} |

## Secondary Metrics

| Metric | Mean | Std Dev |
|--------|------|---------|
| Max Tension | {stats.tension_mean:.4f} | {stats.tension_std:.4f} |
| Final Wealth | {stats.wealth_mean:.4f} | {stats.wealth_std:.4f} |
| Objective Score | {stats.objective_mean:.4f} | {stats.objective_std:.4f} |

## Interpretation

- **Survival Rate**: {100 * stats.survival_rate:.1f}% of simulations survived to max ticks
- **CI Width**: {ci_width:.2f} ticks (narrower = more deterministic behavior)
- **Variance Ratio**: {stats.ticks_std / max(stats.ticks_mean, 0.01):.2f} (lower = more predictable)

{"**Note**: scipy not available, using z-score approximation for CI" if not HAS_SCIPY else ""}
"""


# =============================================================================
# ENTRY POINT
# =============================================================================


def run_monte_carlo(
    *,
    n_samples: int = DEFAULT_SAMPLES,
    base_seed: int | None = None,
    defines: GameDefines | None = None,
    param_overrides: Mapping[str, float] | Iterable[str] | None = None,
    max_ticks: int = DEFAULT_MAX_TICKS,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    csv_path: Path | None = None,
    manifest_path: Path | None = None,
    report_path: Path | None = None,
    progress: bool = True,
) -> MonteCarloArtifact:
    """Run a full Monte Carlo uncertainty-quantification pass and write artifacts.

    The single entry point a CLI (or another algorithm) should call: builds
    the base ``GameDefines`` (optionally overridden), runs ``n_samples``
    trials, aggregates statistics, writes a CSV, and optionally writes a
    markdown report.

    :param n_samples: Number of simulation samples.
    :param base_seed: Base random seed for reproducibility (``None`` = random).
    :param defines: Base ``GameDefines``; ``GameDefines()`` defaults if ``None``.
    :param param_overrides: Either a ``{param_path: value}`` mapping, or an
        iterable of raw ``"category.field=value"`` override strings (as a
        CLI layer would collect from repeated ``--param`` flags) — each
        parsed via :func:`~tools.devtools.sim_analysis.ranges.parse_override`.
    :param max_ticks: Maximum ticks per sample.
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param objective: Scoring function applied to each trial's :class:`Result`
        (default: :func:`~tools.devtools.sim_analysis.objectives.carceral_objective`).
    :param csv_path: Output CSV path (default: :data:`DEFAULT_OUTPUT`).
    :param manifest_path: Replay-input JSON artifact path. Defaults to the
        CSV path with a ``.manifest.json`` suffix.
    :param report_path: Optional markdown report output path.
    :param progress: Print progress + report to stdout.
    :returns: The full :class:`MonteCarloArtifact` (samples, stats, repro
        records, and output paths).
    :raises ValueError: If a ``param_overrides`` entry is malformed (bubbled
        up from :func:`~tools.devtools.sim_analysis.ranges.parse_override`),
        or ``n_samples < 1``.
    """
    if not 1 <= n_samples <= MAX_SAMPLES:
        raise ValueError(f"n_samples must be 1..{MAX_SAMPLES}, got: {n_samples}")
    if not 1 <= max_ticks <= MAX_TICKS:
        raise ValueError(f"max_ticks must be 1..{MAX_TICKS}, got: {max_ticks}")
    tick_evaluations = n_samples * max_ticks
    if tick_evaluations > MAX_TICK_EVALUATIONS:
        raise ValueError(
            "Monte Carlo workload exceeds the tick budget: "
            f"{n_samples} samples * {max_ticks} ticks = {tick_evaluations}, "
            f"limit {MAX_TICK_EVALUATIONS}"
        )

    base_defines = defines if defines is not None else GameDefines()

    overrides: dict[str, float] = {}
    if param_overrides is not None:
        if isinstance(param_overrides, Mapping):
            overrides = dict(param_overrides)
        else:
            overrides = dict(parse_override(spec) for spec in param_overrides)

    if overrides:
        base_defines = inject_parameters(base_defines, overrides)

    resolved_csv_path = csv_path if csv_path is not None else Path(DEFAULT_OUTPUT)
    resolved_manifest_path = (
        manifest_path
        if manifest_path is not None
        else resolved_csv_path.with_suffix(".manifest.json")
    )
    output_paths = [resolved_csv_path, resolved_manifest_path]
    if report_path is not None:
        output_paths.append(report_path)
    resolved_output_paths = [path.resolve() for path in output_paths]
    if len(set(resolved_output_paths)) != len(resolved_output_paths):
        raise ValueError("csv, manifest, and report output paths must be distinct")
    for path in output_paths:
        if path.exists() and path.is_dir():
            raise ValueError(f"analysis output path is a directory: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    samples, repro_records = run_trials(
        n_samples,
        base_defines,
        max_ticks=max_ticks,
        base_seed=base_seed,
        backend=backend,
        scenario=scenario,
        objective=objective,
        progress=progress,
    )

    stats = aggregate(samples)

    write_csv(samples, stats, repro_records, resolved_csv_path)
    if progress:
        print(f"\nResults written to: {resolved_csv_path}")

    write_manifest(
        defines=base_defines,
        overrides=overrides,
        base_seed=base_seed,
        backend=backend,
        scenario=scenario,
        max_ticks=max_ticks,
        objective=objective,
        samples=samples,
        stats=stats,
        repro_records=repro_records,
        output_path=resolved_manifest_path,
    )
    if progress:
        print(f"Replay-input manifest written to: {resolved_manifest_path}")

    report = format_report(stats, base_seed=base_seed, backend=backend)
    if progress:
        print(report)

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        if progress:
            print(f"Report written to: {report_path}")

    return MonteCarloArtifact(
        samples=tuple(samples),
        stats=stats,
        repro_records=tuple(repro_records),
        csv_path=resolved_csv_path,
        manifest_path=resolved_manifest_path,
        report_path=report_path,
    )


__all__ = [
    "DEFAULT_SAMPLES",
    "DEFAULT_MAX_TICKS",
    "MAX_SAMPLES",
    "MAX_TICKS",
    "MAX_TICK_EVALUATIONS",
    "DEFAULT_OUTPUT",
    "CONFIDENCE_LEVEL",
    "HAS_SCIPY",
    "SampleResult",
    "AggregateStats",
    "MonteCarloArtifact",
    "MonteCarloManifest",
    "calculate_confidence_interval",
    "aggregate",
    "run_trials",
    "write_csv",
    "write_manifest",
    "format_report",
    "run_monte_carlo",
]
