"""Evidence contracts for retrospective comparisons, not empirical-fit thresholds."""

from datetime import date
from fractions import Fraction

import pytest
from tools.devtools.historical_evaluate import (
    allocate_months,
    metric_values,
    observation_window,
    sample_stock,
)


def test_exact_calendar_overlap_preserves_mass_across_leap_day() -> None:
    result = allocate_months(date(2020, 2, 15), date(2020, 3, 14), 280)
    assert result == {"2020-02": Fraction(150), "2020-03": Fraction(130)}
    assert sum(result.values()) == 280


def test_fractional_month_overlap_preserves_mass_without_rounding() -> None:
    result = allocate_months(date(2019, 1, 30), date(2019, 2, 27), 1)
    assert result == {"2019-01": Fraction(1, 14), "2019-02": Fraction(13, 14)}


def test_stock_uses_latest_committed_state_before_observation() -> None:
    states = [(date(2010, 1, 1), 100), (date(2010, 1, 29), 200)]
    assert sample_stock(states, date(2010, 1, 28)) == (100, date(2010, 1, 1), 27)
    assert sample_stock(states, date(2010, 1, 29)) == (200, date(2010, 1, 29), 0)
    with pytest.raises(ValueError, match="before"):
        sample_stock(states, date(2009, 12, 31))


def test_high_correlation_does_not_hide_large_magnitude_error() -> None:
    result = metric_values([1, 2, 3], [101, 102, 103])
    assert result["pearson"] == pytest.approx(1)
    assert result["spearman"] == pytest.approx(1)
    assert result["bias"] == 100
    assert result["mae"] == 100
    assert result["rmse"] == 100


def test_reversed_tied_constant_and_missing_statistics_are_explicit() -> None:
    assert metric_values([1, 2, 3], [3, 2, 1])["spearman"] == pytest.approx(-1)
    assert metric_values([1, 1, 2], [2, 2, 3])["spearman"] == pytest.approx(1)
    result = metric_values([1, None, 1], [2, 8, 2])
    assert result["paired_count"] == 2
    assert result["missing_count"] == 1
    assert result["pearson"] is None
    assert result["pearson_reason"] == "constant_series"
    assert metric_values([None], [1])["rmse"] is None


def test_frozen_windows_do_not_change_for_observed_outcomes() -> None:
    assert observation_window("employment", date(2014, 10, 1)) == "development"
    assert observation_window("employment", date(2015, 1, 1)) == "evaluation"
    assert observation_window("employment", date(2009, 1, 1)) == "baseline_history"
    assert observation_window("freight", date(2019, 1, 1)) == "initialization"
    assert observation_window("freight", date(2020, 1, 1)) == "evaluation"


def _verified_setup(trajectory):
    """Synthetic captured wiring for pure evaluator tests; runtime validation is separate."""
    subjects = (
        sorted(
            "workforce-" + key
            for key in (
                "sheet-rolling",
                "panel-forming",
                "subassembly-making",
                "meal-milling",
                "meal-packaging",
            )
        )
        if trajectory.employment
        else []
    )
    counts = {
        "production": len(subjects),
        "staffing": len(subjects),
        "staged_freight": 0 if subjects else 1,
        "local_transfer": 0,
        "merchant_handling": 0,
        "final_demand": 0,
        "maintenance": 0,
    }
    return {
        "wiring": {
            "rules": [
                {
                    "rule_id": "material/period",
                    "role": "mechanic",
                    "evidence": "designed",
                    "effects": ["material-cycle"],
                }
            ],
            "native_compositions": [
                {
                    "rule_id": "g4-workforce-staffing",
                    "role": "mechanic",
                    "evidence": "designed",
                    "effects": [
                        "event:EventType/WORKFORCE_STAFFING",
                        "node-field:social-class/employed-population",
                        "node-field:social-class/previous-unretained-labor-hours",
                        "node-field:social-class/reserve-population",
                    ],
                }
            ]
            if subjects
            else [],
            "bsl_families": [
                {"family": "material", "selected": True, "rule_ids": ["material/period"]},
                {"family": "metabolism", "selected": False, "rule_ids": []},
            ],
            "material_families": [
                {"family": name, "selected": count > 0, "captured_rows": count}
                for name, count in sorted(counts.items())
            ],
            "staffing_subjects": subjects,
        }
    }


def _trajectory(kind: str = "employment") -> tuple[object, dict, list, list]:
    from datetime import timedelta

    from tools.devtools.historical_evaluate import HistoricalTrajectory
    from tools.devtools.historical_extract import DEFAULT_FIXTURES, load_fixtures, starting_specs

    manifest, employment, freight = load_fixtures(DEFAULT_FIXTURES)
    spec = starting_specs(employment, freight, manifest["initialization_snapshot_sha256"])[kind]
    epoch = date.fromisoformat(spec["epoch"])
    employment_states, freight_periods = [], []
    if kind == "employment":
        for item in spec["starting_snapshot"]["series"]:
            for period in range(spec["horizon"] + 1):
                employment_states.append(
                    {
                        "series_id": item["series_id"],
                        "date": epoch + timedelta(days=28 * period),
                        "period": period,
                        "world_hash": f"{period:064x}",
                        "jobs": item["jobs"],
                    }
                )
    else:
        for period in range(1, spec["horizon"] + 1):
            freight_periods.append(
                {
                    "series_id": spec["starting_snapshot"]["series_id"],
                    "period_start": epoch + timedelta(days=28 * (period - 1)),
                    "period_end_exclusive": epoch + timedelta(days=28 * period),
                    "period": period,
                    "world_hash": f"{period:064x}",
                    "arrived_kg": 1000,
                }
            )
    trajectory = HistoricalTrajectory.model_validate(
        {
            "schema_version": 1,
            "experiment": {
                "profile": spec["profile"],
                "epoch": epoch,
                "horizon": spec["horizon"],
                "seed": spec["seed"],
                "source_snapshot_sha256": spec["source_snapshot_sha256"],
                "resolved_inputs_sha256": "a" * 64,
            },
            "completed_periods": spec["horizon"],
            "observed_choice_count": 0,
            "employment": employment_states,
            "freight": freight_periods,
        }
    )
    return trajectory, manifest, employment, freight


def test_complete_reports_keep_coverage_missing_flags_and_calendar_offsets(tmp_path) -> None:
    from tools.devtools.historical_evaluate import evaluate, write_report

    trajectory, manifest, employment, freight = _trajectory()
    employment[25]["status_employment_begin"] = 5
    result = evaluate(
        trajectory, manifest, employment, freight, verified_setup=_verified_setup(trajectory)
    )
    assert result["coverage"] == {
        "series": 5,
        "distinct_dates": 40,
        "rows": 200,
        "missing_observations": 1,
    }
    assert result["aligned"][21]["observed"] is None
    assert result["aligned"][1]["sample_date"] == "2010-03-26"
    assert result["aligned"][1]["offset_days"] == 6
    assert len(result["annual"]) == 50
    write_report(result, tmp_path)
    assert (tmp_path / "summary.md").is_file()
    assert len(list(tmp_path.glob("*.svg"))) == 5
    assert (tmp_path / "metrics.csv").stat().st_size > 100


def test_heldout_observations_change_scores_without_changing_trajectory() -> None:
    from tools.devtools.historical_evaluate import evaluate

    trajectory, manifest, employment, freight = _trajectory()
    before_bytes = trajectory.model_dump_json()
    before = evaluate(
        trajectory, manifest, employment, freight, verified_setup=_verified_setup(trajectory)
    )
    for row in employment:
        if row["year"] >= 2015:
            row["employment_begin"] *= 2
    after = evaluate(
        trajectory, manifest, employment, freight, verified_setup=_verified_setup(trajectory)
    )
    assert before["metrics"] != after["metrics"]
    assert [r for r in before["metrics"] if r["window"] == "development"] == [
        r for r in after["metrics"] if r["window"] == "development"
    ]
    assert trajectory.model_dump_json() == before_bytes


def test_freight_report_uses_source_partitions_and_exact_calendar_fractions() -> None:
    from tools.devtools.historical_evaluate import evaluate

    trajectory, manifest, employment, freight = _trajectory("freight")
    result = evaluate(
        trajectory, manifest, employment, freight, verified_setup=_verified_setup(trajectory)
    )
    assert result["coverage"] == {
        "series": 1,
        "distinct_dates": 71,
        "rows": 71,
        "missing_observations": 0,
    }
    february = result["aligned"][0]
    assert february["date"] == "2019-02-01"
    assert february["predicted"] == 1000
    assert february["observed"] == 103784440
    assert february["no_change"] == 121292613
    assert result["annual"][0]["partial_year"] is True
    assert any(row["predicted_denominator"] != 1 for row in result["aligned"])


@pytest.mark.parametrize(
    "mutation", ["incomplete", "unknown", "gap", "bad_date", "bad_hash", "negative", "float"]
)
def test_invalid_required_trajectory_evidence_fails(mutation: str) -> None:
    from tools.devtools.historical_evaluate import HistoricalTrajectory

    trajectory, _, _, _ = _trajectory()
    data = trajectory.model_dump()
    if mutation == "incomplete":
        data["completed_periods"] -= 1
    elif mutation == "unknown":
        data["override"] = 1
    elif mutation == "gap":
        data["employment"] = data["employment"][:-1]
    elif mutation == "bad_date":
        data["employment"][0]["date"] = date(2009, 1, 1)
    elif mutation == "bad_hash":
        data["employment"][0]["world_hash"] = "bad"
    elif mutation == "negative":
        data["employment"][0]["jobs"] = -1
    else:
        data["employment"][0]["jobs"] = 1.1
    with pytest.raises(ValueError):
        HistoricalTrajectory.model_validate(data)


def test_direction_changes_and_invalid_nonfinite_values() -> None:
    result = metric_values([1, -2, 0], [2, -3, 0], values_are_changes=True)
    assert result["direction_agreement"] == 1
    with pytest.raises(ValueError, match="nonfinite"):
        metric_values([1, float("nan")], [1, 2])


def _capture(tmp_path, *, postgres: bool = False, kind: str = "employment"):
    import hashlib
    import json

    from tools.devtools.historical_evaluate import HistoricalTrajectory
    from tools.devtools.historical_extract import canonical_bytes, starting_specs

    trajectory, manifest, employment, freight = _trajectory(kind)
    spec = starting_specs(employment, freight, manifest["initialization_snapshot_sha256"])[kind]
    defines = b"captured resolved fixture inputs"
    data = trajectory.model_dump()
    data["experiment"]["resolved_inputs_sha256"] = hashlib.sha256(defines).hexdigest()
    trajectory = HistoricalTrajectory.model_validate(data)
    (tmp_path / "captured_defines.bin").write_bytes(defines)
    (tmp_path / "canonical_experiment.json").write_bytes(canonical_bytes(spec))
    (tmp_path / "trajectory.json").write_text(trajectory.model_dump_json())
    foundation = b"captured foundation"
    (tmp_path / "foundation.bin").write_bytes(foundation)
    initial_jobs = {
        row["series_id"]: row["jobs"] for row in spec["starting_snapshot"].get("series", [])
    }
    process_series = {
        "sheet-rolling": "26163/331",
        "panel-forming": "26099/332",
        "subassembly-making": "26163/3363",
        "meal-milling": "26161/311",
        "meal-packaging": "26125/311",
    }
    if kind == "employment":
        resolved = {
            "kind": "regional",
            "capacity_derivation": "floor(initial jobs *40 / recipe hours)",
            "hours_per_person_period": 160,
            "opening_policy": "Designed finite stocks and orders",
            "processes": [
                {
                    "process_key": key,
                    "series_id": series,
                    "initial_jobs": initial_jobs[series],
                    "initial_reserve": 0,
                    "jobs_evidence": "Observed",
                    "hours_per_person_week": 40,
                    "labor_hours_per_batch": 40,
                    "weekly_capacity_batches": initial_jobs[series],
                    "period_capacity_batches": initial_jobs[series] * 4,
                    "opening_planned_batches": initial_jobs[series] * 4,
                    "inputs": [],
                }
                for key, series in process_series.items()
            ],
            "routes": [],
        }
    else:
        resolved = {
            "kind": "freight",
            "source_site": "Canada",
            "destination_site": "Detroit entry",
            "commodity": "HS72",
            "unit": "kg",
            "port_code": "3801",
            "partner_code": "1220",
            "mode_code": "5",
            "trade_type_code": "2",
            "hs_chapter": "72",
            "geographic_scope": "Portwide, no county or bridge attribution",
            "january_observed_kg": spec["starting_snapshot"]["arrived_kg"],
            "capacity_derivation": "floor(January kilograms * 28 / 31)",
            "capacity_kg_per_period": 109554618,
            "ordered_kg": 854525,
            "opening_inventory_kg": 865480,
            "travel_periods": 1,
            "inventory_evidence": "Designed",
            "order_evidence": "Designed",
            "capacity_evidence": "Derived",
            "inventory_derivation": "capacity * (horizon + 1)",
            "order_derivation": "capacity * horizon",
        }
    setup = {
        "canonical_spec": spec,
        "resolved_inputs": resolved,
        "experiment_input_sha256": hashlib.sha256(canonical_bytes(spec)).hexdigest(),
        "defines_sha256": hashlib.sha256(defines).hexdigest(),
        "checkpoint_restarts": (spec["horizon"] + 12) // 13,
        "conserved_mass_grams": 100,
        "foundation_sha256": hashlib.sha256(foundation).hexdigest(),
        "content_sha256": "c" * 64,
        "rules_sha256": "d" * 64,
        "reference_sha256": "e" * 64,
        "initialization_evidence": "Observed starting snapshots; Designed remaining inputs",
        "final_year_active_periods": 0,
    }
    setup.update(_verified_setup(trajectory))
    (tmp_path / "captured_setup.json").write_bytes(canonical_bytes(setup))
    rows = []
    for period in range(1, spec["horizon"] + 1):
        staffing = (
            [
                {"subject": "workforce-" + key, "employed": initial_jobs[series], "reserve": 0}
                for key, series in process_series.items()
            ]
            if kind == "employment"
            else []
        )
        rows.append(
            {
                "period": period,
                "world_hash": f"{period:064x}",
                "tick_content_sha256": f"{period + 1000:064x}",
                "conserved_mass_grams": 100,
                "produced_batches": 0,
                "dispatched_units": 0,
                "arrived_units": 1000 if kind == "freight" else 0,
                "considered_rules": 1,
                "fired_rules": 1,
                "rule_execution": [
                    {"rule_id": "material/period", "considered": 1, "fired": 1, "audit_receipts": 1}
                ],
                "receipt_coverage": {
                    "material_cycles": 1,
                    "staffing_events": len(staffing),
                    "staffing_writes": 3 * len(staffing),
                    "production": 0,
                    "dispatches": 0,
                    "arrivals": int(kind == "freight"),
                    "losses": 0,
                    "deliveries": 0,
                    "realizations": 0,
                    "merchant_handling": 0,
                    "local_fulfillments": 0,
                    "local_transfers": 0,
                    "maintenance": 0,
                },
                "production": [],
                "staffing": staffing,
            }
        )
    (tmp_path / "periods.json").write_bytes(canonical_bytes(rows))
    if postgres:
        (tmp_path / "parity.json").write_bytes(
            canonical_bytes(
                {
                    "schema": "SimulationExperimentParityV1",
                    "mode": "postgresql",
                    "matched": True,
                    "periods": spec["horizon"],
                    "restarts": setup["checkpoint_restarts"],
                    "foundation_sha256": setup["foundation_sha256"],
                    "final_world_hash": rows[-1]["world_hash"],
                }
            )
        )
        (tmp_path / "campaign.json").write_text(
            json.dumps({"campaign_id": "00000000-0000-4000-8000-000000000001"})
        )
    _capture_manifest(tmp_path)
    return trajectory, spec


def _capture_manifest(tmp_path):
    from tools.devtools.historical_extract import canonical_bytes, digest_file

    files = {
        p.name: digest_file(p)
        for p in tmp_path.iterdir()
        if p.name not in {"manifest.json", "failure.json"}
    }
    (tmp_path / "manifest.json").write_bytes(
        canonical_bytes(
            {
                "schema": "SimulationExperimentManifestV1",
                "status": "complete",
                "files_sha256": files,
            }
        )
    )


@pytest.mark.parametrize("postgres", [False, True])
def test_required_capture_evidence_binds_inputs_and_complete_restart_parity(
    tmp_path, postgres: bool
) -> None:
    from tools.devtools.historical_evidence import validate_capture

    trajectory, spec = _capture(tmp_path, postgres=postgres)
    setup = validate_capture(tmp_path, trajectory, spec, require_postgres=postgres)
    assert setup["checkpoint_restarts"] == 11


@pytest.mark.parametrize(
    "failure", ["failure_artifact", "checksum", "input", "parity", "conservation", "restart"]
)
def test_failed_or_corrupt_required_capture_never_qualifies(tmp_path, failure: str) -> None:
    import json

    from tools.devtools.historical_evidence import validate_capture
    from tools.devtools.historical_extract import canonical_bytes

    trajectory, spec = _capture(tmp_path, postgres=True)
    if failure == "failure_artifact":
        (tmp_path / "failure.json").write_text("{}")
    elif failure == "checksum":
        (tmp_path / "captured_defines.bin").write_bytes(b"changed")
    elif failure in {"input", "restart"}:
        path = tmp_path / "captured_setup.json"
        setup = json.loads(path.read_text())
        if failure == "input":
            setup["canonical_spec"]["seed"] = 500
        else:
            setup["checkpoint_restarts"] = 0
        path.write_bytes(canonical_bytes(setup))
        _capture_manifest(tmp_path)
    elif failure == "parity":
        path = tmp_path / "parity.json"
        value = json.loads(path.read_text())
        value["matched"] = False
        path.write_bytes(canonical_bytes(value))
        _capture_manifest(tmp_path)
    else:
        path = tmp_path / "periods.json"
        value = json.loads(path.read_text())
        value[-1]["conserved_mass_grams"] = 99
        path.write_bytes(canonical_bytes(value))
        _capture_manifest(tmp_path)
    with pytest.raises(ValueError):
        validate_capture(tmp_path, trajectory, spec, require_postgres=True)


@pytest.mark.parametrize(
    "failure",
    [
        "foundation_identity",
        "different_raw_trajectory",
        "staffing_receipt",
        "initial_jobs",
        "period_bool",
        "mass_bool",
        "incomplete_restart",
        "parity_bool",
        "invalid_campaign",
    ],
)
def test_historical_identity_and_receipts_cannot_diverge_despite_valid_file_checksums(
    tmp_path, failure: str
) -> None:
    import json

    from tools.devtools.historical_evidence import validate_capture
    from tools.devtools.historical_extract import canonical_bytes

    trajectory, spec = _capture(tmp_path, postgres=True)
    filename = "captured_setup.json"
    if failure == "different_raw_trajectory":
        filename = "trajectory.json"
    elif failure in {"staffing_receipt", "period_bool"}:
        filename = "periods.json"
    elif failure == "parity_bool":
        filename = "parity.json"
    elif failure == "invalid_campaign":
        filename = "campaign.json"
    value = json.loads((tmp_path / filename).read_text())
    if failure == "foundation_identity":
        value["foundation_sha256"] = "a" * 64
    elif failure == "different_raw_trajectory":
        value["employment"][1]["jobs"] += 1
    elif failure == "staffing_receipt":
        value[0]["staffing"][0]["employed"] -= 1
        value[0]["staffing"][0]["reserve"] += 1
    elif failure == "initial_jobs":
        value["resolved_inputs"]["processes"][0]["initial_jobs"] -= 1
    elif failure == "period_bool":
        value[0]["period"] = True
    elif failure == "mass_bool":
        value["conserved_mass_grams"] = True
    elif failure == "incomplete_restart":
        value["checkpoint_restarts"] = 1
    elif failure == "parity_bool":
        value["periods"] = True
    else:
        value["campaign_id"] = "not-a-UUID"
    (tmp_path / filename).write_bytes(canonical_bytes(value))
    _capture_manifest(tmp_path)
    with pytest.raises(ValueError):
        validate_capture(tmp_path, trajectory, spec, require_postgres=True)


def test_historical_freight_binds_arrivals_and_admitted_border_codes(tmp_path) -> None:
    import json

    from tools.devtools.historical_evidence import validate_capture
    from tools.devtools.historical_extract import canonical_bytes

    trajectory, spec = _capture(tmp_path, kind="freight", postgres=True)
    validate_capture(tmp_path, trajectory, spec, require_postgres=True)
    value = json.loads((tmp_path / "periods.json").read_text())
    value[0]["arrived_units"] += 1
    (tmp_path / "periods.json").write_bytes(canonical_bytes(value))
    _capture_manifest(tmp_path)
    with pytest.raises(ValueError, match="arrival receipts"):
        validate_capture(tmp_path, trajectory, spec, require_postgres=True)


@pytest.mark.parametrize("kind", ["employment", "freight"])
def test_historical_reports_separate_coverage_omissions_and_tuning_readiness(
    tmp_path, kind
) -> None:
    from tools.devtools.historical_evaluate import evaluate, write_report

    trajectory, manifest, employment, freight = _trajectory(kind)
    result = evaluate(
        trajectory, manifest, employment, freight, verified_setup=_verified_setup(trajectory)
    )
    coverage = result["benchmark_coverage"]
    assert coverage["profile"] == "historical_" + kind
    assert coverage["admitted_controls"] == ["transport_capacity_permille: 250–2000"]
    assert coverage["tuning_status"] == "historical_response_not_yet_qualified"
    assert {"merchant handling", "final-demand fulfillment", "maintenance"} <= set(
        coverage["existing_engine_not_connected"]
    )
    assert "engine-wide" in coverage["known_omissions"]
    assert "existing parameters" in coverage["known_omissions"]
    assert "causal attribution" in coverage["unexplained_mismatches"]
    assert "material/period BSL" in coverage["bsl_execution"]
    assert "normal tick execution" in coverage["bsl_execution"]
    if kind == "employment":
        assert "production" in coverage["modeled_relationships"]
        assert "staffing" in coverage["modeled_relationships"]
        assert "workforce entry" in coverage["known_omissions"]
        assert coverage["trajectory_evidence"]["employment_series_with_changes"] == 0
    else:
        assert "transit" in coverage["modeled_relationships"]
        assert "No production or employment" in coverage["known_omissions"]
        assert "monthly demand" in coverage["known_omissions"]
        assert coverage["captured_wiring"]["native_compositions"] == []
        assert coverage["trajectory_evidence"]["arrival_active_periods"] == 78
    assert result["fit_status"] == "advisory"
    assert result["evidence_status"] == "complete"
    write_report(result, tmp_path)
    text = (tmp_path / "summary.md").read_text()
    for label in (
        "Modeled relationships",
        "Known omissions",
        "Admitted controls",
        "Tuning readiness",
        "Unexplained mismatches",
    ):
        assert label in text
    assert "alongside playable scenarios" in text
    assert "engineering integrity remains required" in text
    assert "Raw level-change agreement" in text
    if kind == "freight":
        assert "Monthly freight totals vary with month length" in text
        assert "day-normalized first-rate evidence below" in text
    assert "Verified captured wiring" in text
    assert "Provisional level warning bands" in text
    assert "Direction agreement alone" in text
    assert "no derivative warning bands or jerk qualification" in text
    assert "seasonal_persistence" in text
    assert (tmp_path / "warning_assessments.csv").is_file()
    assert (tmp_path / "directional_metrics.csv").is_file()


def test_approved_warning_policy_is_visible_without_changing_fit_or_integrity_status() -> None:
    from tools.devtools.historical_evaluate import evaluate

    trajectory, manifest, employment, freight = _trajectory()
    result = evaluate(
        trajectory, manifest, employment, freight, verified_setup=_verified_setup(trajectory)
    )
    assert result["warning_policy"]["status"] == "provisional"
    assert result["warning_policy"]["approved_on"] == "2026-09-19"
    assert result["warning_policy"]["evidence_class"] == "Designed"
    assert any(row["status"] == "warning" for row in result["warning_assessments"])
    assert result["fit_status"] == "advisory"
    assert result["evidence_status"] == "complete"


def test_discrete_directional_metrics_keep_levels_and_windows_distinct() -> None:
    from tools.devtools.historical_evaluate import evaluate

    trajectory, manifest, employment, freight = _trajectory()
    result = evaluate(
        trajectory, manifest, employment, freight, verified_setup=_verified_setup(trajectory)
    )
    assert {row["order"] for row in result["directional_metrics"]} == {1, 2}
    assert {row["estimator"] for row in result["directional_metrics"]} == {
        "predicted",
        "no_change",
        "seasonal_persistence",
    }
    assert {row["units"] for row in result["directional_metrics"]} == {"jobs/day", "jobs/day^2"}
    assert all(
        row["paired_count"] <= (19 if row["order"] == 1 else 18)
        for row in result["directional_metrics"]
    )


def test_missing_wiring_cannot_claim_complete_coverage() -> None:
    from tools.devtools.historical_evaluate import evaluate

    trajectory, manifest, employment, freight = _trajectory()
    with pytest.raises(KeyError, match="wiring"):
        evaluate(trajectory, manifest, employment, freight, verified_setup={})


def test_failure_evidence_cannot_be_downgraded_to_an_advisory_warning(
    tmp_path, monkeypatch
) -> None:
    from tools.devtools.historical_evaluate import main

    source = tmp_path / "capture"
    source.mkdir()
    _capture(source)
    (source / "failure.json").write_text("{}")
    output = tmp_path / "report"
    monkeypatch.setattr(
        "sys.argv",
        [
            "historical_evaluate",
            "--trajectory",
            str(source / "trajectory.json"),
            "--output",
            str(output),
        ],
    )
    assert main() == 2
    assert not (output / "evaluation.json").exists()
    assert "Required evidence failed" in (output / "summary.md").read_text()
