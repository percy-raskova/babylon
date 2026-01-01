#!/usr/bin/env python3
"""Global sensitivity analysis using SALib (Morris/Sobol methods).

Implements the JASSS best-practice two-stage protocol:
1. Morris screening (fast) - Rank parameters by importance (mu*, sigma)
2. Sobol analysis (thorough) - Quantify variance decomposition (S1, ST)

Usage:
    poetry run python tools/sensitivity_analysis.py morris --trajectories 10
    poetry run python tools/sensitivity_analysis.py sobol --samples 256
    poetry run python tools/sensitivity_analysis.py both

Output:
    JSON files with sensitivity indices for each parameter.

Interpretation:
    Morris:
        - High mu* = important parameter
        - High sigma/mu* = non-linear or interacts with others

    Sobol:
        - S1 = First-order (main effect of single parameter)
        - ST = Total-order (main + all interaction effects)
        - Sum(ST) - Sum(S1) = variance from interactions

See Also:
    :doc:`/ai-docs/tooling.yaml` sensitivity_analysis section
    SALib documentation: https://salib.readthedocs.io/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

import numpy as np

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Import from centralized shared module (ADR036)
# Import Carceral Equilibrium scoring for meaningful output variance
from carceral_scoring import calculate_carceral_equilibrium_score
from shared import (
    DEFAULT_MAX_TICKS,
    get_tunable_parameters,
    inject_parameters,
    run_simulation,
)

from babylon.config.defines import GameDefines

# Try to import SALib
try:
    from SALib.analyze import morris as morris_analyze
    from SALib.analyze import sobol as sobol_analyze
    from SALib.sample import morris as morris_sample
    from SALib.sample import saltelli

    HAS_SALIB = True
except ImportError:
    HAS_SALIB = False

# Constants
DEFAULT_MORRIS_TRAJECTORIES: Final[int] = 10
DEFAULT_SOBOL_SAMPLES: Final[int] = 256
DEFAULT_OUTPUT_DIR: Final[str] = "results"


# Get all tunable parameters from shared module (ADR036)
# This ensures sensitivity analysis covers the complete parameter space
def get_default_params() -> list[str]:
    """Get all tunable parameter names for sensitivity analysis."""
    return list(get_tunable_parameters().keys())


def create_problem(param_names: list[str]) -> dict[str, Any]:
    """Create SALib problem specification.

    Args:
        param_names: List of parameter paths to analyze

    Returns:
        SALib problem dict with names and bounds
    """
    all_params = get_tunable_parameters()

    names = []
    bounds = []

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


def evaluate_simulation(
    param_values: list[list[float]],
    param_names: list[str],
    max_ticks: int,
) -> list[float]:
    """Run simulations for parameter sample matrix.

    Args:
        param_values: N x D matrix of parameter values
        param_names: List of D parameter names
        max_ticks: Maximum ticks per simulation

    Returns:
        List of N output values (Carceral Equilibrium score 0-100)
    """
    n_samples = len(param_values)
    outputs: list[float] = []

    print(f"Evaluating {n_samples} parameter combinations...")

    for i, values in enumerate(param_values):
        # Create parameter dict
        params = dict(zip(param_names, values, strict=True))

        # Inject parameters
        defines = inject_parameters(GameDefines(), params)

        # Run simulation
        result = run_simulation(defines, max_ticks=max_ticks)

        # Calculate Carceral Equilibrium score (0-100)
        # This gives meaningful variance even when all simulations survive
        score = calculate_carceral_equilibrium_score(
            phase_milestones=result["phase_milestones"],
            terminal_outcome=result["terminal_outcome"],
            max_ticks=max_ticks,
        )
        outputs.append(score)

        # Progress indicator
        if (i + 1) % max(1, n_samples // 20) == 0 or i == n_samples - 1:
            pct = 100 * (i + 1) // n_samples
            print(f"\r  [{i + 1}/{n_samples}] {pct}%", end="", flush=True)

    print()  # Newline after progress
    return outputs


def run_morris_analysis(
    param_names: list[str],
    trajectories: int,
    max_ticks: int,
) -> dict[str, Any]:
    """Run Morris elementary effects screening.

    Args:
        param_names: Parameters to analyze
        trajectories: Number of Morris trajectories
        max_ticks: Max ticks per simulation

    Returns:
        Dict with Morris results (mu, mu_star, sigma)
    """
    if not HAS_SALIB:
        raise ImportError("SALib not installed. Run: poetry add SALib")

    problem = create_problem(param_names)
    if problem["num_vars"] == 0:
        raise ValueError("No valid parameters to analyze")

    print("\nMorris Screening Analysis")
    print(f"  Parameters: {problem['num_vars']}")
    print(f"  Trajectories: {trajectories}")
    print(f"  Total samples: {trajectories * (problem['num_vars'] + 1)}")
    print()

    # Generate Morris samples
    param_values = morris_sample.sample(problem, trajectories)

    # Evaluate simulations
    outputs = evaluate_simulation(param_values, problem["names"], max_ticks)

    # Analyze Morris results (SALib requires numpy arrays)
    result = morris_analyze.analyze(problem, param_values, np.array(outputs))

    # Format results
    return {
        "method": "morris",
        "trajectories": trajectories,
        "parameters": {
            name: {
                "mu": float(result["mu"][i]),
                "mu_star": float(result["mu_star"][i]),
                "sigma": float(result["sigma"][i]),
                "mu_star_conf": float(result["mu_star_conf"][i]),
            }
            for i, name in enumerate(problem["names"])
        },
        "ranking": sorted(
            problem["names"],
            key=lambda n: result["mu_star"][problem["names"].index(n)],
            reverse=True,
        ),
    }


def run_sobol_analysis(
    param_names: list[str],
    samples: int,
    max_ticks: int,
) -> dict[str, Any]:
    """Run Sobol variance decomposition.

    Args:
        param_names: Parameters to analyze
        samples: Base sample size (total = samples * (2*D + 2))
        max_ticks: Max ticks per simulation

    Returns:
        Dict with Sobol results (S1, ST, S2)
    """
    if not HAS_SALIB:
        raise ImportError("SALib not installed. Run: poetry add SALib")

    problem = create_problem(param_names)
    if problem["num_vars"] == 0:
        raise ValueError("No valid parameters to analyze")

    total_samples = samples * (2 * problem["num_vars"] + 2)

    print("\nSobol Variance Decomposition Analysis")
    print(f"  Parameters: {problem['num_vars']}")
    print(f"  Base samples: {samples}")
    print(f"  Total samples: {total_samples}")
    print()

    # Generate Saltelli samples (quasi-Monte Carlo for Sobol)
    param_values = saltelli.sample(problem, samples, calc_second_order=True)

    # Evaluate simulations
    outputs = evaluate_simulation(param_values, problem["names"], max_ticks)

    # Analyze Sobol results (SALib requires numpy arrays)
    result = sobol_analyze.analyze(problem, np.array(outputs), calc_second_order=True)

    # Format results
    param_results = {}
    for i, name in enumerate(problem["names"]):
        param_results[name] = {
            "S1": float(result["S1"][i]),
            "S1_conf": float(result["S1_conf"][i]),
            "ST": float(result["ST"][i]),
            "ST_conf": float(result["ST_conf"][i]),
        }

    # Second-order indices (pairwise interactions)
    s2_results = {}
    if "S2" in result:
        for i, name_i in enumerate(problem["names"]):
            for j, name_j in enumerate(problem["names"]):
                if j > i:  # Upper triangle only
                    key = f"{name_i}:{name_j}"
                    s2_results[key] = float(result["S2"][i, j])

    return {
        "method": "sobol",
        "base_samples": samples,
        "total_samples": total_samples,
        "parameters": param_results,
        "S2_interactions": s2_results,
        "ranking_S1": sorted(
            problem["names"],
            key=lambda n: result["S1"][problem["names"].index(n)],
            reverse=True,
        ),
        "ranking_ST": sorted(
            problem["names"],
            key=lambda n: result["ST"][problem["names"].index(n)],
            reverse=True,
        ),
    }


def format_morris_report(results: dict[str, Any]) -> str:
    """Format Morris results as markdown."""
    lines = [
        "# Morris Elementary Effects Screening",
        "",
        f"**Trajectories**: {results['trajectories']}",
        "",
        "## Parameter Importance (by mu*)",
        "",
        "| Rank | Parameter | mu* | sigma | sigma/mu* |",
        "|------|-----------|-----|-------|-----------|",
    ]

    for rank, name in enumerate(results["ranking"], 1):
        p = results["parameters"][name]
        ratio = p["sigma"] / max(p["mu_star"], 0.001)
        lines.append(f"| {rank} | `{name}` | {p['mu_star']:.4f} | {p['sigma']:.4f} | {ratio:.2f} |")

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


def format_sobol_report(results: dict[str, Any]) -> str:
    """Format Sobol results as markdown."""
    lines = [
        "# Sobol Variance Decomposition Analysis",
        "",
        f"**Base Samples**: {results['base_samples']}",
        f"**Total Evaluations**: {results['total_samples']}",
        "",
        "## First-Order Indices (S1)",
        "",
        "| Rank | Parameter | S1 | Conf |",
        "|------|-----------|-----|------|",
    ]

    for rank, name in enumerate(results["ranking_S1"], 1):
        p = results["parameters"][name]
        lines.append(f"| {rank} | `{name}` | {p['S1']:.4f} | {p['S1_conf']:.4f} |")

    lines.extend(
        [
            "",
            "## Total-Order Indices (ST)",
            "",
            "| Rank | Parameter | ST | Conf |",
            "|------|-----------|-----|------|",
        ]
    )

    for rank, name in enumerate(results["ranking_ST"], 1):
        p = results["parameters"][name]
        lines.append(f"| {rank} | `{name}` | {p['ST']:.4f} | {p['ST_conf']:.4f} |")

    # Top interactions
    if results["S2_interactions"]:
        sorted_s2 = sorted(
            results["S2_interactions"].items(),
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


def main() -> int:
    """Run global sensitivity analysis."""
    if not HAS_SALIB:
        print("Error: SALib not installed.")
        print("Run: poetry add SALib>=1.4.7")
        return 1

    parser = argparse.ArgumentParser(
        description="Global sensitivity analysis using Morris/Sobol methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Fast Morris screening (10 trajectories)
    %(prog)s morris --trajectories 10

    # Thorough Sobol analysis (256 base samples)
    %(prog)s sobol --samples 256

    # Run both analyses
    %(prog)s both
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Analysis method")

    # Morris subcommand
    morris_parser = subparsers.add_parser("morris", help="Morris elementary effects")
    morris_parser.add_argument(
        "--trajectories",
        type=int,
        default=DEFAULT_MORRIS_TRAJECTORIES,
        help=f"Number of Morris trajectories (default: {DEFAULT_MORRIS_TRAJECTORIES})",
    )
    morris_parser.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR) / "morris.json",
        help="Output JSON path",
    )
    morris_parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=f"Max ticks per simulation (default: {DEFAULT_MAX_TICKS})",
    )

    # Sobol subcommand
    sobol_parser = subparsers.add_parser("sobol", help="Sobol variance decomposition")
    sobol_parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SOBOL_SAMPLES,
        help=f"Base sample size (default: {DEFAULT_SOBOL_SAMPLES})",
    )
    sobol_parser.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR) / "sobol.json",
        help="Output JSON path",
    )
    sobol_parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=f"Max ticks per simulation (default: {DEFAULT_MAX_TICKS})",
    )

    # Both subcommand
    both_parser = subparsers.add_parser("both", help="Run Morris then Sobol")
    both_parser.add_argument(
        "--trajectories",
        type=int,
        default=DEFAULT_MORRIS_TRAJECTORIES,
        help="Morris trajectories",
    )
    both_parser.add_argument(
        "--samples",
        type=int,
        default=DEFAULT_SOBOL_SAMPLES,
        help="Sobol base samples",
    )
    both_parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help="Max ticks per simulation",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    output_dir = Path(DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "morris":
        results = run_morris_analysis(
            get_default_params(),
            args.trajectories,
            args.max_ticks,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2))
        print(f"\nResults written to: {args.output}")
        print(format_morris_report(results))

    elif args.command == "sobol":
        results = run_sobol_analysis(
            get_default_params(),
            args.samples,
            args.max_ticks,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2))
        print(f"\nResults written to: {args.output}")
        print(format_sobol_report(results))

    elif args.command == "both":
        # Morris first
        print("=" * 60)
        print("PHASE 1: Morris Screening")
        print("=" * 60)
        morris_results = run_morris_analysis(
            get_default_params(),
            args.trajectories,
            args.max_ticks,
        )
        morris_output = output_dir / "morris.json"
        morris_output.write_text(json.dumps(morris_results, indent=2))
        print(f"\nMorris results written to: {morris_output}")
        print(format_morris_report(morris_results))

        print()
        print("=" * 60)
        print("PHASE 2: Sobol Analysis")
        print("=" * 60)
        sobol_results = run_sobol_analysis(
            get_default_params(),
            args.samples,
            args.max_ticks,
        )
        sobol_output = output_dir / "sobol.json"
        sobol_output.write_text(json.dumps(sobol_results, indent=2))
        print(f"\nSobol results written to: {sobol_output}")
        print(format_sobol_report(sobol_results))

    return 0


if __name__ == "__main__":
    sys.exit(main())
