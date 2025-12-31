#!/usr/bin/env python3
"""Autonomous parameter tuning agent using Optuna Bayesian Optimization.

This tool uses TPE (Tree-structured Parzen Estimator) for sample-efficient
optimization and Hyperband pruning to kill non-viable simulations early.

Usage:
    poetry run python tools/tune_agent.py
    poetry run python tools/tune_agent.py --study-name imperial_v1 --trials 200
    poetry run python tools/tune_agent.py --study-name imperial_v1  # resumes

The objective function maximizes a composite score:
    Score = (ticks_survived * 10) + (final_rent_pool / 10)

This balances survival duration with economic health of the imperial circuit.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Final

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import optuna
from optuna.pruners import HyperbandPruner
from optuna.samplers import TPESampler

# Import reusable functions from tune_parameters
from tune_parameters import inject_parameter, is_dead

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step

# Configure Optuna logging
optuna.logging.set_verbosity(optuna.logging.INFO)

# Constants
COMPRADOR_ID: Final[str] = "C002"
PERIPHERY_WORKER_ID: Final[str] = "C001"
DEFAULT_MAX_TICKS: Final[int] = 52
EARLY_DEATH_THRESHOLD: Final[int] = 10  # Prune if Comprador dies before this tick
DEFAULT_STUDY_NAME: Final[str] = "babylon_tune"
DEFAULT_STORAGE: Final[str] = "sqlite:///optuna.db"
DEFAULT_N_TRIALS: Final[int] = 100

# Search space definition (5 parameters - extended)
SEARCH_SPACE: Final[dict[str, tuple[float, float]]] = {
    "economy.extraction_efficiency": (0.1, 0.9),
    "economy.comprador_cut": (0.5, 1.0),
    "economy.super_wage_rate": (0.05, 0.35),
    "survival.default_subsistence": (0.1, 0.5),
    "survival.steepness_k": (1.0, 10.0),
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_objective(max_ticks: int = DEFAULT_MAX_TICKS) -> Any:
    """Factory for objective function with configurable max_ticks.

    Args:
        max_ticks: Maximum simulation ticks to run

    Returns:
        Objective function compatible with Optuna study.optimize()
    """

    def objective(trial: optuna.Trial) -> float:
        """Optuna objective function for parameter optimization.

        Args:
            trial: Optuna trial object for parameter suggestion

        Returns:
            Composite score (higher is better)

        Raises:
            optuna.TrialPruned: When simulation shows early failure
        """
        # 1. Sample parameters from search space
        extraction = trial.suggest_float(
            "extraction_efficiency",
            SEARCH_SPACE["economy.extraction_efficiency"][0],
            SEARCH_SPACE["economy.extraction_efficiency"][1],
        )
        comprador_cut = trial.suggest_float(
            "comprador_cut",
            SEARCH_SPACE["economy.comprador_cut"][0],
            SEARCH_SPACE["economy.comprador_cut"][1],
        )
        super_wage_rate = trial.suggest_float(
            "super_wage_rate",
            SEARCH_SPACE["economy.super_wage_rate"][0],
            SEARCH_SPACE["economy.super_wage_rate"][1],
        )
        subsistence = trial.suggest_float(
            "default_subsistence",
            SEARCH_SPACE["survival.default_subsistence"][0],
            SEARCH_SPACE["survival.default_subsistence"][1],
        )
        steepness = trial.suggest_float(
            "steepness_k",
            SEARCH_SPACE["survival.steepness_k"][0],
            SEARCH_SPACE["survival.steepness_k"][1],
        )

        # 2. Inject parameters into GameDefines
        defines = GameDefines()
        defines = inject_parameter(defines, "economy.extraction_efficiency", extraction)
        defines = inject_parameter(defines, "economy.comprador_cut", comprador_cut)
        defines = inject_parameter(defines, "economy.super_wage_rate", super_wage_rate)
        defines = inject_parameter(defines, "survival.default_subsistence", subsistence)
        defines = inject_parameter(defines, "survival.steepness_k", steepness)

        # 3. Create scenario and run simulation tick-by-tick
        state, config, _ = create_imperial_circuit_scenario()
        persistent_context: dict[str, Any] = {}

        ticks_survived = 0
        final_rent = 0.0

        for tick in range(max_ticks):
            try:
                state = step(state, config, persistent_context, defines)
            except Exception as e:
                # Crashed simulation = failed trial (return low score, don't crash script)
                logger.warning(f"Trial {trial.number}: Simulation crashed at tick {tick}: {e}")
                return 0.0

            # Check Comprador (P_c) health for early pruning (uses VitalitySystem's active field)
            comprador = state.entities.get(COMPRADOR_ID)
            if comprador and is_dead(comprador):
                if tick < EARLY_DEATH_THRESHOLD:
                    # Too early death - prune this trial
                    raise optuna.TrialPruned()
                # Comprador died after threshold - end simulation but don't prune
                ticks_survived = tick + 1
                final_rent = float(state.economy.imperial_rent_pool)
                break

            # Check Periphery Worker health too (uses VitalitySystem's active field)
            worker = state.entities.get(PERIPHERY_WORKER_ID)
            if worker and is_dead(worker):
                ticks_survived = tick + 1
                final_rent = float(state.economy.imperial_rent_pool)
                break

            # Report intermediate metric for Hyperband pruner
            rent_pool = float(state.economy.imperial_rent_pool)
            intermediate_value = tick + (rent_pool / 100.0)
            trial.report(intermediate_value, tick)

            # Check if Hyperband wants to prune
            if trial.should_prune():
                raise optuna.TrialPruned()

            ticks_survived = tick + 1
            final_rent = rent_pool

        # 4. Calculate composite score
        # Higher score = better (more ticks survived + healthier rent pool)
        score = (ticks_survived * 10.0) + (final_rent / 10.0)

        return score

    return objective


def run_optimization(
    study_name: str = DEFAULT_STUDY_NAME,
    storage: str = DEFAULT_STORAGE,
    n_trials: int = DEFAULT_N_TRIALS,
    max_ticks: int = DEFAULT_MAX_TICKS,
) -> optuna.Study:
    """Run Optuna optimization study.

    Args:
        study_name: Name for the study (enables resumption)
        storage: SQLite database URL for persistence
        n_trials: Number of optimization trials
        max_ticks: Maximum simulation ticks per trial

    Returns:
        Completed Optuna study object
    """
    logger.info(f"Creating/loading study: {study_name}")
    logger.info(f"Storage: {storage}")
    logger.info(f"Trials: {n_trials}")
    logger.info(f"Max ticks per trial: {max_ticks}")

    # Create study with TPE sampler and Hyperband pruner
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        sampler=TPESampler(seed=42, multivariate=True),
        pruner=HyperbandPruner(
            min_resource=1,
            max_resource=max_ticks,
            reduction_factor=3,
        ),
        direction="maximize",
        load_if_exists=True,  # Resume capability
    )

    # Check if resuming
    existing_trials = len(study.trials)
    if existing_trials > 0:
        logger.info(f"Resuming study with {existing_trials} existing trials")

    # Run optimization
    study.optimize(
        create_objective(max_ticks=max_ticks),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    return study


def print_results(study: optuna.Study) -> None:
    """Print optimization results.

    Args:
        study: Completed Optuna study
    """
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)

    # Statistics
    completed = len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])
    pruned = len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])
    failed = len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL])

    print(f"\nTrials: {len(study.trials)} total")
    print(f"  - Completed: {completed}")
    print(f"  - Pruned: {pruned}")
    print(f"  - Failed: {failed}")

    if study.best_trial:
        print(f"\nBest Score: {study.best_value:.2f}")
        print("\nBest Parameters:")
        for key, value in study.best_params.items():
            print(f"  {key}: {value:.4f}")

        # Decode the score
        ticks_component = study.best_value // 10
        rent_component = (study.best_value % 10) * 10
        print("\nScore Breakdown:")
        print(f"  ~Ticks survived: {int(ticks_component)}")
        print(f"  ~Rent pool contribution: {rent_component:.1f}")

    print("\n" + "=" * 70)
    print("To visualize results, run:")
    print("  optuna-dashboard sqlite:///optuna.db")
    print("=" * 70)


def main() -> int:
    """Main entry point for the tuning agent."""
    parser = argparse.ArgumentParser(
        description="Autonomous parameter tuning agent using Optuna",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with defaults (100 trials)
    %(prog)s

    # Custom study with more trials
    %(prog)s --study-name imperial_v1 --trials 200

    # Resume existing study
    %(prog)s --study-name imperial_v1

    # Use different database
    %(prog)s --storage sqlite:///my_study.db
        """,
    )
    parser.add_argument(
        "--study-name",
        default=DEFAULT_STUDY_NAME,
        help=f"Name for the optimization study (default: {DEFAULT_STUDY_NAME})",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=DEFAULT_N_TRIALS,
        help=f"Number of optimization trials (default: {DEFAULT_N_TRIALS})",
    )
    parser.add_argument(
        "--storage",
        default=DEFAULT_STORAGE,
        help=f"Database URL for study persistence (default: {DEFAULT_STORAGE})",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=f"Maximum simulation ticks per trial (default: {DEFAULT_MAX_TICKS})",
    )
    parser.add_argument(
        "--show-best",
        action="store_true",
        help="Only show best parameters from existing study (don't run new trials)",
    )
    args = parser.parse_args()

    if args.show_best:
        # Load existing study and show results
        try:
            study = optuna.load_study(
                study_name=args.study_name,
                storage=args.storage,
            )
            print_results(study)
        except KeyError:
            print(f"Study '{args.study_name}' not found in {args.storage}")
            return 1
        return 0

    # Run optimization
    study = run_optimization(
        study_name=args.study_name,
        storage=args.storage,
        n_trials=args.trials,
        max_ticks=args.max_ticks,
    )

    # Print results
    print_results(study)

    return 0


if __name__ == "__main__":
    sys.exit(main())
