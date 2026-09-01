"""Core invariants for normalized simulation analysis results."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError
from tools.devtools.sim_analysis.backends.types import Result


@pytest.mark.parametrize("field", ["max_tension", "final_wealth"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_result_rejects_nonfinite_observables(field: str, value: float) -> None:
    values: dict[str, object] = {
        "ticks_survived": 1,
        "outcome": "SURVIVED",
        "max_tension": 0.25,
        "final_wealth": 10.0,
        "phase_milestones": {},
        "terminal_outcome": None,
        "defines_hash": "0" * 64,
        "rng_seed": 7,
        "backend": "in_memory",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        Result.model_validate(values)


def test_result_accepts_finite_observables() -> None:
    result = Result(
        ticks_survived=1,
        outcome="SURVIVED",
        max_tension=0.25,
        final_wealth=10.0,
        defines_hash="0" * 64,
        rng_seed=7,
        backend="in_memory",
    )

    assert math.isfinite(result.max_tension)
    assert math.isfinite(result.final_wealth)
