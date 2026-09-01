"""Native-type and schema-boundary guards for Optuna-facing analysis."""

from __future__ import annotations

from typing import Any

import pytest
from tools.devtools.sim_analysis import bayesian
from tools.devtools.sim_analysis.params import get_tunable_parameters


class _StubTrial:
    def __init__(self, *, int_value: Any = 7, float_value: Any = 0.5) -> None:
        self.int_value = int_value
        self.float_value = float_value
        self.number = 0
        self.suggested_names: list[str] = []

    def suggest_int(self, name: str, _lower: int, _upper: int) -> Any:
        self.suggested_names.append(name)
        return self.int_value

    def suggest_float(self, name: str, _lower: float, _upper: float) -> Any:
        self.suggested_names.append(name)
        return self.float_value


class _StubStudy:
    def __init__(self, *, trials: list[object] | None = None) -> None:
        self.user_attrs: dict[str, object] = {}
        self.trials = [] if trials is None else trials

    def set_user_attr(self, name: str, value: object) -> None:
        self.user_attrs[name] = value


def test_integer_proposal_remains_native_int() -> None:
    params = bayesian._sample_params(
        _StubTrial(int_value=7),
        {"crisis.crisis_period_ticks": (1, 52)},
    )

    value = params["crisis.crisis_period_ticks"]
    assert value == 7
    assert type(value) is int


def test_fractional_integer_proposal_fails_before_simulation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bayesian, "HAS_OPTUNA", True)
    simulation_called = False

    def fail_if_called(*_args: Any, **_kwargs: Any) -> None:
        nonlocal simulation_called
        simulation_called = True

    monkeypatch.setattr(bayesian, "run_trial", fail_if_called)
    objective = bayesian.create_objective(
        {"crisis.crisis_period_ticks": (1, 52)},
        max_ticks=52,
        backend="in_memory",
        seed=2010,
    )

    with pytest.raises(TypeError, match="non-int value"):
        objective(_StubTrial(int_value=7.5))
    assert simulation_called is False


def test_narrow_search_space_cannot_restore_strict_float_endpoint() -> None:
    with pytest.raises(ValueError, match="exceed its sampleable GameDefines bounds"):
        bayesian._resolve_search_space(
            ["crisis"],
            {"crisis.r_threshold": (0.0, 1.0)},
        )


def test_integer_search_space_requires_native_integer_bounds() -> None:
    with pytest.raises(TypeError, match="requires integer bounds"):
        bayesian._resolve_search_space(
            ["crisis"],
            {"crisis.crisis_period_ticks": (1.0, 52.0)},
        )


def test_optuna_uses_full_paths_for_colliding_leaf_names() -> None:
    full_space = get_tunable_parameters()
    search_space = {
        "metabolism.entropy_factor": full_space["metabolism.entropy_factor"],
        "substrate.entropy_factor": full_space["substrate.entropy_factor"],
    }
    trial = _StubTrial(float_value=2.0)

    params = bayesian._sample_params(trial, search_space)

    assert trial.suggested_names == [
        "metabolism.entropy_factor",
        "substrate.entropy_factor",
    ]
    assert set(params) == set(search_space)


def test_best_parameter_mapping_refuses_legacy_leaf_only_identity() -> None:
    search_space = {"metabolism.entropy_factor": (0.0, 1.0)}

    with pytest.raises(ValueError, match="outside this search space"):
        bayesian._map_best_params({"entropy_factor": 0.5}, search_space)


def test_new_study_records_and_reuses_exact_experiment_manifest() -> None:
    study = _StubStudy()
    manifest = {"fingerprint_sha256": "a" * 64, "max_ticks": 52}

    bayesian._validate_or_record_experiment(study, manifest)
    bayesian._validate_or_record_experiment(study, manifest)

    assert study.user_attrs[bayesian._EXPERIMENT_ATTRIBUTE] == manifest


def test_resume_refuses_legacy_or_changed_experiment() -> None:
    legacy = _StubStudy(trials=[object()])
    manifest = {"fingerprint_sha256": "a" * 64, "max_ticks": 52}

    with pytest.raises(ValueError, match="no Babylon experiment fingerprint"):
        bayesian._validate_or_record_experiment(legacy, manifest)

    current = _StubStudy()
    bayesian._validate_or_record_experiment(current, manifest)
    changed = {"fingerprint_sha256": "b" * 64, "max_ticks": 104}
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        bayesian._validate_or_record_experiment(current, changed)


def test_experiment_manifest_binds_runtime_and_source_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bayesian, "_source_tree_sha256", lambda: "c" * 64)
    space = {"crisis.crisis_period_ticks": (1, 52)}

    first = bayesian._experiment_manifest(
        space,
        max_ticks=52,
        backend="in_memory",
        seed=7,
    )
    changed = bayesian._experiment_manifest(
        space,
        max_ticks=104,
        backend="in_memory",
        seed=7,
    )

    assert first["source_tree_sha256"] == "c" * 64
    assert first["parameters"] == [
        {
            "name": "crisis.crisis_period_ticks",
            "native_type": "int",
            "lower": 1,
            "upper": 52,
        }
    ]
    assert first["fingerprint_sha256"] != changed["fingerprint_sha256"]
