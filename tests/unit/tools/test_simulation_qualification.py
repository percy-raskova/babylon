"""Long diagnostic success requires complete, typed, replayable engine evidence."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from tools.devtools.simulation_qualification import validate_run

SUBJECTS = [
    f"workforce-{key}"
    for key in [
        "sheet-rolling",
        "panel-forming",
        "subassembly-making",
        "meal-milling",
        "meal-packaging",
    ]
]


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _refresh(output: Path) -> None:
    files = [p for p in output.iterdir() if p.name not in {"manifest.json", "failure.json"}]
    _json(
        output / "manifest.json",
        {
            "schema": "SimulationExperimentManifestV1",
            "status": "complete",
            "files_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        },
    )


def _fixture(output: Path, profile: str = "sustained", *, persisted: bool = False) -> dict:
    horizon = 16 if profile == "delivery_stock" else 130
    spec = {
        "schema": "SimulationExperimentV1",
        "profile": profile,
        "epoch": None,
        "horizon": horizon,
        "seed": 319,
        "source_snapshot_sha256": None,
        "starting_snapshot": None,
        "interventions": [],
    }
    if profile == "delivery_stock":
        spec["interventions"] = [
            {"kind": "regional_delivery", "delivery": "standard"},
            {"kind": "transport_capacity_permille", "permille": 500},
            {"kind": "opening_sheet_stock", "kilograms": 320},
        ]
    output.mkdir()
    _json(output / "canonical_experiment.json", spec)
    defines = b"defines"
    foundation = b"foundation"
    (output / "captured_defines.bin").write_bytes(defines)
    (output / "foundation.bin").write_bytes(foundation)
    setup = {
        "canonical_spec": spec,
        "resolved_inputs": {
            "kind": "regional",
            "capacity_derivation": "Designed capacities",
            "hours_per_person_period": 160,
            "opening_policy": "Designed opening inventories",
            "processes": [
                {
                    "process_key": subject.removeprefix("workforce-"),
                    "series_id": "example",
                    "initial_jobs": 2,
                    "initial_reserve": 3,
                    "jobs_evidence": "Designed",
                    "hours_per_person_week": 40,
                    "labor_hours_per_batch": 8,
                    "weekly_capacity_batches": 10,
                    "period_capacity_batches": 40,
                    "opening_planned_batches": 1,
                    "inputs": [],
                }
                for subject in SUBJECTS
            ],
            "routes": [],
        },
        "experiment_input_sha256": hashlib.sha256(
            (output / "canonical_experiment.json").read_bytes()
        ).hexdigest(),
        "defines_sha256": hashlib.sha256(defines).hexdigest(),
        "foundation_sha256": hashlib.sha256(foundation).hexdigest(),
        "content_sha256": "c" * 64,
        "rules_sha256": "d" * 64,
        "reference_sha256": "e" * 64,
        "initialization_evidence": "Designed diagnostic inputs",
        "checkpoint_restarts": (horizon + 12) // 13,
        "final_year_active_periods": 0 if profile == "depletion" else 13,
        "conserved_mass_grams": 1000000,
    }
    _json(output / "captured_setup.json", setup)
    _json(
        output / "trajectory.json",
        {
            "schema_version": 1,
            "experiment": {
                key: spec[key]
                for key in ["profile", "epoch", "horizon", "seed", "source_snapshot_sha256"]
            }
            | {"resolved_inputs_sha256": setup["defines_sha256"]},
            "completed_periods": horizon,
            "employment": [],
            "freight": [],
            "observed_choice_count": 0,
        },
    )
    rows = []
    for period in range(1, horizon + 1):
        active = 0 if profile == "depletion" and period > 16 else 1
        rows.append(
            {
                "period": period,
                "world_hash": f"{period:064x}",
                "tick_content_sha256": f"{period + 1000:064x}",
                "produced_batches": active,
                "dispatched_units": active * 8,
                "arrived_units": active * 8,
                "conserved_mass_grams": 1000000,
                "considered_rules": 1,
                "fired_rules": 1,
                "production": [
                    {
                        "process_id": "f" * 64,
                        "process_key": "sheet-rolling",
                        "produced_batches": active,
                    }
                ],
                "staffing": [
                    {"subject": subject, "employed": 2, "reserve": 3} for subject in SUBJECTS
                ],
            }
        )
    _json(output / "periods.json", rows)
    if persisted:
        _json(
            output / "parity.json",
            {
                "schema": "SimulationExperimentParityV1",
                "mode": "postgresql",
                "matched": True,
                "periods": horizon,
                "restarts": (horizon + 12) // 13,
                "foundation_sha256": setup["foundation_sha256"],
                "final_world_hash": rows[-1]["world_hash"],
            },
        )
        _json(output / "campaign.json", {"campaign_id": "00000000-0000-4000-8000-000000000001"})
    _refresh(output)
    return spec


def test_rust_canonical_intervention_order_compares_by_meaning(tmp_path: Path) -> None:
    output = tmp_path / "run"
    spec = _fixture(output, "delivery_stock")
    submitted = copy.deepcopy(spec)
    submitted["interventions"].reverse()
    result = validate_run(output, submitted, persisted=False)
    assert result["periods"] == 16


@pytest.mark.parametrize(
    "location",
    [
        "period",
        "completed_periods",
        "mass",
        "checkpoint_restarts",
        "seed",
        "production",
        "staffing",
        "draws",
    ],
)
def test_boolean_is_never_an_artifact_integer(tmp_path: Path, location: str) -> None:
    output = tmp_path / "run"
    spec = _fixture(output)
    filename = "periods.json"
    if location in {"completed_periods", "draws", "seed"}:
        filename = "trajectory.json"
    elif location == "checkpoint_restarts":
        filename = "captured_setup.json"
    value = json.loads((output / filename).read_text())
    if location == "seed":
        value["experiment"]["seed"] = True
    elif location == "mass":
        value[0]["conserved_mass_grams"] = True
    elif location == "production":
        value[0]["production"][0]["produced_batches"] = True
    elif location == "staffing":
        value[0]["staffing"][0]["employed"] = True
    elif location == "draws":
        value["observed_choice_count"] = False
    elif location == "period":
        value[0]["period"] = True
    else:
        value[location] = True
    _json(output / filename, value)
    _refresh(output)
    with pytest.raises(ValueError):
        validate_run(output, spec, persisted=False)


@pytest.mark.parametrize(
    "profile,persisted",
    [("sustained", False), ("depletion", False), ("sustained", True), ("depletion", True)],
)
def test_complete_long_profiles_and_persisted_restarts(
    tmp_path: Path, profile: str, persisted: bool
) -> None:
    output = tmp_path / "run"
    spec = _fixture(output, profile, persisted=persisted)
    result = validate_run(output, spec, persisted=persisted)
    assert result["periods"] == 130
    assert result["postgresql_parity"] is persisted
    assert result["final_year_active_periods"] == (0 if profile == "depletion" else 13)
    assert result["final_employed_slots"] == 10
    assert result["final_reserve_slots"] == 15
    assert result["produced_batches_by_process"]["sheet-rolling"] == (
        16 if profile == "depletion" else 130
    )
    assert "dispatched_units" not in result
    assert "produced_batches" not in result


@pytest.mark.parametrize(
    "failure",
    [
        "corrupt",
        "missing_manifest_file",
        "unknown_manifest_file",
        "incomplete",
        "false_conservation",
        "false_activity",
        "missing_parity",
        "unmatched_parity",
        "parity_restarts",
        "draws",
        "missing_staffing",
        "pool_loss",
        "receipt_total",
        "resolved_bool",
        "unknown_field",
        "failure_artifact",
    ],
)
def test_incomplete_or_inconsistent_evidence_fails_closed(tmp_path: Path, failure: str) -> None:
    output = tmp_path / "run"
    spec = _fixture(output, persisted=True)
    if failure == "corrupt":
        (output / "foundation.bin").write_bytes(b"corrupt")
    elif failure == "failure_artifact":
        (output / "failure.json").write_text("{}")
    elif failure in {"missing_manifest_file", "unknown_manifest_file"}:
        manifest = json.loads((output / "manifest.json").read_text())
        if failure == "missing_manifest_file":
            del manifest["files_sha256"]["periods.json"]
        else:
            manifest["files_sha256"]["unrelated.json"] = "a" * 64
        _json(output / "manifest.json", manifest)
    elif failure == "missing_parity":
        (output / "parity.json").unlink()
        _refresh(output)
    else:
        filename = "periods.json"
        if failure in {"unmatched_parity", "parity_restarts"}:
            filename = "parity.json"
        elif failure == "draws":
            filename = "trajectory.json"
        elif failure in {"false_activity", "resolved_bool"}:
            filename = "captured_setup.json"
        value = json.loads((output / filename).read_text())
        _mutate_evidence(value, failure)
        _json(output / filename, value)
        _refresh(output)
    with pytest.raises((ValueError, OSError)):
        validate_run(output, spec, persisted=True)


def test_readable_six_case_table_keeps_recipe_counts_separate(tmp_path: Path) -> None:
    from tools.devtools.simulation_qualification import render_summary

    rows = []
    for capacity in (500, 1000, 1500):
        for stock in (0, 320):
            output = tmp_path / f"{capacity}-{stock}"
            spec = _fixture(output, "delivery_stock")
            # Reporting labels come from validated captured interventions.
            row = {"case": output.name, **validate_run(output, spec, persisted=False)}
            row["transport_capacity_permille"] = capacity
            row["opening_sheet_kg"] = stock
            rows.append(row)
    text = render_summary(rows, [])
    assert text.count("| 500 |") == 2
    assert text.count("| 1000 |") == 2
    assert text.count("| 1500 |") == 2
    assert "sheet-rolling" in text
    assert "Production-active periods" in text
    assert "Final employed slots" in text
    assert "never added into a physical total" in text
    assert "sampled ensemble" in text


def _mutate_evidence(value, failure: str) -> None:
    if failure == "incomplete":
        value.pop()
    elif failure == "false_conservation":
        value[-1]["conserved_mass_grams"] -= 1
    elif failure == "false_activity":
        value["final_year_active_periods"] = 12
    elif failure == "unmatched_parity":
        value["matched"] = False
    elif failure == "parity_restarts":
        value["restarts"] = True
    elif failure == "draws":
        value["observed_choice_count"] = 1
    elif failure == "missing_staffing":
        value[-1]["staffing"].pop()
    elif failure == "pool_loss":
        value[-1]["staffing"][0]["reserve"] -= 1
    elif failure == "receipt_total":
        value[0]["produced_batches"] += 1
    elif failure == "resolved_bool":
        value["resolved_inputs"]["processes"][0]["initial_jobs"] = True
    else:
        value[0]["unexpected"] = 1


def test_preflight_failure_is_readable_and_existing_evidence_is_preserved(tmp_path: Path) -> None:
    from tools.devtools.simulation_qualification import run

    output = tmp_path / "run"
    assert run(tmp_path / "missing-runtime", output, dsn=None, sensitivity=True) == 2
    before = (output / "summary.md").read_bytes()
    assert b"Required preflight failed" in before
    assert run(tmp_path / "missing-runtime", output, dsn=None, sensitivity=True) == 2
    assert (output / "summary.md").read_bytes() == before


def test_runtime_failure_retains_both_long_profiles_and_six_sensitivity_inputs(
    tmp_path: Path, monkeypatch
) -> None:
    import tools.devtools.simulation_qualification as module

    source = tmp_path / "source"
    profiles = source / "content/scenarios/michigan"
    profiles.mkdir(parents=True)
    for profile in ("sustained", "depletion"):
        spec = _fixture(tmp_path / f"example-{profile}", profile)
        _json(profiles / f"diagnostic-{profile}.json", spec)
    monkeypatch.setattr(module, "ROOT", source)
    runtime = tmp_path / "runtime"
    runtime.write_text('#!/bin/sh\nprintf "deliberate failure" >&2\nexit 3\n')
    runtime.chmod(0o755)
    output = tmp_path / "run"
    assert module.run(runtime, output, dsn=None, sensitivity=True) == 2
    results = json.loads((output / "comparison.json").read_text())
    assert len(results["failures"]) == 8
    assert len(list(output.glob("*/input.json"))) == 8
    assert all(path.read_text() == "deliberate failure" for path in output.glob("*/stderr.log"))
    receipts = list(output.glob("*/execution.json"))
    assert len(receipts) == 8
    for path in receipts:
        receipt = json.loads(path.read_text())
        assert receipt["returncode"] == 3
        assert receipt["runtime_sha256"] == hashlib.sha256(runtime.read_bytes()).hexdigest()
        assert (
            receipt["input_sha256"]
            == hashlib.sha256(path.with_name("input.json").read_bytes()).hexdigest()
        )
