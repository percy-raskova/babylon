"""Run both historical profiles serially and retain replayable evidence.

Build ``cargo build --locked -p babylon-persistence --example
simulation_experiment`` from rust/ first. Then run ``python -m
tools.devtools.historical_report --runtime PATH_TO_EXAMPLE --output DIR``.
The runtime receives only the captured starting observations. The separate
Parquet targets enter the evaluator after authoritative execution finishes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from tools.devtools.historical_evaluate import HistoricalTrajectory, evaluate, write_report
from tools.devtools.historical_evidence import validate_capture
from tools.devtools.historical_extract import (
    DEFAULT_FIXTURES,
    canonical_bytes,
    digest_file,
    load_fixtures,
    starting_specs,
)
from tools.devtools.sim_report import _bounded_process_run

MAX_TRAJECTORY_BYTES = 4 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 900.0


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def initialization_summary(setup: dict[str, Any]) -> str:
    """Explain the actual captured setup; no evaluator target enters initialization."""
    value = setup["resolved_inputs"]
    lines = ["## Captured historical initialization", "", setup["initialization_evidence"], ""]
    if value["kind"] == "regional":
        lines += [
            value["capacity_derivation"],
            "",
            value["opening_policy"],
            "",
            "Employment observations are quarter-beginning jobs, not unique people. Scoring uses 2010-01-01 through 2019-10-01; the 131-period trajectory continues beyond the end of 2019. Each observation uses the latest committed state on or before that date.",
            "",
            f"Working time: {value['hours_per_person_period']} Designed hours per employed slot per 28-day period.",
            "",
            "| Recipe / county-industry | Initial jobs | Initial reserve | Hours/person/week | Labor hours/batch | Weekly batches | Period batches | Opening commitment (batches) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in value["processes"]:
            numbers = [
                row[key]
                for key in (
                    "initial_jobs",
                    "initial_reserve",
                    "hours_per_person_week",
                    "labor_hours_per_batch",
                    "weekly_capacity_batches",
                    "period_capacity_batches",
                    "opening_planned_batches",
                )
            ]
            lines.append(
                f"| {_cell(row['process_key'])} / {_cell(row['series_id'])} | "
                + " | ".join(map(str, numbers))
                + " |"
            )
        lines += [
            "",
            "Opening inputs retain their own commodity units:",
            "",
            "| Recipe | Input good | Unit | Quantity/batch | Opening quantity |",
            "|---|---|---|---:|---:|",
        ]
        for row in value["processes"]:
            for item in row["inputs"]:
                lines.append(
                    "| "
                    + " | ".join(
                        _cell(item)
                        for item in (
                            row["process_key"],
                            item["good_key"],
                            item["unit"],
                            item["quantity_per_batch"],
                            item["opening_quantity"],
                        )
                    )
                    + " |"
                )
        lines += [
            "",
            "| Route / endpoints | Good | Unit | Finite ordered quantity | Travel periods | Captured capacity bounds |",
            "|---|---|---|---:|---:|---|",
        ]
        for row in value["routes"]:
            capacities = (
                "; ".join(
                    f"{entry['key']}: {entry['grams_per_period']} g/period"
                    for entry in row["capacities"]
                )
                or "Local transfer; no corridor bound"
            )
            cells = (
                f"{row['route_key']}: {row['supplier_site']} → {row['buyer_site']}",
                row["good_key"],
                row["unit"],
                row["ordered_quantity"],
                row["travel_periods"],
                capacities,
            )
            lines.append("| " + " | ".join(map(_cell, cells)) + " |")
    elif value["kind"] == "freight":
        lines += [
            f"{value['source_site']} → {value['destination_site']}; {value['commodity']}, measured in {value['unit']}.",
            "",
            value["geographic_scope"],
            "",
            f"Boundary codes: Detroit port {value['port_code']}; Canada {value['partner_code']}; truck mode {value['mode_code']}; imports {value['trade_type_code']}; HS{value['hs_chapter']}. January 2019 sets the initial scale; only February 2019–December 2024 is scored.",
            "",
            "| Captured quantity | Kilograms | Evidence |",
            "|---|---:|---|",
            f"| January 2019 imports | {value['january_observed_kg']} | Observed |",
            f"| Transport capacity per 28-day period | {value['capacity_kg_per_period']} | {_cell(value['capacity_evidence'])} |",
            f"| Opening Canadian inventory | {value['opening_inventory_kg']} | {_cell(value['inventory_evidence'])} |",
            f"| Finite order ceiling | {value['ordered_kg']} | {_cell(value['order_evidence'])} |",
            "",
            "Capacity and rounding: " + value["capacity_derivation"],
            "",
            "Inventory derivation: " + value["inventory_derivation"],
            "",
            "Order derivation: " + value["order_derivation"],
            "",
            f"Travel delay: {value['travel_periods']} modeled periods. Period arrivals are allocated across calendar months by exact day overlap.",
        ]
    else:
        raise ValueError("unknown captured historical initialization kind")
    return "\n".join(lines) + "\n"


def combined_child_summary(name: str, child: str) -> str:
    """Keep standalone SVG links usable when a child summary moves to its parent."""
    if name not in {"employment", "freight"}:
        raise ValueError("unknown historical report child")
    child = child.replace("# Historical comparison:", "### Historical comparison:")
    return re.sub(
        r"(!\[[^\]]*\]\()([A-Za-z0-9_-]+\.svg)(\))",
        lambda match: f"{match[1]}{name}/{match[2]}{match[3]}",
        child,
    )


def run_profiles(
    runtime: Path,
    fixtures: Path,
    output: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    dsn: str | None = None,
) -> int:
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        print(
            "Historical output directory must be empty; preserve prior evidence and choose a new directory."
        )
        return 2
    summaries: list[str] = ["# Historical simulation validation", ""]
    failed = False
    try:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("runtime timeout must be finite and positive")
        runtime = runtime.resolve(strict=True)
        if not runtime.is_file() or not os.access(runtime, os.X_OK):
            raise ValueError("runtime must be an executable file")
        manifest, employment, freight = load_fixtures(fixtures)
        specs = starting_specs(employment, freight, manifest["initialization_snapshot_sha256"])
    except (ValueError, OSError, KeyError, TypeError) as error:
        (output / "summary.md").write_text(
            "\n".join(summaries + [f"Required preflight failed: {error}", ""])
        )
        return 2
    for name, spec in specs.items():
        destination = output / name
        destination.mkdir(parents=True, exist_ok=True)
        try:
            committed_spec = json.loads((fixtures / f"{name}_experiment.json").read_text())
            if committed_spec != spec:
                raise ValueError(
                    "committed experiment differs from initialization-only observations"
                )
            spec_path = destination / "input.json"
            spec_path.write_bytes(canonical_bytes(spec))
            argv = [
                str(runtime),
                "--input",
                str(spec_path.resolve()),
                "--output",
                str(destination.resolve()),
            ]
            if dsn:
                argv += ["--dsn", dsn]
            outcome = _bounded_process_run(
                argv, environment=os.environ, timeout_seconds=timeout_seconds
            )
            (destination / "stdout.log").write_bytes(outcome.stdout)
            (destination / "stderr.log").write_bytes(outcome.stderr)
            evidence: dict[str, Any] = {
                "schema": "babylon.historical-execution.v1",
                "runtime_sha256": digest_file(runtime),
                "input_sha256": digest_file(spec_path),
                "wall_time_ns": outcome.wall_time_ns,
                "max_rss_bytes": outcome.max_rss_bytes,
                "returncode": outcome.returncode,
                "wrapper_status": outcome.wrapper_status,
            }
            (destination / "execution.json").write_bytes(canonical_bytes(evidence))
            if outcome.wrapper_error or outcome.returncode != 0:
                raise ValueError(
                    outcome.wrapper_error or f"authoritative runtime exited {outcome.returncode}"
                )
            trajectory_path = destination / "trajectory.json"
            if trajectory_path.stat().st_size > MAX_TRAJECTORY_BYTES:
                raise ValueError("trajectory exceeded the 4 MiB report bound")
            trajectory = HistoricalTrajectory.model_validate_json(trajectory_path.read_bytes())
            if (
                trajectory.experiment.seed != spec["seed"]
                or trajectory.experiment.profile != spec["profile"]
            ):
                raise ValueError("runtime identity differs from submitted experiment")
            setup = validate_capture(
                destination, trajectory, spec, require_postgres=dsn is not None
            )
            write_report(
                evaluate(trajectory, manifest, employment, freight, verified_setup=setup),
                destination,
            )
            summary_path = destination / "summary.md"
            summary_path.write_text(summary_path.read_text() + "\n" + initialization_summary(setup))
            summaries += [
                f"## {name.title()}",
                "",
                combined_child_summary(name, summary_path.read_text()),
                "",
            ]
        except (ValueError, OSError, KeyError, TypeError) as error:
            failed = True
            failure = (
                f"# Historical {name} failed\n\nRequired execution or evidence failed: {error}\n"
            )
            (destination / "summary.md").write_text(failure)
            summaries += [failure, ""]
    (output / "summary.md").write_text("\n".join(summaries))
    return 2 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--dsn-env", help="Optional environment variable containing a scratch PostgreSQL DSN"
    )
    args = parser.parse_args()
    dsn = os.environ[args.dsn_env] if args.dsn_env else None
    return run_profiles(
        args.runtime, args.fixtures, args.output, timeout_seconds=args.timeout_seconds, dsn=dsn
    )


if __name__ == "__main__":
    raise SystemExit(main())
