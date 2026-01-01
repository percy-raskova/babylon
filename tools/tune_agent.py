#!/usr/bin/env python3
"""Autonomous parameter tuning agent using Optuna Bayesian Optimization.

This tool uses TPE (Tree-structured Parzen Estimator) for sample-efficient
optimization and Hyperband pruning to kill non-viable simulations early.

Usage:
    poetry run python tools/tune_agent.py
    poetry run python tools/tune_agent.py --study-name imperial_v1 --trials 200
    poetry run python tools/tune_agent.py --study-name imperial_v1  # resumes

The objective function maximizes a "Hump Shape" score (0-100):
    - Growth (0-30): C_b wealth increases in Years 0-2
    - Peak (0-20): Peak wealth occurs in Years 2-10
    - Decay (0-30): C_b wealth declines in Years 10-20
    - Survival (0-20): Bonus for completing full 1040 ticks

This models the rise and fall of imperial hegemony over 20 simulated years.
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
from tune_parameters import inject_parameter

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step

# Configure Optuna logging
optuna.logging.set_verbosity(optuna.logging.INFO)

# Entity IDs
COMPRADOR_ID: Final[str] = "C002"
CORE_BOURGEOISIE_ID: Final[str] = "C003"
PERIPHERY_WORKER_ID: Final[str] = "C001"

# Hump Shape phase boundaries (ticks)
GROWTH_END: Final[int] = 104  # Year 2
PLATEAU_END: Final[int] = 520  # Year 10
SIMULATION_END: Final[int] = 1040  # Year 20

# Optimization settings
DEFAULT_MAX_TICKS: Final[int] = SIMULATION_END
EARLY_DEATH_THRESHOLD: Final[int] = 52  # Prune if death before 1 year (more lenient)
DEFAULT_STUDY_NAME: Final[str] = "babylon_hump"
DEFAULT_STORAGE: Final[str] = "sqlite:///optuna.db"
DEFAULT_N_TRIALS: Final[int] = 100

# Search space definition (6 parameters for Hump Shape dynamics)
SEARCH_SPACE: Final[dict[str, tuple[float, float]]] = {
    # Core economic balance
    "economy.base_subsistence": (0.0002, 0.001),  # CRITICAL: tighter range for viability
    "economy.extraction_efficiency": (0.5, 0.9),  # Minimum viable extraction
    "economy.comprador_cut": (0.80, 0.95),
    "economy.super_wage_rate": (0.10, 0.30),
    # Long-term decay drivers
    "economy.trpf_coefficient": (0.0003, 0.001),  # Controls extraction decay
    "metabolism.entropy_factor": (1.1, 1.5),  # Higher = faster biocapacity depletion
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def calculate_hump_shape_score(wealth_history: list[float]) -> float:
    """Score how well the simulation exhibits Hump Shape dynamics.

    Components:
    1. Growth Score (0-30): Did wealth grow in Years 0-2?
    2. Peak Score (0-20): Is there a clear peak in Years 2-10?
    3. Decay Score (0-30): Did wealth decline in Years 10-20?
    4. Survival Score (0-20): Bonus for surviving all 1040 ticks

    Args:
        wealth_history: List of C_b wealth values at each tick

    Returns:
        Score from 0-100 (higher = better Hump Shape)
    """
    if len(wealth_history) < GROWTH_END:
        return 0.0  # Failed in growth phase

    # 1. Growth Score: Compare end of growth phase to start
    growth_start = wealth_history[0]
    growth_end_idx = min(GROWTH_END - 1, len(wealth_history) - 1)
    growth_end_wealth = wealth_history[growth_end_idx]
    growth_ratio = growth_end_wealth / max(growth_start, 0.01)

    if growth_ratio < 1.0:
        growth_score = 0.0
    elif growth_ratio < 1.5:
        growth_score = 15.0 * (growth_ratio - 1.0) / 0.5
    else:
        growth_score = 15.0 + 15.0 * min(1.0, (growth_ratio - 1.5) / 0.5)

    # 2. Peak Score: Find peak and verify it's in plateau phase
    peak_idx = max(range(len(wealth_history)), key=lambda i: wealth_history[i])
    peak_value = wealth_history[peak_idx]

    if GROWTH_END <= peak_idx <= min(PLATEAU_END, len(wealth_history) - 1):
        peak_score = 20.0  # Peak in correct phase
    elif peak_idx < GROWTH_END:
        peak_score = 5.0  # Peak too early
    else:
        peak_score = 10.0  # Peak too late

    # 3. Decay Score: Compare end of simulation to peak
    if len(wealth_history) >= SIMULATION_END:
        final_wealth = wealth_history[-1]
        decay_ratio = final_wealth / max(peak_value, 0.01)
        if decay_ratio > 0.9:
            decay_score = 0.0
        elif decay_ratio > 0.5:
            decay_score = 15.0 * (0.9 - decay_ratio) / 0.4
        elif decay_ratio > 0.1:
            decay_score = 15.0 + 15.0 * (0.5 - decay_ratio) / 0.4
        else:
            decay_score = 30.0
    else:
        # Partial decay score based on progress
        decay_score = 15.0 * len(wealth_history) / SIMULATION_END

    # 4. Survival Score
    survival_ticks = len(wealth_history)
    if survival_ticks >= SIMULATION_END:
        survival_score = 20.0
    elif survival_ticks >= PLATEAU_END:
        progress = (survival_ticks - PLATEAU_END) / (SIMULATION_END - PLATEAU_END)
        survival_score = 10.0 + 10.0 * progress
    else:
        survival_score = 10.0 * survival_ticks / PLATEAU_END

    return growth_score + peak_score + decay_score + survival_score


def create_objective(max_ticks: int = DEFAULT_MAX_TICKS) -> Any:
    """Factory for objective function with configurable max_ticks.

    Args:
        max_ticks: Maximum simulation ticks to run

    Returns:
        Objective function compatible with Optuna study.optimize()
    """

    def objective(trial: optuna.Trial) -> float:
        """Optuna objective function for parameter optimization.

        Optimizes for "Hump Shape" dynamics over 20 years (1040 ticks):
        - Growth (Years 0-2): C_b wealth increases
        - Stagnation (Years 2-10): Wealth plateaus
        - Decay (Years 10-20): Wealth declines, natural collapse near end

        Args:
            trial: Optuna trial object for parameter suggestion

        Returns:
            Composite score (higher is better)

        Raises:
            optuna.TrialPruned: When simulation shows early failure
        """
        # 1. Sample parameters from search space (6 parameters for Hump Shape)
        base_subsistence = trial.suggest_float(
            "base_subsistence",
            SEARCH_SPACE["economy.base_subsistence"][0],
            SEARCH_SPACE["economy.base_subsistence"][1],
        )
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
        trpf_coefficient = trial.suggest_float(
            "trpf_coefficient",
            SEARCH_SPACE["economy.trpf_coefficient"][0],
            SEARCH_SPACE["economy.trpf_coefficient"][1],
        )
        entropy_factor = trial.suggest_float(
            "entropy_factor",
            SEARCH_SPACE["metabolism.entropy_factor"][0],
            SEARCH_SPACE["metabolism.entropy_factor"][1],
        )

        # 2. Inject parameters into GameDefines
        defines = GameDefines()
        defines = inject_parameter(defines, "economy.base_subsistence", base_subsistence)
        defines = inject_parameter(defines, "economy.extraction_efficiency", extraction)
        defines = inject_parameter(defines, "economy.comprador_cut", comprador_cut)
        defines = inject_parameter(defines, "economy.super_wage_rate", super_wage_rate)
        defines = inject_parameter(defines, "economy.trpf_coefficient", trpf_coefficient)
        defines = inject_parameter(defines, "metabolism.entropy_factor", entropy_factor)

        # 3. Create scenario and run simulation tick-by-tick
        state, config, _ = create_imperial_circuit_scenario()
        persistent_context: dict[str, Any] = {}

        # Track C_b wealth history for Hump Shape scoring
        c_b_wealth_history: list[float] = []

        for tick in range(max_ticks):
            try:
                state = step(state, config, persistent_context, defines)
            except Exception as e:
                # Crashed simulation = failed trial (return low score, don't crash script)
                logger.warning(f"Trial {trial.number}: Simulation crashed at tick {tick}: {e}")
                return 0.0

            # Track C_b (Core Bourgeoisie) wealth
            c_b = state.entities.get(CORE_BOURGEOISIE_ID)
            if c_b and getattr(c_b, "active", True):
                c_b_wealth_history.append(float(c_b.wealth))
            else:
                # C_b died - end simulation
                if tick < EARLY_DEATH_THRESHOLD:
                    raise optuna.TrialPruned()
                break

            # Note: P_c (Comprador) and P_w (Worker) deaths are expected dynamics
            # We only care about C_b (Core Bourgeoisie) for Hump Shape scoring
            # Those deaths will end data collection but don't trigger pruning

            # Report intermediate Hump Shape score for Hyperband pruner
            # Only report at phase boundaries to reduce overhead
            if tick in (GROWTH_END, PLATEAU_END) or tick == max_ticks - 1:
                intermediate_score = calculate_hump_shape_score(c_b_wealth_history)
                trial.report(intermediate_score, tick)

                if trial.should_prune():
                    raise optuna.TrialPruned()

        # 4. Calculate final Hump Shape score
        score = calculate_hump_shape_score(c_b_wealth_history)

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
    # Less aggressive pruning: keep 50% (not 33%), don't prune before 1 year
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        sampler=TPESampler(seed=42, multivariate=True),
        pruner=HyperbandPruner(
            min_resource=52,  # Don't prune before 1 year (52 ticks)
            max_resource=max_ticks,
            reduction_factor=2,  # Keep 50% at each stage (not 33%)
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

    # Handle case where no trials completed (all pruned)
    if completed == 0:
        print("\n⚠️  WARNING: No trials completed!")
        print(f"   All trials were pruned (entities died before tick {EARLY_DEATH_THRESHOLD}).")
        print("   This indicates the simulation parameters are fundamentally broken.")
        print("\n   Likely causes:")
        print("   - Subsistence burn rate too high relative to income")
        print("   - Initial wealth insufficient for survival")
        print("   - Production/extraction balance broken")
        print("\n   Try running: mise run audit")
        print("   Or manually testing with: poetry run python tools/audit_simulation.py")
    elif study.best_trial:
        print(f"\nBest Hump Shape Score: {study.best_value:.2f}/100")
        print("\nBest Parameters:")
        for key, value in study.best_params.items():
            print(f"  {key}: {value:.6f}")

        # Explain Hump Shape score components
        print("\nScore Components (max 100):")
        print("  Growth (0-30): Wealth increase in Years 0-2")
        print("  Peak (0-20):   Peak occurs in Years 2-10")
        print("  Decay (0-30):  Wealth decline in Years 10-20")
        print("  Survival (0-20): Complete 1040 ticks")

        # Classify the result
        score = study.best_value
        if score >= 80:
            print("\n✅ EXCELLENT: Strong Hump Shape dynamics achieved!")
        elif score >= 60:
            print("\n🔶 GOOD: Reasonable Hump Shape, some tuning may help")
        elif score >= 40:
            print("\n⚠️  PARTIAL: Some phase characteristics present")
        else:
            print("\n❌ WEAK: Hump Shape not achieved, parameters need adjustment")

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
