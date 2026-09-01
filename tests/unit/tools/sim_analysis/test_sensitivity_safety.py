"""Safety and evidence contracts for bounded sensitivity analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from tools.devtools.sim_analysis import sensitivity
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.reproducibility import ReproRecord

from babylon.config.defines import canonical_defines_hash


def _records(count: int, *, seed: int = 2010, max_ticks: int = 1) -> list[ReproRecord]:
    return [
        ReproRecord(
            defines_hash=f"hash-{index}",
            rng_seed=seed,
            backend="in_memory",
            scenario="imperial_circuit",
            max_ticks=max_ticks,
            ticks_survived=max_ticks,
            outcome="SURVIVED",
        )
        for index in range(count)
    ]


def test_default_surface_is_curated_and_bounded() -> None:
    names = sensitivity.get_default_params()

    assert tuple(names) == sensitivity.DEFAULT_PARAMETER_NAMES
    assert len(names) == 8
    assert len(names) <= sensitivity.MAX_PARAMETER_COUNT
    assert "economy.extraction_efficiency" in names


def test_strict_schema_bound_is_not_sampled_as_an_endpoint() -> None:
    definition = sensitivity._parameter_definition("crisis.r_threshold")
    problem = sensitivity.create_problem(["crisis.r_threshold"])

    assert definition.declared_lower == 0.0
    assert definition.lower_inclusive is False
    assert definition.sample_lower > 0.0
    assert problem["bounds"] == [[float(definition.sample_lower), float(definition.sample_upper)]]


def test_oversized_sobol_is_rejected_before_sampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sampled = False

    def sample(*_args: object, **_kwargs: object) -> np.ndarray:
        nonlocal sampled
        sampled = True
        return np.empty((0, 0))

    monkeypatch.setattr(sensitivity.sobol_sample, "sample", sample)

    with pytest.raises(ValueError, match="evaluations"):
        sensitivity.run_sobol_analysis(
            sensitivity.get_default_params(),
            samples=sensitivity.MAX_SOBOL_BASE_SAMPLES,
            max_ticks=1,
            progress=False,
        )

    assert sampled is False


def test_one_morris_trajectory_is_rejected_before_sampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sampled = False

    def sample(*_args: object, **_kwargs: object) -> np.ndarray:
        nonlocal sampled
        sampled = True
        return np.empty((0, 0))

    monkeypatch.setattr(sensitivity.morris_sample, "sample", sample)

    with pytest.raises(ValueError, match=r"2\.\."):
        sensitivity.run_morris_analysis(
            ["economy.extraction_efficiency"],
            trajectories=1,
            max_ticks=1,
            progress=False,
        )

    assert sampled is False


def test_combined_sensitivity_rejects_one_trajectory_before_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analysis_started = False

    def morris(*_args: object, **_kwargs: object) -> None:
        nonlocal analysis_started
        analysis_started = True

    monkeypatch.setattr(sensitivity, "run_morris_analysis", morris)

    with pytest.raises(ValueError, match=r"2\.\."):
        sensitivity.run_sensitivity(
            "both",
            param_names=["economy.extraction_efficiency"],
            trajectories=1,
            samples=1,
            max_ticks=1,
            progress=False,
        )

    assert analysis_started is False


def test_constant_objective_is_rejected_before_morris_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzed = False

    monkeypatch.setattr(
        sensitivity.morris_sample,
        "sample",
        lambda *_args, **_kwargs: np.array([[0.1], [0.3], [0.7], [0.9]]),
    )
    monkeypatch.setattr(
        sensitivity,
        "evaluate_simulation",
        lambda *_args, **_kwargs: ([2.0] * 4, _records(4)),
    )

    def analyze(*_args: object, **_kwargs: object) -> dict[str, np.ndarray]:
        nonlocal analyzed
        analyzed = True
        return {}

    monkeypatch.setattr(sensitivity.morris_analyze, "analyze", analyze)

    with pytest.raises(ValueError, match="zero variance"):
        sensitivity.run_morris_analysis(
            ["economy.extraction_efficiency"],
            trajectories=2,
            max_ticks=1,
            progress=False,
        )

    assert analyzed is False


def test_nonfinite_morris_index_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sensitivity.morris_sample,
        "sample",
        lambda *_args, **_kwargs: np.array([[0.1], [0.3], [0.7], [0.9]]),
    )
    monkeypatch.setattr(
        sensitivity,
        "evaluate_simulation",
        lambda *_args, **_kwargs: ([1.0, 2.0, 3.0, 4.0], _records(4)),
    )
    monkeypatch.setattr(
        sensitivity.morris_analyze,
        "analyze",
        lambda *_args, **_kwargs: {
            "mu": np.array([0.1]),
            "mu_star": np.array([np.nan]),
            "sigma": np.array([0.3]),
            "mu_star_conf": np.array([0.4]),
        },
    )

    with pytest.raises(ValueError, match="non-finite Morris mu_star"):
        sensitivity.run_morris_analysis(
            ["economy.extraction_efficiency"],
            trajectories=2,
            max_ticks=1,
            progress=False,
        )


def test_integer_samples_are_native_and_artifact_is_replayable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed: list[int] = []

    monkeypatch.setattr(
        sensitivity.morris_sample,
        "sample",
        lambda *_args, **_kwargs: np.array([[1.6], [2.6], [3.6], [4.6]]),
    )

    def run(defines: Any, *, seed: int, **_kwargs: object) -> Result:
        value = defines.crisis.crisis_period_ticks
        assert type(value) is int
        observed.append(value)
        return Result(
            ticks_survived=1,
            outcome="SURVIVED",
            max_tension=0.0,
            final_wealth=1.0,
            defines_hash=canonical_defines_hash(defines),
            rng_seed=seed,
            backend="in_memory",
        )

    monkeypatch.setattr(sensitivity.runner_api, "run", run)
    monkeypatch.setattr(
        sensitivity.morris_analyze,
        "analyze",
        lambda *_args, **_kwargs: {
            "mu": np.array([0.1]),
            "mu_star": np.array([0.2]),
            "sigma": np.array([0.3]),
            "mu_star_conf": np.array([0.4]),
        },
    )

    result, _records_out = sensitivity.run_morris_analysis(
        ["crisis.crisis_period_ticks"],
        trajectories=2,
        max_ticks=1,
        objective=lambda trial: trial.final_wealth + len(observed),
        progress=False,
    )

    assert observed == [2, 3, 4, 5]
    assert result.parameter_definitions[0].native_type == "int"
    assert result.trials[0].sampled_values == (1.6,)
    assert result.trials[0].native_overrides == {"crisis.crisis_period_ticks": 2}
    assert result.trials[0].repro.defines_hash == canonical_defines_hash(
        sensitivity.inject_parameters(
            sensitivity.GameDefines(),
            {"crisis.crisis_period_ticks": 2},
        )
    )
    base_crisis = result.base_defines["crisis"]
    assert isinstance(base_crisis, dict)
    assert base_crisis["crisis_period_ticks"] != 2

    artifact_path = tmp_path / "morris.json"
    sensitivity._write_strict_json(artifact_path, result)
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["trials"][0]["sampled_values"] == [1.6]
    assert payload["trials"][0]["native_overrides"] == {"crisis.crisis_period_ticks": 2}
    assert payload["schema"] == "babylon.sim-analysis.morris.v1"


def test_both_refuses_colliding_output_paths_before_analysis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    analysis_started = False

    def morris(*_args: object, **_kwargs: object) -> None:
        nonlocal analysis_started
        analysis_started = True

    monkeypatch.setattr(sensitivity, "run_morris_analysis", morris)
    shared = tmp_path / "shared.json"

    with pytest.raises(ValueError, match="must be distinct"):
        sensitivity.run_sensitivity(
            "both",
            param_names=["economy.extraction_efficiency"],
            trajectories=2,
            samples=1,
            max_ticks=1,
            morris_output=shared,
            sobol_output=shared,
            progress=False,
        )

    assert analysis_started is False


@pytest.mark.parametrize(
    ("morris_relative", "sobol_relative"),
    [
        ("bundle", "bundle/sobol.json"),
        ("bundle/morris.json", "bundle"),
    ],
)
def test_both_refuses_nested_output_paths_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    morris_relative: str,
    sobol_relative: str,
) -> None:
    analysis_started = False

    def morris(*_args: object, **_kwargs: object) -> None:
        nonlocal analysis_started
        analysis_started = True
        raise AssertionError("nested paths must fail before analysis")

    monkeypatch.setattr(sensitivity, "run_morris_analysis", morris)
    bundle_path = tmp_path / "bundle"

    with pytest.raises(ValueError, match="must not contain one another"):
        sensitivity.run_sensitivity(
            "both",
            param_names=["economy.extraction_efficiency"],
            trajectories=2,
            samples=1,
            max_ticks=1,
            morris_output=tmp_path / morris_relative,
            sobol_output=tmp_path / sobol_relative,
            progress=False,
        )

    assert analysis_started is False
    assert not bundle_path.exists()


def test_both_validates_all_outputs_before_analysis_or_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    analysis_started = False

    def morris(*_args: object, **_kwargs: object) -> None:
        nonlocal analysis_started
        analysis_started = True
        raise AssertionError("invalid paths must fail before analysis")

    monkeypatch.setattr(sensitivity, "run_morris_analysis", morris)
    new_parent = tmp_path / "not-created"
    existing_directory = tmp_path / "existing-directory"
    existing_directory.mkdir()

    with pytest.raises(ValueError, match="is a directory"):
        sensitivity.run_sensitivity(
            "both",
            param_names=["economy.extraction_efficiency"],
            trajectories=2,
            samples=1,
            max_ticks=1,
            morris_output=new_parent / "morris.json",
            sobol_output=existing_directory,
            progress=False,
        )

    assert analysis_started is False
    assert not new_parent.exists()


def test_both_promotes_only_top_morris_parameters_to_sobol(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    names = sensitivity.get_default_params()[:5]
    ranking = tuple(reversed(names))
    morris = sensitivity.MorrisResult(
        trajectories=2,
        seed=7,
        max_ticks=1,
        backend="in_memory",
        scenario="imperial_circuit",
        base_defines={},
        parameter_definitions=(),
        trials=(),
        parameters={
            name: sensitivity.MorrisParameterResult(
                mu=1.0,
                mu_star=float(index + 1),
                sigma=0.1,
                mu_star_conf=0.01,
            )
            for index, name in enumerate(names)
        },
        ranking=ranking,
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        sensitivity,
        "run_morris_analysis",
        lambda *_args, **_kwargs: (morris, []),
    )

    def sobol(
        selected_names: list[str],
        *_args: object,
        selection: str,
        **_kwargs: object,
    ) -> tuple[sensitivity.SobolResult, list[ReproRecord]]:
        captured["names"] = selected_names
        captured["selection"] = selection
        result = sensitivity.SobolResult(
            base_samples=1,
            total_samples=10,
            seed=7,
            max_ticks=1,
            backend="in_memory",
            scenario="imperial_circuit",
            selection="morris_top_mu_star",
            base_defines={},
            parameter_definitions=(),
            trials=(),
            parameters={},
            S2_interactions={},
            ranking_S1=(),
            ranking_ST=(),
        )
        return result, []

    monkeypatch.setattr(sensitivity, "run_sobol_analysis", sobol)

    sensitivity.run_sensitivity(
        "both",
        param_names=names,
        trajectories=2,
        samples=1,
        max_ticks=1,
        seed=7,
        output_dir=tmp_path,
        progress=False,
    )

    assert captured == {
        "names": list(ranking[: sensitivity.DEFAULT_SOBOL_SCREENED_PARAMETERS]),
        "selection": "morris_top_mu_star",
    }
