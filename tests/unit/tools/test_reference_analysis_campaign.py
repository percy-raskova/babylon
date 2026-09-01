"""Bounded frozen-Python reference-analysis campaign contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tools.devtools import reference_analysis_campaign as campaign


def _write_success_artifacts(spec: campaign.LegSpec) -> None:
    spec.output_dir.mkdir(parents=True, exist_ok=True)
    (spec.output_dir / "stdout.log").write_text("ok\n", encoding="utf-8")
    (spec.output_dir / "stderr.log").write_text("", encoding="utf-8")
    if spec.name == "monte_carlo":
        (spec.output_dir / "samples.csv").write_text("sample\n", encoding="utf-8")
        (spec.output_dir / "report.md").write_text("# Monte Carlo\n", encoding="utf-8")
        (spec.output_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema": "babylon.sim-analysis.monte-carlo.v1",
                    "stats": {"n_samples": spec.requested_workload["samples"]},
                }
            ),
            encoding="utf-8",
        )
    elif spec.name == "optuna":
        (spec.output_dir / "study.sqlite3").write_bytes(b"sqlite")
        (spec.output_dir / "trials.csv").write_text("number\n", encoding="utf-8")
        (spec.output_dir / "report.md").write_text("# Optuna\n", encoding="utf-8")
        (spec.output_dir / "summary.json").write_text(
            json.dumps(
                {
                    "schema": "babylon.sim-analysis.optuna-summary.v1",
                    "trial_counts": {
                        "total": spec.requested_workload["trials"],
                        "complete": spec.requested_workload["trials"],
                        "pruned": 0,
                        "failed": 0,
                        "running": 0,
                        "waiting": 0,
                        "other": 0,
                    },
                }
            ),
            encoding="utf-8",
        )
    else:
        for name, schema, samples in (
            ("morris.json", "babylon.sim-analysis.morris.v1", 20),
            ("sobol.json", "babylon.sim-analysis.sobol.v1", 80),
        ):
            payload = {"schema": schema, "trials": [{}] * samples}
            if name == "sobol.json":
                payload["total_samples"] = samples
            (spec.output_dir / name).write_text(json.dumps(payload), encoding="utf-8")


def _success_runner(spec: campaign.LegSpec) -> campaign.LegExecution:
    _write_success_artifacts(spec)
    return campaign.LegExecution(
        status="succeeded",
        return_code=0,
        failure_reason=None,
        resources=campaign.ResourceMetrics(
            wall_time_ns=1,
            user_cpu_ns=2,
            system_cpu_ns=3,
            max_rss_bytes=4,
        ),
    )


def _fake_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "uv.lock").write_text("frozen\n", encoding="utf-8")
    return repository


def test_weekly_profile_runs_exact_bounded_required_legs_and_skips_sensitivity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _fake_repository(tmp_path)
    observed: list[campaign.LegSpec] = []

    def runner(spec: campaign.LegSpec) -> campaign.LegExecution:
        observed.append(spec)
        return _success_runner(spec)

    monkeypatch.setattr(campaign, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(campaign, "_source_tree_sha256", lambda _root: "c" * 64)

    result = campaign.run_campaign(
        "weekly",
        output_root=tmp_path / "reports",
        repository_root=repository,
        leg_runner=runner,
    )

    assert result.exit_code == 0
    assert [spec.name for spec in observed] == ["monte_carlo", "optuna"]
    monte_carlo, optuna = observed
    assert monte_carlo.argv[:3] == [sys.executable, "-m", "tools.devtools.sim_analysis"]
    assert monte_carlo.requested_workload == {
        "samples": 16,
        "max_ticks": 520,
        "maximum_tick_evaluations": 8320,
        "seed": 304,
        "objective": "carceral",
    }
    assert optuna.requested_workload == {
        "trials": 8,
        "max_ticks": 5200,
        "maximum_trial_tick_evaluations": 41600,
        "best_trial_report_rerun_maximum_ticks": 5200,
        "seed": 304,
        "objective": "carceral",
        "fresh_study": True,
    }
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["authority"] == "frozen_python_reference"
    assert manifest["game_state_authoritative"] is False
    assert manifest["frozen_ref"] == "p27-python-freeze"
    assert manifest["deterministic_seeds"] == {
        "monte_carlo_base_seed": 304,
        "optuna_simulation_seed": 304,
        "sensitivity_sampling_and_simulation_seed": 304,
    }
    assert manifest["source"] == {
        "git_sha": "b" * 40,
        "source_tree_sha256": "c" * 64,
        "uv_lock_sha256": campaign._sha256_file(repository / "uv.lock"),
    }
    sensitivity = next(leg for leg in manifest["legs"] if leg["name"] == "sensitivity")
    assert sensitivity["status"] == "skipped"
    assert sensitivity["skip_reason"] == "weekly profile excludes sensitivity analysis"
    assert sensitivity["required"] is False
    assert sensitivity["argv"] == []
    for leg in manifest["legs"]:
        assert all(type(value) is int for value in leg["resources"].values())
    monte_manifest = next(
        artifact
        for artifact in manifest["legs"][0]["artifacts"]
        if artifact["path"].endswith("manifest.json")
    )
    assert monte_manifest["schema"] == "babylon.sim-analysis.monte-carlo.v1"
    assert monte_manifest["status"] == "present"
    assert type(monte_manifest["bytes"]) is int
    assert len(monte_manifest["sha256"]) == 64


def test_full_profile_adds_exact_final_wealth_sensitivity_workload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _fake_repository(tmp_path)
    observed: list[campaign.LegSpec] = []

    def runner(spec: campaign.LegSpec) -> campaign.LegExecution:
        observed.append(spec)
        return _success_runner(spec)

    monkeypatch.setattr(campaign, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(campaign, "_source_tree_sha256", lambda _root: "c" * 64)

    result = campaign.run_campaign(
        "full",
        output_root=tmp_path / "reports",
        repository_root=repository,
        leg_runner=runner,
    )

    assert result.exit_code == 0
    assert [spec.name for spec in observed] == ["monte_carlo", "optuna", "sensitivity"]
    assert observed[0].requested_workload["samples"] == 64
    assert observed[1].requested_workload["trials"] == 16
    sensitivity = observed[2]
    assert sensitivity.requested_workload == {
        "method": "both",
        "parameters": [
            "economy.base_subsistence",
            "economy.extraction_efficiency",
            "economy.comprador_cut",
            "economy.super_wage_rate",
        ],
        "morris_trajectories": 4,
        "morris_evaluations": 20,
        "sobol_base_samples": 8,
        "sobol_evaluations": 80,
        "maximum_tick_evaluations": 52000,
        "max_ticks": 520,
        "seed": 304,
        "objective": "final-wealth",
    }
    assert "--objective" in sensitivity.argv
    assert sensitivity.argv[sensitivity.argv.index("--objective") + 1] == "final-wealth"


def test_partial_failure_is_manifested_and_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _fake_repository(tmp_path)

    def runner(spec: campaign.LegSpec) -> campaign.LegExecution:
        if spec.name == "monte_carlo":
            spec.output_dir.mkdir(parents=True, exist_ok=True)
            (spec.output_dir / "stderr.log").write_text("boom\n", encoding="utf-8")
            return campaign.LegExecution(
                status="failed",
                return_code=7,
                failure_reason="process exited with status 7",
                resources=campaign.ResourceMetrics(1, 2, 3, 4),
            )
        return _success_runner(spec)

    monkeypatch.setattr(campaign, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(campaign, "_source_tree_sha256", lambda _root: "c" * 64)

    result = campaign.run_campaign(
        "weekly",
        output_root=tmp_path / "reports",
        repository_root=repository,
        leg_runner=runner,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.exit_code == 1
    assert result.manifest_path.is_file()
    assert manifest["status"] == "failed"
    failed = next(leg for leg in manifest["legs"] if leg["name"] == "monte_carlo")
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "process exited with status 7"
    assert any(artifact["path"].endswith("stderr.log") for artifact in failed["artifacts"])
    assert any(artifact["status"] == "missing" for artifact in failed["artifacts"])


def test_missing_required_artifact_turns_a_zero_exit_leg_into_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _fake_repository(tmp_path)

    def runner(spec: campaign.LegSpec) -> campaign.LegExecution:
        if spec.name == "monte_carlo":
            spec.output_dir.mkdir(parents=True, exist_ok=True)
            (spec.output_dir / "stdout.log").write_text("ok\n", encoding="utf-8")
            (spec.output_dir / "stderr.log").write_text("", encoding="utf-8")
            return campaign.LegExecution(
                status="succeeded",
                return_code=0,
                failure_reason=None,
                resources=campaign.ResourceMetrics(1, 2, 3, 4),
            )
        return _success_runner(spec)

    monkeypatch.setattr(campaign, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(campaign, "_source_tree_sha256", lambda _root: "c" * 64)

    result = campaign.run_campaign(
        "weekly",
        output_root=tmp_path / "reports",
        repository_root=repository,
        leg_runner=runner,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    failed = next(leg for leg in manifest["legs"] if leg["name"] == "monte_carlo")

    assert result.exit_code == 1
    assert failed["status"] == "failed"
    assert "missing required artifact" in failed["failure_reason"]


def test_campaign_profiles_are_allowlisted_and_run_directories_do_not_collide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _fake_repository(tmp_path)
    monkeypatch.setattr(campaign, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(campaign, "_source_tree_sha256", lambda _root: "c" * 64)

    with pytest.raises(ValueError, match="weekly or full"):
        campaign.run_campaign("custom", tmp_path / "reports", repository_root=repository)

    first = campaign.run_campaign(
        "weekly",
        tmp_path / "reports",
        repository_root=repository,
        leg_runner=_success_runner,
    )
    second = campaign.run_campaign(
        "weekly",
        tmp_path / "reports",
        repository_root=repository,
        leg_runner=_success_runner,
    )

    assert first.run_directory != second.run_directory
    assert first.run_directory.parent == second.run_directory.parent == tmp_path / "reports"


def test_leg_runner_enforces_output_limit_and_preserves_logs(tmp_path: Path) -> None:
    output_dir = tmp_path / "bounded-output"
    spec = campaign.LegSpec(
        name="probe",
        argv=[sys.executable, "-c", "print('x' * 10000)"],
        output_dir=output_dir,
        timeout_seconds=10,
        max_output_bytes=128,
        required=True,
        requested_workload={},
        expected_artifacts=(),
    )

    execution = campaign._run_leg(spec)

    assert execution.status == "output_limit_exceeded"
    assert execution.return_code is not None
    assert (output_dir / "stdout.log").is_file()
    assert "output limit exceeded" in (output_dir / "stderr.log").read_text(encoding="utf-8")
    assert all(type(value) is int for value in execution.resources.as_dict().values())
