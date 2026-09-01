"""Behavioral contract: deterministic frozen-reference analysis trials.

Given identical ``(defines, seed, backend, scenario, max_ticks)``,
:func:`tools.devtools.sim_analysis.runner_api.run` must produce a
byte-identical :class:`~tools.devtools.sim_analysis.backends.types.Result`,
and the derived :class:`~tools.devtools.sim_analysis.reproducibility.ReproRecord`
must carry an identical ``defines_hash``. This is the property that makes a
trial replayable and a sweep/Monte Carlo/sensitivity result trustworthy — if
two runs of the same inputs ever diverge, some System has picked up
process-global randomness or unseeded state, which Constitution III.7
declares a bug, not a feature.

Uses ``backend="in_memory"`` exclusively — no Postgres required.
"""

from __future__ import annotations

import pytest
from tools.devtools.sim_analysis import runner_api
from tools.devtools.sim_analysis.__main__ import build_parser
from tools.devtools.sim_analysis.backends.types import Result
from tools.devtools.sim_analysis.reproducibility import build_repro_record

from babylon.config.defines import GameDefines

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
        from tools.devtools.sim_analysis.params import inject_parameter

        defines = inject_parameter(GameDefines(), "economy.base_subsistence", 0.1)
        first, second = _run_twice(defines)
        assert first == second

    def test_repro_record_defines_hash_identical(self) -> None:
        defines = GameDefines()
        first, second = _run_twice(defines)
        record_a = build_repro_record(first, scenario=_SCENARIO, max_ticks=_MAX_TICKS)
        record_b = build_repro_record(second, scenario=_SCENARIO, max_ticks=_MAX_TICKS)
        assert record_a.defines_hash == record_b.defines_hash
        assert record_a == record_b
        assert record_a.scenario == _SCENARIO
        assert "scope_name" not in record_a.model_dump()

    def test_retired_postgres_backend_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown backend 'headless'"):
            runner_api.run(GameDefines(), backend="headless")

    def test_cli_has_no_retired_postgres_scope_flag(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "sweep",
                    "--param",
                    "economy.base_subsistence=0.1:0.2:0.1",
                    "--scope-name",
                    "detroit-tri-county",
                ]
            )
