"""Anti-regression guard: injected GameDefines reach the frozen reference engine.

The ``in_memory`` backend threads ``defines`` through ``step()`` on
every tick (see ``backends/in_memory.py`` module docstring), so it is the
canary: if this test ever goes green-for-the-wrong-reason (i.e. starts
failing because the two Results become equal again), the inert-defines bug
has come back — in this backend or in whatever it delegates to.

Sweeps ``economy.base_subsistence`` across its full documented range
(``ge=0.0, le=0.5``) at two widely separated points and asserts the two
trials produce genuinely different outcomes.
"""

from __future__ import annotations

import pytest
from tools.devtools.sim_analysis import runner_api
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.params import inject_parameter

from babylon.config.defines import GameDefines

_SEED = 2010
_MAX_TICKS = 5
_SCENARIO = "imperial_circuit"
_PARAM_PATH = "economy.base_subsistence"
_LOW = 0.001
_HIGH = 0.4


def _run_at(value: float) -> Result:
    defines = inject_parameter(GameDefines(), _PARAM_PATH, value)
    return runner_api.run(
        defines,
        seed=_SEED,
        max_ticks=_MAX_TICKS,
        backend="in_memory",
        scenario=_SCENARIO,
    )


class TestDefinesInjectionReachesEngine:
    """A swept coefficient must change the trial's outcome, not just its hash."""

    def test_injected_value_lands_on_the_defines(self) -> None:
        low_defines = inject_parameter(GameDefines(), _PARAM_PATH, _LOW)
        high_defines = inject_parameter(GameDefines(), _PARAM_PATH, _HIGH)
        assert low_defines.economy.base_subsistence == _LOW
        assert high_defines.economy.base_subsistence == _HIGH

    def test_sweep_produces_different_results(self) -> None:
        low_result = _run_at(_LOW)
        high_result = _run_at(_HIGH)
        assert low_result != high_result, (
            f"economy.base_subsistence={_LOW} and ={_HIGH} produced an "
            "identical Result — the inert-defines bug (fixed in bd3772a9) "
            "appears to have regressed: the in_memory backend is not "
            "honoring the injected GameDefines."
        )

    def test_sweep_produces_different_defines_hash(self) -> None:
        """The hash is the cheapest possible canary: two different
        coefficient sets must never hash identically.
        """
        low_result = _run_at(_LOW)
        high_result = _run_at(_HIGH)
        assert low_result.defines_hash != high_result.defines_hash

    def test_sweep_produces_different_final_wealth(self) -> None:
        """A higher subsistence burn must change the terminal wealth
        aggregate — the specific, human-legible signal an engineer would
        check by hand if this test failed.
        """
        low_result = _run_at(_LOW)
        high_result = _run_at(_HIGH)
        assert low_result.final_wealth != high_result.final_wealth


@pytest.mark.parametrize("max_ticks", [0, -1, True])
def test_runner_refuses_nonpositive_or_boolean_tick_limits(max_ticks: int) -> None:
    with pytest.raises(ValueError, match="max_ticks must be a positive integer"):
        runner_api.run(GameDefines(), max_ticks=max_ticks)


def test_runner_refuses_boolean_seed() -> None:
    with pytest.raises(ValueError, match="seed must be an integer"):
        runner_api.run(GameDefines(), seed=True, max_ticks=1)
