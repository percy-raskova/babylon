#!/usr/bin/env python3
"""2D parameter landscape analysis for Babylon simulation.

Performs grid search over two GameDefines parameters to identify
parameter interaction effects and survival boundaries.

Usage:
    poetry run python tools/landscape_analysis.py \\
      --param1 economy.extraction_efficiency \\
      --range1 0.1:0.9:0.1 \\
      --param2 economy.comprador_cut \\
      --range2 0.5:1.0:0.1

Output:
    Matrix CSV where rows=param1 values, cols=param2 values, cells=ticks_survived
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Final

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import reusable functions from tune_parameters (no duplication)
from tune_parameters import inject_parameter, run_simulation

from babylon.config.defines import GameDefines

DEFAULT_OUTPUT: Final[str] = "results/landscape.csv"
DEFAULT_MAX_TICKS: Final[int] = 52


def parse_range(range_str: str) -> list[float]:
    """Parse 'start:end:step' string into list of values.

    Args:
        range_str: Range specification as "start:end:step"

    Returns:
        List of float values from start to end (inclusive) by step

    Raises:
        ValueError: If range_str is malformed
    """
    parts = range_str.split(":")
    if len(parts) != 3:
        raise ValueError(f"Range must be 'start:end:step', got: {range_str}")

    start, end, step = map(float, parts)
    if step <= 0:
        raise ValueError(f"Step must be positive, got: {step}")

    values: list[float] = []
    current = start
    # Tolerance for float precision
    while current <= end + (step / 10):
        values.append(round(current, 6))
        current += step

    return values


def run_landscape_sweep(
    param1: str,
    values1: list[float],
    param2: str,
    values2: list[float],
    max_ticks: int,
) -> list[list[int]]:
    """Run 2D parameter sweep.

    Args:
        param1: First parameter path (e.g., "economy.extraction_efficiency")
        values1: List of values for param1 (rows)
        param2: Second parameter path
        values2: List of values for param2 (columns)
        max_ticks: Maximum simulation ticks per run

    Returns:
        2D matrix of ticks_survived values [rows][cols]
    """
    base_defines = GameDefines()
    total_runs = len(values1) * len(values2)
    run_count = 0

    results: list[list[int]] = []

    for v1 in values1:
        row: list[int] = []
        for v2 in values2:
            run_count += 1
            # Inject both parameters
            defines = inject_parameter(base_defines, param1, v1)
            defines = inject_parameter(defines, param2, v2)

            # Run simulation
            result = run_simulation(defines, max_ticks=max_ticks)
            ticks = result["ticks_survived"]
            row.append(ticks)

            # Progress indicator
            print(
                f"\r[{run_count}/{total_runs}] "
                f"{param1}={v1:.3f}, {param2}={v2:.3f} -> {ticks} ticks",
                end="",
                flush=True,
            )

        results.append(row)

    print()  # Newline after progress
    return results


def write_matrix_csv(
    output_path: Path,
    param1: str,
    values1: list[float],
    param2: str,
    values2: list[float],
    results: list[list[int]],
) -> None:
    """Write results as matrix CSV.

    Args:
        output_path: Path to output CSV file
        param1: Name of row parameter
        values1: Row header values
        param2: Name of column parameter
        values2: Column header values
        results: 2D matrix of results
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header row: corner cell + column values
        header = [f"{param1}\\{param2}"] + [f"{v:.4f}" for v in values2]
        writer.writerow(header)

        # Data rows: row value + cells
        for i, v1 in enumerate(values1):
            row_data = [f"{v1:.4f}"] + [str(x) for x in results[i]]
            writer.writerow(row_data)


def main() -> int:
    """Run 2D parameter landscape analysis."""
    parser = argparse.ArgumentParser(
        description="2D parameter landscape analysis for Babylon simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Sweep extraction_efficiency vs comprador_cut
    %(prog)s --param1 economy.extraction_efficiency --range1 0.1:0.9:0.1 \\
             --param2 economy.comprador_cut --range2 0.5:1.0:0.1

    # Quick test with small grid
    %(prog)s --param1 economy.extraction_efficiency --range1 0.3:0.7:0.2 \\
             --param2 economy.comprador_cut --range2 0.7:0.9:0.1 --max-ticks 30
        """,
    )
    parser.add_argument(
        "--param1",
        required=True,
        help="First parameter path (e.g., economy.extraction_efficiency)",
    )
    parser.add_argument(
        "--range1",
        required=True,
        help="Range for param1 as start:end:step (e.g., 0.1:0.9:0.1)",
    )
    parser.add_argument(
        "--param2",
        required=True,
        help="Second parameter path (e.g., economy.comprador_cut)",
    )
    parser.add_argument(
        "--range2",
        required=True,
        help="Range for param2 as start:end:step (e.g., 0.5:1.0:0.1)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=DEFAULT_MAX_TICKS,
        help=f"Maximum ticks per simulation (default: {DEFAULT_MAX_TICKS})",
    )
    args = parser.parse_args()

    # Parse ranges
    try:
        values1 = parse_range(args.range1)
        values2 = parse_range(args.range2)
    except ValueError as e:
        print(f"Error parsing range: {e}", file=sys.stderr)
        return 1

    print(f"Landscape Analysis: {args.param1} x {args.param2}")
    print(f"Grid size: {len(values1)} x {len(values2)} = {len(values1) * len(values2)} runs")
    print(f"Max ticks per run: {args.max_ticks}")
    print()

    # Run sweep
    results = run_landscape_sweep(
        args.param1,
        values1,
        args.param2,
        values2,
        args.max_ticks,
    )

    # Write output
    output_path = Path(args.output)
    write_matrix_csv(output_path, args.param1, values1, args.param2, values2, results)

    print(f"\nLandscape saved to {output_path}")
    print(f"Format: Rows={args.param1}, Cols={args.param2}, Cells=ticks_survived")

    return 0


if __name__ == "__main__":
    sys.exit(main())
