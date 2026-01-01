#!/usr/bin/env python3
"""Parameter tuning tool for sensitivity analysis.

This tool automates sensitivity analysis for the simulation by sweeping through
a range of values for specific GameDefines parameters and reporting survival outcomes.

The tool helps find the "Playable Boundary" where the game is challenging but not
impossible - specifically finding parameter values where the periphery survives
longer than a target number of ticks.

Usage:
    poetry run python tools/tune_parameters.py
    poetry run python tools/tune_parameters.py --start 0.1 --end 0.5 --step 0.05
    poetry run python tools/tune_parameters.py --param economy.base_subsistence --start 1.0 --end 5.0 --step 0.5

Example:
    # Sweep extraction_efficiency from 0.05 to 0.50 by 0.05
    results = run_sweep("economy.extraction_efficiency", 0.05, 0.50, 0.05)
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

# Import from centralized shared module (ADR036)
from shared import (
    DEATH_THRESHOLD,
    DEFAULT_MAX_TICKS,
    PERIPHERY_WORKER_ID,
    inject_parameter,
    is_dead,
    is_dead_by_wealth,
    run_simulation,
)

from babylon.config.defines import GameDefines

# Re-export for backwards compatibility with tools that import from here
__all__ = [
    "PERIPHERY_WORKER_ID",
    "MAX_TICKS",
    "DEATH_THRESHOLD",
    "is_dead_by_wealth",
    "is_dead",
    "inject_parameter",
    "run_simulation",
]

# Alias for backwards compatibility
MAX_TICKS: Final[int] = DEFAULT_MAX_TICKS


def format_results(results: list[dict[str, Any]]) -> str:
    """Format sweep results as a table.

    Args:
        results: List of result dictionaries from run_sweep

    Returns:
        Formatted table string
    """
    lines = [
        "",
        "=" * 70,
        "PARAMETER SWEEP RESULTS",
        "=" * 70,
        "",
        f"{'Value':>10} | {'Ticks Survived':>15} | {'Max Tension':>12} | {'Outcome':>10}",
        "-" * 70,
    ]

    for result in results:
        lines.append(
            f"{result['value']:>10.4f} | "
            f"{result['ticks_survived']:>15} | "
            f"{result['max_tension']:>12.4f} | "
            f"{result['outcome']:>10}"
        )

    lines.append("-" * 70)
    lines.append("")

    # Summary
    survived_count = sum(1 for r in results if r["outcome"] == "SURVIVED")
    died_count = sum(1 for r in results if r["outcome"] == "DIED")

    lines.append(
        f"Summary: {survived_count} survived, {died_count} died out of {len(results)} runs"
    )

    # Find boundary value (lowest value where periphery survives > 25 ticks)
    target_ticks = 25
    boundary_results = [r for r in results if r["ticks_survived"] >= target_ticks]
    if boundary_results:
        # Find highest extraction where survival is still possible
        highest_surviving = max(boundary_results, key=lambda x: x["value"])
        lines.append(
            f"Playable Boundary: extraction_efficiency <= {highest_surviving['value']:.4f} "
            f"(survives {highest_surviving['ticks_survived']} ticks)"
        )
    else:
        lines.append(f"No parameter value found where periphery survives >= {target_ticks} ticks")

    lines.append("")

    return "\n".join(lines)


def run_sweep(
    param_path: str,
    start: float,
    end: float,
    step: float,
) -> list[dict[str, Any]]:
    """Run a parameter sweep over a range of values.

    Args:
        param_path: Dot-separated path like "economy.extraction_efficiency"
        start: Starting value (inclusive)
        end: Ending value (inclusive)
        step: Step size between values

    Returns:
        List of result dictionaries, each containing:
            - value: The parameter value tested
            - ticks_survived: Number of ticks before death
            - max_tension: Maximum tension observed
            - outcome: "SURVIVED" or "DIED"
    """
    results: list[dict[str, Any]] = []
    base_defines = GameDefines()

    # Calculate number of steps (handle floating point precision)
    num_steps = int(round((end - start) / step)) + 1

    for i in range(num_steps):
        value = start + (i * step)

        # Ensure we don't exceed end due to floating point
        if value > end + (step / 10):
            break

        # Round to avoid floating point artifacts
        value = round(value, 6)

        # Inject the parameter value
        modified_defines = inject_parameter(base_defines, param_path, value)

        # Run simulation
        result = run_simulation(modified_defines)
        result["value"] = value
        results.append(result)

    return results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Parameter tuning tool for sensitivity analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default sweep of extraction_efficiency
  python tools/tune_parameters.py

  # Custom range
  python tools/tune_parameters.py --start 0.1 --end 0.5 --step 0.05

  # Different parameter
  python tools/tune_parameters.py --param economy.base_subsistence --start 1.0 --end 5.0 --step 0.5
        """,
    )
    parser.add_argument(
        "--param",
        type=str,
        default="economy.extraction_efficiency",
        help="Parameter path to sweep (default: economy.extraction_efficiency)",
    )
    parser.add_argument(
        "--start",
        type=float,
        default=0.05,
        help="Starting value for sweep (default: 0.05)",
    )
    parser.add_argument(
        "--end",
        type=float,
        default=0.50,
        help="Ending value for sweep (default: 0.50)",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.05,
        help="Step size between values (default: 0.05)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=MAX_TICKS,
        help=f"Maximum ticks per simulation (default: {MAX_TICKS})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def main() -> int:
    """Run parameter sweep with configurable parameters.

    Returns:
        Exit code: 0 for success
    """
    args = parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger("babylon").setLevel(logging.INFO)
    else:
        logging.getLogger("babylon").setLevel(logging.WARNING)

    print("=" * 70)
    print(f"PARAMETER TUNING: Sensitivity Analysis for {args.param}")
    print("=" * 70)
    print()
    print(f"Sweeping {args.param} from {args.start} to {args.end} by {args.step}")
    print(f"Running {args.ticks} ticks per simulation")
    print("Death detection: VitalitySystem active field (wealth < consumption_needs)")
    print()
    print("Running simulations...")
    print()

    # Run sweep
    results = run_sweep(
        param_path=args.param,
        start=args.start,
        end=args.end,
        step=args.step,
    )

    # Format and print results
    output = format_results(results)
    print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
