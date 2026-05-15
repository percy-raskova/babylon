#!/usr/bin/env python3
"""Parameter analysis tool: trace and sweep, routed through the headless runner.

Spec-064 migration: this tool no longer touches the in-memory engine
(SC-007). The ``trace`` subcommand produces the headless runner's
``trace.csv`` (per-tick × per-county); the ``sweep`` subcommand drives
multiple headless runs across a parameter range and emits a per-value
summary CSV.

Usage:
    poetry run python tools/parameter_analysis.py trace --csv results/trace.csv
    poetry run python tools/parameter_analysis.py trace --ticks 50 --csv results/trace.csv
    poetry run python tools/parameter_analysis.py sweep \\
        --param economy.extraction_efficiency --start 0.05 --end 0.5 --step 0.05 \\
        --csv results/sweep.csv

Note:
    Per-parameter custom values are accepted on the CLI for backwards
    compatibility but are not currently re-applied to the headless
    runner's per-tick advancement (which is a no-op carry-forward in the
    MVP — see ``runner.py``). The seed flows through; defines do not.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path
from typing import Any, Final

# Add src and tools to path for imports.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from shared import DEFAULT_MAX_TICKS, ENTITY_IDS, inject_parameter, run_simulation  # noqa: E402

from babylon.config.defines import GameDefines  # noqa: E402
from babylon.engine.headless_runner import run as headless_run  # noqa: E402
from babylon.engine.headless_runner.models import SimulationRunConfig  # noqa: E402
from babylon.engine.headless_runner.scopes import resolve_scope  # noqa: E402

__all__ = ["ENTITY_IDS"]

DEFAULT_TICKS: Final[int] = DEFAULT_MAX_TICKS


def run_trace(
    param_path: str | None = None,
    param_value: float | None = None,
    max_ticks: int = DEFAULT_TICKS,
) -> tuple[Path, GameDefines]:
    """Run a single headless simulation, return path to its trace.csv.

    Args:
        param_path: Optional dot-separated parameter path (accepted for
            CLI compatibility; not re-applied to headless advancement
            in the MVP).
        param_value: Optional value for the parameter override.
        max_ticks: Maximum number of ticks to run.

    Returns:
        Tuple of (trace_csv_path, defines used).
    """
    defines: GameDefines
    if param_path is not None and param_value is not None:
        defines = inject_parameter(GameDefines(), param_path, param_value)
    else:
        defines = GameDefines.load_default()

    scope = resolve_scope("detroit-tri-county")
    out_dir = Path(tempfile.mkdtemp(prefix="babylon-trace-"))
    config = SimulationRunConfig(
        ticks=max_ticks,
        random_seed=getattr(defines, "rng_seed", 2010),
        scope_name="detroit-tri-county",
        scope_fips=scope.scope_fips,
        external_node_ids=scope.external_node_ids,
        output_dir=out_dir,
    )
    headless_run(config)
    return out_dir / "trace.csv", defines


def extract_sweep_summary(value: float, result: dict[str, Any]) -> dict[str, Any]:
    """Extract a one-row summary from a ``shared.run_simulation`` result."""
    return {
        "value": value,
        "ticks_survived": result["ticks_survived"],
        "outcome": result["outcome"],
        "max_tension": result["max_tension"],
        "final_wealth": result["final_wealth"],
    }


def run_sweep(
    param_path: str,
    start: float,
    end: float,
    step_size: float,
    max_ticks: int = DEFAULT_TICKS,
) -> list[dict[str, Any]]:
    """Sweep ``param_path`` over [start, end] in steps of ``step_size``.

    Each sweep point invokes the headless runner via ``shared.run_simulation``
    and emits a one-row summary keyed on the swept value.
    """
    results: list[dict[str, Any]] = []
    num_steps = int(round((end - start) / step_size)) + 1
    for i in range(num_steps):
        value = round(start + (i * step_size), 6)
        if value > end + (step_size / 10):
            break
        defines = inject_parameter(GameDefines(), param_path, value)
        result = run_simulation(defines, max_ticks=max_ticks)
        results.append(extract_sweep_summary(value, result))
    return results


def write_csv(data: list[dict[str, Any]], output_path: Path) -> None:
    """Write a list-of-dicts to ``output_path`` as CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not data:
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["tick"])
            writer.writeheader()
        return
    all_keys: set[str] = set()
    for row in data:
        all_keys.update(row.keys())
    fieldnames = (
        ["tick"] + sorted(k for k in all_keys if k != "tick")
        if "tick" in all_keys
        else sorted(all_keys)
    )
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def parse_param_arg(param_str: str | None) -> tuple[str | None, float | None]:
    """Parse ``--param path=value`` into (path, value)."""
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
    parser = argparse.ArgumentParser(
        description="Parameter analysis tool (spec-064: headless-runner-backed)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__ or "",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    trace_parser = subparsers.add_parser("trace", help="Run one sim, copy trace.csv to output path")
    trace_parser.add_argument(
        "--param",
        type=str,
        default=None,
        help="Parameter override 'path=value' (accepted but not applied to MVP)",
    )
    trace_parser.add_argument(
        "--ticks", type=int, default=DEFAULT_TICKS, help=f"Max ticks (default: {DEFAULT_TICKS})"
    )
    trace_parser.add_argument("--csv", type=Path, required=True, help="Output CSV file path")
    trace_parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Output JSON metadata path (no-op in spec-064 — kept for back-compat)",
    )

    sweep_parser = subparsers.add_parser("sweep", help="Run parameter sweep and emit summary CSV")
    sweep_parser.add_argument(
        "--param",
        type=str,
        required=True,
        help="Parameter path to sweep (e.g., economy.extraction_efficiency)",
    )
    sweep_parser.add_argument("--start", type=float, required=True)
    sweep_parser.add_argument("--end", type=float, required=True)
    sweep_parser.add_argument("--step", type=float, required=True)
    sweep_parser.add_argument(
        "--ticks",
        type=int,
        default=DEFAULT_TICKS,
        help=f"Max ticks per sim (default: {DEFAULT_TICKS})",
    )
    sweep_parser.add_argument("--csv", type=Path, required=True, help="Output CSV file path")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "trace":
        try:
            param_path, param_value = parse_param_arg(args.param)
            print(f"Running trace for {args.ticks} ticks via headless_runner...")
            if param_path is not None:
                print(f"  Parameter override (accepted, MVP no-op): {param_path}={param_value}")
            trace_csv, _defines = run_trace(
                param_path=param_path,
                param_value=param_value,
                max_ticks=args.ticks,
            )
            args.csv.parent.mkdir(parents=True, exist_ok=True)
            args.csv.write_bytes(trace_csv.read_bytes())
            row_count = sum(1 for _ in trace_csv.open()) - 1
            print(f"Trace complete: {row_count} rows recorded")
            print(f"Output written to: {args.csv}")
            if args.json is not None:
                print("(--json is a no-op in spec-064; trace contract lives in manifest.json)")
            return 0
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if args.command == "sweep":
        try:
            print(f"Running sweep: {args.param} from {args.start} to {args.end} step {args.step}")
            sweep_data = run_sweep(
                param_path=args.param,
                start=args.start,
                end=args.end,
                step_size=args.step,
                max_ticks=args.ticks,
            )
            write_csv(sweep_data, args.csv)
            print(f"Sweep complete: {len(sweep_data)} parameter values tested")
            print(f"Output written to: {args.csv}")
            return 0
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
