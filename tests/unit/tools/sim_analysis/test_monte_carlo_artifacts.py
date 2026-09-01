"""Durability and finite-number contracts for Monte Carlo artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from tools.devtools.sim_analysis import monte_carlo
from tools.devtools.sim_analysis.monte_carlo import (
    AggregateStats,
    SampleResult,
    aggregate,
    run_monte_carlo,
    write_csv,
    write_manifest,
)
from tools.devtools.sim_analysis.objectives import carceral_objective
from tools.devtools.sim_analysis.reproducibility import ReproRecord

from babylon.config.defines import GameDefines, canonical_defines_hash


def _sample_and_record(defines: GameDefines) -> tuple[SampleResult, ReproRecord]:
    sample = SampleResult(
        sample_id=1,
        seed=17,
        ticks_survived=3,
        outcome="SURVIVED",
        max_tension=0.25,
        final_wealth=12.5,
        objective_score=0.75,
    )
    record = ReproRecord(
        defines_hash=canonical_defines_hash(defines),
        rng_seed=sample.seed,
        backend="in_memory",
        scenario="imperial_circuit",
        max_ticks=3,
        ticks_survived=sample.ticks_survived,
        outcome=sample.outcome,
    )
    return sample, record


def _reject_json_constant(token: str) -> object:
    raise AssertionError(f"non-standard JSON constant escaped validation: {token}")


def test_manifest_retains_replay_inputs_and_uses_strict_json(tmp_path: Path) -> None:
    defines = GameDefines()
    sample, record = _sample_and_record(defines)
    stats = aggregate([sample])
    output = tmp_path / "monte-carlo.json"

    write_manifest(
        defines=defines,
        overrides={"crisis.crisis_period_ticks": 52.0},
        base_seed=41,
        backend="in_memory",
        scenario="imperial_circuit",
        max_ticks=3,
        objective=carceral_objective,
        samples=[sample],
        stats=stats,
        repro_records=[record],
        output_path=output,
    )

    payload = json.loads(output.read_text(), parse_constant=_reject_json_constant)
    assert payload["schema"] == "babylon.sim-analysis.monte-carlo.v1"
    assert GameDefines.model_validate(payload["base_defines"]) == defines
    assert payload["defines_hash"] == canonical_defines_hash(defines)
    assert payload["parameter_overrides"] == {"crisis.crisis_period_ticks": 52.0}
    assert payload["base_seed"] == 41
    assert payload["samples"][0]["seed"] == 17
    assert payload["repro_records"][0]["rng_seed"] == 17


def test_csv_binds_each_sample_to_its_defines_hash(tmp_path: Path) -> None:
    defines = GameDefines()
    sample, record = _sample_and_record(defines)
    output = tmp_path / "monte-carlo.csv"

    write_csv([sample], aggregate([sample]), [record], output)

    rows = list(csv.reader(output.open(newline="")))
    assert rows[0][:3] == ["sample_id", "seed", "defines_hash"]
    assert rows[1][:3] == ["1", "17", canonical_defines_hash(defines)]


def test_run_writes_replay_manifest_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    defines = GameDefines()
    sample, record = _sample_and_record(defines)

    def fake_run_trials(
        *args: object, **kwargs: object
    ) -> tuple[list[SampleResult], list[ReproRecord]]:
        return [sample], [record]

    monkeypatch.setattr(monte_carlo, "run_trials", fake_run_trials)
    csv_path = tmp_path / "run.csv"

    artifact = run_monte_carlo(
        n_samples=1,
        base_seed=41,
        defines=defines,
        max_ticks=3,
        csv_path=csv_path,
        progress=False,
    )

    assert artifact.csv_path == csv_path
    assert artifact.manifest_path == csv_path.with_suffix(".manifest.json")
    assert artifact.manifest_path.is_file()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_sample_and_aggregate_models_reject_nonfinite_values(value: float) -> None:
    with pytest.raises(ValidationError):
        SampleResult(
            sample_id=1,
            seed=17,
            ticks_survived=3,
            outcome="SURVIVED",
            max_tension=value,
            final_wealth=12.5,
            objective_score=0.75,
        )

    with pytest.raises(ValidationError):
        AggregateStats(
            n_samples=1,
            n_survived=1,
            n_died=0,
            survival_rate=1.0,
            ticks_mean=3.0,
            ticks_std=0.0,
            ticks_ci_lower=3.0,
            ticks_ci_upper=3.0,
            tension_mean=value,
            tension_std=0.0,
            wealth_mean=12.5,
            wealth_std=0.0,
            objective_mean=0.75,
            objective_std=0.0,
        )


def test_artifact_writers_refuse_misaligned_receipts(tmp_path: Path) -> None:
    defines = GameDefines()
    sample, _record = _sample_and_record(defines)
    stats = aggregate([sample])

    with pytest.raises(ValueError, match="identical lengths"):
        write_csv([sample], stats, [], tmp_path / "bad.csv")
    with pytest.raises(ValueError, match="identical lengths"):
        write_manifest(
            defines=defines,
            overrides={},
            base_seed=41,
            backend="in_memory",
            scenario="imperial_circuit",
            max_ticks=3,
            objective=carceral_objective,
            samples=[sample],
            stats=stats,
            repro_records=[],
            output_path=tmp_path / "bad.json",
        )


def test_run_refuses_colliding_output_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    defines = GameDefines()
    trials_started = False

    def fake_run_trials(
        *args: object, **kwargs: object
    ) -> tuple[list[SampleResult], list[ReproRecord]]:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("colliding paths must fail before trials")

    monkeypatch.setattr(monte_carlo, "run_trials", fake_run_trials)
    shared_path = tmp_path / "shared.out"

    with pytest.raises(ValueError, match="must be distinct"):
        run_monte_carlo(
            n_samples=1,
            base_seed=41,
            defines=defines,
            max_ticks=3,
            csv_path=shared_path,
            manifest_path=shared_path,
            progress=False,
        )

    assert trials_started is False


@pytest.mark.parametrize(
    ("csv_relative", "manifest_relative"),
    [
        ("bundle", "bundle/manifest.json"),
        ("bundle/results.csv", "bundle"),
    ],
)
def test_run_refuses_nested_output_paths_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    csv_relative: str,
    manifest_relative: str,
) -> None:
    trials_started = False

    def fake_run_trials(
        *args: object, **kwargs: object
    ) -> tuple[list[SampleResult], list[ReproRecord]]:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("nested paths must fail before trials")

    monkeypatch.setattr(monte_carlo, "run_trials", fake_run_trials)
    bundle_path = tmp_path / "bundle"

    with pytest.raises(ValueError, match="must not contain one another"):
        run_monte_carlo(
            n_samples=1,
            base_seed=41,
            max_ticks=3,
            csv_path=tmp_path / csv_relative,
            manifest_path=tmp_path / manifest_relative,
            progress=False,
        )

    assert trials_started is False
    assert not bundle_path.exists()


def test_run_validates_all_outputs_before_creating_parents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    trials_started = False

    def fake_run_trials(
        *args: object, **kwargs: object
    ) -> tuple[list[SampleResult], list[ReproRecord]]:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("invalid paths must fail before trials")

    monkeypatch.setattr(monte_carlo, "run_trials", fake_run_trials)
    new_parent = tmp_path / "not-created"
    existing_directory = tmp_path / "existing-directory"
    existing_directory.mkdir()

    with pytest.raises(ValueError, match="is a directory"):
        run_monte_carlo(
            csv_path=new_parent / "run.csv",
            manifest_path=new_parent / "run.manifest.json",
            report_path=existing_directory,
            progress=False,
        )

    assert trials_started is False
    assert not new_parent.exists()


def test_run_refuses_directory_output_before_trials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    trials_started = False

    def fake_run_trials(
        *args: object, **kwargs: object
    ) -> tuple[list[SampleResult], list[ReproRecord]]:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("invalid paths must fail before trials")

    monkeypatch.setattr(monte_carlo, "run_trials", fake_run_trials)

    with pytest.raises(ValueError, match="is a directory"):
        run_monte_carlo(csv_path=tmp_path, progress=False)

    assert trials_started is False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"n_samples": 0}, "n_samples must be"),
        ({"n_samples": monte_carlo.MAX_SAMPLES + 1}, "n_samples must be"),
        ({"max_ticks": 0}, "max_ticks must be"),
        ({"max_ticks": monte_carlo.MAX_TICKS + 1}, "max_ticks must be"),
    ],
)
def test_run_refuses_unbounded_workloads_before_trials(
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, int],
    message: str,
) -> None:
    trials_started = False

    def fake_run_trials(
        *args: object, **run_kwargs: object
    ) -> tuple[list[SampleResult], list[ReproRecord]]:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("invalid workloads must fail before trials")

    monkeypatch.setattr(monte_carlo, "run_trials", fake_run_trials)

    with pytest.raises(ValueError, match=message):
        run_monte_carlo(progress=False, **kwargs)

    assert trials_started is False
