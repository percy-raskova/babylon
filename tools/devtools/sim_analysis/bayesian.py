"""Development-only Bayesian analysis of the frozen Python reference simulation.

Trials execute through :func:`tools.devtools.sim_analysis.runner_api.run`.
The search space is introspected from
:func:`tools.devtools.sim_analysis.params.get_tunable_parameters` instead of
a hand-maintained, disconnected bounds dict, and scoring routes through
:func:`tools.devtools.sim_analysis.objectives.calculate_carceral_equilibrium_score`.

The optimization math itself — TPE sampling with a fixed seed for
reproducible fresh studies, Hyperband pruning of non-viable trials, the
early-death prune threshold, the phase-milestone-count intermediate report
used by Hyperband, and the console results report — is carried over
unchanged from ``tools/tune_agent.py``.

Usage::

    from tools.devtools.sim_analysis.bayesian import run_bayesian

    study = run_bayesian(study_name="carceral_v1", n_trials=200)
    print(study.best_value)

See Also:
    ai/carceral-equilibrium.md: the theoretical 100-year trajectory this
    objective scores against (Superwage Crisis, Class Decomposition,
    Control Ratio Crisis, Terminal Decision).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import shlex
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit

from tools.devtools.sim_analysis.objectives import (
    TICKS_PER_YEAR,
    calculate_carceral_equilibrium_score,
    format_phase_report,
)
from tools.devtools.sim_analysis.params import (
    ParameterBounds,
    ParameterValue,
    get_parameter_type,
    get_tunable_parameters,
    inject_parameters,
)
from tools.devtools.sim_analysis.runner_api import run as run_trial

from babylon.config.defines import GameDefines, canonical_defines_hash

try:
    import optuna
    from optuna.pruners import HyperbandPruner
    from optuna.samplers import TPESampler

    HAS_OPTUNA = True
except ImportError:  # pragma: no cover - exercised only without the dev group installed
    HAS_OPTUNA = False

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_N_TRIALS: Final[int] = 1_000
MAX_TICKS: Final[int] = 5_200
MAX_TICK_EVALUATIONS: Final[int] = 2_000_000
DEFAULT_MAX_TICKS: Final[int] = MAX_TICKS
"""100 years at 52 ticks/year — matches ``runner_api.run``'s own default."""

EARLY_DEATH_THRESHOLD: Final[int] = 5 * TICKS_PER_YEAR
"""Prune a trial if the tracked entity dies before year 5."""

DEFAULT_STUDY_NAME: Final[str] = "babylon_carceral"
DEFAULT_STORAGE: Final[str] = "sqlite:///optuna.db"
DEFAULT_N_TRIALS: Final[int] = 100
DEFAULT_BACKEND: Final[str] = "in_memory"
DEFAULT_SEED: Final[int] = 2010
"""RNG seed for simulation trials — matches ``runner_api.run``'s own default."""

_TPE_SEED: Final[int] = 42
"""Fixed TPE seed for reproducible fresh studies.

Optuna's RDB storage preserves trials but not sampler RNG state, so a resumed
study is durable but is not claimed to match one uninterrupted process. This
is distinct from ``DEFAULT_SEED``, which seeds each trial's simulation RNG.
"""

_HYPERBAND_MIN_RESOURCE: Final[int] = 1
_HYPERBAND_MAX_RESOURCE: Final[int] = 4
_HYPERBAND_REDUCTION_FACTOR: Final[int] = 2

_EXPERIMENT_ATTRIBUTE: Final[str] = "babylon.experiment-manifest.v1"
_EXPERIMENT_SCHEMA: Final[str] = "babylon.sim-analysis.optuna-experiment.v1"
_SOURCE_FILE_LIMIT: Final[int] = 5_000
_SOURCE_BYTE_LIMIT: Final[int] = 64 * 1024 * 1024
_SOURCE_READ_CHUNK_BYTES: Final[int] = 64 * 1024
_CARCERAL_DRIVER_PATH: Final[str] = "carceral.enforcer_fraction"
_CARCERAL_DERIVED_PATH: Final[str] = "carceral.proletariat_fraction"

TUNING_CATEGORIES: Final[list[str]] = ["economy", "consciousness", "solidarity", "carceral"]
"""GameDefines categories relevant to Carceral Equilibrium trajectory timing."""

# Narrowing restriction of tools.devtools.sim_analysis.params.get_tunable_parameters()
# down to the curated subset of parameters known (ai/carceral-equilibrium.md) to
# drive phase timing, with tighter-than-Field-constraint ranges for sample-efficient
# TPE search.
# This RETIRES the old tools/tune_agent.py::OPTIMIZATION_BOUNDS dict as an
# independent source of truth — every key here is validated against the real
# GameDefines schema (via get_tunable_parameters) by _resolve_search_space
# before use, so a typo'd or renamed path fails loudly instead of silently
# tuning nothing.
_NARROW_BOUNDS: Final[dict[str, ParameterBounds]] = {
    # Core economic parameters (affect accumulation and crisis timing)
    "economy.base_subsistence": (0.0002, 0.002),
    "economy.extraction_efficiency": (0.5, 0.95),
    "economy.comprador_cut": (0.75, 0.95),
    "economy.super_wage_rate": (0.10, 0.35),
    # Long-term decay drivers (affect when crises occur)
    "economy.trpf_coefficient": (0.0002, 0.002),
    "economy.trpf_efficiency_floor": (0.0, 0.1),
    "economy.rent_pool_decay": (0.0, 0.01),
    # Consciousness and solidarity (affect terminal outcome)
    "consciousness.sensitivity": (0.2, 0.8),
    "solidarity.scaling_factor": (0.3, 0.9),
    # Carceral parameters (affect control ratio crisis and terminal decision)
    "carceral.control_capacity": (1, 10),
    "carceral.enforcer_fraction": (0.05, 0.30),
}


# =============================================================================
# SEARCH SPACE
# =============================================================================


def _resolve_search_space(
    categories: list[str] | None,
    narrow_bounds: dict[str, ParameterBounds] | None,
) -> dict[str, ParameterBounds]:
    """Derive the Optuna search space from :func:`get_tunable_parameters`.

    ``narrow_bounds`` — when non-empty — *restricts* the search to exactly
    its keys (with its tighter bounds), rather than merely overriding a few
    entries within the full introspected space: this is what makes it a
    genuine narrowing (matching ``tools/tune_agent.py``'s original 11-key
    ``OPTIMIZATION_BOUNDS`` search space) instead of silently widening the
    search to every tunable field across ``categories``.

    :param categories: ``GameDefines`` category names to introspect (``None``
        for all categories).
    :param narrow_bounds: Optional tighter ``(min, max)`` bounds for a
        curated subset of parameters. Falsy (``None`` or ``{}``) means no
        narrowing — search every independent introspected parameter under
        ``categories``. The proletariat fraction is excluded whenever its
        complementary enforcer fraction is present because it is derived,
        not an independent Optuna dimension. Every explicit key must already
        be present in the introspected space.
    :returns: Dict mapping ``"category.field"`` -> ``(min_value, max_value)``
        — either the full introspected space, or exactly ``narrow_bounds``
        once its keys are validated.
    :raises ValueError: If ``narrow_bounds`` contains a key that is not a
        valid ``GameDefines`` path under ``categories`` — i.e. not a key
        :func:`get_tunable_parameters` itself produced.
    """
    full_space = get_tunable_parameters(categories=categories)
    if not narrow_bounds:
        if _CARCERAL_DRIVER_PATH in full_space:
            full_space.pop(_CARCERAL_DERIVED_PATH, None)
        return full_space

    unknown = sorted(set(narrow_bounds) - set(full_space))
    if unknown:
        raise ValueError(
            f"narrow_bounds keys are not valid GameDefines paths under "
            f"categories={categories!r}: {unknown}"
        )
    if {_CARCERAL_DRIVER_PATH, _CARCERAL_DERIVED_PATH} <= narrow_bounds.keys():
        raise ValueError(
            f"{_CARCERAL_DERIVED_PATH} is derived from {_CARCERAL_DRIVER_PATH}; "
            "they cannot both be independent Optuna dimensions"
        )

    resolved: dict[str, ParameterBounds] = {}
    for param_path, requested_bounds in narrow_bounds.items():
        if len(requested_bounds) != 2:
            raise ValueError(f"narrow_bounds for {param_path} must contain exactly two values")
        lower, upper = requested_bounds
        parameter_type = get_parameter_type(param_path)

        if parameter_type is int:
            if type(lower) is not int or type(upper) is not int:
                raise TypeError(
                    f"Integer parameter {param_path} requires integer bounds, "
                    f"got {requested_bounds!r}"
                )
            normalized: ParameterBounds = (lower, upper)
        else:
            if isinstance(lower, bool) or not isinstance(lower, (int, float)):
                raise TypeError(f"Float parameter {param_path} has invalid lower bound {lower!r}")
            if isinstance(upper, bool) or not isinstance(upper, (int, float)):
                raise TypeError(f"Float parameter {param_path} has invalid upper bound {upper!r}")
            normalized = (float(lower), float(upper))

        normalized_lower, normalized_upper = normalized
        if not math.isfinite(float(normalized_lower)) or not math.isfinite(float(normalized_upper)):
            raise ValueError(f"narrow_bounds for {param_path} must be finite: {normalized!r}")
        if normalized_lower > normalized_upper:
            raise ValueError(f"narrow_bounds for {param_path} are reversed: {normalized!r}")

        schema_lower, schema_upper = full_space[param_path]
        if normalized_lower < schema_lower or normalized_upper > schema_upper:
            raise ValueError(
                f"narrow_bounds for {param_path}={normalized!r} exceed its sampleable "
                f"GameDefines bounds {(schema_lower, schema_upper)!r}"
            )
        resolved[param_path] = normalized

    return resolved


def _resolve_experiment_search_space(
    categories: list[str] | None,
    narrow_bounds: dict[str, ParameterBounds] | None,
) -> dict[str, ParameterBounds]:
    """Resolve one experiment space with category-aware curated defaults."""
    resolved_categories = categories if categories is not None else TUNING_CATEGORIES
    if not resolved_categories:
        raise ValueError("categories must contain at least one GameDefines category")
    resolved_bounds = narrow_bounds
    if resolved_bounds is None:
        selected_categories = set(resolved_categories)
        resolved_bounds = {
            path: bounds
            for path, bounds in _NARROW_BOUNDS.items()
            if path.partition(".")[0] in selected_categories
        }
    search_space = _resolve_search_space(resolved_categories, resolved_bounds)
    if not search_space:
        raise ValueError(
            f"categories={resolved_categories!r} contain no tunable GameDefines parameters"
        )
    return search_space


def _validate_independent_search_space(search_space: dict[str, ParameterBounds]) -> None:
    """Reject a driver and its derived complement as separate dimensions."""
    if {_CARCERAL_DRIVER_PATH, _CARCERAL_DERIVED_PATH} <= search_space.keys():
        raise ValueError(
            f"{_CARCERAL_DERIVED_PATH} is derived from {_CARCERAL_DRIVER_PATH}; "
            "they cannot both be independent Optuna dimensions"
        )


def _validate_max_ticks(max_ticks: int) -> None:
    """Reject an invalid per-trial simulation horizon."""
    if not 1 <= max_ticks <= MAX_TICKS:
        raise ValueError(f"max_ticks must be 1..{MAX_TICKS}, got: {max_ticks}")


def _validate_optimization_workload(n_trials: int, max_ticks: int) -> None:
    """Reject unbounded Optuna campaigns before storage or simulation work."""
    if not 1 <= n_trials <= MAX_N_TRIALS:
        raise ValueError(f"n_trials must be 1..{MAX_N_TRIALS}, got: {n_trials}")
    _validate_max_ticks(max_ticks)
    tick_evaluations = n_trials * max_ticks
    if tick_evaluations > MAX_TICK_EVALUATIONS:
        raise ValueError(
            "Optuna workload exceeds the tick budget: "
            f"{n_trials} trials * {max_ticks} ticks = {tick_evaluations}, "
            f"limit {MAX_TICK_EVALUATIONS}"
        )


def _validate_storage_url(storage: str) -> None:
    """Allow only secret-free local SQLite storage for this development tool."""
    try:
        parsed = urlsplit(storage)
    except ValueError as exc:
        raise ValueError("Optuna storage must be a local SQLite URL") from exc
    if (
        parsed.scheme != "sqlite"
        or parsed.netloc
        or not parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Optuna storage must be a local SQLite URL such as sqlite:///optuna.db")


def _validate_sampled_value(
    param_path: str,
    value: Any,
    bounds: ParameterBounds,
) -> ParameterValue:
    """Refuse sampler values with the wrong native type or outside the space."""
    parameter_type = get_parameter_type(param_path)
    if parameter_type is int:
        if type(value) is not int:
            raise TypeError(f"Sampler returned non-int value for {param_path}: {value!r}")
        normalized: ParameterValue = value
    else:
        if type(value) is not float:
            raise TypeError(f"Sampler returned non-float value for {param_path}: {value!r}")
        normalized = value

    if not math.isfinite(float(normalized)):
        raise ValueError(f"Sampler returned non-finite value for {param_path}: {value!r}")
    lower, upper = bounds
    if normalized < lower or normalized > upper:
        raise ValueError(
            f"Sampler returned out-of-bounds value for {param_path}: {value!r} not in {bounds!r}"
        )
    return normalized


def _sample_params(
    trial: Any,
    search_space: dict[str, ParameterBounds],
) -> dict[str, ParameterValue]:
    """Sample one trial's parameters from ``search_space`` via Optuna.

    Uses :func:`get_parameter_type` to route each path to
    ``trial.suggest_int`` or ``trial.suggest_float``, then derives
    ``carceral.proletariat_fraction`` from ``carceral.enforcer_fraction``
    (implicit complementary-fraction constraint — the two must sum to 1.0).

    :param trial: The Optuna ``Trial`` suggesting values for this run.
    :param search_space: Dict mapping ``"category.field"`` -> ``(min, max)``,
        as produced by :func:`_resolve_search_space`.
    :returns: Dict mapping ``"category.field"`` -> sampled value, ready for
        :func:`~tools.devtools.sim_analysis.params.inject_parameters`.
    """
    _validate_independent_search_space(search_space)
    params: dict[str, ParameterValue] = {}
    for param_path, (min_val, max_val) in search_space.items():
        param_type = get_parameter_type(param_path)
        if param_type is int:
            if type(min_val) is not int or type(max_val) is not int:
                raise TypeError(
                    f"Integer parameter {param_path} requires native integer bounds, "
                    f"got {(min_val, max_val)!r}"
                )
            proposed = trial.suggest_int(param_path, min_val, max_val)
        else:
            proposed = trial.suggest_float(param_path, float(min_val), float(max_val))
        params[param_path] = _validate_sampled_value(param_path, proposed, (min_val, max_val))

    if "carceral.enforcer_fraction" in params:
        params["carceral.proletariat_fraction"] = 1.0 - params["carceral.enforcer_fraction"]

    return params


def _map_best_params(
    best_params: dict[str, Any],
    search_space: dict[str, ParameterBounds],
) -> dict[str, ParameterValue]:
    """Validate Optuna's canonical parameter paths for ``GameDefines``.

    :param best_params: ``study.best_params`` — keyed by the full parameter
        path passed to ``trial.suggest_*``.
    :param search_space: The space the study was run against, as produced by
        :func:`_resolve_search_space`.
    :returns: Dict mapping ``"category.field"`` -> value.
    """
    _validate_independent_search_space(search_space)
    unknown = sorted(set(best_params) - set(search_space))
    if unknown:
        raise ValueError(f"Optuna reported parameters outside this search space: {unknown}")

    mapped = {
        param_path: _validate_sampled_value(
            param_path,
            value,
            search_space[param_path],
        )
        for param_path, value in best_params.items()
    }
    if "carceral.enforcer_fraction" in mapped:
        mapped["carceral.proletariat_fraction"] = 1.0 - mapped["carceral.enforcer_fraction"]
    return mapped


# =============================================================================
# OBJECTIVE
# =============================================================================


def create_objective(
    search_space: dict[str, ParameterBounds],
    max_ticks: int,
    backend: str,
    seed: int,
) -> Any:
    """Build an Optuna objective closed over one trial configuration.

    :param search_space: The space to sample from, as produced by
        :func:`_resolve_search_space`.
    :param max_ticks: Maximum simulation ticks per trial.
    :param backend: Must be ``"in_memory"``.
    :param seed: RNG seed threaded into every trial (Constitution III.7 —
        every trial is independently reproducible given its sampled
        parameters, this seed, and this backend).
    :returns: A callable compatible with ``optuna.Study.optimize``.
    :raises ImportError: If Optuna is not installed.
    """
    if not HAS_OPTUNA:
        raise ImportError(
            "optuna is required for Bayesian tuning. Install the dev dependency group: `uv sync`."
        )
    _validate_max_ticks(max_ticks)
    if backend != DEFAULT_BACKEND:
        raise ValueError(f"backend must be {DEFAULT_BACKEND!r}, got: {backend!r}")

    def objective(trial: optuna.Trial) -> float:
        """Score one Optuna trial by Carceral Equilibrium phase timing.

        :param trial: Optuna trial object for parameter suggestion.
        :returns: Carceral Equilibrium score (0.0-100.0, higher is better).
        :raises optuna.TrialPruned: On early death, or when Hyperband's
            intermediate-value pruner decides this trial is not competitive.
        """
        params = _sample_params(trial, search_space)
        # Parameter validation intentionally remains outside the simulation
        # failure boundary. Invalid proposals are failed trials, never valid
        # simulations assigned a misleading zero score.
        defines = inject_parameters(GameDefines(), params)

        # Unexpected simulation faults propagate so Optuna and the caller
        # cannot mistake broken execution for a completed zero-score trial.
        result = run_trial(defines, seed=seed, max_ticks=max_ticks, backend=backend)

        if result.ticks_survived < EARLY_DEATH_THRESHOLD:
            raise optuna.TrialPruned()

        score = calculate_carceral_equilibrium_score(
            phase_milestones=result.phase_milestones,
            terminal_outcome=result.terminal_outcome,
            max_ticks=max_ticks,
        )

        phases_reached = sum(1 for v in result.phase_milestones.values() if v is not None)
        trial.report(score, phases_reached)
        if trial.should_prune():
            raise optuna.TrialPruned()

        return score

    return objective


# =============================================================================
# STUDY EXECUTION
# =============================================================================


def _source_tree_sha256(repository_root: Path | None = None) -> str:
    """Hash the Python simulation and analysis source used by an experiment."""
    root = (
        repository_root.resolve()
        if repository_root is not None
        else Path(__file__).resolve().parents[3]
    )
    candidates = list((root / "src" / "babylon").rglob("*.py"))
    candidates.extend((root / "tools" / "devtools" / "sim_analysis").rglob("*.py"))
    candidates.extend(
        path
        for path in (
            root / "src" / "babylon" / "data" / "defines.yaml",
            root / "pyproject.toml",
            root / "uv.lock",
        )
        if path.is_file()
    )
    files = sorted(set(candidates), key=lambda path: path.relative_to(root).as_posix())
    if not files:
        raise ValueError("Optuna experiment source fingerprint found no source files")
    if len(files) > _SOURCE_FILE_LIMIT:
        raise ValueError(f"Optuna experiment source fingerprint exceeds {_SOURCE_FILE_LIMIT} files")

    digest = hashlib.sha256()
    total_bytes = 0
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        try:
            with path.open("rb") as source:
                while chunk := source.read(_SOURCE_READ_CHUNK_BYTES):
                    total_bytes += len(chunk)
                    if total_bytes > _SOURCE_BYTE_LIMIT:
                        raise ValueError(
                            "Optuna experiment source fingerprint exceeds "
                            f"{_SOURCE_BYTE_LIMIT} bytes"
                        )
                    digest.update(chunk)
        except OSError as exc:
            raise ValueError(f"Cannot fingerprint Optuna source file {relative!r}") from exc
    return digest.hexdigest()


def _experiment_manifest(
    search_space: dict[str, ParameterBounds],
    *,
    max_ticks: int,
    backend: str,
    seed: int,
) -> dict[str, Any]:
    """Build the persisted identity that makes resumed trial scores comparable."""
    _validate_independent_search_space(search_space)
    parameters = [
        {
            "name": name,
            "native_type": get_parameter_type(name).__name__,
            "lower": bounds[0],
            "upper": bounds[1],
        }
        for name, bounds in sorted(search_space.items())
    ]
    payload: dict[str, Any] = {
        "schema": _EXPERIMENT_SCHEMA,
        "source_tree_sha256": _source_tree_sha256(),
        "base_defines_sha256": canonical_defines_hash(GameDefines()),
        "scenario": "imperial_circuit",
        "backend": backend,
        "simulation_seed": seed,
        "max_ticks": max_ticks,
        "objective": (
            "tools.devtools.sim_analysis.objectives:calculate_carceral_equilibrium_score"
        ),
        "parameters": parameters,
        "sampler": {"name": "TPESampler", "seed": _TPE_SEED, "multivariate": True},
        "pruner": {
            "name": "HyperbandPruner",
            "min_resource": _HYPERBAND_MIN_RESOURCE,
            "max_resource": _HYPERBAND_MAX_RESOURCE,
            "reduction_factor": _HYPERBAND_REDUCTION_FACTOR,
        },
    }
    canonical = json.dumps(
        payload,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    payload["fingerprint_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def _validate_or_record_experiment(
    study: Any,
    manifest: dict[str, Any],
) -> None:
    """Record a new study identity or refuse an incompatible resumption."""
    stored = study.user_attrs.get(_EXPERIMENT_ATTRIBUTE)
    if stored is None:
        if study.trials:
            raise ValueError(
                "Existing Optuna study has trials but no Babylon experiment fingerprint; "
                "use a new study name or storage"
            )
        study.set_user_attr(_EXPERIMENT_ATTRIBUTE, manifest)
        return
    if stored != manifest:
        stored_fingerprint = (
            stored.get("fingerprint_sha256", "unknown") if isinstance(stored, dict) else "invalid"
        )
        raise ValueError(
            "Optuna experiment fingerprint mismatch "
            f"(stored={stored_fingerprint}, current={manifest['fingerprint_sha256']}); "
            "use a new study name or storage"
        )


def run_optimization(
    study_name: str = DEFAULT_STUDY_NAME,
    storage: str = DEFAULT_STORAGE,
    n_trials: int = DEFAULT_N_TRIALS,
    max_ticks: int = DEFAULT_MAX_TICKS,
    backend: str = DEFAULT_BACKEND,
    seed: int = DEFAULT_SEED,
    categories: list[str] | None = None,
    narrow_bounds: dict[str, ParameterBounds] | None = None,
) -> optuna.Study:
    """Run (or resume) an Optuna study over the Carceral Equilibrium objective.

    :param study_name: Name for the study (enables resumption via
        ``load_if_exists``).
    :param storage: Secret-free local SQLite URL (resumable and
        ``optuna-dashboard``-compatible).
    :param n_trials: Number of *new* optimization trials to run this call.
    :param max_ticks: Maximum simulation ticks per trial.
    :param backend: Must be ``"in_memory"``.
    :param seed: RNG seed threaded into every trial.
    :param categories: ``GameDefines`` categories to introspect for the
        search space (default: :data:`TUNING_CATEGORIES`).
    :param narrow_bounds: Optional tighter bounds overlay (default:
        :data:`_NARROW_BOUNDS`); pass ``{}`` to search the full introspected
        space unnarrowed.
    :returns: The (possibly resumed) Optuna ``Study`` after ``n_trials`` more
        trials.
    :raises ImportError: If Optuna is not installed.
    """
    if not HAS_OPTUNA:
        raise ImportError(
            "optuna is required for Bayesian tuning. Install the dev dependency group: `uv sync`."
        )
    _validate_optimization_workload(n_trials, max_ticks)
    _validate_storage_url(storage)
    if backend != DEFAULT_BACKEND:
        raise ValueError(f"backend must be {DEFAULT_BACKEND!r}, got: {backend!r}")

    search_space = _resolve_experiment_search_space(categories, narrow_bounds)
    experiment_manifest = _experiment_manifest(
        search_space,
        max_ticks=max_ticks,
        backend=backend,
        seed=seed,
    )

    logger.info("Creating/loading study: %s", study_name)
    logger.info("Storage: %s", storage)
    logger.info("Trials: %d", n_trials)
    logger.info("Max ticks per trial: %d (%d years)", max_ticks, max_ticks // TICKS_PER_YEAR)
    logger.info("Backend: %s", backend)

    # Conservative pruning: keep 50% at each stage, don't prune before 5 years.
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        sampler=TPESampler(seed=_TPE_SEED, multivariate=True),
        pruner=HyperbandPruner(
            min_resource=_HYPERBAND_MIN_RESOURCE,
            max_resource=_HYPERBAND_MAX_RESOURCE,
            reduction_factor=_HYPERBAND_REDUCTION_FACTOR,
        ),
        direction="maximize",
        load_if_exists=True,
    )
    _validate_or_record_experiment(study, experiment_manifest)

    existing_trials = len(study.trials)
    if existing_trials > 0:
        logger.info("Resuming study with %d existing trials", existing_trials)
        logger.info(
            "Optuna storage preserves trials, not sampler RNG state; "
            "exact uninterrupted search-order equivalence is not claimed"
        )

    study.optimize(
        create_objective(search_space, max_ticks, backend, seed),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    return study


# =============================================================================
# REPORTING
# =============================================================================


def format_results(
    study: optuna.Study,
    max_ticks: int,
    backend: str,
    seed: int,
    storage: str,
    categories: list[str] | None = None,
    narrow_bounds: dict[str, ParameterBounds] | None = None,
) -> str:
    """Format a human-readable optimization results report.

    Re-runs the study's best parameters (via the same ``backend``/``seed``)
    to show full phase timing alongside the summary statistics.

    :param study: Completed (or partially-run) Optuna study.
    :param max_ticks: Simulation length used (for context and the re-run).
    :param backend: Backend the study's trials ran under.
    :param seed: RNG seed to re-run the best trial with.
    :param storage: The study's storage URL (echoed in the
        ``optuna-dashboard`` hint).
    :param categories: Categories the study's search space was built from
        (default: :data:`TUNING_CATEGORIES`) — needed to reconstruct the
        search space for mapping ``study.best_params`` back to full paths.
    :param narrow_bounds: Narrowing restriction the study's search space was
        built from (default: :data:`_NARROW_BOUNDS`; ``{}`` for unnarrowed).
    :returns: Multi-line report string.
    """
    _validate_max_ticks(max_ticks)
    _validate_storage_url(storage)
    search_space = _resolve_experiment_search_space(categories, narrow_bounds)

    lines: list[str] = ["", "=" * 70, "CARCERAL EQUILIBRIUM OPTIMIZATION RESULTS", "=" * 70]

    completed = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
    pruned = len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])
    failed = len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL])

    lines.append(f"\nTrials: {len(study.trials)} total")
    lines.append(f"  - Completed: {completed}")
    lines.append(f"  - Pruned: {pruned}")
    lines.append(f"  - Failed: {failed}")

    if completed == 0:
        lines.append("\nWARNING: No trials completed!")
        if not study.trials:
            lines.append("   The study contains no trials.")
        else:
            other = len(study.trials) - pruned - failed
            lines.append(
                f"   Observed terminal states: {pruned} pruned, {failed} failed, {other} other."
            )
            lines.append(
                "   Inspect failed-trial exceptions and pruning reasons before "
                "interpreting the parameter space."
            )
        lines.append("\n   Try a bounded diagnostic sweep: mise run analysis:sweep 52")
    elif study.best_trial:
        lines.append(f"\nBest Carceral Equilibrium Score: {study.best_value:.2f}/100")
        lines.append("\nBest Parameters:")
        for key, value in study.best_params.items():
            lines.append(f"  {key}: {value:.6f}")

        lines.append("\n" + "-" * 70)
        lines.append("Running best parameters to show phase timing...")

        params = _map_best_params(study.best_params, search_space)
        defines = inject_parameters(GameDefines(), params)

        try:
            result = run_trial(defines, seed=seed, max_ticks=max_ticks, backend=backend)
            report = format_phase_report(
                result.phase_milestones, result.terminal_outcome, max_ticks
            )
            lines.append(report)
        except Exception as exc:  # noqa: BLE001 - reporting-only re-run, never fatal to the report
            lines.append(f"Could not re-run best trial: {exc}")

        score = study.best_value
        if score >= 80:
            lines.append("\nEXCELLENT: Full Carceral Equilibrium trajectory achieved!")
            lines.append("   All phase transitions occurred within expected windows.")
        elif score >= 60:
            lines.append("\nGOOD: Most phase transitions occurred.")
            lines.append("   Some timing adjustments may improve the trajectory.")
        elif score >= 40:
            lines.append("\nPARTIAL: Some phase transitions occurred.")
            lines.append("   Parameters need tuning to trigger later phases.")
        elif score > 0:
            lines.append("\nWEAK: Few phase transitions occurred.")
            lines.append("   Simulation may be too stable or unstable.")
        else:
            lines.append("\nNO PHASES: No Carceral Equilibrium phases detected.")
            lines.append("   Parameters prevent the theoretical trajectory.")

    lines.append("\n" + "=" * 70)
    lines.append("To visualize results, run:")
    lines.append(f"  uv run optuna-dashboard {shlex.quote(storage)}")
    lines.append("=" * 70)

    return "\n".join(lines)


# =============================================================================
# ENTRY POINT
# =============================================================================


def run_bayesian(
    *,
    study_name: str = DEFAULT_STUDY_NAME,
    storage: str = DEFAULT_STORAGE,
    n_trials: int = DEFAULT_N_TRIALS,
    max_ticks: int = DEFAULT_MAX_TICKS,
    backend: str = DEFAULT_BACKEND,
    seed: int = DEFAULT_SEED,
    categories: list[str] | None = None,
    narrow_bounds: dict[str, ParameterBounds] | None = None,
    show_best: bool = False,
) -> optuna.Study:
    """Entry point for Bayesian (Optuna) Carceral Equilibrium tuning.

    Callable directly, or from the analysis package's CLI (argparse
    lives in the package ``__main__``, not here).

    :param study_name: Name for the optimization study.
    :param storage: Secret-free local SQLite storage URL.
    :param n_trials: Number of new trials to run (ignored if ``show_best``).
    :param max_ticks: Maximum simulation ticks per trial.
    :param backend: Must be ``"in_memory"``.
    :param seed: RNG seed threaded into every trial.
    :param categories: ``GameDefines`` categories to search over (default:
        :data:`TUNING_CATEGORIES`).
    :param narrow_bounds: Curated-subset restriction atop the introspected
        space (default: :data:`_NARROW_BOUNDS`; ``{}`` for unnarrowed).
    :param show_best: If ``True``, skip running new trials and only load +
        report the existing study.
    :returns: The Optuna ``Study`` (new trials run, or loaded as-is when
        ``show_best``).
    :raises ImportError: If Optuna is not installed.
    :raises ValueError: If ``show_best`` is set but ``study_name`` does not
        exist in ``storage``.
    """
    if not HAS_OPTUNA:
        raise ImportError(
            "optuna is required for Bayesian tuning. Install the dev dependency group: `uv sync`."
        )
    if show_best:
        _validate_max_ticks(max_ticks)
    else:
        _validate_optimization_workload(n_trials, max_ticks)
    _validate_storage_url(storage)
    if backend != DEFAULT_BACKEND:
        raise ValueError(f"backend must be {DEFAULT_BACKEND!r}, got: {backend!r}")

    if show_best:
        try:
            study = optuna.load_study(study_name=study_name, storage=storage)
        except KeyError as exc:
            raise ValueError(f"Study {study_name!r} not found in {storage!r}") from exc
        search_space = _resolve_experiment_search_space(categories, narrow_bounds)
        manifest = _experiment_manifest(
            search_space,
            max_ticks=max_ticks,
            backend=backend,
            seed=seed,
        )
        _validate_or_record_experiment(study, manifest)
    else:
        study = run_optimization(
            study_name=study_name,
            storage=storage,
            n_trials=n_trials,
            max_ticks=max_ticks,
            backend=backend,
            seed=seed,
            categories=categories,
            narrow_bounds=narrow_bounds,
        )

    print(
        format_results(
            study,
            max_ticks=max_ticks,
            backend=backend,
            seed=seed,
            storage=storage,
            categories=categories,
            narrow_bounds=narrow_bounds,
        )
    )

    return study


__all__ = [
    "HAS_OPTUNA",
    "DEFAULT_MAX_TICKS",
    "MAX_N_TRIALS",
    "MAX_TICKS",
    "MAX_TICK_EVALUATIONS",
    "EARLY_DEATH_THRESHOLD",
    "DEFAULT_STUDY_NAME",
    "DEFAULT_STORAGE",
    "DEFAULT_N_TRIALS",
    "DEFAULT_BACKEND",
    "DEFAULT_SEED",
    "TUNING_CATEGORIES",
    "create_objective",
    "run_optimization",
    "format_results",
    "run_bayesian",
]
