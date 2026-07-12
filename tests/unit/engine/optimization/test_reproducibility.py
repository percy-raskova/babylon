"""Behavioral contract: determinism (Constitution III.7).

Given identical ``(defines, seed, backend, scenario, max_ticks)``,
:func:`babylon.engine.optimization.runner_api.run` must produce a
byte-identical :class:`~babylon.engine.optimization.backends.types.Result`,
and the derived :class:`~babylon.engine.optimization.reproducibility.ReproRecord`
must carry an identical ``defines_hash``. This is the property that makes a
trial replayable and a sweep/Monte Carlo/sensitivity result trustworthy — if
two runs of the same inputs ever diverge, some System has picked up
process-global randomness or unseeded state, which Constitution III.7
declares a bug, not a feature.

Uses ``backend="in_memory"`` exclusively — no Postgres required.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.engine.optimization import runner_api
from babylon.engine.optimization.backends.types import Result
from babylon.engine.optimization.reproducibility import build_repro_record

_SEED = 2010
_MAX_TICKS = 5
_SCENARIO = "imperial_circuit"


def _run_twice(defines: GameDefines) -> tuple[Result, Result]:
    first = runner_api.run(
        defines,
        seed=_SEED,
        max_ticks=_MAX_TICKS,
        backend="in_memory",
        scenario=_SCENARIO,
    )
    second = runner_api.run(
        defines,
        seed=_SEED,
        max_ticks=_MAX_TICKS,
        backend="in_memory",
        scenario=_SCENARIO,
    )
    return first, second


class TestResultDeterminism:
    """Same inputs -> identical Result, on default and swept defines."""

    def test_default_defines_identical_result(self) -> None:
        defines = GameDefines()
        first, second = _run_twice(defines)
        assert first == second

    def test_default_defines_identical_core_fields(self) -> None:
        """Spell out the fields the task calls out explicitly, in addition
        to the whole-object equality above (belt + suspenders: a future
        field addition to Result that breaks equality shouldn't silently
        also break this contract's visibility into *which* field moved).
        """
        defines = GameDefines()
        first, second = _run_twice(defines)
        assert first.ticks_survived == second.ticks_survived
        assert first.final_wealth == second.final_wealth
        assert first.outcome == second.outcome

    def test_swept_defines_identical_result(self) -> None:
        """Determinism must hold for non-default defines too, not just the
        hardcoded default — otherwise a sweep over many defines values could
        be internally non-reproducible even though the base-case test above
        is green.
        """
        from babylon.engine.optimization.params import inject_parameter

        defines = inject_parameter(GameDefines(), "economy.base_subsistence", 0.1)
        first, second = _run_twice(defines)
        assert first == second

    def test_repro_record_defines_hash_identical(self) -> None:
        defines = GameDefines()
        first, second = _run_twice(defines)
        record_a = build_repro_record(first, scope_name=_SCENARIO, max_ticks=_MAX_TICKS)
        record_b = build_repro_record(second, scope_name=_SCENARIO, max_ticks=_MAX_TICKS)
        assert record_a.defines_hash == record_b.defines_hash
        assert record_a == record_b
