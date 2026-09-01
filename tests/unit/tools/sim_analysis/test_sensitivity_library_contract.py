"""Pin the current SALib sampling APIs and deterministic seed plumbing."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from tools.devtools.sim_analysis import sensitivity
from tools.devtools.sim_analysis.reproducibility import ReproRecord

pytestmark = pytest.mark.unit


def _problem(_names: list[str]) -> dict[str, Any]:
    return {
        "num_vars": 1,
        "names": ["economy.extraction_efficiency"],
        "bounds": [[0.1, 0.9]],
    }


def _outputs(
    param_values: object, *_args: object, **_kwargs: object
) -> tuple[list[float], list[ReproRecord]]:
    count = len(param_values)  # type: ignore[arg-type]
    outputs = [float(index + 1) for index in range(count)]
    records = [
        ReproRecord(
            defines_hash=f"hash-{index}",
            rng_seed=2010,
            backend="in_memory",
            scenario="imperial_circuit",
            max_ticks=1,
            ticks_survived=1,
            outcome="SURVIVED",
        )
        for index in range(count)
    ]
    return outputs, records


def test_morris_uses_seeded_current_salib_sample_and_analyze_apis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, int] = {}

    def sample(_problem: object, _trajectories: int, *, seed: int) -> np.ndarray:
        calls["sample_seed"] = seed
        return np.array([[0.1], [0.3], [0.7], [0.9]])

    def analyze(
        _problem: object,
        _parameters: object,
        _outputs: object,
        *,
        seed: int,
    ) -> dict[str, np.ndarray]:
        calls["analyze_seed"] = seed
        return {
            "mu": np.array([0.1]),
            "mu_star": np.array([0.2]),
            "sigma": np.array([0.3]),
            "mu_star_conf": np.array([0.4]),
        }

    monkeypatch.setattr(sensitivity, "create_problem", _problem)
    monkeypatch.setattr(sensitivity.morris_sample, "sample", sample)
    monkeypatch.setattr(sensitivity, "evaluate_simulation", _outputs)
    monkeypatch.setattr(sensitivity.morris_analyze, "analyze", analyze)

    result, records = sensitivity.run_morris_analysis(
        ["economy.extraction_efficiency"],
        trajectories=2,
        max_ticks=1,
        seed=73,
        progress=False,
    )

    assert calls == {"sample_seed": 73, "analyze_seed": 73}
    assert result.ranking == ("economy.extraction_efficiency",)
    assert len(records) == 4
    assert result.trials[0].sampled_values == (0.1,)


def test_sobol_uses_seeded_current_salib_sample_and_analyze_apis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    def sample(
        _problem: object,
        _samples: int,
        *,
        calc_second_order: bool,
        seed: int,
    ) -> np.ndarray:
        calls["sample"] = (calc_second_order, seed)
        return np.array([[0.1], [0.3], [0.7], [0.9]])

    def analyze(
        _problem: object,
        _outputs: object,
        *,
        calc_second_order: bool,
        seed: int,
    ) -> dict[str, np.ndarray]:
        calls["analyze"] = (calc_second_order, seed)
        return {
            "S1": np.array([0.1]),
            "S1_conf": np.array([0.01]),
            "ST": np.array([0.2]),
            "ST_conf": np.array([0.02]),
            "S2": np.array([[np.nan]]),
        }

    monkeypatch.setattr(sensitivity, "create_problem", _problem)
    monkeypatch.setattr(sensitivity.sobol_sample, "sample", sample)
    monkeypatch.setattr(sensitivity, "evaluate_simulation", _outputs)
    monkeypatch.setattr(sensitivity.sobol_analyze, "analyze", analyze)

    result, records = sensitivity.run_sobol_analysis(
        ["economy.extraction_efficiency"],
        samples=1,
        max_ticks=1,
        seed=91,
        progress=False,
    )

    assert calls == {
        "sample": (True, 91),
        "analyze": (True, 91),
    }
    assert result.ranking_ST == ("economy.extraction_efficiency",)
    assert len(records) == 4
    assert len(result.trials) == 4
