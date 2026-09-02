"""Immutable file exports for bounded Optuna reference campaigns."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from tools.devtools.sim_analysis import bayesian


def _completed_trial() -> SimpleNamespace:
    started = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)
    return SimpleNamespace(
        number=3,
        state=bayesian.optuna.trial.TrialState.COMPLETE,
        value=12.5,
        params={"economy.base_subsistence": 0.001},
        datetime_start=started,
        datetime_complete=started + timedelta(seconds=2),
        duration=timedelta(seconds=2),
    )


def _study() -> SimpleNamespace:
    trial = _completed_trial()
    experiment = {
        "schema": "babylon.sim-analysis.optuna-experiment.v1",
        "fingerprint_sha256": "a" * 64,
    }
    return SimpleNamespace(
        study_name="weekly-reference",
        direction=SimpleNamespace(name="MAXIMIZE"),
        user_attrs={bayesian._EXPERIMENT_ATTRIBUTE: experiment},
        trials=[trial],
        best_trial=trial,
        best_value=trial.value,
        best_params=trial.params,
    )


def test_export_study_artifacts_writes_strict_csv_summary_and_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "optuna"
    monkeypatch.setattr(
        bayesian,
        "_get_param_importances",
        lambda _study: {"economy.base_subsistence": 1.0},
    )

    paths = bayesian.export_study_artifacts(_study(), output_dir, report="# Optuna\n")

    assert paths == {
        "trials_csv": output_dir / "trials.csv",
        "summary_json": output_dir / "summary.json",
        "report_markdown": output_dir / "report.md",
    }
    with paths["trials_csv"].open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [
        {
            "number": "3",
            "state": "COMPLETE",
            "value": "12.5",
            "params_json": '{"economy.base_subsistence":0.001}',
            "datetime_start": "2026-01-02T03:04:00+00:00",
            "datetime_complete": "2026-01-02T03:04:02+00:00",
            "duration_seconds": "2.0",
        }
    ]
    summary = json.loads(paths["summary_json"].read_text(encoding="utf-8"))
    assert summary["schema"] == "babylon.sim-analysis.optuna-summary.v1"
    assert summary["experiment_fingerprint_sha256"] == "a" * 64
    assert summary["experiment_manifest"] == _study().user_attrs[bayesian._EXPERIMENT_ATTRIBUTE]
    assert summary["trial_counts"] == {
        "total": 1,
        "complete": 1,
        "pruned": 0,
        "failed": 0,
        "running": 0,
        "waiting": 0,
        "other": 0,
    }
    assert summary["best_trial_number"] == 3
    assert summary["best_value"] == 12.5
    assert summary["best_params"] == {"economy.base_subsistence": 0.001}
    assert summary["parameter_importances"] == {
        "status": "available",
        "values": {"economy.base_subsistence": 1.0},
    }
    assert paths["report_markdown"].read_text(encoding="utf-8") == "# Optuna\n"


def test_export_marks_insufficient_parameter_importance_data_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(_study: object) -> dict[str, float]:
        raise ValueError("Cannot evaluate parameter importances with only a single trial")

    monkeypatch.setattr(bayesian, "_get_param_importances", unavailable)

    paths = bayesian.export_study_artifacts(_study(), tmp_path / "optuna", report="report\n")
    summary = json.loads(paths["summary_json"].read_text(encoding="utf-8"))

    assert summary["parameter_importances"] == {
        "status": "unavailable",
        "reason": "insufficient_completed_trials",
        "detail": "Cannot evaluate parameter importances with only a single trial",
    }


def test_export_marks_zero_variance_parameter_importance_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(_study: object) -> dict[str, float]:
        raise RuntimeError("Encountered zero total variance in all trees")

    monkeypatch.setattr(bayesian, "_get_param_importances", unavailable)

    paths = bayesian.export_study_artifacts(_study(), tmp_path / "optuna", report="report\n")
    summary = json.loads(paths["summary_json"].read_text(encoding="utf-8"))

    assert summary["parameter_importances"] == {
        "status": "unavailable",
        "reason": "zero_total_variance",
        "detail": "Encountered zero total variance in all trees",
    }


def test_export_does_not_hide_unexpected_parameter_importance_runtime_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(_study: object) -> dict[str, float]:
        raise RuntimeError("unexpected evaluator failure")

    monkeypatch.setattr(bayesian, "_get_param_importances", broken)

    with pytest.raises(RuntimeError, match="unexpected evaluator failure"):
        bayesian.export_study_artifacts(_study(), tmp_path / "optuna", report="report\n")


def test_output_directory_forces_a_fresh_local_sqlite_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "optuna"
    study = _study()
    observed: dict[str, object] = {}
    monkeypatch.setattr(bayesian, "HAS_OPTUNA", True)

    def fake_run_optimization(**kwargs: object) -> SimpleNamespace:
        observed.update(kwargs)
        (output_dir / "study.sqlite3").write_bytes(b"sqlite")
        return study

    monkeypatch.setattr(bayesian, "run_optimization", fake_run_optimization)
    monkeypatch.setattr(bayesian, "format_results", lambda *_args, **_kwargs: "report\n")
    monkeypatch.setattr(
        bayesian,
        "export_study_artifacts",
        lambda *_args, **_kwargs: {},
    )

    returned = bayesian.run_bayesian(output_dir=output_dir, n_trials=8, max_ticks=52)

    assert returned is study
    assert observed["storage"] == f"sqlite:///{(output_dir / 'study.sqlite3').resolve()}"
    assert observed["n_trials"] == 8
    assert observed["allow_resume"] is False

    with pytest.raises(FileExistsError, match="fresh Optuna output"):
        bayesian.run_bayesian(output_dir=output_dir, n_trials=8, max_ticks=52)


def test_output_directory_cannot_resume_or_override_storage(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="show_best"):
        bayesian.run_bayesian(output_dir=tmp_path / "show", show_best=True)

    with pytest.raises(ValueError, match="storage"):
        bayesian.run_bayesian(
            output_dir=tmp_path / "storage",
            storage="sqlite:///elsewhere.sqlite3",
        )
