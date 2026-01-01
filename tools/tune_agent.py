#!/usr/bin/env python3
"""Autonomous parameter tuning agent using Optuna Bayesian Optimization.

This tool uses TPE (Tree-structured Parzen Estimator) for sample-efficient
optimization and Hyperband pruning to kill non-viable simulations early.

Usage:
    poetry run python tools/tune_agent.py
    poetry run python tools/tune_agent.py --study-name carceral_v1 --trials 200
    poetry run python tools/tune_agent.py --study-name carceral_v1  # resumes

The objective function maximizes a Carceral Equilibrium score (0-100) based on
the theoretical trajectory in ai-docs/carceral-equilibrium.md:

    - Superwage Crisis (0-25): Event occurs in Years 20-40
    - Class Decomposition (0-25): Event occurs in Years 25-50
    - Control Ratio Crisis (0-25): Event occurs in Years 35-60
    - Terminal Decision (0-25): Event occurs in Years 45-100

This models the inevitable collapse of imperial hegemony over 100 simulated years.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Final

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import optuna

# Import Carceral Equilibrium scoring
from carceral_scoring import (
    TICKS_PER_YEAR,
    calculate_carceral_equilibrium_score,
    format_phase_report,
)
from optuna.pruners import HyperbandPruner
from optuna.samplers import TPESampler

# Import from centralized shared module (ADR036)
from shared import (
    DEFAULT_MAX_TICKS,
    inject_parameter,
    run_simulation,
)

from babylon.config.defines import GameDefines

# Configure Optuna logging
optuna.logging.set_verbosity(optuna.logging.INFO)

# Carceral Equilibrium phase boundaries (ticks)
# These map to theoretical year ranges in ai-docs/carceral-equilibrium.md
SUPERWAGE_CRISIS_WINDOW: Final[tuple[int, int]] = (20 * TICKS_PER_YEAR, 40 * TICKS_PER_YEAR)
CLASS_DECOMPOSITION_WINDOW: Final[tuple[int, int]] = (25 * TICKS_PER_YEAR, 50 * TICKS_PER_YEAR)
CONTROL_CRISIS_WINDOW: Final[tuple[int, int]] = (35 * TICKS_PER_YEAR, 60 * TICKS_PER_YEAR)
TERMINAL_DECISION_WINDOW: Final[tuple[int, int]] = (45 * TICKS_PER_YEAR, 100 * TICKS_PER_YEAR)

# Optimization settings
SIMULATION_LENGTH: Final[int] = DEFAULT_MAX_TICKS  # 100 years (5200 ticks)
EARLY_DEATH_THRESHOLD: Final[int] = 5 * TICKS_PER_YEAR  # Prune if death before 5 years
DEFAULT_STUDY_NAME: Final[str] = "babylon_carceral"
DEFAULT_STORAGE: Final[str] = "sqlite:///optuna.db"
DEFAULT_N_TRIALS: Final[int] = 100

# Search space definition for Carceral Equilibrium dynamics
# These parameters influence the 100-year trajectory phase transitions
SEARCH_SPACE: Final[dict[str, tuple[float, float]]] = {
    # Core economic parameters (affect accumulation and crisis timing)
    "economy.base_subsistence": (0.0002, 0.002),  # Calorie check - subsistence burn rate
    "economy.extraction_efficiency": (0.5, 0.95),  # Alpha - how much surplus is captured
    "economy.comprador_cut": (0.75, 0.95),  # How much comprador keeps (rest to C_b)
    "economy.super_wage_rate": (0.10, 0.35),  # LA super-wage as fraction of rent
    # Long-term decay drivers (affect when crises occur)
    "economy.trpf_coefficient": (0.0002, 0.002),  # Tendential rate of profit fall
    "economy.trpf_efficiency_floor": (0.0, 0.1),  # CRITICAL: Floor=0 allows full collapse
    "economy.rent_pool_decay": (0.0, 0.02),  # Imperial rent pool depletion rate (widened)
    # Consciousness and solidarity (affect terminal outcome)
    "consciousness.sensitivity": (0.2, 0.8),  # How responsive to material conditions
    "solidarity.scaling_factor": (0.3, 0.9),  # Solidarity network effectiveness
    # Carceral parameters (affect control ratio crisis and terminal decision)
    # After SUPERWAGE_CRISIS, LA decomposes: some → guards, rest → prisoners
    # Based on real-world prison staffing: US average ~4:1, crisis >15:1
    "carceral.control_capacity": (1, 10),  # Prisoners per guard (int, cast in objective)
    "carceral.enforcer_fraction": (0.05, 0.30),  # % of former LA → guards
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_objective(max_ticks: int = SIMULATION_LENGTH) -> Any:
    """Factory for objective function with configurable max_ticks.

    Args:
        max_ticks: Maximum simulation ticks to run (default: 5200 = 100 years)

    Returns:
        Objective function compatible with Optuna study.optimize()
    """

    def objective(trial: optuna.Trial) -> float:
        """Optuna objective function for Carceral Equilibrium optimization.

        Optimizes for the 100-year Carceral Equilibrium trajectory:
        - Years 20-40:  Superwage Crisis (rent pool exhaustion)
        - Years 25-50:  Class Decomposition (LA splits)
        - Years 35-60:  Control Ratio Crisis (prison capacity exceeded)
        - Years 45-100: Terminal Decision (revolution vs genocide)

        Args:
            trial: Optuna trial object for parameter suggestion

        Returns:
            Carceral Equilibrium score (0-100, higher is better)

        Raises:
            optuna.TrialPruned: When simulation shows early failure
        """
        # 1. Sample parameters from search space
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
        trpf_floor = trial.suggest_float(
            "trpf_efficiency_floor",
            SEARCH_SPACE["economy.trpf_efficiency_floor"][0],
            SEARCH_SPACE["economy.trpf_efficiency_floor"][1],
        )
        rent_pool_decay = trial.suggest_float(
            "rent_pool_decay",
            SEARCH_SPACE["economy.rent_pool_decay"][0],
            SEARCH_SPACE["economy.rent_pool_decay"][1],
        )
        consciousness_sensitivity = trial.suggest_float(
            "consciousness_sensitivity",
            SEARCH_SPACE["consciousness.sensitivity"][0],
            SEARCH_SPACE["consciousness.sensitivity"][1],
        )
        solidarity_scaling = trial.suggest_float(
            "solidarity_scaling",
            SEARCH_SPACE["solidarity.scaling_factor"][0],
            SEARCH_SPACE["solidarity.scaling_factor"][1],
        )
        # Carceral parameters (critical for later phase transitions)
        control_capacity = trial.suggest_int(
            "control_capacity",
            int(SEARCH_SPACE["carceral.control_capacity"][0]),
            int(SEARCH_SPACE["carceral.control_capacity"][1]),
        )
        enforcer_fraction = trial.suggest_float(
            "enforcer_fraction",
            SEARCH_SPACE["carceral.enforcer_fraction"][0],
            SEARCH_SPACE["carceral.enforcer_fraction"][1],
        )

        # 2. Inject parameters into GameDefines
        defines = GameDefines()
        defines = inject_parameter(defines, "economy.base_subsistence", base_subsistence)
        defines = inject_parameter(defines, "economy.extraction_efficiency", extraction)
        defines = inject_parameter(defines, "economy.comprador_cut", comprador_cut)
        defines = inject_parameter(defines, "economy.super_wage_rate", super_wage_rate)
        defines = inject_parameter(defines, "economy.trpf_coefficient", trpf_coefficient)
        defines = inject_parameter(defines, "economy.trpf_efficiency_floor", trpf_floor)
        defines = inject_parameter(defines, "economy.rent_pool_decay", rent_pool_decay)
        defines = inject_parameter(defines, "consciousness.sensitivity", consciousness_sensitivity)
        defines = inject_parameter(defines, "solidarity.scaling_factor", solidarity_scaling)
        defines = inject_parameter(defines, "carceral.control_capacity", control_capacity)
        defines = inject_parameter(defines, "carceral.enforcer_fraction", enforcer_fraction)
        # proletariat_fraction = 1 - enforcer_fraction (implicit constraint)
        defines = inject_parameter(
            defines, "carceral.proletariat_fraction", 1.0 - enforcer_fraction
        )

        # 3. Run simulation with phase milestone tracking
        try:
            result = run_simulation(defines, max_ticks=max_ticks)
        except Exception as e:
            # Crashed simulation = failed trial
            logger.warning(f"Trial {trial.number}: Simulation crashed: {e}")
            return 0.0

        # 4. Check for early death (prune non-viable parameter combinations)
        ticks_survived = result["ticks_survived"]
        if ticks_survived < EARLY_DEATH_THRESHOLD:
            raise optuna.TrialPruned()

        # 5. Calculate Carceral Equilibrium score
        score = calculate_carceral_equilibrium_score(
            phase_milestones=result["phase_milestones"],
            terminal_outcome=result["terminal_outcome"],
            max_ticks=max_ticks,
        )

        # 6. Report intermediate score at phase boundaries for Hyperband
        # Check if any phases occurred and report progress
        milestones = result["phase_milestones"]
        phases_reached = sum(1 for v in milestones.values() if v is not None)

        trial.report(score, phases_reached)
        if trial.should_prune():
            raise optuna.TrialPruned()

        return score

    return objective


def run_optimization(
    study_name: str = DEFAULT_STUDY_NAME,
    storage: str = DEFAULT_STORAGE,
    n_trials: int = DEFAULT_N_TRIALS,
    max_ticks: int = SIMULATION_LENGTH,
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
    logger.info(f"Max ticks per trial: {max_ticks} ({max_ticks // TICKS_PER_YEAR} years)")

    # Create study with TPE sampler and Hyperband pruner
    # Conservative pruning: keep 50% at each stage, don't prune before 5 years
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        sampler=TPESampler(seed=42, multivariate=True),
        pruner=HyperbandPruner(
            min_resource=1,  # Minimum phases reached before pruning
            max_resource=4,  # Maximum 4 phases
            reduction_factor=2,  # Keep 50% at each stage
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


def print_results(study: optuna.Study, max_ticks: int = SIMULATION_LENGTH) -> None:
    """Print optimization results.

    Args:
        study: Completed Optuna study
        max_ticks: Simulation length used (for context)
    """
    print("\n" + "=" * 70)
    print("CARCERAL EQUILIBRIUM OPTIMIZATION RESULTS")
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
        print(
            f"   All trials were pruned (entities died before year {EARLY_DEATH_THRESHOLD // TICKS_PER_YEAR})."
        )
        print("   This indicates the simulation parameters are fundamentally broken.")
        print("\n   Likely causes:")
        print("   - Subsistence burn rate too high relative to income")
        print("   - Initial wealth insufficient for survival")
        print("   - Production/extraction balance broken")
        print("\n   Try running: mise run qa:audit")
    elif study.best_trial:
        print(f"\nBest Carceral Equilibrium Score: {study.best_value:.2f}/100")
        print("\nBest Parameters:")
        for key, value in study.best_params.items():
            print(f"  {key}: {value:.6f}")

        # Run the best parameters to get phase details
        print("\n" + "-" * 70)
        print("Running best parameters to show phase timing...")

        defines = GameDefines()
        for key, value in study.best_params.items():
            # Map Optuna parameter names back to GameDefines paths
            param_map = {
                "base_subsistence": "economy.base_subsistence",
                "extraction_efficiency": "economy.extraction_efficiency",
                "comprador_cut": "economy.comprador_cut",
                "super_wage_rate": "economy.super_wage_rate",
                "trpf_coefficient": "economy.trpf_coefficient",
                "trpf_efficiency_floor": "economy.trpf_efficiency_floor",
                "rent_pool_decay": "economy.rent_pool_decay",
                "consciousness_sensitivity": "consciousness.sensitivity",
                "solidarity_scaling": "solidarity.scaling_factor",
                "control_capacity": "carceral.control_capacity",
                "enforcer_fraction": "carceral.enforcer_fraction",
            }
            if key in param_map:
                defines = inject_parameter(defines, param_map[key], value)
                # Derive proletariat_fraction from enforcer_fraction
                if key == "enforcer_fraction":
                    defines = inject_parameter(
                        defines, "carceral.proletariat_fraction", 1.0 - value
                    )

        try:
            result = run_simulation(defines, max_ticks=max_ticks)
            report = format_phase_report(
                result["phase_milestones"],
                result["terminal_outcome"],
                max_ticks,
            )
            print(report)
        except Exception as e:
            print(f"Could not re-run best trial: {e}")

        # Classify the result
        score = study.best_value
        if score >= 80:
            print("\n✅ EXCELLENT: Full Carceral Equilibrium trajectory achieved!")
            print("   All phase transitions occurred within expected windows.")
        elif score >= 60:
            print("\n🔶 GOOD: Most phase transitions occurred.")
            print("   Some timing adjustments may improve the trajectory.")
        elif score >= 40:
            print("\n⚠️  PARTIAL: Some phase transitions occurred.")
            print("   Parameters need tuning to trigger later phases.")
        elif score > 0:
            print("\n⚠️  WEAK: Few phase transitions occurred.")
            print("   Simulation may be too stable or unstable.")
        else:
            print("\n❌ NO PHASES: No Carceral Equilibrium phases detected.")
            print("   Parameters prevent the theoretical trajectory.")

    print("\n" + "=" * 70)
    print("To visualize results, run:")
    print("  optuna-dashboard sqlite:///optuna.db")
    print("=" * 70)


def main() -> int:
    """Main entry point for the tuning agent."""
    parser = argparse.ArgumentParser(
        description="Autonomous parameter tuning for Carceral Equilibrium trajectory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with defaults (100 trials, 100 years)
    %(prog)s

    # Custom study with more trials
    %(prog)s --study-name carceral_v1 --trials 200

    # Resume existing study
    %(prog)s --study-name carceral_v1

    # Use different database
    %(prog)s --storage sqlite:///my_study.db

    # Run shorter simulation (70 years)
    %(prog)s --max-ticks 3640
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
        default=SIMULATION_LENGTH,
        help=f"Maximum simulation ticks per trial (default: {SIMULATION_LENGTH} = 100 years)",
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
            print_results(study, max_ticks=args.max_ticks)
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
    print_results(study, max_ticks=args.max_ticks)

    return 0


if __name__ == "__main__":
    sys.exit(main())
