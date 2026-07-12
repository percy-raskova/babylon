"""Anti-regression guard: injected GameDefines must actually reach the engine.

Before commit ``bd3772a9`` (Phase 1 fix), ``headless_runner`` silently
ignored the caller's injected ``GameDefines`` and always ran against the
default coefficients — every sweep/Monte Carlo/sensitivity/Bayesian trial
was therefore exploring a single point, not a parameter space. The
``in_memory`` backend genuinely threads ``defines`` through ``step()`` on
every tick (see ``backends/in_memory.py`` module docstring), so it is the
canary: if this test ever goes green-for-the-wrong-reason (i.e. starts
failing because the two Results become equal again), the inert-defines bug
has come back — in this backend or in whatever it delegates to.

Sweeps ``economy.base_subsistence`` across its full documented range
(``ge=0.0, le=0.5``) at two widely separated points and asserts the two
trials produce genuinely different outcomes.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.engine.optimization import runner_api
from babylon.engine.optimization.backends.types import Result
from babylon.engine.optimization.params import inject_parameter

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
