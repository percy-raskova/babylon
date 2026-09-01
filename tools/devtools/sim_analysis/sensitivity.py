"""Development-only sensitivity analysis of the frozen Python reference simulation.

Trials execute through :func:`tools.devtools.sim_analysis.runner_api.run`.
Parameter bounds come from
:func:`tools.devtools.sim_analysis.params.get_tunable_parameters` instead of
a hand-maintained bounds dict, and scoring is
:func:`tools.devtools.sim_analysis.objectives.carceral_objective` (or any
other :class:`~tools.devtools.sim_analysis.objectives.Objective`). The
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

    from tools.devtools.sim_analysis.sensitivity import run_sensitivity

    artifact = run_sensitivity("morris", trajectories=10)
    print(artifact.morris.ranking)

See Also:
    :doc:`/ai/tooling.yaml` sensitivity_analysis section.
    SALib documentation: https://salib.readthedocs.io/
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from tools.devtools.sim_analysis import runner_api
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.objectives import Objective, carceral_objective
from tools.devtools.sim_analysis.params import (
    ParameterValue,
    get_parameter_type,
    get_tunable_parameters,
    inject_parameters,
)
from tools.devtools.sim_analysis.reproducibility import ReproRecord, build_repro_record

from babylon.config.defines import GameDefines, canonical_defines_hash

# Try to import SALib; sensitivity analysis is unavailable without it.
try:
    from SALib.analyze import morris as morris_analyze  # type: ignore[import-untyped]
    from SALib.analyze import sobol as sobol_analyze
    from SALib.sample import morris as morris_sample  # type: ignore[import-untyped]
    from SALib.sample import sobol as sobol_sample

    HAS_SALIB = True
except ImportError:  # pragma: no cover - exercised only in SALib-less envs
    HAS_SALIB = False

# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_MORRIS_TRAJECTORIES: Final[int] = 8
"""Default Morris trajectory count for an exploratory screening run."""

DEFAULT_SOBOL_SAMPLES: Final[int] = 64
"""Default Sobol base sample size (total evaluations = samples * (2*D + 2))."""

DEFAULT_MAX_TICKS: Final[int] = 2600
"""Default simulation length: 2600 ticks = 50 years (1 tick = 1 week).

This reaches the first three Carceral Equilibrium phase windows without making
an exploratory sensitivity command a 100-year run for every sampled point.
"""

DEFAULT_PARAMETER_NAMES: Final[tuple[str, ...]] = (
    "economy.base_subsistence",
    "economy.extraction_efficiency",
    "economy.comprador_cut",
    "economy.super_wage_rate",
    "economy.trpf_coefficient",
    "consciousness.sensitivity",
    "solidarity.scaling_factor",
    "carceral.enforcer_fraction",
)
"""Curated, bounded drivers of the retained Carceral Equilibrium objective."""

DEFAULT_SOBOL_SCREENED_PARAMETERS: Final[int] = 4
"""Number of top Morris ``mu*`` parameters promoted to Sobol in ``both`` mode."""

MAX_PARAMETER_COUNT: Final[int] = 16
MAX_MORRIS_TRAJECTORIES: Final[int] = 64
MAX_SOBOL_BASE_SAMPLES: Final[int] = 256
MAX_TICKS: Final[int] = 5200
MAX_EVALUATIONS: Final[int] = 2048
MAX_TICK_EVALUATIONS: Final[int] = 5_000_000
MAX_ARTIFACT_BYTES: Final[int] = 8 * 1024 * 1024
"""Hard safety limits applied before SALib allocates or a simulation runs."""

DEFAULT_OUTPUT_DIR: Final[str] = "results"
"""Default directory for ``morris.json`` / ``sobol.json`` artifacts."""

SensitivityMethod = Literal["morris", "sobol", "both"]
"""The three analysis modes :func:`run_sensitivity` dispatches on."""


# =============================================================================
# DATA SHAPES
# =============================================================================


class ParameterDefinition(BaseModel):
    """Exact analyzed parameter type and effective SALib sampling interval."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    name: str
    native_type: Literal["int", "float"]
    declared_lower: float
    declared_upper: float
    lower_inclusive: bool
    upper_inclusive: bool
    sample_lower: int | float
    sample_upper: int | float


class SensitivityTrial(BaseModel):
    """Invertible sampled input, native overrides, output, and replay receipt."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    ordinal: int = Field(ge=0)
    sampled_values: tuple[float, ...]
    native_overrides: dict[str, int | float]
    output: float
    repro: ReproRecord


class MorrisParameterResult(BaseModel):
    """One parameter's Morris elementary-effects indices.

    :ivar mu: Mean elementary effect (signed — can cancel out for
        non-monotonic responses).
    :ivar mu_star: Mean *absolute* elementary effect (higher = more important).
    :ivar sigma: Standard deviation of elementary effects (higher = non-linear
        or interactive).
    :ivar mu_star_conf: Bootstrap confidence interval half-width for ``mu_star``.
    """

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

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

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    schema_id: Literal["babylon.sim-analysis.morris.v1"] = Field(
        default="babylon.sim-analysis.morris.v1",
        alias="schema",
    )
    method: Literal["morris"] = "morris"
    trajectories: int = Field(ge=1)
    seed: int
    max_ticks: int = Field(ge=1)
    backend: str
    scenario: str
    base_defines: dict[str, Any]
    parameter_definitions: tuple[ParameterDefinition, ...]
    trials: tuple[SensitivityTrial, ...]
    parameters: dict[str, MorrisParameterResult]
    ranking: tuple[str, ...]


class SobolParameterResult(BaseModel):
    """One parameter's Sobol first-order and total-order indices.

    :ivar S1: First-order index — variance explained by this parameter alone.
    :ivar S1_conf: Bootstrap confidence interval half-width for ``S1``.
    :ivar ST: Total-order index — variance explained including all interactions.
    :ivar ST_conf: Bootstrap confidence interval half-width for ``ST``.
    """

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

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

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    schema_id: Literal["babylon.sim-analysis.sobol.v1"] = Field(
        default="babylon.sim-analysis.sobol.v1",
        alias="schema",
    )
    method: Literal["sobol"] = "sobol"
    base_samples: int = Field(ge=1)
    total_samples: int = Field(ge=1)
    seed: int
    max_ticks: int = Field(ge=1)
    backend: str
    scenario: str
    selection: Literal["explicit", "morris_top_mu_star"] = "explicit"
    base_defines: dict[str, Any]
    parameter_definitions: tuple[ParameterDefinition, ...]
    trials: tuple[SensitivityTrial, ...]
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
    :ivar repro_records: One verification receipt per simulation trial
        (Morris first, then Sobol for ``method="both"``). A receipt's hash is
        not invertible; replay also needs the enclosing phase result's
        ``base_defines`` and trial ``native_overrides`` plus the same source
        revision.
    :ivar output_paths: Written JSON artifact paths, keyed by ``"morris"``
        and/or ``"sobol"``.
    """

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    morris: MorrisResult | None = None
    sobol: SobolResult | None = None
    repro_records: tuple[ReproRecord, ...] = ()
    output_paths: dict[str, Path] = Field(default_factory=dict)


# =============================================================================
# PARAMETER SPACE
# =============================================================================


def get_default_params() -> list[str]:
    """Get the curated default parameter names for sensitivity analysis.

    The full registry currently contains hundreds of fields and is unsuitable
    as an implicit global-analysis workload. Callers can still pass an
    explicit subset, up to :data:`MAX_PARAMETER_COUNT`.

    :returns: Eight schema-validated Carceral Equilibrium drivers.
    """
    all_params = get_tunable_parameters()
    missing = [name for name in DEFAULT_PARAMETER_NAMES if name not in all_params]
    if missing:
        raise ValueError(f"Default sensitivity parameters missing from GameDefines: {missing}")
    return list(DEFAULT_PARAMETER_NAMES)


def _parameter_definition(name: str) -> ParameterDefinition:
    """Resolve native type, declared bounds, and an open-bound-safe interval."""
    all_params = get_tunable_parameters()
    if name not in all_params:
        raise ValueError(f"Unknown sensitivity parameter {name!r}")

    sample_lower, sample_upper = all_params[name]
    declared_lower = float(sample_lower)
    declared_upper = float(sample_upper)
    category_name, field_name = name.split(".", maxsplit=1)
    category_model = GameDefines.model_fields[category_name].annotation
    if category_model is None or not hasattr(category_model, "model_fields"):
        raise ValueError(f"Parameter category {category_name!r} is not a model")
    field_info = category_model.model_fields[field_name]

    lower_inclusive = True
    upper_inclusive = True
    for constraint in field_info.metadata:
        constraint_name = type(constraint).__name__
        if constraint_name == "Gt":
            declared_lower = float(constraint.gt)
            lower_inclusive = False
        elif constraint_name == "Ge":
            declared_lower = float(constraint.ge)
            lower_inclusive = True
        elif constraint_name == "Lt":
            declared_upper = float(constraint.lt)
            upper_inclusive = False
        elif constraint_name == "Le":
            declared_upper = float(constraint.le)
            upper_inclusive = True

    native_type = get_parameter_type(name)
    if native_type is int:
        native_type_name: Literal["int", "float"] = "int"
    else:
        native_type_name = "float"

    if not math.isfinite(float(sample_lower)) or not math.isfinite(float(sample_upper)):
        raise ValueError(f"Sensitivity bounds for {name!r} must be finite")
    if sample_lower >= sample_upper:
        raise ValueError(
            f"Sensitivity interval for {name!r} has fewer than two native values: "
            f"[{sample_lower}, {sample_upper}]"
        )

    return ParameterDefinition(
        name=name,
        native_type=native_type_name,
        declared_lower=declared_lower,
        declared_upper=declared_upper,
        lower_inclusive=lower_inclusive,
        upper_inclusive=upper_inclusive,
        sample_lower=sample_lower,
        sample_upper=sample_upper,
    )


def _parameter_definitions(param_names: Sequence[str]) -> tuple[ParameterDefinition, ...]:
    if not param_names:
        raise ValueError("At least one sensitivity parameter is required")
    if len(param_names) > MAX_PARAMETER_COUNT:
        raise ValueError(
            f"Sensitivity analysis is limited to {MAX_PARAMETER_COUNT} parameters; "
            f"received {len(param_names)}"
        )
    if len(set(param_names)) != len(param_names):
        raise ValueError("Sensitivity parameter names must be unique")
    return tuple(_parameter_definition(name) for name in param_names)


def create_problem(param_names: list[str]) -> dict[str, Any]:
    """Create a SALib problem specification from tunable-parameter bounds.

    :param param_names: Explicit, unique parameter paths to analyze.
    :returns: SALib problem dict with ``num_vars``, ``names``, and ``bounds``.
    :raises ValueError: If names are unknown, duplicated, empty, or exceed the
        bounded analysis surface.
    """
    definitions = _parameter_definitions(param_names)
    names = [definition.name for definition in definitions]
    bounds = [
        [float(definition.sample_lower), float(definition.sample_upper)]
        for definition in definitions
    ]

    return {
        "num_vars": len(names),
        "names": names,
        "bounds": bounds,
    }


def _estimate_artifact_bytes(evaluations: int, parameter_count: int) -> int:
    """Conservatively bound JSON trial receipts before sampling or execution."""
    base_defines = json.dumps(
        GameDefines().model_dump(mode="json"),
        allow_nan=False,
        separators=(",", ":"),
    )
    return len(base_defines.encode("utf-8")) + 4096 + evaluations * (1024 + 128 * parameter_count)


def _validate_run_metadata(*, backend: str, scenario: str) -> None:
    """Keep repeated receipt metadata bounded before any trial runs."""
    if not backend or len(backend) > 32:
        raise ValueError("backend must contain 1..32 characters")
    if not scenario or len(scenario) > 128:
        raise ValueError("scenario must contain 1..128 characters")


def _validate_workload(
    *,
    parameter_count: int,
    evaluations: int,
    max_ticks: int,
) -> None:
    """Reject unsafe sample, tick, and receipt sizes before any allocation."""
    if not 1 <= parameter_count <= MAX_PARAMETER_COUNT:
        raise ValueError(
            f"Sensitivity parameter count must be 1..{MAX_PARAMETER_COUNT}; "
            f"received {parameter_count}"
        )
    if not 1 <= max_ticks <= MAX_TICKS:
        raise ValueError(f"max_ticks must be 1..{MAX_TICKS}; received {max_ticks}")
    if not 1 <= evaluations <= MAX_EVALUATIONS:
        raise ValueError(
            f"Sensitivity workload must be 1..{MAX_EVALUATIONS} evaluations; "
            f"requested {evaluations}"
        )
    tick_evaluations = evaluations * max_ticks
    if tick_evaluations > MAX_TICK_EVALUATIONS:
        raise ValueError(
            "Sensitivity workload exceeds the tick budget: "
            f"{evaluations} evaluations * {max_ticks} ticks = {tick_evaluations}, "
            f"limit {MAX_TICK_EVALUATIONS}"
        )
    estimated_bytes = _estimate_artifact_bytes(evaluations, parameter_count)
    if estimated_bytes > MAX_ARTIFACT_BYTES:
        raise ValueError(
            "Sensitivity artifact would exceed the receipt budget: "
            f"estimated {estimated_bytes} bytes, limit {MAX_ARTIFACT_BYTES}"
        )


def _coerce_parameter_value(
    definition: ParameterDefinition,
    value: Any,
) -> ParameterValue:
    """Convert a SALib scalar into the field's exact native, valid value."""
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"SALib proposed a non-finite value for {definition.name!r}: {numeric!r}")
    lower = float(definition.sample_lower)
    upper = float(definition.sample_upper)
    if numeric < lower or numeric > upper:
        raise ValueError(
            f"SALib proposed {numeric!r} outside {definition.name!r} "
            f"sampling bounds [{lower}, {upper}]"
        )
    if definition.native_type == "int":
        return min(
            max(math.floor(numeric + 0.5), int(definition.sample_lower)),
            int(definition.sample_upper),
        )
    return numeric


def _native_overrides(
    values: Sequence[object],
    definitions: Sequence[ParameterDefinition],
) -> dict[str, ParameterValue]:
    if len(values) != len(definitions):
        raise ValueError(
            f"SALib sample width {len(values)} does not match parameter count {len(definitions)}"
        )
    return {
        definition.name: _coerce_parameter_value(definition, value)
        for definition, value in zip(definitions, values, strict=True)
    }


def _finite(value: Any, *, label: str) -> float:
    """Return a finite float or fail instead of leaking JSON NaN/Infinity."""
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"Sensitivity analysis produced non-finite {label}: {numeric!r}")
    return numeric


def _validated_outputs(outputs: Sequence[float], *, method: str) -> np.ndarray:
    """Validate objective evidence before asking SALib to estimate indices."""
    finite_outputs = np.asarray(
        [
            _finite(output, label=f"{method} objective output at trial {index}")
            for index, output in enumerate(outputs)
        ],
        dtype=float,
    )
    if len(finite_outputs) < 2 or all(output == finite_outputs[0] for output in finite_outputs[1:]):
        raise ValueError(
            f"{method} indices are undefined because the objective has zero variance "
            "across sampled trials"
        )
    return finite_outputs


def _build_trials(
    param_values: Any,
    definitions: Sequence[ParameterDefinition],
    outputs: Sequence[float],
    repro_records: Sequence[ReproRecord],
) -> tuple[SensitivityTrial, ...]:
    """Join SALib proposals, native overrides, outputs, and replay receipts."""
    if not (len(param_values) == len(outputs) == len(repro_records)):
        raise ValueError(
            "Sensitivity trial evidence is incomplete: sample, output, and repro counts differ"
        )
    trials: list[SensitivityTrial] = []
    for ordinal, (values, output, repro) in enumerate(
        zip(param_values, outputs, repro_records, strict=True)
    ):
        sampled_values = tuple(
            _finite(value, label=f"sample value at trial {ordinal}") for value in values
        )
        trials.append(
            SensitivityTrial(
                ordinal=ordinal,
                sampled_values=sampled_values,
                native_overrides=_native_overrides(sampled_values, definitions),
                output=_finite(output, label=f"objective output at trial {ordinal}"),
                repro=repro,
            )
        )
    return tuple(trials)


def _write_strict_json(path: Path, result: BaseModel) -> None:
    """Write a bounded RFC-compliant artifact with non-finite values forbidden."""
    payload = json.dumps(
        result.model_dump(mode="json", by_alias=True),
        indent=2,
        allow_nan=False,
    )
    encoded_size = len(payload.encode("utf-8"))
    if encoded_size > MAX_ARTIFACT_BYTES:
        raise ValueError(
            f"Sensitivity artifact is {encoded_size} bytes; limit is {MAX_ARTIFACT_BYTES}"
        )
    path.write_text(f"{payload}\n", encoding="utf-8")


# =============================================================================
# TRIAL EXECUTION
# =============================================================================


def evaluate_simulation(
    param_values: Any,
    param_names: list[str],
    *,
    max_ticks: int,
    seed: int = 2010,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    progress: bool = True,
) -> tuple[list[float], list[ReproRecord]]:
    """Run simulations for a SALib parameter sample matrix.

    :param param_values: ``N x D`` sample matrix (a SALib sampler's output —
        ``morris.sample`` or ``sobol.sample``).
    :param param_names: The ``D`` parameter paths, in ``param_values`` column
        order.
    :param max_ticks: Maximum ticks per simulation.
    :param seed: RNG seed threaded through every trial (Constitution III.7 —
        every trial uses the *same* seed, so output variance is attributable
        to the swept parameters, not noise).
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param objective: Scores each trial's :class:`~tools.devtools.sim_analysis.backends.types.Result`
        into the output SALib analyzes (default: the Carceral Equilibrium score).
    :param progress: Print a progress line to stdout.
    :returns: ``(outputs, repro_records)`` — ``outputs`` is the ``N``-length
        list SALib's ``analyze`` functions consume; ``repro_records`` is one
        :class:`~tools.devtools.sim_analysis.reproducibility.ReproRecord` per
        trial, same order.
    """
    n_samples = len(param_values)
    definitions = _parameter_definitions(param_names)
    _validate_run_metadata(backend=backend, scenario=scenario)
    _validate_workload(
        parameter_count=len(definitions),
        evaluations=n_samples,
        max_ticks=max_ticks,
    )
    outputs: list[float] = []
    repro_records: list[ReproRecord] = []

    if progress:
        print(f"Evaluating {n_samples} parameter combinations...")

    for i, values in enumerate(param_values):
        trial_params = _native_overrides(values, definitions)
        defines = inject_parameters(GameDefines(), trial_params)

        result: Result = runner_api.run(
            defines,
            seed=seed,
            max_ticks=max_ticks,
            backend=backend,
            scenario=scenario,
        )
        expected_hash = canonical_defines_hash(defines)
        if result.defines_hash != expected_hash:
            raise ValueError(
                f"trial {i} receipt hash does not match its validated GameDefines payload"
            )
        outputs.append(_finite(objective(result), label=f"objective output at trial {i}"))
        repro_records.append(build_repro_record(result, scenario=scenario, max_ticks=max_ticks))

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
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    progress: bool = True,
) -> tuple[MorrisResult, list[ReproRecord]]:
    """Run Morris elementary-effects screening.

    :param param_names: Parameters to analyze.
    :param trajectories: Number of Morris trajectories.
    :param max_ticks: Max ticks per simulation.
    :param seed: RNG seed threaded through every trial.
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param objective: Scores each trial's :class:`~tools.devtools.sim_analysis.backends.types.Result`.
    :param progress: Print progress to stdout.
    :returns: ``(result, repro_records)``.
    :raises ImportError: If SALib is not installed.
    :raises ValueError: If no parameter in ``param_names`` is a known tunable
        parameter.
    """
    if not HAS_SALIB:
        raise ImportError("SALib not installed. Install the dev dependency group: `uv sync`.")
    _validate_run_metadata(backend=backend, scenario=scenario)
    if not 1 <= trajectories <= MAX_MORRIS_TRAJECTORIES:
        raise ValueError(
            f"Morris trajectories must be 1..{MAX_MORRIS_TRAJECTORIES}; received {trajectories}"
        )

    problem = create_problem(param_names)
    definitions = _parameter_definitions(problem["names"])
    total_samples = trajectories * (problem["num_vars"] + 1)
    _validate_workload(
        parameter_count=problem["num_vars"],
        evaluations=total_samples,
        max_ticks=max_ticks,
    )

    if progress:
        print("\nMorris Screening Analysis")
        print(f"  Parameters: {problem['num_vars']}")
        print(f"  Trajectories: {trajectories}")
        print(f"  Total samples: {total_samples}")
        print()

    param_values = morris_sample.sample(problem, trajectories, seed=seed)
    if len(param_values) != total_samples:
        raise ValueError(
            f"Morris sampler returned {len(param_values)} rows; expected {total_samples}"
        )
    outputs, repro_records = evaluate_simulation(
        param_values,
        problem["names"],
        max_ticks=max_ticks,
        seed=seed,
        backend=backend,
        scenario=scenario,
        objective=objective,
        progress=progress,
    )
    analysis_outputs = _validated_outputs(outputs, method="Morris")

    analysis = morris_analyze.analyze(
        problem,
        param_values,
        analysis_outputs,
        seed=seed,
    )

    names: list[str] = problem["names"]
    parameters = {
        name: MorrisParameterResult(
            mu=_finite(analysis["mu"][i], label=f"Morris mu for {name}"),
            mu_star=_finite(analysis["mu_star"][i], label=f"Morris mu_star for {name}"),
            sigma=_finite(analysis["sigma"][i], label=f"Morris sigma for {name}"),
            mu_star_conf=_finite(
                analysis["mu_star_conf"][i],
                label=f"Morris mu_star_conf for {name}",
            ),
        )
        for i, name in enumerate(names)
    }
    ranking = tuple(sorted(names, key=lambda name: parameters[name].mu_star, reverse=True))
    trials = _build_trials(param_values, definitions, outputs, repro_records)

    result = MorrisResult(
        trajectories=trajectories,
        seed=seed,
        max_ticks=max_ticks,
        backend=backend,
        scenario=scenario,
        base_defines=GameDefines().model_dump(mode="json"),
        parameter_definitions=definitions,
        trials=trials,
        parameters=parameters,
        ranking=ranking,
    )
    return result, repro_records


def run_sobol_analysis(
    param_names: list[str],
    samples: int,
    max_ticks: int,
    *,
    seed: int = 2010,
    backend: str = "in_memory",
    scenario: str = "imperial_circuit",
    objective: Objective = carceral_objective,
    progress: bool = True,
    selection: Literal["explicit", "morris_top_mu_star"] = "explicit",
) -> tuple[SobolResult, list[ReproRecord]]:
    """Run Sobol variance decomposition.

    :param param_names: Parameters to analyze.
    :param samples: Base sample size (total = ``samples * (2*D + 2)``).
    :param max_ticks: Max ticks per simulation.
    :param seed: RNG seed threaded through every trial.
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param objective: Scores each trial's :class:`~tools.devtools.sim_analysis.backends.types.Result`.
    :param progress: Print progress to stdout.
    :returns: ``(result, repro_records)``.
    :raises ImportError: If SALib is not installed.
    :raises ValueError: If no parameter in ``param_names`` is a known tunable
        parameter.
    """
    if not HAS_SALIB:
        raise ImportError("SALib not installed. Install the dev dependency group: `uv sync`.")
    _validate_run_metadata(backend=backend, scenario=scenario)
    if not 1 <= samples <= MAX_SOBOL_BASE_SAMPLES:
        raise ValueError(
            f"Sobol base samples must be 1..{MAX_SOBOL_BASE_SAMPLES}; received {samples}"
        )

    problem = create_problem(param_names)
    definitions = _parameter_definitions(problem["names"])

    total_samples = samples * (2 * problem["num_vars"] + 2)
    _validate_workload(
        parameter_count=problem["num_vars"],
        evaluations=total_samples,
        max_ticks=max_ticks,
    )

    if progress:
        print("\nSobol Variance Decomposition Analysis")
        print(f"  Parameters: {problem['num_vars']}")
        print(f"  Base samples: {samples}")
        print(f"  Total samples: {total_samples}")
        print()

    param_values = sobol_sample.sample(
        problem,
        samples,
        calc_second_order=True,
        seed=seed,
    )
    if len(param_values) != total_samples:
        raise ValueError(
            f"Sobol sampler returned {len(param_values)} rows; expected {total_samples}"
        )
    outputs, repro_records = evaluate_simulation(
        param_values,
        problem["names"],
        max_ticks=max_ticks,
        seed=seed,
        backend=backend,
        scenario=scenario,
        objective=objective,
        progress=progress,
    )
    analysis_outputs = _validated_outputs(outputs, method="Sobol")

    analysis = sobol_analyze.analyze(
        problem,
        analysis_outputs,
        calc_second_order=True,
        seed=seed,
    )

    names: list[str] = problem["names"]
    parameters = {
        name: SobolParameterResult(
            S1=_finite(analysis["S1"][i], label=f"Sobol S1 for {name}"),
            S1_conf=_finite(analysis["S1_conf"][i], label=f"Sobol S1_conf for {name}"),
            ST=_finite(analysis["ST"][i], label=f"Sobol ST for {name}"),
            ST_conf=_finite(analysis["ST_conf"][i], label=f"Sobol ST_conf for {name}"),
        )
        for i, name in enumerate(names)
    }

    s2_interactions: dict[str, float] = {}
    if "S2" in analysis:
        for i, name_i in enumerate(names):
            for j, name_j in enumerate(names):
                if j > i:  # Upper triangle only
                    key = f"{name_i}:{name_j}"
                    s2_interactions[key] = _finite(
                        analysis["S2"][i, j],
                        label=f"Sobol S2 for {key}",
                    )

    ranking_s1 = tuple(sorted(names, key=lambda name: parameters[name].S1, reverse=True))
    ranking_st = tuple(sorted(names, key=lambda name: parameters[name].ST, reverse=True))
    trials = _build_trials(param_values, definitions, outputs, repro_records)

    result = SobolResult(
        base_samples=samples,
        total_samples=total_samples,
        seed=seed,
        max_ticks=max_ticks,
        backend=backend,
        scenario=scenario,
        selection=selection,
        base_defines=GameDefines().model_dump(mode="json"),
        parameter_definitions=definitions,
        trials=trials,
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
    backend: str = "in_memory",
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
    :param param_names: Parameter paths to analyze. Defaults to the curated
        eight-parameter :func:`get_default_params` surface when ``None``.
    :param trajectories: Morris trajectory count. Ignored for ``method="sobol"``.
    :param samples: Sobol base sample size. Ignored for ``method="morris"``.
    :param max_ticks: Maximum ticks per trial.
    :param seed: RNG seed threaded through every trial (Constitution III.7).
    :param backend: Must be ``"in_memory"``.
    :param scenario: In-memory scenario name.
    :param objective: Scores each trial's :class:`~tools.devtools.sim_analysis.backends.types.Result`
        (default: :func:`~tools.devtools.sim_analysis.objectives.carceral_objective`).
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
    _validate_run_metadata(backend=backend, scenario=scenario)
    parameter_count = len(_parameter_definitions(resolved_param_names))
    if method in ("morris", "both") and not 1 <= trajectories <= MAX_MORRIS_TRAJECTORIES:
        raise ValueError(
            f"Morris trajectories must be 1..{MAX_MORRIS_TRAJECTORIES}; received {trajectories}"
        )
    if method in ("sobol", "both") and not 1 <= samples <= MAX_SOBOL_BASE_SAMPLES:
        raise ValueError(
            f"Sobol base samples must be 1..{MAX_SOBOL_BASE_SAMPLES}; received {samples}"
        )
    morris_evaluations = trajectories * (parameter_count + 1)
    sobol_parameter_count = (
        min(DEFAULT_SOBOL_SCREENED_PARAMETERS, parameter_count)
        if method == "both"
        else parameter_count
    )
    sobol_evaluations = samples * (2 * sobol_parameter_count + 2)
    total_evaluations = (morris_evaluations if method in ("morris", "both") else 0) + (
        sobol_evaluations if method in ("sobol", "both") else 0
    )
    _validate_workload(
        parameter_count=parameter_count,
        evaluations=total_evaluations,
        max_ticks=max_ticks,
    )
    resolved_output_dir = output_dir if output_dir is not None else Path(DEFAULT_OUTPUT_DIR)
    resolved_morris_path = (
        morris_output if morris_output is not None else resolved_output_dir / "morris.json"
    )
    resolved_sobol_path = (
        sobol_output if sobol_output is not None else resolved_output_dir / "sobol.json"
    )
    if method == "both" and resolved_morris_path.resolve() == resolved_sobol_path.resolve():
        raise ValueError("Morris and Sobol output paths must be distinct")

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
            scenario=scenario,
            objective=objective,
            progress=progress,
        )
        repro_records.extend(morris_repro)

        morris_path = resolved_morris_path
        morris_path.parent.mkdir(parents=True, exist_ok=True)
        _write_strict_json(morris_path, morris_result)
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

        sobol_param_names = (
            list(morris_result.ranking[:DEFAULT_SOBOL_SCREENED_PARAMETERS])
            if method == "both" and morris_result is not None
            else resolved_param_names
        )
        sobol_result, sobol_repro = run_sobol_analysis(
            sobol_param_names,
            samples,
            max_ticks,
            seed=seed,
            backend=backend,
            scenario=scenario,
            objective=objective,
            progress=progress,
            selection="morris_top_mu_star" if method == "both" else "explicit",
        )
        repro_records.extend(sobol_repro)

        sobol_path = resolved_sobol_path
        sobol_path.parent.mkdir(parents=True, exist_ok=True)
        _write_strict_json(sobol_path, sobol_result)
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
    "DEFAULT_PARAMETER_NAMES",
    "DEFAULT_SOBOL_SCREENED_PARAMETERS",
    "MAX_PARAMETER_COUNT",
    "MAX_MORRIS_TRAJECTORIES",
    "MAX_SOBOL_BASE_SAMPLES",
    "MAX_TICKS",
    "MAX_EVALUATIONS",
    "MAX_TICK_EVALUATIONS",
    "MAX_ARTIFACT_BYTES",
    "DEFAULT_OUTPUT_DIR",
    "SensitivityMethod",
    "ParameterDefinition",
    "SensitivityTrial",
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
