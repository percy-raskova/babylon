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

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.config.defines import (
    GameDefines,
)
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step
from babylon.models.enums import EdgeType

# Constants
PERIPHERY_WORKER_ID: Final[str] = "C001"
MAX_TICKS: Final[int] = 50


def is_dead(entity: Any) -> bool:
    """Check if an entity is dead using VitalitySystem's active field.

    This aligns with VitalitySystem which sets active=False when
    wealth < consumption_needs (s_bio + s_class).

    Args:
        entity: SocialClass entity or None

    Returns:
        True if entity is None or has active=False
    """
    if entity is None:
        return True
    return not getattr(entity, "active", True)


def inject_parameter(
    base_defines: GameDefines,
    param_path: str,
    value: float,
) -> GameDefines:
    """Create a new GameDefines with a nested parameter overridden.

    Uses Pydantic's model_copy(update=...) to create an immutable copy
    with the specified parameter changed.

    Args:
        base_defines: Original GameDefines (not mutated)
        param_path: Dot-separated path like "economy.extraction_efficiency"
        value: New value to set

    Returns:
        New GameDefines with the parameter updated

    Raises:
        ValueError: If param_path is invalid
    """
    parts = param_path.split(".")
    if len(parts) != 2:
        raise ValueError(f"param_path must be 'category.field', got: {param_path}")

    category, field = parts

    # Get the current category model
    category_model = getattr(base_defines, category, None)
    if category_model is None:
        raise ValueError(f"Unknown category: {category}")

    # Verify the field exists
    if not hasattr(category_model, field):
        raise ValueError(f"Unknown field '{field}' in category '{category}'")

    # Create new category model with updated field
    new_category = category_model.model_copy(update={field: value})

    # Create new GameDefines with updated category
    return base_defines.model_copy(update={category: new_category})


def run_simulation(
    defines: GameDefines,
    max_ticks: int = MAX_TICKS,
) -> dict[str, Any]:
    """Run a single simulation with the given GameDefines.

    Args:
        defines: GameDefines to use for this simulation
        max_ticks: Maximum number of ticks to run

    Returns:
        Dictionary with:
            - ticks_survived: Number of ticks before death (or max_ticks)
            - max_tension: Maximum tension observed on any edge
            - outcome: "SURVIVED" or "DIED"
            - final_wealth: Final wealth of periphery worker
    """
    # Create scenario with default parameters
    state, config, _scenario_defines = create_imperial_circuit_scenario()

    # We use our injected defines instead of scenario_defines
    persistent_context: dict[str, Any] = {}
    max_tension: float = 0.0
    ticks_survived: int = 0
    final_wealth: float = 0.0

    for tick in range(max_ticks):
        state = step(state, config, persistent_context, defines)

        # Get periphery worker wealth
        worker = state.entities.get(PERIPHERY_WORKER_ID)
        if worker is None:
            # Unexpected state - worker entity missing
            break

        final_wealth = worker.wealth

        # Track maximum tension across all edges
        for rel in state.relationships:
            if rel.edge_type == EdgeType.EXPLOITATION:
                max_tension = max(max_tension, rel.tension)

        # Check for death (uses VitalitySystem's active field)
        if is_dead(worker):
            ticks_survived = tick + 1
            return {
                "ticks_survived": ticks_survived,
                "max_tension": max_tension,
                "outcome": "DIED",
                "final_wealth": final_wealth,
            }

        ticks_survived = tick + 1

    return {
        "ticks_survived": ticks_survived,
        "max_tension": max_tension,
        "outcome": "SURVIVED",
        "final_wealth": final_wealth,
    }


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
