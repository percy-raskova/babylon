"""Global sensitivity analysis using SALib (Morris/Sobol methods).

Migrated from ``tools/sensitivity_analysis.py`` (the pre-package
implementation) onto the optimization core: trials execute through
:func:`babylon.engine.optimization.runner_api.run` (backend-selectable,
``"headless"`` or ``"in_memory"``) instead of ``tools/shared.py``'s
``run_simulation``, parameter bounds come from
:func:`babylon.engine.optimization.params.get_tunable_parameters` instead of
a hand-maintained bounds dict, and scoring is
:func:`babylon.engine.optimization.objectives.carceral_objective` (or any
other :class:`~babylon.engine.optimization.objectives.Objective`). The
statistical core — the JASSS two-stage protocol, SALib problem construction,
Morris ``mu``/``mu_star``/``sigma`` screening, Sobol ``S1``/``ST``/``S2``
variance decomposition, and the markdown report formatting — is unchanged
from the original tool.

Implements the JASSS best-practice two-stage protocol:

1. Morris screening (fast) — rank parameters by importance (``mu*``, ``sigma``).
2. Sobol analysis (thorough) — quantify variance decomposition (``S1``, ``ST``, ``S2``).

Interpretation:
    Morris:
        - High ``mu*`` = important parameter.
        - High ``sigma / mu*`` = non-linear or interacts with others.

    Sobol:
        - ``S1`` = first-order (main effect of single parameter).
        - ``ST`` = total-order (main + all interaction effects).
        - ``sum(ST) - sum(S1)`` = variance from interactions.

Usage (programmatic; argparse lives in the package ``__main__``, not here)::

    from babylon.engine.optimization.sensitivity import run_sensitivity

    artifact = run_sensitivity("morris", trajectories=10)
    print(artifact.morris.ranking)

See Also:
    :doc:`/ai/tooling.yaml` sensitivity_analysis section.
    SALib documentation: https://salib.readthedocs.io/
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from babylon.config.defines import GameDefines
from babylon.engine.optimization import runner_api
from babylon.engine.optimization.backends.types import Result
from babylon.engine.optimization.objectives import Objective, carceral_objective
from babylon.engine.optimization.params import get_tunable_parameters, inject_parameters
from babylon.engine.optimization.reproducibility import ReproRecord, build_repro_record

# Try to import SALib; sensitivity analysis is unavailable without it.
try:
    from SALib.analyze import morris as morris_analyze  # type: ignore[import-untyped]
    from SALib.analyze import sobol as sobol_analyze
    from SALib.sample import morris as morris_sample  # type: ignore[import-untyped]
    from SALib.sample import saltelli

    HAS_SALIB = True
except ImportError:  # pragma: no cover - exercised only in SALib-less envs
    HAS_SALIB = False

# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_MORRIS_TRAJECTORIES: Final[int] = 10
"""Default Morris trajectory count for an exploratory screening run."""

DEFAULT_SOBOL_SAMPLES: Final[int] = 256
"""Default Sobol base sample size (total evaluations = samples * (2*D + 2))."""

DEFAULT_MAX_TICKS: Final[int] = 5200
"""Default simulation length: 5200 ticks = 100 years (1 tick = 1 week).

Matches ``tools/shared.py::DEFAULT_MAX_TICKS`` — the default the pre-package
tool ultimately ran against.
"""

DEFAULT_OUTPUT_DIR: Final[str] = "results"
"""Default directory for ``morris.json`` / ``sobol.json`` artifacts."""

SensitivityMethod = Literal["morris", "sobol", "both"]
"""The three analysis modes :func:`run_sensitivity` dispatches on."""


# =============================================================================
# DATA SHAPES
# =============================================================================


class MorrisParameterResult(BaseModel):
    """One parameter's Morris elementary-effects indices.

    :ivar mu: Mean elementary effect (signed — can cancel out for
        non-monotonic responses).
    :ivar mu_star: Mean *absolute* elementary effect (higher = more important).
    :ivar sigma: Standard deviation of elementary effects (higher = non-linear
        or interactive).
    :ivar mu_star_conf: Bootstrap confidence interval half-width for ``mu_star``.
    """

    model_config = ConfigDict(frozen=True)

    mu: float
    mu_star: float
    sigma: float
    mu_star_conf: float


class MorrisResult(BaseModel):
    """Full output of one Morris screening analysis.

    :ivar method: Always ``"morris"`` (discriminator field, matches the
        pre-migration tool's JSON shape).
    :ivar trajectories: Number of Morris trajectories sampled.
    :ivar parameters: Per-parameter :class:`MorrisParameterResult`, keyed by
        ``"category.field"`` path.
    :ivar ranking: Parameter paths sorted by descending ``mu_star``.
    """

    model_config = ConfigDict(frozen=True)

    method: Literal["morris"] = "morris"
    trajectories: int = Field(ge=1)
    parameters: dict[str, MorrisParameterResult]
    ranking: tuple[str, ...]


class SobolParameterResult(BaseModel):
    """One parameter's Sobol first-order and total-order indices.

    :ivar S1: First-order index — variance explained by this parameter alone.
    :ivar S1_conf: Bootstrap confidence interval half-width for ``S1``.
    :ivar ST: Total-order index — variance explained including all interactions.
    :ivar ST_conf: Bootstrap confidence interval half-width for ``ST``.
    """

    model_config = ConfigDict(frozen=True)

    S1: float
    S1_conf: float
    ST: float
    ST_conf: float


class SobolResult(BaseModel):
    """Full output of one Sobol variance-decomposition analysis.

    :ivar method: Always ``"sobol"`` (discriminator field, matches the
        pre-migration tool's JSON shape).
    :ivar base_samples: Base sample size passed to Saltelli sampling.
    :ivar total_samples: Total simulation evaluations (``samples * (2*D + 2)``).
    :ivar parameters: Per-parameter :class:`SobolParameterResult`, keyed by
        ``"category.field"`` path.
    :ivar S2_interactions: Pairwise second-order indices, keyed by
        ``"param_i:param_j"`` (upper triangle only).
    :ivar ranking_S1: Parameter paths sorted by descending ``S1``.
    :ivar ranking_ST: Parameter paths sorted by descending ``ST``.
    """

    model_config = ConfigDict(frozen=True)

    method: Literal["sobol"] = "sobol"
    base_samples: int = Field(ge=1)
    total_samples: int = Field(ge=1)
    parameters: dict[str, SobolParameterResult]
    S2_interactions: dict[str, float]
    ranking_S1: tuple[str, ...]
    ranking_ST: tuple[str, ...]


class SensitivityArtifact(BaseModel):
    """Full output of one :func:`run_sensitivity` call.

    :ivar morris: The Morris screening result, or ``None`` if ``method`` was
        ``"sobol"``.
    :ivar sobol: The Sobol variance-decomposition result, or ``None`` if
        ``method`` was ``"morris"``.
    :ivar repro_records: One :class:`~babylon.engine.optimization.reproducibility.ReproRecord`
        per simulation trial actually run (Morris trials first, then Sobol
        trials, when ``method="both"``) — replay any trial from its receipt
        alone.
    :ivar output_paths: Written JSON artifact paths, keyed by ``"morris"``
        and/or ``"sobol"``.
    """

    model_config = ConfigDict(frozen=True)

    morris: MorrisResult | None = None
    sobol: SobolResult | None = None
    repro_records: tuple[ReproRecord, ...] = ()
    output_paths: dict[str, Path] = Field(default_factory=dict)


# =============================================================================
# PARAMETER SPACE
# =============================================================================


def get_default_params() -> list[str]:
    """Get all tunable parameter names for sensitivity analysis.

    :returns: Every ``"category.field"`` path from
        :func:`~babylon.engine.optimization.params.get_tunable_parameters`.
    """
    return list(get_tunable_parameters().keys())


def create_problem(param_names: list[str]) -> dict[str, Any]:
    """Create a SALib problem specification from tunable-parameter bounds.

    :param param_names: List of parameter paths to analyze. Names not found
        in :func:`~babylon.engine.optimization.params.get_tunable_parameters`
        are skipped with a printed warning (not a hard failure — matches the
        pre-migration tool's lenient behavior).
    :returns: SALib problem dict with ``num_vars``, ``names``, and ``bounds``.
    """
    all_params = get_tunable_parameters()

    names: list[str] = []
    bounds: list[list[float]] = []

    for name in param_names:
        if name not in all_params:
            print(f"Warning: Unknown parameter '{name}', skipping")
            continue
        names.append(name)
        bounds.append(list(all_params[name]))

    return {
        "num_vars": len(names),
        "names": names,
        "bounds": bounds,
    }


# =============================================================================
# TRIAL EXECUTION
# =============================================================================


def evaluate_simulation(
    param_values: Any,
    param_names: list[str],
    *,
    max_ticks: int,
    seed: int = 2010,
    backend: str = "headless",
    scope_name: str = "detroit-tri-county",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    progress: bool = True,
) -> tuple[list[float], list[ReproRecord]]:
    """Run simulations for a SALib parameter sample matrix.

    :param param_values: ``N x D`` sample matrix (a SALib sampler's output —
        ``morris.sample`` or ``saltelli.sample``).
    :param param_names: The ``D`` parameter paths, in ``param_values`` column
        order.
    :param max_ticks: Maximum ticks per simulation.
    :param seed: RNG seed threaded through every trial (Constitution III.7 —
        every trial uses the *same* seed, so output variance is attributable
        to the swept parameters, not noise).
    :param backend: ``"headless"`` or ``"in_memory"`` — forwarded to
        :func:`~babylon.engine.optimization.runner_api.run`.
    :param scope_name: Headless scope label. ``backend="headless"`` only.
    :param scenario: In-memory scenario name. ``backend="in_memory"`` only.
    :param objective: Scores each trial's :class:`~babylon.engine.optimization.backends.types.Result`
        into the output SALib analyzes (default: the Carceral Equilibrium score).
    :param progress: Print a progress line to stdout.
    :returns: ``(outputs, repro_records)`` — ``outputs`` is the ``N``-length
        list SALib's ``analyze`` functions consume; ``repro_records`` is one
        :class:`~babylon.engine.optimization.reproducibility.ReproRecord` per
        trial, same order.
    """
    n_samples = len(param_values)
    outputs: list[float] = []
    repro_records: list[ReproRecord] = []
    scope_label = scope_name if backend == "headless" else scenario

    if progress:
        print(f"Evaluating {n_samples} parameter combinations...")

    for i, values in enumerate(param_values):
        trial_params = {name: float(v) for name, v in zip(param_names, values, strict=True)}
        defines = inject_parameters(GameDefines(), trial_params)

        result: Result = runner_api.run(
            defines,
            seed=seed,
            max_ticks=max_ticks,
            backend=backend,
            scope_name=scope_name,
            scenario=scenario,
        )
        outputs.append(objective(result))
        repro_records.append(
            build_repro_record(result, scope_name=scope_label, max_ticks=max_ticks)
        )

        if progress and ((i + 1) % max(1, n_samples // 20) == 0 or i == n_samples - 1):
            pct = 100 * (i + 1) // n_samples
            print(f"\r  [{i + 1}/{n_samples}] {pct}%", end="", flush=True)

    if progress:
        print()  # Newline after progress

    return outputs, repro_records


# =============================================================================
# ANALYSIS
# =============================================================================


def run_morris_analysis(
    param_names: list[str],
    trajectories: int,
    max_ticks: int,
    *,
    seed: int = 2010,
    backend: str = "headless",
    scope_name: str = "detroit-tri-county",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    progress: bool = True,
) -> tuple[MorrisResult, list[ReproRecord]]:
    """Run Morris elementary-effects screening.

    :param param_names: Parameters to analyze.
    :param trajectories: Number of Morris trajectories.
    :param max_ticks: Max ticks per simulation.
    :param seed: RNG seed threaded through every trial.
    :param backend: ``"headless"`` or ``"in_memory"``.
    :param scope_name: Headless scope label. ``backend="headless"`` only.
    :param scenario: In-memory scenario name. ``backend="in_memory"`` only.
    :param objective: Scores each trial's :class:`~babylon.engine.optimization.backends.types.Result`.
    :param progress: Print progress to stdout.
    :returns: ``(result, repro_records)``.
    :raises ImportError: If SALib is not installed.
    :raises ValueError: If no parameter in ``param_names`` is a known tunable
        parameter.
    """
    if not HAS_SALIB:
        raise ImportError("SALib not installed. Run: poetry add SALib")

    problem = create_problem(param_names)
    if problem["num_vars"] == 0:
        raise ValueError("No valid parameters to analyze")

    if progress:
        print("\nMorris Screening Analysis")
        print(f"  Parameters: {problem['num_vars']}")
        print(f"  Trajectories: {trajectories}")
        print(f"  Total samples: {trajectories * (problem['num_vars'] + 1)}")
        print()

    param_values = morris_sample.sample(problem, trajectories)
    outputs, repro_records = evaluate_simulation(
        param_values,
        problem["names"],
        max_ticks=max_ticks,
        seed=seed,
        backend=backend,
        scope_name=scope_name,
        scenario=scenario,
        objective=objective,
        progress=progress,
    )

    analysis = morris_analyze.analyze(problem, param_values, np.array(outputs))

    names: list[str] = problem["names"]
    parameters = {
        name: MorrisParameterResult(
            mu=float(analysis["mu"][i]),
            mu_star=float(analysis["mu_star"][i]),
            sigma=float(analysis["sigma"][i]),
            mu_star_conf=float(analysis["mu_star_conf"][i]),
        )
        for i, name in enumerate(names)
    }
    ranking = tuple(sorted(names, key=lambda n: analysis["mu_star"][names.index(n)], reverse=True))

    result = MorrisResult(trajectories=trajectories, parameters=parameters, ranking=ranking)
    return result, repro_records


def run_sobol_analysis(
    param_names: list[str],
    samples: int,
    max_ticks: int,
    *,
    seed: int = 2010,
    backend: str = "headless",
    scope_name: str = "detroit-tri-county",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    progress: bool = True,
) -> tuple[SobolResult, list[ReproRecord]]:
    """Run Sobol variance decomposition.

    :param param_names: Parameters to analyze.
    :param samples: Base sample size (total = ``samples * (2*D + 2)``).
    :param max_ticks: Max ticks per simulation.
    :param seed: RNG seed threaded through every trial.
    :param backend: ``"headless"`` or ``"in_memory"``.
    :param scope_name: Headless scope label. ``backend="headless"`` only.
    :param scenario: In-memory scenario name. ``backend="in_memory"`` only.
    :param objective: Scores each trial's :class:`~babylon.engine.optimization.backends.types.Result`.
    :param progress: Print progress to stdout.
    :returns: ``(result, repro_records)``.
    :raises ImportError: If SALib is not installed.
    :raises ValueError: If no parameter in ``param_names`` is a known tunable
        parameter.
    """
    if not HAS_SALIB:
        raise ImportError("SALib not installed. Run: poetry add SALib")

    problem = create_problem(param_names)
    if problem["num_vars"] == 0:
        raise ValueError("No valid parameters to analyze")

    total_samples = samples * (2 * problem["num_vars"] + 2)

    if progress:
        print("\nSobol Variance Decomposition Analysis")
        print(f"  Parameters: {problem['num_vars']}")
        print(f"  Base samples: {samples}")
        print(f"  Total samples: {total_samples}")
        print()

    param_values = saltelli.sample(problem, samples, calc_second_order=True)
    outputs, repro_records = evaluate_simulation(
        param_values,
        problem["names"],
        max_ticks=max_ticks,
        seed=seed,
        backend=backend,
        scope_name=scope_name,
        scenario=scenario,
        objective=objective,
        progress=progress,
    )

    analysis = sobol_analyze.analyze(problem, np.array(outputs), calc_second_order=True)

    names: list[str] = problem["names"]
    parameters = {
        name: SobolParameterResult(
            S1=float(analysis["S1"][i]),
            S1_conf=float(analysis["S1_conf"][i]),
            ST=float(analysis["ST"][i]),
            ST_conf=float(analysis["ST_conf"][i]),
        )
        for i, name in enumerate(names)
    }

    s2_interactions: dict[str, float] = {}
    if "S2" in analysis:
        for i, name_i in enumerate(names):
            for j, name_j in enumerate(names):
                if j > i:  # Upper triangle only
                    s2_interactions[f"{name_i}:{name_j}"] = float(analysis["S2"][i, j])

    ranking_s1 = tuple(sorted(names, key=lambda n: analysis["S1"][names.index(n)], reverse=True))
    ranking_st = tuple(sorted(names, key=lambda n: analysis["ST"][names.index(n)], reverse=True))

    result = SobolResult(
        base_samples=samples,
        total_samples=total_samples,
        parameters=parameters,
        S2_interactions=s2_interactions,
        ranking_S1=ranking_s1,
        ranking_ST=ranking_st,
    )
    return result, repro_records


# =============================================================================
# REPORT FORMATTING
# =============================================================================


def format_morris_report(result: MorrisResult) -> str:
    """Format Morris results as markdown.

    :param result: A :func:`run_morris_analysis` result.
    :returns: Markdown report string.
    """
    lines = [
        "# Morris Elementary Effects Screening",
        "",
        f"**Trajectories**: {result.trajectories}",
        "",
        "## Parameter Importance (by mu*)",
        "",
        "| Rank | Parameter | mu* | sigma | sigma/mu* |",
        "|------|-----------|-----|-------|-----------|",
    ]

    for rank, name in enumerate(result.ranking, 1):
        p = result.parameters[name]
        ratio = p.sigma / max(p.mu_star, 0.001)
        lines.append(f"| {rank} | `{name}` | {p.mu_star:.4f} | {p.sigma:.4f} | {ratio:.2f} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **mu***: Mean absolute effect on output (higher = more important)",
            "- **sigma**: Standard deviation of effects (higher = non-linear or interactive)",
            "- **sigma/mu***: Ratio indicates degree of non-linearity/interaction",
            "  - < 0.5: Linear, additive effect",
            "  - 0.5-1.0: Moderate non-linearity",
            "  - > 1.0: Strong non-linearity or interactions",
        ]
    )

    return "\n".join(lines)


def format_sobol_report(result: SobolResult) -> str:
    """Format Sobol results as markdown.

    :param result: A :func:`run_sobol_analysis` result.
    :returns: Markdown report string.
    """
    lines = [
        "# Sobol Variance Decomposition Analysis",
        "",
        f"**Base Samples**: {result.base_samples}",
        f"**Total Evaluations**: {result.total_samples}",
        "",
        "## First-Order Indices (S1)",
        "",
        "| Rank | Parameter | S1 | Conf |",
        "|------|-----------|-----|------|",
    ]

    for rank, name in enumerate(result.ranking_S1, 1):
        p = result.parameters[name]
        lines.append(f"| {rank} | `{name}` | {p.S1:.4f} | {p.S1_conf:.4f} |")

    lines.extend(
        [
            "",
            "## Total-Order Indices (ST)",
            "",
            "| Rank | Parameter | ST | Conf |",
            "|------|-----------|-----|------|",
        ]
    )

    for rank, name in enumerate(result.ranking_ST, 1):
        p = result.parameters[name]
        lines.append(f"| {rank} | `{name}` | {p.ST:.4f} | {p.ST_conf:.4f} |")

    # Top interactions
    if result.S2_interactions:
        sorted_s2 = sorted(
            result.S2_interactions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:5]  # Top 5

        lines.extend(
            [
                "",
                "## Top Pairwise Interactions (S2)",
                "",
                "| Parameters | S2 |",
                "|------------|-----|",
            ]
        )
        for key, value in sorted_s2:
            lines.append(f"| `{key}` | {value:.4f} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **S1**: Variance explained by parameter alone (main effect)",
            "- **ST**: Variance explained including all interactions",
            "- **ST - S1**: Contribution from interactions with other parameters",
            "",
            "Sum(S1) + interactions = total variance explained",
        ]
    )

    return "\n".join(lines)


# =============================================================================
# ENTRY POINT
# =============================================================================


def run_sensitivity(
    method: SensitivityMethod,
    *,
    param_names: Sequence[str] | None = None,
    trajectories: int = DEFAULT_MORRIS_TRAJECTORIES,
    samples: int = DEFAULT_SOBOL_SAMPLES,
    max_ticks: int = DEFAULT_MAX_TICKS,
    seed: int = 2010,
    backend: str = "headless",
    scope_name: str = "detroit-tri-county",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    output_dir: Path | None = None,
    morris_output: Path | None = None,
    sobol_output: Path | None = None,
    progress: bool = True,
) -> SensitivityArtifact:
    """Run global sensitivity analysis and write JSON artifacts.

    The single entry point a CLI (or another algorithm) should call: builds
    the SALib problem from tunable-parameter bounds, runs Morris and/or
    Sobol, writes ``morris.json`` / ``sobol.json``, and (when ``progress`` is
    ``True``) prints the markdown report — matching the pre-migration tool's
    console output.

    :param method: ``"morris"``, ``"sobol"``, or ``"both"`` (Morris then Sobol).
    :param param_names: Parameter paths to analyze. Defaults to every known
        tunable parameter (:func:`get_default_params`) when ``None`` — note
        this is a *lot* of parameters and therefore a lot of trials; pass an
        explicit subset for a quick run.
    :param trajectories: Morris trajectory count. Ignored for ``method="sobol"``.
    :param samples: Sobol base sample size. Ignored for ``method="morris"``.
    :param max_ticks: Maximum ticks per trial.
    :param seed: RNG seed threaded through every trial (Constitution III.7).
    :param backend: ``"headless"`` or ``"in_memory"`` — forwarded to
        :func:`~babylon.engine.optimization.runner_api.run`.
    :param scope_name: Headless scope label. ``backend="headless"`` only.
    :param scenario: In-memory scenario name. ``backend="in_memory"`` only.
    :param objective: Scores each trial's :class:`~babylon.engine.optimization.backends.types.Result`
        (default: :func:`~babylon.engine.optimization.objectives.carceral_objective`).
    :param output_dir: Directory for ``morris.json`` / ``sobol.json`` when
        ``morris_output`` / ``sobol_output`` are not given (default:
        :data:`DEFAULT_OUTPUT_DIR`).
    :param morris_output: Explicit override for the Morris JSON path.
    :param sobol_output: Explicit override for the Sobol JSON path.
    :param progress: Print progress + reports to stdout.
    :returns: The full :class:`SensitivityArtifact` (results, repro records,
        and output paths).
    :raises ValueError: If ``method`` is not ``"morris"``/``"sobol"``/``"both"``,
        or if no parameter in ``param_names`` is a known tunable parameter.
    :raises ImportError: If SALib is not installed.
    """
    if method not in ("morris", "sobol", "both"):
        raise ValueError(f"Unknown method {method!r}; expected 'morris', 'sobol', or 'both'")

    resolved_param_names = list(param_names) if param_names is not None else get_default_params()
    resolved_output_dir = output_dir if output_dir is not None else Path(DEFAULT_OUTPUT_DIR)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    morris_result: MorrisResult | None = None
    sobol_result: SobolResult | None = None
    repro_records: list[ReproRecord] = []
    output_paths: dict[str, Path] = {}

    if method in ("morris", "both"):
        if progress and method == "both":
            print("=" * 60)
            print("PHASE 1: Morris Screening")
            print("=" * 60)

        morris_result, morris_repro = run_morris_analysis(
            resolved_param_names,
            trajectories,
            max_ticks,
            seed=seed,
            backend=backend,
            scope_name=scope_name,
            scenario=scenario,
            objective=objective,
            progress=progress,
        )
        repro_records.extend(morris_repro)

        morris_path = (
            morris_output if morris_output is not None else resolved_output_dir / "morris.json"
        )
        morris_path.parent.mkdir(parents=True, exist_ok=True)
        morris_path.write_text(json.dumps(morris_result.model_dump(mode="json"), indent=2))
        output_paths["morris"] = morris_path

        if progress:
            print(f"\nResults written to: {morris_path}")
            print(format_morris_report(morris_result))

    if method in ("sobol", "both"):
        if progress and method == "both":
            print()
            print("=" * 60)
            print("PHASE 2: Sobol Analysis")
            print("=" * 60)

        sobol_result, sobol_repro = run_sobol_analysis(
            resolved_param_names,
            samples,
            max_ticks,
            seed=seed,
            backend=backend,
            scope_name=scope_name,
            scenario=scenario,
            objective=objective,
            progress=progress,
        )
        repro_records.extend(sobol_repro)

        sobol_path = (
            sobol_output if sobol_output is not None else resolved_output_dir / "sobol.json"
        )
        sobol_path.parent.mkdir(parents=True, exist_ok=True)
        sobol_path.write_text(json.dumps(sobol_result.model_dump(mode="json"), indent=2))
        output_paths["sobol"] = sobol_path

        if progress:
            print(f"\nResults written to: {sobol_path}")
            print(format_sobol_report(sobol_result))

    return SensitivityArtifact(
        morris=morris_result,
        sobol=sobol_result,
        repro_records=tuple(repro_records),
        output_paths=output_paths,
    )


__all__ = [
    "HAS_SALIB",
    "DEFAULT_MORRIS_TRAJECTORIES",
    "DEFAULT_SOBOL_SAMPLES",
    "DEFAULT_MAX_TICKS",
    "DEFAULT_OUTPUT_DIR",
    "SensitivityMethod",
    "MorrisParameterResult",
    "MorrisResult",
    "SobolParameterResult",
    "SobolResult",
    "SensitivityArtifact",
    "get_default_params",
    "create_problem",
    "evaluate_simulation",
    "run_morris_analysis",
    "run_sobol_analysis",
    "format_morris_report",
    "format_sobol_report",
    "run_sensitivity",
]
