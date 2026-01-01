#!/usr/bin/env python3
"""Parameter analysis tool for deep simulation observation.

This tool provides detailed tracing of simulation state over time, capturing
all entity and edge data for analysis. It is designed for deep observation
of how parameters affect the simulation dynamics.

Usage:
    poetry run python tools/parameter_analysis.py trace --csv results/trace.csv
    poetry run python tools/parameter_analysis.py trace --ticks 50 --csv results/trace.csv
    poetry run python tools/parameter_analysis.py trace --param economy.extraction_efficiency=0.1 --csv results/trace.csv

The trace command runs a single simulation and outputs full time-series data
for all entities and edges to a CSV file.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Final

# Add src and tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Import from centralized shared module (ADR036)
from shared import (
    DEFAULT_MAX_TICKS,
    PERIPHERY_WORKER_ID,
    inject_parameter,
    is_dead,
)

from babylon.config.defines import GameDefines
from babylon.engine.observers.metrics import MetricsCollector
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation import Simulation
from babylon.models.config import SimulationConfig
from babylon.models.world_state import WorldState

# Use centralized constant
DEFAULT_TICKS: Final[int] = DEFAULT_MAX_TICKS


def _run_simulation_with_metrics(
    state: WorldState,
    config: SimulationConfig,
    defines: GameDefines,
    max_ticks: int,
) -> MetricsCollector:
    """Run simulation with MetricsCollector observer.

    Uses Simulation facade with observer pattern for unified metrics collection.
    MetricsCollector records initial state (tick 0) plus state after each step,
    so we run max_ticks - 1 steps to get max_ticks total data points.

    Args:
        state: Initial WorldState
        config: Simulation configuration
        defines: GameDefines with parameters
        max_ticks: Maximum ticks to run (total data points collected)

    Returns:
        MetricsCollector with recorded history
    """
    collector = MetricsCollector(mode="batch")
    sim = Simulation(state, config, observers=[collector], defines=defines)

    # First step triggers on_simulation_start (records tick 0) + on_tick (records tick 1)
    # Each subsequent step records one more tick
    # To get max_ticks data points: initial (1) + steps (max_ticks - 1) = max_ticks
    for _ in range(max_ticks - 1):
        sim.step()
        # Check death condition - stop if periphery worker dies (uses VitalitySystem's active field)
        worker = sim.current_state.entities.get(PERIPHERY_WORKER_ID)
        if worker is not None and is_dead(worker):
            break

    sim.end()
    return collector


def run_trace(
    param_path: str | None = None,
    param_value: float | None = None,
    max_ticks: int = DEFAULT_TICKS,
) -> tuple[MetricsCollector, SimulationConfig, GameDefines]:
    """Run single simulation, return collector with config for export.

    Executes a simulation using MetricsCollector observer and returns
    the collector along with config/defines for flexible export (CSV/JSON).

    Args:
        param_path: Optional dot-separated parameter path to modify
        param_value: Optional value to set for the parameter
        max_ticks: Maximum number of ticks to run

    Returns:
        Tuple of (MetricsCollector, SimulationConfig, GameDefines)
    """
    # Create scenario with default parameters
    state, config, scenario_defines = create_imperial_circuit_scenario()

    # Optionally inject custom parameter
    defines: GameDefines
    if param_path is not None and param_value is not None:
        defines = inject_parameter(GameDefines(), param_path, param_value)
    else:
        defines = scenario_defines

    # Run simulation with MetricsCollector
    collector = _run_simulation_with_metrics(state, config, defines, max_ticks)
    return collector, config, defines


def extract_sweep_summary(
    collector: MetricsCollector,
    param_value: float,
) -> dict[str, Any]:
    """Extract summary metrics from MetricsCollector.

    Args:
        collector: MetricsCollector with recorded history
        param_value: The parameter value used

    Returns:
        Summary dict with aggregated metrics
    """
    if collector.summary is None:
        return {"value": param_value, "ticks_survived": 0, "outcome": "ERROR"}

    summary = collector.summary
    return {
        "value": param_value,
        "ticks_survived": summary.ticks_survived,
        "outcome": summary.outcome,
        "final_p_w_wealth": float(summary.final_p_w_wealth),
        "final_p_c_wealth": float(summary.final_p_c_wealth),
        "final_c_b_wealth": float(summary.final_c_b_wealth),
        "final_c_w_wealth": float(summary.final_c_w_wealth),
        "max_tension": float(summary.max_tension),
        "crossover_tick": summary.crossover_tick,
        "cumulative_rent": float(summary.cumulative_rent),
        "peak_p_w_consciousness": float(summary.peak_p_w_consciousness),
        "peak_c_w_consciousness": float(summary.peak_c_w_consciousness),
    }


def run_sweep(
    param_path: str,
    start: float,
    end: float,
    step_size: float,
    max_ticks: int = DEFAULT_TICKS,
) -> list[dict[str, Any]]:
    """Run parameter sweep, return summary per value.

    For each parameter value in the range [start, end] with given step,
    runs a full simulation and collects summary metrics.

    Args:
        param_path: Dot-separated parameter path (e.g., 'economy.extraction_efficiency')
        start: Starting value for the parameter
        end: Ending value for the parameter
        step_size: Step size between values
        max_ticks: Maximum ticks per simulation

    Returns:
        List of summary dicts, one per parameter value
    """
    results: list[dict[str, Any]] = []

    # Calculate number of steps
    num_steps = int(round((end - start) / step_size)) + 1

    for i in range(num_steps):
        value = round(start + (i * step_size), 6)
        if value > end + (step_size / 10):
            break

        # Create fresh scenario and inject parameter
        state, config, scenario_defines = create_imperial_circuit_scenario()
        defines = inject_parameter(GameDefines(), param_path, value)

        # Run simulation with MetricsCollector
        collector = _run_simulation_with_metrics(state, config, defines, max_ticks)

        # Extract summary metrics
        summary = extract_sweep_summary(collector, value)
        results.append(summary)

    return results


def write_csv(data: list[dict[str, Any]], output_path: Path) -> None:
    """Write trace data to CSV file.

    Args:
        data: List of tick data dictionaries
        output_path: Path to write CSV file
    """
    if not data:
        # Create empty file with headers only
        fieldnames = ["tick"]
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        return

    # Get all unique keys across all rows for fieldnames
    all_keys: set[str] = set()
    for row in data:
        all_keys.update(row.keys())

    # Define column order (tick first, then alphabetically)
    fieldnames = ["tick"] + sorted(key for key in all_keys if key != "tick")

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def parse_param_arg(param_str: str | None) -> tuple[str | None, float | None]:
    """Parse --param argument in format 'path=value'.

    Args:
        param_str: Parameter string in format 'category.field=value'

    Returns:
        Tuple of (param_path, param_value) or (None, None) if not provided

    Raises:
        ValueError: If param_str is invalid format
    """
    if param_str is None:
        return None, None

    if "=" not in param_str:
        raise ValueError(f"--param must be in format 'path=value', got: {param_str}")

    path, value_str = param_str.split("=", 1)
    try:
        value = float(value_str)
    except ValueError as e:
        raise ValueError(f"Invalid value '{value_str}' in --param, must be numeric") from e

    return path.strip(), value


def main() -> int:
    """CLI entry point with trace subcommand.

    Returns:
        Exit code: 0 for success, 1 for error
    """
    parser = argparse.ArgumentParser(
        description="Parameter analysis tool for deep simulation observation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run trace and output to CSV
  python tools/parameter_analysis.py trace --csv results/trace.csv

  # Run trace with custom tick limit
  python tools/parameter_analysis.py trace --ticks 100 --csv results/trace.csv

  # Run trace with custom parameter value
  python tools/parameter_analysis.py trace --param economy.extraction_efficiency=0.1 --csv results/trace.csv
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # trace subcommand
    trace_parser = subparsers.add_parser(
        "trace",
        help="Run simulation and output time-series data to CSV",
    )
    trace_parser.add_argument(
        "--param",
        type=str,
        default=None,
        help="Parameter to modify in format 'path=value' (e.g., economy.extraction_efficiency=0.1)",
    )
    trace_parser.add_argument(
        "--ticks",
        type=int,
        default=DEFAULT_TICKS,
        help=f"Maximum number of ticks to run (default: {DEFAULT_TICKS})",
    )
    trace_parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Output CSV file path (required)",
    )
    trace_parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Output JSON metadata file path (optional, captures DAG structure)",
    )

    # sweep subcommand
    sweep_parser = subparsers.add_parser(
        "sweep",
        help="Run parameter sweep and output summary statistics to CSV",
    )
    sweep_parser.add_argument(
        "--param",
        type=str,
        required=True,
        help="Parameter path to sweep (e.g., economy.extraction_efficiency)",
    )
    sweep_parser.add_argument(
        "--start",
        type=float,
        required=True,
        help="Starting value for sweep",
    )
    sweep_parser.add_argument(
        "--end",
        type=float,
        required=True,
        help="Ending value for sweep",
    )
    sweep_parser.add_argument(
        "--step",
        type=float,
        required=True,
        help="Step size between values",
    )
    sweep_parser.add_argument(
        "--ticks",
        type=int,
        default=DEFAULT_TICKS,
        help=f"Maximum ticks per simulation (default: {DEFAULT_TICKS})",
    )
    sweep_parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Output CSV file path (required)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "trace":
        try:
            # Parse parameter if provided
            param_path, param_value = parse_param_arg(args.param)

            print(f"Running trace for {args.ticks} ticks...")
            if param_path is not None:
                print(f"  Parameter override: {param_path}={param_value}")

            # Run trace
            collector, config, defines = run_trace(
                param_path=param_path,
                param_value=param_value,
                max_ticks=args.ticks,
            )

            # Write CSV
            trace_data = collector.to_csv_rows()
            write_csv(trace_data, args.csv)

            print(f"Trace complete: {len(trace_data)} ticks recorded")
            print(f"Output written to: {args.csv}")

            # Write JSON if requested
            if args.json is not None:
                collector.export_json(args.json, defines, config, csv_path=args.csv)
                print(f"JSON metadata written to: {args.json}")

            return 0

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if args.command == "sweep":
        try:
            print(f"Running sweep: {args.param} from {args.start} to {args.end} step {args.step}")
            print(f"  Max ticks per simulation: {args.ticks}")

            # Run sweep
            sweep_data = run_sweep(
                param_path=args.param,
                start=args.start,
                end=args.end,
                step_size=args.step,
                max_ticks=args.ticks,
            )

            # Write CSV
            write_csv(sweep_data, args.csv)

            print(f"Sweep complete: {len(sweep_data)} parameter values tested")
            print(f"Output written to: {args.csv}")

            return 0

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
