"""Durability, alignment, and workload contracts for parameter sweeps."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from tools.devtools.sim_analysis import sweep as sweep_module
from tools.devtools.sim_analysis.__main__ import main
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.objectives import carceral_objective
from tools.devtools.sim_analysis.params import ParameterValue, inject_parameter
from tools.devtools.sim_analysis.reproducibility import ReproRecord
from tools.devtools.sim_analysis.sweep import (
    MAX_SWEEP_EVALUATIONS,
    MAX_SWEEP_TICK_EVALUATIONS,
    SweepManifest1D,
    SweepManifest2D,
    SweepPoint,
    run_sweep,
    sweep_1d,
    sweep_2d,
    write_sweep_csv,
    write_sweep_manifest_1d,
    write_sweep_manifest_2d,
)

from babylon.config.defines import GameDefines, canonical_defines_hash

_PARAM1 = "economy.base_subsistence"
_PARAM2 = "economy.extraction_efficiency"
_SEED = 17
_MAX_TICKS = 3
_SCENARIO = "imperial_circuit"


def _point(
    base: GameDefines,
    value: ParameterValue,
    *,
    value2: ParameterValue | None = None,
) -> SweepPoint:
    defines = inject_parameter(base, _PARAM1, value)
    if value2 is not None:
        defines = inject_parameter(defines, _PARAM2, value2)
    result = Result(
        ticks_survived=_MAX_TICKS,
        outcome="SURVIVED",
        max_tension=0.25,
        final_wealth=12.5,
        phase_milestones={},
        terminal_outcome=None,
        defines_hash=canonical_defines_hash(defines),
        rng_seed=_SEED,
        backend="in_memory",
    )
    receipt = ReproRecord(
        defines_hash=result.defines_hash,
        rng_seed=_SEED,
        backend="in_memory",
        scenario=_SCENARIO,
        max_ticks=_MAX_TICKS,
        ticks_survived=result.ticks_survived,
        outcome=result.outcome,
        terminal_outcome=result.terminal_outcome,
    )
    return SweepPoint(
        value=value,
        value2=value2,
        result=result,
        repro=receipt,
        score=carceral_objective(result),
    )


def _reject_json_constant(token: str) -> object:
    raise AssertionError(f"non-standard JSON constant escaped validation: {token}")


def test_1d_manifest_retains_exact_replay_inputs_and_all_receipts(tmp_path: Path) -> None:
    base = GameDefines()
    values: list[ParameterValue] = [0.1, 0.2]
    points = [_point(base, value) for value in values]
    output = tmp_path / "sweep.manifest.json"

    write_sweep_manifest_1d(
        base_defines=base,
        param_path=_PARAM1,
        values=values,
        seed=_SEED,
        backend="in_memory",
        scenario=_SCENARIO,
        max_ticks=_MAX_TICKS,
        objective=carceral_objective,
        points=points,
        output_path=output,
    )

    payload = json.loads(output.read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    assert payload["schema"] == "babylon.sim-analysis.sweep-1d.v1"
    assert GameDefines.model_validate(payload["base_defines"]) == base
    assert payload["base_defines_hash"] == canonical_defines_hash(base)
    assert payload["parameter_path"] == _PARAM1
    assert payload["values"] == values
    assert payload["seed"] == _SEED
    assert payload["backend"] == "in_memory"
    assert payload["scenario"] == _SCENARIO
    assert payload["max_ticks"] == _MAX_TICKS
    assert payload["objective"].endswith(":carceral_objective")
    assert len(payload["points"]) == len(values)
    assert [point["repro"]["defines_hash"] for point in payload["points"]] == [
        point.repro.defines_hash for point in points
    ]
    assert SweepManifest1D.model_validate_json(output.read_text(encoding="utf-8")).values == (
        0.1,
        0.2,
    )


def test_2d_manifest_retains_grid_results_and_aligned_receipts(tmp_path: Path) -> None:
    base = GameDefines()
    values1: list[ParameterValue] = [0.1, 0.2]
    values2: list[ParameterValue] = [0.3, 0.4]
    matrix = [[_point(base, value1, value2=value2) for value2 in values2] for value1 in values1]
    output = tmp_path / "landscape.manifest.json"

    write_sweep_manifest_2d(
        base_defines=base,
        param1=_PARAM1,
        values1=values1,
        param2=_PARAM2,
        values2=values2,
        seed=_SEED,
        backend="in_memory",
        scenario=_SCENARIO,
        max_ticks=_MAX_TICKS,
        objective=carceral_objective,
        matrix=matrix,
        output_path=output,
    )

    payload = json.loads(output.read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    assert payload["schema"] == "babylon.sim-analysis.sweep-2d.v1"
    assert payload["parameter1_path"] == _PARAM1
    assert payload["values1"] == values1
    assert payload["parameter2_path"] == _PARAM2
    assert payload["values2"] == values2
    assert [[point["value2"] for point in row] for row in payload["matrix"]] == [
        values2,
        values2,
    ]
    assert all("result" in point and "repro" in point for row in payload["matrix"] for point in row)
    validated = SweepManifest2D.model_validate_json(output.read_text(encoding="utf-8"))
    assert validated.values1 == (0.1, 0.2)
    assert validated.values2 == (0.3, 0.4)


def test_manifest_rejects_misaligned_lengths_and_hashes(tmp_path: Path) -> None:
    base = GameDefines()
    point = _point(base, 0.1)

    with pytest.raises(ValueError, match="identical lengths"):
        write_sweep_manifest_1d(
            base_defines=base,
            param_path=_PARAM1,
            values=[0.1, 0.2],
            seed=_SEED,
            backend="in_memory",
            scenario=_SCENARIO,
            max_ticks=_MAX_TICKS,
            objective=carceral_objective,
            points=[point],
            output_path=tmp_path / "misaligned.json",
        )

    bad_result = point.result.model_copy(update={"defines_hash": "0" * 64})
    mismatched = SweepPoint.model_construct(
        value=point.value,
        value2=point.value2,
        result=bad_result,
        repro=point.repro,
        score=point.score,
    )
    with pytest.raises(ValueError, match="hash does not match"):
        write_sweep_manifest_1d(
            base_defines=base,
            param_path=_PARAM1,
            values=[0.1],
            seed=_SEED,
            backend="in_memory",
            scenario=_SCENARIO,
            max_ticks=_MAX_TICKS,
            objective=carceral_objective,
            points=[mismatched],
            output_path=tmp_path / "bad-hash.json",
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_sweep_point_rejects_nonfinite_values_and_results(value: float) -> None:
    base = GameDefines()
    point = _point(base, 0.1)

    with pytest.raises(ValidationError):
        SweepPoint(
            value=value,
            value2=None,
            result=point.result,
            repro=point.repro,
            score=point.score,
        )
    with pytest.raises(ValidationError):
        SweepPoint(
            value=point.value,
            value2=None,
            result=point.result.model_copy(update={"max_tension": value}),
            repro=point.repro,
            score=point.score,
        )


def test_csv_binds_each_point_to_seed_and_defines_hash(tmp_path: Path) -> None:
    point = _point(GameDefines(), 0.1)
    output = tmp_path / "sweep.csv"

    write_sweep_csv([point], output)

    rows = list(csv.DictReader(output.open(newline="")))
    assert rows[0]["defines_hash"] == point.repro.defines_hash
    assert rows[0]["rng_seed"] == str(_SEED)


def test_run_defaults_manifest_path_from_csv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base = GameDefines()
    point = _point(base, 0.1)

    def fake_sweep_1d(*_args: object, **_kwargs: object) -> list[SweepPoint]:
        return [point]

    monkeypatch.setattr(sweep_module, "sweep_1d", fake_sweep_1d)
    csv_path = tmp_path / "sweep.csv"

    run_sweep(
        param=f"{_PARAM1}=0.1:0.1:0.1",
        max_ticks=_MAX_TICKS,
        seed=_SEED,
        base_defines=base,
        output_csv=csv_path,
    )

    assert csv_path.is_file()
    assert csv_path.with_suffix(".manifest.json").is_file()


@pytest.mark.parametrize("invalid_output", ["collision", "directory"])
def test_run_refuses_invalid_outputs_before_trials(
    invalid_output: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    trials_started = False

    def fail_if_started(*args: object, **kwargs: object) -> list[SweepPoint]:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("invalid output paths must fail before trials")

    monkeypatch.setattr(sweep_module, "sweep_1d", fail_if_started)
    csv_path = tmp_path / "sweep.csv"
    manifest_path = csv_path if invalid_output == "collision" else tmp_path

    with pytest.raises(ValueError, match="distinct|is a directory|must not contain"):
        run_sweep(
            param=f"{_PARAM1}=0.1:0.1:0.1",
            output_csv=csv_path,
            manifest_path=manifest_path,
        )

    assert trials_started is False


def test_grid_workload_cap_fails_before_trials(monkeypatch: pytest.MonkeyPatch) -> None:
    trials_started = False

    def fail_if_started(*args: object, **kwargs: object) -> Result:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("oversized grids must fail before trials")

    monkeypatch.setattr(sweep_module, "run_trial", fail_if_started)

    with pytest.raises(ValueError, match=f"1..{MAX_SWEEP_EVALUATIONS}"):
        sweep_2d(
            _PARAM1,
            [0.1] * (MAX_SWEEP_EVALUATIONS + 1),
            _PARAM2,
            [0.3],
            progress=False,
        )

    assert trials_started is False


def test_tick_workload_cap_fails_before_trials(monkeypatch: pytest.MonkeyPatch) -> None:
    trials_started = False

    def fail_if_started(*args: object, **kwargs: object) -> Result:
        nonlocal trials_started
        trials_started = True
        raise AssertionError("oversized tick workloads must fail before trials")

    monkeypatch.setattr(sweep_module, "run_trial", fail_if_started)

    with pytest.raises(ValueError, match="exceeds the tick budget"):
        sweep_1d(
            _PARAM1,
            [0.1],
            max_ticks=MAX_SWEEP_TICK_EVALUATIONS + 1,
        )

    assert trials_started is False


def test_cli_forwards_explicit_sweep_manifest_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_run_sweep(**kwargs: object) -> list[SweepPoint]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr("tools.devtools.sim_analysis.__main__.run_sweep", fake_run_sweep)
    manifest_path = tmp_path / "custom.json"

    assert (
        main(
            [
                "sweep",
                "--param",
                f"{_PARAM1}=0.1:0.1:0.1",
                "--manifest-path",
                str(manifest_path),
            ]
        )
        == 0
    )
    assert captured["manifest_path"] == manifest_path
