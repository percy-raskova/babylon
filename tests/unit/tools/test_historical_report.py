"""A failing runtime or stale report must never produce a successful comparison."""

import json
from pathlib import Path

from tools.devtools.historical_extract import DEFAULT_FIXTURES
from tools.devtools.historical_report import run_profiles


def test_failed_runtime_keeps_inputs_logs_and_failure_summary(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.write_text('#!/bin/sh\nprintf "deliberate diagnostic failure" >&2\nexit 7\n')
    runtime.chmod(0o755)
    output = tmp_path / "report"
    assert run_profiles(runtime, DEFAULT_FIXTURES, output, timeout_seconds=2) == 2
    for name in ("employment", "freight"):
        directory = output / name
        assert "runtime exited 7" in (directory / "summary.md").read_text()
        assert (directory / "stderr.log").read_text() == "deliberate diagnostic failure"
        assert json.loads((directory / "execution.json").read_text())["returncode"] == 7
        assert (directory / "input.json").is_file()
        assert not (directory / "evaluation.json").exists()


def test_successful_exit_without_trajectory_is_failure(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.write_text("#!/bin/sh\nexit 0\n")
    runtime.chmod(0o755)
    output = tmp_path / "report"
    assert run_profiles(runtime, DEFAULT_FIXTURES, output, timeout_seconds=2) == 2
    assert "trajectory.json" in (output / "summary.md").read_text()


def test_existing_report_cannot_supply_stale_success_evidence(tmp_path: Path) -> None:
    sentinel = tmp_path / "summary.md"
    sentinel.write_text("valuable earlier evidence")
    assert run_profiles(Path("/missing/runtime"), DEFAULT_FIXTURES, tmp_path) == 2
    assert sentinel.read_text() == "valuable earlier evidence"


def test_preflight_failure_is_visible_in_summary(tmp_path: Path) -> None:
    assert run_profiles(Path("/missing/runtime"), DEFAULT_FIXTURES, tmp_path) == 2
    assert "Required preflight failed" in (tmp_path / "summary.md").read_text()


def test_combined_summary_resolves_child_chart_paths() -> None:
    from tools.devtools.historical_report import combined_child_summary

    child = "# Historical comparison: employment\n\n![26163/331](26163_331.svg)\n"
    assert "](employment/26163_331.svg)" in combined_child_summary("employment", child)
    child = "![freight](detroit_canada_truck_import_hs72.svg)"
    assert "](freight/detroit_canada_truck_import_hs72.svg)" in combined_child_summary(
        "freight", child
    )


def test_regional_initialization_report_explains_observed_and_designed_inputs() -> None:
    from tools.devtools.historical_report import initialization_summary

    setup = {
        "initialization_evidence": "Observed starting jobs; Derived capacities; Designed recipes and reserves",
        "resolved_inputs": {
            "kind": "regional",
            "capacity_derivation": "weekly = floor(jobs * 40 / labor)",
            "hours_per_person_period": 160,
            "opening_policy": "finite stocks and orders",
            "processes": [
                {
                    "process_key": "sheet-rolling",
                    "series_id": "26163/331",
                    "initial_jobs": 4464,
                    "initial_reserve": 0,
                    "jobs_evidence": "Observed QWI jobs",
                    "hours_per_person_week": 40,
                    "labor_hours_per_batch": 16,
                    "weekly_capacity_batches": 11160,
                    "period_capacity_batches": 44640,
                    "opening_planned_batches": 44640,
                    "inputs": [
                        {
                            "good_key": "coil",
                            "unit": "kg",
                            "quantity_per_batch": 10,
                            "opening_quantity": 58478400,
                        }
                    ],
                }
            ],
            "routes": [
                {
                    "route_key": "sheet-transfer",
                    "supplier_site": "Wayne",
                    "buyer_site": "Macomb",
                    "good_key": "sheet",
                    "unit": "kg",
                    "ordered_quantity": 58478400,
                    "travel_periods": 1,
                    "capacities": [{"key": "truck", "grams_per_period": 446400000}],
                }
            ],
        },
    }
    text = initialization_summary(setup)
    for expected in [
        "26163/331",
        "4464",
        "11160",
        "44640",
        "58478400",
        "446400000",
        "Derived",
        "Designed",
        "2019-10-01",
        "not unique people",
    ]:
        assert expected in text


def test_freight_initialization_report_keeps_border_scope_and_units_explicit() -> None:
    from tools.devtools.historical_report import initialization_summary

    setup = {
        "initialization_evidence": "Observed January weight; Designed inventory",
        "resolved_inputs": {
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
            "january_observed_kg": 121292613,
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
        },
    }
    text = initialization_summary(setup)
    for expected in [
        "3801",
        "1220",
        "HS72",
        "121292613",
        "109554618",
        "kg",
        "Portwide",
        "28 / 31",
        "Derived",
        "Designed",
    ]:
        assert expected in text
