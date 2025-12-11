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

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step
from babylon.models.enums import EdgeType
from babylon.models.world_state import WorldState

# Constants
ENTITY_IDS: Final[list[str]] = ["C001", "C002", "C003", "C004"]
DEFAULT_TICKS: Final[int] = 50
DEATH_THRESHOLD: Final[float] = 0.001
PERIPHERY_WORKER_ID: Final[str] = "C001"

# Column name mapping for entities
# p_w = Periphery Worker (C001)
# p_c = Comprador (C002)
# c_b = Core Bourgeoisie (C003)
# c_w = Labor Aristocracy (C004)
ENTITY_COLUMN_PREFIX: Final[dict[str, str]] = {
    "C001": "p_w",  # Periphery Worker
    "C002": "p_c",  # Comprador
    "C003": "c_b",  # Core Bourgeoisie
    "C004": "c_w",  # Labor Aristocracy (Core Worker)
}


def is_dead(wealth: float) -> bool:
    """Check if an entity's wealth indicates death.

    Args:
        wealth: Current wealth value

    Returns:
        True if wealth is at or below death threshold
    """
    return wealth <= DEATH_THRESHOLD


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


def collect_tick_data(state: WorldState, tick: int) -> dict[str, Any]:
    """Collect all entity and edge data for one tick.

    Captures comprehensive state information for analysis:
    - Entity wealth, consciousness, organization, survival probabilities
    - Edge tension, value flows, solidarity strength

    Args:
        state: Current WorldState snapshot
        tick: Current tick number

    Returns:
        Dictionary with all collected metrics for this tick
    """
    row: dict[str, Any] = {"tick": tick}

    # Collect entity data
    # Periphery Worker (C001)
    p_w = state.entities.get("C001")
    if p_w is not None:
        row["p_w_wealth"] = float(p_w.wealth)
        row["p_w_consciousness"] = float(p_w.ideology.class_consciousness)
        row["p_w_psa"] = float(p_w.p_acquiescence)
        row["p_w_psr"] = float(p_w.p_revolution)
        row["p_w_organization"] = float(p_w.organization)

    # Comprador (C002)
    p_c = state.entities.get("C002")
    if p_c is not None:
        row["p_c_wealth"] = float(p_c.wealth)

    # Core Bourgeoisie (C003)
    c_b = state.entities.get("C003")
    if c_b is not None:
        row["c_b_wealth"] = float(c_b.wealth)

    # Labor Aristocracy (C004)
    c_w = state.entities.get("C004")
    if c_w is not None:
        row["c_w_wealth"] = float(c_w.wealth)
        row["c_w_consciousness"] = float(c_w.ideology.class_consciousness)

    # Collect edge data
    # Initialize edge columns with defaults
    row["exploitation_tension"] = 0.0
    row["exploitation_rent"] = 0.0
    row["tribute_flow"] = 0.0
    row["wages_paid"] = 0.0
    row["solidarity_strength"] = 0.0

    for rel in state.relationships:
        if rel.edge_type == EdgeType.EXPLOITATION:
            row["exploitation_tension"] = float(rel.tension)
            row["exploitation_rent"] = float(rel.value_flow)
        elif rel.edge_type == EdgeType.TRIBUTE:
            row["tribute_flow"] = float(rel.value_flow)
        elif rel.edge_type == EdgeType.WAGES:
            row["wages_paid"] = float(rel.value_flow)
        elif rel.edge_type == EdgeType.SOLIDARITY:
            row["solidarity_strength"] = float(rel.solidarity_strength)

    return row


def run_trace(
    param_path: str | None = None,
    param_value: float | None = None,
    max_ticks: int = DEFAULT_TICKS,
) -> list[dict[str, Any]]:
    """Run single simulation, return per-tick data.

    Executes a simulation and collects comprehensive state data at each tick.
    Optionally injects a custom parameter value before running.

    Args:
        param_path: Optional dot-separated parameter path to modify
        param_value: Optional value to set for the parameter
        max_ticks: Maximum number of ticks to run

    Returns:
        List of dictionaries, one per tick, with all collected metrics
    """
    # Create scenario with default parameters
    state, config, scenario_defines = create_imperial_circuit_scenario()

    # Optionally inject custom parameter
    defines: GameDefines
    if param_path is not None and param_value is not None:
        defines = inject_parameter(GameDefines(), param_path, param_value)
    else:
        defines = scenario_defines

    # Run simulation and collect data
    trace_data: list[dict[str, Any]] = []
    persistent_context: dict[str, Any] = {}

    for tick in range(max_ticks):
        # Collect data before step (for tick 0) or after previous step
        tick_data = collect_tick_data(state, tick)
        trace_data.append(tick_data)

        # Check for death - stop if periphery worker dies
        worker = state.entities.get(PERIPHERY_WORKER_ID)
        if worker is not None and is_dead(worker.wealth):
            break

        # Run simulation step
        state = step(state, config, persistent_context, defines)

    return trace_data


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
            trace_data = run_trace(
                param_path=param_path,
                param_value=param_value,
                max_ticks=args.ticks,
            )

            # Write CSV
            write_csv(trace_data, args.csv)

            print(f"Trace complete: {len(trace_data)} ticks recorded")
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
