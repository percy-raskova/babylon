"""Bayesian (Optuna TPE + Hyperband) parameter tuning for the Carceral trajectory.

Migrated from ``tools/tune_agent.py`` (the pre-package single source of truth
for this algorithm) onto the optimization core package
(:mod:`babylon.engine.optimization`): trials execute through
:func:`babylon.engine.optimization.runner_api.run` (not
``tools/shared.py::run_simulation``), the search space is introspected from
:func:`babylon.engine.optimization.params.get_tunable_parameters` instead of
a hand-maintained, disconnected bounds dict, and scoring routes through
:func:`babylon.engine.optimization.objectives.calculate_carceral_equilibrium_score`.

The optimization math itself — TPE sampling with a fixed seed for
reproducible search order, Hyperband pruning of non-viable trials, the
early-death prune threshold, the phase-milestone-count intermediate report
used by Hyperband, and the console results report — is carried over
unchanged from ``tools/tune_agent.py``.

Usage::

    from babylon.engine.optimization.bayesian import run_bayesian

    study = run_bayesian(study_name="carceral_v1", n_trials=200)
    print(study.best_value)

See Also:
    ai/carceral-equilibrium.md: the theoretical 100-year trajectory this
    objective scores against (Superwage Crisis, Class Decomposition,
    Control Ratio Crisis, Terminal Decision).
"""

from __future__ import annotations

import logging
from typing import Any, Final

from babylon.config.defines import GameDefines
from babylon.engine.optimization.objectives import (
    TICKS_PER_YEAR,
    calculate_carceral_equilibrium_score,
    format_phase_report,
)
from babylon.engine.optimization.params import (
    get_parameter_type,
    get_tunable_parameters,
    inject_parameters,
)
from babylon.engine.optimization.runner_api import run as run_trial

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

DEFAULT_MAX_TICKS: Final[int] = 5200
"""100 years at 52 ticks/year — matches ``runner_api.run``'s own default."""

EARLY_DEATH_THRESHOLD: Final[int] = 5 * TICKS_PER_YEAR
"""Prune a trial if the tracked entity dies before year 5."""

DEFAULT_STUDY_NAME: Final[str] = "babylon_carceral"
DEFAULT_STORAGE: Final[str] = "sqlite:///optuna.db"
DEFAULT_N_TRIALS: Final[int] = 100
DEFAULT_BACKEND: Final[str] = "headless"
DEFAULT_SEED: Final[int] = 2010
"""RNG seed for simulation trials — matches ``runner_api.run``'s own default."""

_TPE_SEED: Final[int] = 42
"""Fixed TPE sampler seed for reproducible *search order* across resumed
studies — distinct from ``DEFAULT_SEED``, which seeds each trial's
simulation RNG."""

_HYPERBAND_MIN_RESOURCE: Final[int] = 1
_HYPERBAND_MAX_RESOURCE: Final[int] = 4
_HYPERBAND_REDUCTION_FACTOR: Final[int] = 2

TUNING_CATEGORIES: Final[list[str]] = ["economy", "consciousness", "solidarity", "carceral"]
"""GameDefines categories relevant to Carceral Equilibrium trajectory timing."""

# Narrowing restriction of babylon.engine.optimization.params.get_tunable_parameters()
# down to the curated subset of parameters known (ai/carceral-equilibrium.md) to
# drive phase timing, with tighter-than-Field-constraint ranges for sample-efficient
# TPE search.
# This RETIRES the old tools/tune_agent.py::OPTIMIZATION_BOUNDS dict as an
# independent source of truth — every key here is validated against the real
# GameDefines schema (via get_tunable_parameters) by _resolve_search_space
# before use, so a typo'd or renamed path fails loudly instead of silently
# tuning nothing.
_NARROW_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    # Core economic parameters (affect accumulation and crisis timing)
    "economy.base_subsistence": (0.0002, 0.002),
    "economy.extraction_efficiency": (0.5, 0.95),
    "economy.comprador_cut": (0.75, 0.95),
    "economy.super_wage_rate": (0.10, 0.35),
    # Long-term decay drivers (affect when crises occur)
    "economy.trpf_coefficient": (0.0002, 0.002),
    "economy.trpf_efficiency_floor": (0.0, 0.1),
    "economy.rent_pool_decay": (0.0, 0.02),
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
    narrow_bounds: dict[str, tuple[float, float]] | None,
) -> dict[str, tuple[float, float]]:
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
        narrowing — search every introspected parameter under
        ``categories``. Every key must already be present in the
        introspected space.
    :returns: Dict mapping ``"category.field"`` -> ``(min_value, max_value)``
        — either the full introspected space, or exactly ``narrow_bounds``
        once its keys are validated.
    :raises ValueError: If ``narrow_bounds`` contains a key that is not a
        valid ``GameDefines`` path under ``categories`` — i.e. not a key
        :func:`get_tunable_parameters` itself produced.
    """
    full_space = get_tunable_parameters(categories=categories)
    if not narrow_bounds:
        return full_space

    unknown = sorted(set(narrow_bounds) - set(full_space))
    if unknown:
        raise ValueError(
            f"narrow_bounds keys are not valid GameDefines paths under "
            f"categories={categories!r}: {unknown}"
        )

    return dict(narrow_bounds)


def _sample_params(trial: Any, search_space: dict[str, tuple[float, float]]) -> dict[str, float]:
    """Sample one trial's parameters from ``search_space`` via Optuna.

    Uses :func:`get_parameter_type` to route each path to
    ``trial.suggest_int`` or ``trial.suggest_float``, then derives
    ``carceral.proletariat_fraction`` from ``carceral.enforcer_fraction``
    (implicit complementary-fraction constraint — the two must sum to 1.0).

    :param trial: The Optuna ``Trial`` suggesting values for this run.
    :param search_space: Dict mapping ``"category.field"`` -> ``(min, max)``,
        as produced by :func:`_resolve_search_space`.
    :returns: Dict mapping ``"category.field"`` -> sampled value, ready for
        :func:`~babylon.engine.optimization.params.inject_parameters`.
    """
    params: dict[str, float] = {}
    for param_path, (min_val, max_val) in search_space.items():
        param_type = get_parameter_type(param_path)
        short_name = param_path.split(".")[-1]
        if param_type is int:
            params[param_path] = float(trial.suggest_int(short_name, int(min_val), int(max_val)))
        else:
            params[param_path] = trial.suggest_float(short_name, min_val, max_val)

    if "carceral.enforcer_fraction" in params:
        params["carceral.proletariat_fraction"] = 1.0 - params["carceral.enforcer_fraction"]

    return params


def _map_best_params(
    best_params: dict[str, Any],
    search_space: dict[str, tuple[float, float]],
) -> dict[str, float]:
    """Map Optuna's short parameter names back to full ``GameDefines`` paths.

    :param best_params: ``study.best_params`` — keyed by the short name
        Optuna reports (``trial.suggest_*``'s first argument).
    :param search_space: The space the study was run against, as produced by
        :func:`_resolve_search_space`.
    :returns: Dict mapping ``"category.field"`` -> value.
    """
    mapped: dict[str, float] = {}
    for short_name, value in best_params.items():
        for full_path in search_space:
            if full_path.endswith(f".{short_name}"):
                mapped[full_path] = float(value)
                break
    if "carceral.enforcer_fraction" in mapped:
        mapped["carceral.proletariat_fraction"] = 1.0 - mapped["carceral.enforcer_fraction"]
    return mapped


# =============================================================================
# OBJECTIVE
# =============================================================================


def create_objective(
    search_space: dict[str, tuple[float, float]],
    max_ticks: int,
    backend: str,
    seed: int,
) -> Any:
    """Build an Optuna objective closed over one trial configuration.

    :param search_space: The space to sample from, as produced by
        :func:`_resolve_search_space`.
    :param max_ticks: Maximum simulation ticks per trial.
    :param backend: ``"headless"`` or ``"in_memory"`` — threaded straight
        into :func:`~babylon.engine.optimization.runner_api.run`.
    :param seed: RNG seed threaded into every trial (Constitution III.7 —
        every trial is independently reproducible given its sampled
        parameters, this seed, and this backend).
    :returns: A callable compatible with ``optuna.Study.optimize``.
    :raises ImportError: If Optuna is not installed.
    """
    if not HAS_OPTUNA:
        raise ImportError(
            "optuna is required for Bayesian tuning. Install the dev "
            "dependency group: `poetry install --with dev`."
        )

    def objective(trial: optuna.Trial) -> float:
        """Score one Optuna trial by Carceral Equilibrium phase timing.

        :param trial: Optuna trial object for parameter suggestion.
        :returns: Carceral Equilibrium score (0.0-100.0, higher is better).
        :raises optuna.TrialPruned: On early death, or when Hyperband's
            intermediate-value pruner decides this trial is not competitive.
        """
        params = _sample_params(trial, search_space)
        defines = inject_parameters(GameDefines(), params)

        # Infrastructure-layer boundary (project CLAUDE.md III): a crashed
        # trial simulation must not crash the whole study — it is scored as
        # a failed trial (0.0), not re-raised, mirroring
        # tools/tune_agent.py's original behavior.
        try:
            result = run_trial(defines, seed=seed, max_ticks=max_ticks, backend=backend)
        except Exception as exc:  # noqa: BLE001 - deliberate trial-failure boundary, see above
            logger.warning("Trial %d: simulation crashed: %s", trial.number, exc)
            return 0.0

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


def run_optimization(
    study_name: str = DEFAULT_STUDY_NAME,
    storage: str = DEFAULT_STORAGE,
    n_trials: int = DEFAULT_N_TRIALS,
    max_ticks: int = DEFAULT_MAX_TICKS,
    backend: str = DEFAULT_BACKEND,
    seed: int = DEFAULT_SEED,
    categories: list[str] | None = None,
    narrow_bounds: dict[str, tuple[float, float]] | None = None,
) -> optuna.Study:
    """Run (or resume) an Optuna study over the Carceral Equilibrium objective.

    :param study_name: Name for the study (enables resumption via
        ``load_if_exists``).
    :param storage: Optuna storage URL (SQLite by default — resumable and
        ``optuna-dashboard``-compatible).
    :param n_trials: Number of *new* optimization trials to run this call.
    :param max_ticks: Maximum simulation ticks per trial.
    :param backend: ``"headless"`` (Postgres-backed) or ``"in_memory"``
        (fast legacy engine) — see
        :func:`babylon.engine.optimization.runner_api.run`.
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
            "optuna is required for Bayesian tuning. Install the dev "
            "dependency group: `poetry install --with dev`."
        )

    resolved_categories = categories if categories is not None else TUNING_CATEGORIES
    resolved_narrow_bounds = narrow_bounds if narrow_bounds is not None else _NARROW_BOUNDS
    search_space = _resolve_search_space(resolved_categories, resolved_narrow_bounds)

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

    existing_trials = len(study.trials)
    if existing_trials > 0:
        logger.info("Resuming study with %d existing trials", existing_trials)

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
    narrow_bounds: dict[str, tuple[float, float]] | None = None,
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
    resolved_categories = categories if categories is not None else TUNING_CATEGORIES
    resolved_narrow_bounds = narrow_bounds if narrow_bounds is not None else _NARROW_BOUNDS
    search_space = _resolve_search_space(resolved_categories, resolved_narrow_bounds)

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
        lines.append(
            f"   All trials were pruned (entities died before year "
            f"{EARLY_DEATH_THRESHOLD // TICKS_PER_YEAR})."
        )
        lines.append("   This indicates the simulation parameters are fundamentally broken.")
        lines.append("\n   Likely causes:")
        lines.append("   - Subsistence burn rate too high relative to income")
        lines.append("   - Initial wealth insufficient for survival")
        lines.append("   - Production/extraction balance broken")
        lines.append("\n   Try running: mise run qa:audit")
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
    lines.append(f"  optuna-dashboard {storage}")
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
    narrow_bounds: dict[str, tuple[float, float]] | None = None,
    show_best: bool = False,
) -> optuna.Study:
    """Entry point for Bayesian (Optuna) Carceral Equilibrium tuning.

    Callable directly, or from the optimization package's CLI (argparse
    lives in the package ``__main__``, not here).

    :param study_name: Name for the optimization study.
    :param storage: SQLite (or other Optuna-supported) storage URL.
    :param n_trials: Number of new trials to run (ignored if ``show_best``).
    :param max_ticks: Maximum simulation ticks per trial.
    :param backend: ``"headless"`` or ``"in_memory"``.
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
            "optuna is required for Bayesian tuning. Install the dev "
            "dependency group: `poetry install --with dev`."
        )

    if show_best:
        try:
            study = optuna.load_study(study_name=study_name, storage=storage)
        except KeyError as exc:
            raise ValueError(f"Study {study_name!r} not found in {storage!r}") from exc
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
