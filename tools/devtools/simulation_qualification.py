"""Qualify long diagnostic content and bounded deterministic input sensitivity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from tools.devtools.sim_report import _bounded_process_run

ROOT = Path(__file__).resolve().parents[2]
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024


SPEC_FIELDS = {
    "schema",
    "profile",
    "epoch",
    "horizon",
    "seed",
    "source_snapshot_sha256",
    "starting_snapshot",
    "interventions",
}
SETUP_FIELDS = {
    "canonical_spec",
    "resolved_inputs",
    "experiment_input_sha256",
    "defines_sha256",
    "foundation_sha256",
    "content_sha256",
    "rules_sha256",
    "reference_sha256",
    "initialization_evidence",
    "checkpoint_restarts",
    "final_year_active_periods",
    "conserved_mass_grams",
}
PERIOD_FIELDS = {
    "period",
    "world_hash",
    "tick_content_sha256",
    "produced_batches",
    "dispatched_units",
    "arrived_units",
    "conserved_mass_grams",
    "considered_rules",
    "fired_rules",
    "production",
    "staffing",
}
WORKFORCE_SUBJECTS = {
    f"workforce-{key}"
    for key in (
        "sheet-rolling",
        "panel-forming",
        "subassembly-making",
        "meal-milling",
        "meal-packaging",
    )
}
INTERVENTION_ORDER = {
    "regional_delivery": 0,
    "transport_capacity_permille": 1,
    "opening_sheet_stock": 2,
}


def _integer(value: object, label: str, *, minimum: int = 0, maximum: int = 2**64 - 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def _object(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} has missing or unknown fields")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a SHA-256 digest")
    return value


def _load(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate field in {path.name}: {key}")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise ValueError(f"nonfinite number in {path.name}: {value}")

    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=nonfinite)


def _canonical_spec(value: object) -> dict[str, Any]:
    spec = _object(value, SPEC_FIELDS, "experiment")
    horizon = _integer(spec["horizon"], "horizon", minimum=1)
    _integer(spec["seed"], "seed", minimum=-(2**63), maximum=2**63 - 1)
    if spec["schema"] != "SimulationExperimentV1" or spec["profile"] not in {
        "sustained",
        "depletion",
        "delivery_stock",
    }:
        raise ValueError("experiment is not an admitted long or sensitivity profile")
    expected_horizon = 16 if spec["profile"] == "delivery_stock" else 130
    if horizon != expected_horizon or any(
        spec[key] is not None for key in ("epoch", "source_snapshot_sha256", "starting_snapshot")
    ):
        raise ValueError(
            "diagnostic profile has an unsupported horizon or historical initialization"
        )
    interventions = _list(spec["interventions"], "interventions")
    kinds = set()
    for row in interventions:
        if (
            not isinstance(row, dict)
            or row.get("kind") not in INTERVENTION_ORDER
            or row["kind"] in kinds
        ):
            raise ValueError("unknown or duplicate intervention")
        kind = row["kind"]
        kinds.add(kind)
        if kind == "regional_delivery":
            _object(row, {"kind", "delivery"}, "delivery intervention")
            if (
                row["delivery"] not in {"standard", "delayed"}
                or spec["profile"] != "delivery_stock"
            ):
                raise ValueError("delivery intervention is not admitted for this profile")
        elif kind == "transport_capacity_permille":
            _object(row, {"kind", "permille"}, "transport intervention")
            _integer(row["permille"], "transport permille", minimum=250, maximum=2000)
            if spec["profile"] == "depletion":
                raise ValueError("depletion profile cannot receive interventions")
        else:
            _object(row, {"kind", "kilograms"}, "opening stock intervention")
            _integer(row["kilograms"], "opening kilograms", maximum=1_000_000)
            if spec["profile"] == "depletion":
                raise ValueError("depletion profile cannot receive interventions")
    return {
        **spec,
        "interventions": sorted(interventions, key=lambda row: INTERVENTION_ORDER[row["kind"]]),
    }


def _resolved_inputs(value: object) -> dict[str, int]:
    regional = _object(
        value,
        {
            "kind",
            "capacity_derivation",
            "hours_per_person_period",
            "opening_policy",
            "processes",
            "routes",
        },
        "resolved initialization",
    )
    if regional["kind"] != "regional":
        raise ValueError("long diagnostic setup must use the captured regional boundary")
    _integer(regional["hours_per_person_period"], "working hours per period", minimum=1)
    pools: dict[str, int] = {}
    for value in _list(regional["processes"], "resolved processes"):
        process = _object(
            value,
            {
                "process_key",
                "series_id",
                "initial_jobs",
                "initial_reserve",
                "jobs_evidence",
                "hours_per_person_week",
                "labor_hours_per_batch",
                "weekly_capacity_batches",
                "period_capacity_batches",
                "opening_planned_batches",
                "inputs",
            },
            "resolved process",
        )
        key = process["process_key"]
        if (
            not isinstance(key, str)
            or "workforce-" + key not in WORKFORCE_SUBJECTS
            or "workforce-" + key in pools
        ):
            raise ValueError("resolved process identity is unknown or duplicated")
        for field in (
            "initial_jobs",
            "initial_reserve",
            "hours_per_person_week",
            "labor_hours_per_batch",
            "weekly_capacity_batches",
            "period_capacity_batches",
            "opening_planned_batches",
        ):
            _integer(process[field], "resolved process." + field)
        pools["workforce-" + key] = process["initial_jobs"] + process["initial_reserve"]
        for value in _list(process["inputs"], "resolved inputs"):
            item = _object(
                value,
                {"good_key", "unit", "quantity_per_batch", "opening_quantity"},
                "resolved input",
            )
            _integer(item["quantity_per_batch"], "input quantity per batch")
            _integer(item["opening_quantity"], "opening input quantity")
    if set(pools) != WORKFORCE_SUBJECTS:
        raise ValueError("resolved initialization must cover the five workforce pools")
    for value in _list(regional["routes"], "resolved routes"):
        route = _object(
            value,
            {
                "route_key",
                "supplier_site",
                "buyer_site",
                "good_key",
                "unit",
                "ordered_quantity",
                "travel_periods",
                "capacities",
            },
            "resolved route",
        )
        _integer(route["ordered_quantity"], "ordered quantity")
        _integer(route["travel_periods"], "travel periods", maximum=2**16 - 1)
        for value in _list(route["capacities"], "resolved capacities"):
            capacity = _object(value, {"key", "grams_per_period"}, "resolved capacity")
            _integer(capacity["grams_per_period"], "capacity grams per period")
    return pools


def _periods(
    value: object, horizon: int, mass: int, initial_pools: dict[str, int]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    periods = _list(value, "period evidence")
    if len(periods) != horizon:
        raise ValueError("incomplete period evidence")
    pool_totals = dict(initial_pools)
    process_ids: dict[str, str] = {}
    process_batches = {subject.removeprefix("workforce-"): 0 for subject in initial_pools}
    for expected, value in enumerate(periods, 1):
        row = _object(value, PERIOD_FIELDS, "period evidence")
        for key in (
            "period",
            "produced_batches",
            "dispatched_units",
            "arrived_units",
            "conserved_mass_grams",
            "considered_rules",
            "fired_rules",
        ):
            _integer(row[key], f"period.{key}")
        if row["period"] != expected or row["conserved_mass_grams"] != mass:
            raise ValueError("period sequence or conserved inventory including transit differs")
        if row["considered_rules"] != 1 or row["fired_rules"] != 1:
            raise ValueError("required material rule did not execute exactly once")
        _hash(row["world_hash"], "period world hash")
        _hash(row["tick_content_sha256"], "period content hash")
        production = _list(row["production"], "production receipts")
        unique_processes = set()
        for value in production:
            receipt = _object(
                value, {"process_id", "process_key", "produced_batches"}, "production receipt"
            )
            process_id = _hash(receipt["process_id"], "production process id")
            process_key = receipt["process_key"]
            if not isinstance(process_key, str) or process_key not in process_batches:
                raise ValueError("unknown production recipe key")
            if process_key in process_ids and process_ids[process_key] != process_id:
                raise ValueError("production recipe identity changed between periods")
            process_ids[process_key] = process_id
            if process_id in unique_processes:
                raise ValueError("duplicate process production receipt")
            unique_processes.add(process_id)
            count = _integer(receipt["produced_batches"], "process batches")
            process_batches[process_key] += count
        if sum(receipt["produced_batches"] for receipt in production) != row["produced_batches"]:
            raise ValueError("production activity count differs from receipts")
        staffing = _list(row["staffing"], "staffing receipts")
        unique_subjects = set()
        for value in staffing:
            receipt = _object(value, {"subject", "employed", "reserve"}, "staffing receipt")
            subject = receipt["subject"]
            if (
                not isinstance(subject, str)
                or subject not in WORKFORCE_SUBJECTS
                or subject in unique_subjects
            ):
                raise ValueError("unknown or duplicate workforce subject")
            unique_subjects.add(subject)
            employed = _integer(receipt["employed"], "employed slots")
            reserve = _integer(receipt["reserve"], "reserve slots")
            if subject in pool_totals and pool_totals[subject] != employed + reserve:
                raise ValueError("workforce pool does not conserve employed and reserve slots")
            pool_totals[subject] = employed + reserve
        if unique_subjects != WORKFORCE_SUBJECTS:
            raise ValueError("staffing evidence does not cover the five workforce pools")
    return periods, process_batches


def validate_run(output: Path, spec: dict[str, Any], *, persisted: bool) -> dict[str, Any]:
    """Incomplete, inconsistent or unqualified evidence cannot produce success."""
    spec = _canonical_spec(spec)
    if (output / "failure.json").exists():
        raise ValueError("runtime retained failure evidence")
    files = [path for path in output.iterdir() if path.is_file()]
    if sum(path.stat().st_size for path in files) > MAX_ARTIFACT_BYTES:
        raise ValueError("experiment exceeds the 4 MiB artifact budget")
    manifest = _object(
        _load(output / "manifest.json"), {"schema", "status", "files_sha256"}, "manifest"
    )
    required = {
        "canonical_experiment.json",
        "trajectory.json",
        "captured_setup.json",
        "periods.json",
        "captured_defines.bin",
        "foundation.bin",
    }
    if persisted:
        required |= {"parity.json", "campaign.json"}
    inventory = _object(manifest["files_sha256"], required, "manifest inventory")
    if manifest["schema"] != "SimulationExperimentManifestV1" or manifest["status"] != "complete":
        raise ValueError("incomplete experiment manifest")
    for filename, digest in inventory.items():
        _hash(digest, "artifact digest")
        if hashlib.sha256((output / filename).read_bytes()).hexdigest() != digest:
            raise ValueError(f"corrupt artifact: {filename}")
    setup = _object(_load(output / "captured_setup.json"), SETUP_FIELDS, "captured setup")
    canonical = (output / "canonical_experiment.json").read_bytes()
    if (
        _canonical_spec(_load(output / "canonical_experiment.json")) != spec
        or _canonical_spec(setup["canonical_spec"]) != spec
    ):
        raise ValueError("captured inputs differ from submitted experiment")
    digest = hashlib.sha256(canonical).hexdigest()
    for key in (
        "experiment_input_sha256",
        "defines_sha256",
        "foundation_sha256",
        "content_sha256",
        "rules_sha256",
        "reference_sha256",
    ):
        _hash(setup[key], "setup." + key)
    if setup["experiment_input_sha256"] != digest:
        raise ValueError("captured input checksum mismatch")
    for filename, key in (
        ("foundation.bin", "foundation_sha256"),
        ("captured_defines.bin", "defines_sha256"),
    ):
        if hashlib.sha256((output / filename).read_bytes()).hexdigest() != setup[key]:
            raise ValueError(f"{filename} checksum mismatch")
    if (
        not isinstance(setup["initialization_evidence"], str)
        or not setup["initialization_evidence"]
    ):
        raise ValueError("initialization evidence class is missing")
    horizon = spec["horizon"]
    expected_restarts = (horizon + 12) // 13
    if _integer(setup["checkpoint_restarts"], "checkpoint restarts") != expected_restarts:
        raise ValueError("complete checkpoint replay evidence missing")
    mass = _integer(setup["conserved_mass_grams"], "setup conserved mass")
    periods, process_batches = _periods(
        _load(output / "periods.json"), horizon, mass, _resolved_inputs(setup["resolved_inputs"])
    )
    trajectory = _object(
        _load(output / "trajectory.json"),
        {
            "schema_version",
            "experiment",
            "completed_periods",
            "employment",
            "freight",
            "observed_choice_count",
        },
        "trajectory",
    )
    if (
        _integer(trajectory["schema_version"], "trajectory schema") != 1
        or _integer(trajectory["completed_periods"], "completed periods") != horizon
    ):
        raise ValueError("trajectory is incomplete or uses an unknown schema")
    if _list(trajectory["employment"], "employment") or _list(trajectory["freight"], "freight"):
        raise ValueError("long diagnostic profile cannot emit historical boundary observations")
    identity = _object(
        trajectory["experiment"],
        {"profile", "epoch", "horizon", "seed", "source_snapshot_sha256", "resolved_inputs_sha256"},
        "trajectory identity",
    )
    _integer(identity["seed"], "trajectory seed", minimum=-(2**63), maximum=2**63 - 1)
    _integer(identity["horizon"], "trajectory horizon", minimum=1)
    for key in ("profile", "epoch", "horizon", "seed", "source_snapshot_sha256"):
        if identity[key] != spec[key]:
            raise ValueError(f"trajectory identity mismatch: {key}")
    if (
        _hash(identity["resolved_inputs_sha256"], "trajectory input hash")
        != setup["defines_sha256"]
    ):
        raise ValueError("trajectory input checksum mismatch")
    active = sum(
        row["produced_batches"] > 0 and row["dispatched_units"] > 0 for row in periods[-13:]
    )
    if _integer(setup["final_year_active_periods"], "final year active periods") != active:
        raise ValueError("claimed final-year activity differs from period evidence")
    if spec["profile"] == "sustained" and active != 13:
        raise ValueError("sustained profile is inactive during the final modeled year")
    if spec["profile"] == "depletion" and active != 0:
        raise ValueError("finite-endowment control did not deplete")
    if _integer(trajectory["observed_choice_count"], "observed choices") != 0:
        raise ValueError("deterministic sensitivity profile consumed randomness")
    if persisted:
        parity = _object(
            _load(output / "parity.json"),
            {
                "schema",
                "mode",
                "matched",
                "periods",
                "restarts",
                "foundation_sha256",
                "final_world_hash",
            },
            "PostgreSQL parity",
        )
        if (
            parity["schema"] != "SimulationExperimentParityV1"
            or parity["mode"] != "postgresql"
            or parity["matched"] is not True
            or _integer(parity["periods"], "parity periods") != horizon
            or _integer(parity["restarts"], "parity restarts") != expected_restarts
            or parity["foundation_sha256"] != setup["foundation_sha256"]
            or parity["final_world_hash"] != periods[-1]["world_hash"]
        ):
            raise ValueError("persisted replay parity is incomplete or inconsistent")
        campaign = _object(_load(output / "campaign.json"), {"campaign_id"}, "persisted campaign")
        if (
            not isinstance(campaign["campaign_id"], str)
            or str(UUID(campaign["campaign_id"])) != campaign["campaign_id"]
        ):
            raise ValueError("persisted campaign identity is invalid")
    interventions = {row["kind"]: row for row in spec["interventions"]}
    return {
        "profile": spec["profile"],
        "periods": horizon,
        "final_year_active_periods": active,
        "production_active_periods": sum(row["produced_batches"] > 0 for row in periods),
        "dispatch_active_periods": sum(row["dispatched_units"] > 0 for row in periods),
        "arrival_active_periods": sum(row["arrived_units"] > 0 for row in periods),
        "produced_batches_by_process": dict(sorted(process_batches.items())),
        "final_staffing_by_subject": {
            row["subject"]: {"employed": row["employed"], "reserve": row["reserve"]}
            for row in periods[-1]["staffing"]
        },
        "final_employed_slots": sum(row["employed"] for row in periods[-1]["staffing"]),
        "final_reserve_slots": sum(row["reserve"] for row in periods[-1]["staffing"]),
        "conserved_mass_grams": mass,
        "transport_capacity_permille": interventions.get("transport_capacity_permille", {}).get(
            "permille"
        ),
        "opening_sheet_kg": interventions.get("opening_sheet_stock", {}).get("kilograms"),
        "checkpoint_restarts": setup["checkpoint_restarts"],
        "postgresql_parity": persisted,
        "experiment_input_sha256": digest,
        "manifest_sha256": hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest(),
    }


def render_summary(rows: list[dict[str, Any]], failures: list[str]) -> str:
    lines = [
        "# Long simulation qualification",
        "",
        "Ten modeled years use 130 periods of 28 days.",
        "Sensitivity is a deterministic input comparison; it is not a sampled ensemble or a set of independent replicates.",
        "",
        "| Profile | Completed periods | Active periods in final modeled year | Replay restarts | PostgreSQL parity |",
        "|---|---:|---:|---:|---|",
    ]
    for row in rows:
        if row["profile"] != "delivery_stock":
            lines.append(
                f"| {row['case']} | {row['periods']} | {row['final_year_active_periods']} | {row['checkpoint_restarts']} | {'verified' if row['postgresql_parity'] else 'not requested'} |"
            )
    sensitivity = [row for row in rows if row["profile"] == "delivery_stock"]
    if sensitivity:
        lines += [
            "",
            "## Sensitivity: standard delivery, 16 periods",
            "",
            "| Transport capacity (per mille) | Opening sheet (kg) | Production-active periods | Dispatch-active periods | Arrival-active periods | Final employed slots | Final reserve slots |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in sensitivity:
            lines.append(
                f"| {row['transport_capacity_permille']} | {row['opening_sheet_kg']} | {row['production_active_periods']} | {row['dispatch_active_periods']} | {row['arrival_active_periods']} | {row['final_employed_slots']} | {row['final_reserve_slots']} |"
            )
        process_keys = sorted(
            {key for row in sensitivity for key in row["produced_batches_by_process"]}
        )
        lines += [
            "",
            "Batch completions by recipe (each column retains its own recipe unit):",
            "",
            "| Capacity / opening sheet | " + " | ".join(process_keys) + " |",
            "|---|" + "---:|" * len(process_keys),
        ]
        for row in sensitivity:
            lines.append(
                f"| {row['transport_capacity_permille']} / {row['opening_sheet_kg']} kg | "
                + " | ".join(
                    str(row["produced_batches_by_process"].get(key, 0)) for key in process_keys
                )
                + " |"
            )
        lines += [
            "",
            "Production and freight columns count periods with activity, not quantities. Per-process batch completions and per-workforce staffing are retained in `comparison.json`; unlike commodity units and different recipes are never added into a physical total. Conserved physical mass is measured separately in grams, including transit.",
            "",
        ]
    if failures:
        lines += ["", "## Required evidence failures", ""] + [
            f"- {failure}" for failure in failures
        ]
    return "\n".join(lines) + "\n"


def run(runtime: Path, output: Path, *, dsn: str | None, sensitivity: bool) -> int:
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(
            "Output directory already exists; preserve prior evidence and choose a new directory."
        )
        return 2
    try:
        runtime = runtime.resolve(strict=True)
        if not runtime.is_file() or not os.access(runtime, os.X_OK):
            raise ValueError("runtime must be an executable file")
        with runtime.open("rb") as executable:
            runtime_sha256 = hashlib.file_digest(executable, "sha256").hexdigest()
        cases: dict[str, dict[str, Any]] = {
            name: _canonical_spec(
                _load(ROOT / f"content/scenarios/michigan/diagnostic-{name}.json")
            )
            for name in ("sustained", "depletion")
        }
    except (ValueError, OSError, KeyError, TypeError) as error:
        failure = f"Required preflight failed: {error}"
        (output / "summary.md").write_text(render_summary([], [failure]))
        (output / "comparison.json").write_text(
            json.dumps({"status": "failed", "cases": [], "failures": [failure]}, indent=2) + "\n"
        )
        return 2
    if sensitivity:
        for capacity in (500, 1000, 1500):
            for stock in (0, 320):
                cases[f"capacity-{capacity}-stock-{stock}"] = {
                    "schema": "SimulationExperimentV1",
                    "profile": "delivery_stock",
                    "epoch": None,
                    "horizon": 16,
                    "seed": 319,
                    "source_snapshot_sha256": None,
                    "starting_snapshot": None,
                    "interventions": [
                        {"kind": "regional_delivery", "delivery": "standard"},
                        {"kind": "transport_capacity_permille", "permille": capacity},
                        {"kind": "opening_sheet_stock", "kilograms": stock},
                    ],
                }
    failures: list[str] = []
    rows = []
    failed = False
    for name, spec in cases.items():
        destination = output / name
        destination.mkdir()
        input_path = destination / "input.json"
        input_path.write_text(json.dumps(spec))
        persisted = dsn is not None and name in {"sustained", "depletion"}
        try:
            argv = [
                str(runtime.resolve()),
                "--input",
                str(input_path.resolve()),
                "--output",
                str(destination.resolve()),
            ]
            if persisted:
                argv += ["--dsn", str(dsn)]
            outcome = _bounded_process_run(argv, environment=os.environ, timeout_seconds=900.0)
            (destination / "stdout.log").write_bytes(outcome.stdout)
            (destination / "stderr.log").write_bytes(outcome.stderr)
            (destination / "execution.json").write_text(
                json.dumps(
                    {
                        "schema": "babylon.simulation-execution.v1",
                        "runtime_sha256": runtime_sha256,
                        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
                        "wall_time_ns": outcome.wall_time_ns,
                        "max_rss_bytes": outcome.max_rss_bytes,
                        "returncode": outcome.returncode,
                        "wrapper_status": outcome.wrapper_status,
                    },
                    indent=2,
                )
                + "\n"
            )
            if outcome.wrapper_status or outcome.returncode != 0:
                raise ValueError(outcome.wrapper_error or f"runtime exited {outcome.returncode}")
            row = {
                "case": name,
                **validate_run(destination, spec, persisted=persisted),
                "wall_seconds": outcome.wall_time_ns / 1e9,
            }
            rows.append(row)
        except (ValueError, OSError, KeyError, TypeError) as error:
            failed = True
            failures.append(f"{name}: **FAILED** — {error}")
        (output / "summary.md").write_text(render_summary(rows, failures))
    (output / "comparison.json").write_text(
        json.dumps(
            {
                "status": "failed" if failed else "complete",
                "kind": "deterministic_sensitivity",
                "cases": rows,
                "failures": failures,
                "quantity_policy": "Per-process batches are retained separately. Activity periods count execution, not physical quantities; conserved mass includes transit and is measured in grams.",
            },
            indent=2,
        )
        + "\n"
    )
    return 2 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dsn-env")
    parser.add_argument("--sensitivity", action="store_true")
    args = parser.parse_args()
    return run(
        args.runtime,
        args.output,
        dsn=os.environ[args.dsn_env] if args.dsn_env else None,
        sensitivity=args.sensitivity,
    )


if __name__ == "__main__":
    raise SystemExit(main())
