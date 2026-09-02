"""Cross-algorithm contracts for normalized simulation objectives."""

from __future__ import annotations

import pytest
from tools.devtools.sim_analysis import runner_api
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.objectives import (
    calculate_carceral_equilibrium_score,
    carceral_objective,
    final_wealth_objective,
)

from babylon.config.defines import GameDefines


def _early_death_result(*, extra: dict[str, object]) -> Result:
    return Result(
        ticks_survived=2600,
        outcome="DIED",
        max_tension=0.0,
        final_wealth=0.0,
        phase_milestones={"superwage_crisis": 2500},
        terminal_outcome=None,
        defines_hash="0" * 64,
        rng_seed=2010,
        backend="in_memory",
        extra=extra,
    )


def test_carceral_objective_scores_early_death_against_configured_horizon() -> None:
    configured_max_ticks = 5200
    result = _early_death_result(extra={"max_ticks": configured_max_ticks})
    expected = calculate_carceral_equilibrium_score(
        result.phase_milestones,
        result.terminal_outcome,
        max_ticks=configured_max_ticks,
    )
    truncated_horizon_score = calculate_carceral_equilibrium_score(
        result.phase_milestones,
        result.terminal_outcome,
        max_ticks=result.ticks_survived,
    )

    assert expected != truncated_horizon_score
    assert carceral_objective(result) == expected


@pytest.mark.parametrize("invalid_max_ticks", [None, 0, -1, True, 1.5, "5200"])
def test_carceral_objective_requires_positive_integer_configured_horizon(
    invalid_max_ticks: object,
) -> None:
    extra = {} if invalid_max_ticks is None else {"max_ticks": invalid_max_ticks}

    with pytest.raises(ValueError, match=r"Result\.extra\['max_ticks'\]"):
        carceral_objective(_early_death_result(extra=extra))


def test_carceral_objective_rejects_ticks_beyond_configured_horizon() -> None:
    with pytest.raises(ValueError, match="ticks_survived cannot exceed configured max_ticks"):
        carceral_objective(_early_death_result(extra={"max_ticks": 2599}))


def test_in_memory_result_carries_configured_horizon() -> None:
    result = runner_api.run(GameDefines(), max_ticks=1)

    assert result.extra["max_ticks"] == 1


def test_final_wealth_objective_returns_the_normalized_terminal_value() -> None:
    result = _early_death_result(extra={}).model_copy(update={"final_wealth": 123.5})

    assert final_wealth_objective(result) == 123.5
