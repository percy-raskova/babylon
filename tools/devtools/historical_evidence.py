"""Required capture, checksum, and replay evidence for historical runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from tools.devtools.historical_evaluate import HistoricalTrajectory
from tools.devtools.historical_extract import digest_file
from tools.devtools.simulation_qualification import (
    PERIOD_FIELDS,
    SETUP_FIELDS,
    _hash,
    _integer,
    _list,
    _load,
    _object,
    _periods,
    _resolved_inputs,
    _wiring,
)

MAX_EVIDENCE_BYTES = 4 * 1024 * 1024
REQUIRED_FILES = {
    "canonical_experiment.json",
    "trajectory.json",
    "captured_setup.json",
    "periods.json",
    "captured_defines.bin",
    "foundation.bin",
}
FREIGHT_SETUP_FIELDS = {
    "kind",
    "source_site",
    "destination_site",
    "commodity",
    "unit",
    "port_code",
    "partner_code",
    "mode_code",
    "trade_type_code",
    "hs_chapter",
    "geographic_scope",
    "january_observed_kg",
    "capacity_derivation",
    "capacity_kg_per_period",
    "ordered_kg",
    "opening_inventory_kg",
    "travel_periods",
    "inventory_evidence",
    "order_evidence",
    "capacity_evidence",
    "inventory_derivation",
    "order_derivation",
}


def _freight_periods(value: object, horizon: int, mass: int) -> list[dict[str, Any]]:
    rows = _list(value, "freight periods")
    if len(rows) != horizon:
        raise ValueError("freight evidence does not cover the complete trajectory")
    for expected, value in enumerate(rows, 1):
        row = _object(value, PERIOD_FIELDS, "freight period")
        for key in PERIOD_FIELDS - {
            "world_hash",
            "tick_content_sha256",
            "production",
            "staffing",
            "rule_execution",
            "receipt_coverage",
        }:
            _integer(row[key], "freight period." + key)
        if row["period"] != expected or row["conserved_mass_grams"] != mass:
            raise ValueError("freight period sequence or conserved mass differs")
        if row["production"] != [] or row["staffing"] != [] or row["produced_batches"] != 0:
            raise ValueError("freight boundary cannot substitute domestic production or staffing")
        if row["considered_rules"] != 1 or row["fired_rules"] != 1:
            raise ValueError("freight material rule did not execute exactly once")
        _hash(row["world_hash"], "freight world hash")
        _hash(row["tick_content_sha256"], "freight content hash")
    return rows


def _resolved_freight(value: object, spec: dict[str, Any]) -> None:
    setup = _object(value, FREIGHT_SETUP_FIELDS, "resolved freight initialization")
    for key in (
        "january_observed_kg",
        "capacity_kg_per_period",
        "ordered_kg",
        "opening_inventory_kg",
        "travel_periods",
    ):
        _integer(setup[key], "freight initialization." + key)
    if setup["january_observed_kg"] != spec["starting_snapshot"]["arrived_kg"]:
        raise ValueError("freight scale differs from captured January observation")
    expected = {
        "kind": "freight",
        "unit": "kg",
        "port_code": "3801",
        "partner_code": "1220",
        "mode_code": "5",
        "trade_type_code": "2",
        "hs_chapter": "72",
    }
    if any(setup[key] != value for key, value in expected.items()):
        raise ValueError("resolved freight setup is outside the admitted border boundary")


def validate_capture(
    directory: Path,
    trajectory: HistoricalTrajectory,
    spec: dict[str, Any],
    *,
    require_postgres: bool = False,
) -> dict[str, Any]:
    if (directory / "failure.json").exists():
        raise ValueError("runtime failure artifact forbids successful qualification")
    manifest = _object(
        _load(directory / "manifest.json"), {"schema", "status", "files_sha256"}, "manifest"
    )
    if manifest["schema"] != "SimulationExperimentManifestV1" or manifest["status"] != "complete":
        raise ValueError("runtime manifest must be complete")
    expected = REQUIRED_FILES | ({"parity.json", "campaign.json"} if require_postgres else set())
    inventory = _object(manifest["files_sha256"], expected, "runtime manifest inventory")
    if (
        sum((directory / name).stat().st_size for name in expected | {"manifest.json"})
        > MAX_EVIDENCE_BYTES
    ):
        raise ValueError("historical runtime artifacts exceeded the 4 MiB evidence bound")
    for name, checksum in inventory.items():
        if _hash(checksum, "artifact checksum") != digest_file(directory / name):
            raise ValueError(f"runtime artifact checksum mismatch: {name}")
    raw_trajectory = _load(directory / "trajectory.json")
    _integer(raw_trajectory["schema_version"], "trajectory schema version")
    captured_trajectory = HistoricalTrajectory.model_validate_json(
        (directory / "trajectory.json").read_bytes()
    )
    if captured_trajectory != trajectory:
        raise ValueError("evaluated trajectory differs from checksum-protected raw evidence")
    setup = _object(_load(directory / "captured_setup.json"), SETUP_FIELDS, "captured setup")
    canonical_spec = _load(directory / "canonical_experiment.json")
    if canonical_spec != spec or setup["canonical_spec"] != spec:
        raise ValueError("captured experiment differs from initialization-only input")
    identity = trajectory.experiment.model_dump(mode="json")
    if any(
        identity[key] != spec[key]
        for key in ("profile", "epoch", "horizon", "seed", "source_snapshot_sha256")
    ):
        raise ValueError("trajectory identity differs from captured initialization")
    for key in (
        "experiment_input_sha256",
        "defines_sha256",
        "foundation_sha256",
        "content_sha256",
        "rules_sha256",
        "reference_sha256",
    ):
        _hash(setup[key], "setup." + key)
    for filename, key in (
        ("canonical_experiment.json", "experiment_input_sha256"),
        ("foundation.bin", "foundation_sha256"),
        ("captured_defines.bin", "defines_sha256"),
    ):
        if setup[key] != digest_file(directory / filename):
            raise ValueError(f"{filename} differs from captured identity")
    if setup["defines_sha256"] != trajectory.experiment.resolved_inputs_sha256:
        raise ValueError("captured resolved inputs differ from trajectory identity")
    horizon = trajectory.completed_periods
    expected_restarts = (horizon + 12) // 13
    if _integer(setup["checkpoint_restarts"], "checkpoint restarts") != expected_restarts:
        raise ValueError("complete checkpoint restart parity evidence is missing")
    mass = _integer(setup["conserved_mass_grams"], "captured conserved mass")
    raw_periods = _load(directory / "periods.json")
    if spec["profile"] == "historical_employment":
        pools = _resolved_inputs(setup["resolved_inputs"])
        processes = setup["resolved_inputs"]["processes"]
        initial = {row["series_id"]: row["jobs"] for row in spec["starting_snapshot"]["series"]}
        if {row["series_id"]: row["initial_jobs"] for row in processes} != initial or any(
            row["initial_reserve"] != 0 for row in processes
        ):
            raise ValueError(
                "resolved employment differs from observed starting jobs or Designed zero reserve"
            )
        periods, _ = _periods(raw_periods, horizon, mass, pools)
        subjects = {"workforce-" + row["process_key"]: row["series_id"] for row in processes}
        jobs = {(row.period, row.series_id): row.jobs for row in trajectory.employment}
        for period in periods:
            if any(
                row["employed"] != jobs[(period["period"], subjects[row["subject"]])]
                for row in period["staffing"]
            ):
                raise ValueError(
                    "employment trajectory differs from authoritative staffing receipts"
                )
    else:
        _resolved_freight(setup["resolved_inputs"], spec)
        periods = _freight_periods(raw_periods, horizon, mass)
        arrivals = {row.period: row.arrived_kg for row in trajectory.freight}
        if any(row["arrived_units"] != arrivals[row["period"]] for row in periods):
            raise ValueError("freight trajectory differs from authoritative arrival receipts")
    _wiring(setup, periods)
    states = trajectory.employment or trajectory.freight
    world_hashes = {row.period: row.world_hash for row in states}
    if any(row["world_hash"] != world_hashes[row["period"]] for row in periods):
        raise ValueError("period and trajectory world hashes differ")
    active = sum(
        row["produced_batches"] > 0 and row["dispatched_units"] > 0 for row in periods[-13:]
    )
    if _integer(setup["final_year_active_periods"], "final modeled year activity") != active:
        raise ValueError("captured activity claim differs from period evidence")
    if require_postgres:
        parity = _object(
            _load(directory / "parity.json"),
            {
                "schema",
                "mode",
                "matched",
                "periods",
                "restarts",
                "final_world_hash",
                "foundation_sha256",
            },
            "PostgreSQL parity",
        )
        if (
            parity["schema"] != "SimulationExperimentParityV1"
            or parity["mode"] != "postgresql"
            or parity["matched"] is not True
            or _integer(parity["periods"], "parity periods") != horizon
            or _integer(parity["restarts"], "parity restarts") != expected_restarts
            or parity["final_world_hash"] != world_hashes[horizon]
            or parity["foundation_sha256"] != setup["foundation_sha256"]
        ):
            raise ValueError("PostgreSQL parity evidence is incomplete or mismatched")
        campaign = _object(
            _load(directory / "campaign.json"), {"campaign_id"}, "persisted campaign"
        )
        if (
            not isinstance(campaign["campaign_id"], str)
            or str(UUID(campaign["campaign_id"])) != campaign["campaign_id"]
        ):
            raise ValueError("persisted campaign identity is invalid")
    return setup
