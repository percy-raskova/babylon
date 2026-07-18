"""D4: the Vol III calculators threaded into qa:regression (Task U1.3) must be
genuinely INVOKED during a scenario run, not merely constructed.

Construction is not the contract — execution is. TickDynamicsSystem's
`if services.melt_calculator is None` guard sits before Step 2 of the annual
economics pipeline, so a fully-wired-but-MELT-less container produces exactly
zero Vol III calculator calls across a whole run while every construction-level
assertion stays green.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from babylon.domain.economics.tick.system import TickDynamicsSystem

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402

# Derived from the same expression TickDynamicsSystem._determine_year uses
# (base_year + tick // WEEKS_PER_YEAR), rather than a hardcoded literal, so
# this test cannot drift from the engine again. context.tick == state.tick
# (see engine/simulation_engine.py step()) and _run_scenario_ticks' loop
# advances state starting from tick 0, so the first (and, given
# DEFAULT_MAX_TICKS == WEEKS_PER_YEAR == 52, only) year-boundary evaluation
# happens at tick 0 -> year 2010, never tick 52 (context.tick only ever
# reaches 0..max_ticks-1 == 0..51).
EXPECTED_YEAR: int = TickDynamicsSystem()._determine_year(0)


def test_regression_run_actually_invokes_the_vol3_financial_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED->GREEN: a full regression run must reach Step 5.5 (financial layer).

    ``_compute_national_financial_state`` calls
    ``interest_calculator.compute_interest_rate_state(year)`` once per
    year-boundary tick, *before* the per-county loop — so it fires even though
    these scenarios carry no real counties. Zero calls means the pipeline never
    got past the ``melt_calculator is None`` gate.
    """
    from babylon.domain.economics.credit.interest import DefaultInterestCalculator

    original = DefaultInterestCalculator.compute_interest_rate_state
    observed_years: list[int] = []

    def _counting(self: Any, year: int) -> Any:
        observed_years.append(year)
        return original(self, year)

    monkeypatch.setattr(DefaultInterestCalculator, "compute_interest_rate_state", _counting)

    rt.run_scenario("two_node", max_ticks=rt.DEFAULT_MAX_TICKS)

    assert observed_years, (
        "Vol III financial calculators were CONSTRUCTED but never INVOKED across a "
        f"full {rt.DEFAULT_MAX_TICKS}-tick qa:regression run. TickDynamicsSystem's "
        "`if services.melt_calculator is None` guard "
        "(src/babylon/domain/economics/tick/system/__init__.py) is still closed, so "
        "Steps 2-9 of the annual economics pipeline — national params, county state, "
        "Vol I production, imperial rent, circulation, crisis triggers, the Step 5.5 "
        "financial layer, class transitions, bifurcation risk, derived rates — never "
        "execute. qa:regression remains blind to the whole economics estate."
    )
    # context.tick == state.tick and the harness loop starts state.tick at 0,
    # so the sole year boundary in a DEFAULT_MAX_TICKS == 52 run is context.tick
    # 0 -> EXPECTED_YEAR (2010), never context.tick 52 (that value is never
    # reached; the loop's 52nd iteration passes context.tick == 51).
    assert observed_years == [EXPECTED_YEAR], (
        f"expected exactly one year-boundary evaluation at year {EXPECTED_YEAR}, "
        f"got {observed_years}"
    )


def test_committed_melt_fixture_yields_a_real_tau_not_a_sentinel() -> None:
    """The fixture must be materially right, not merely present.

    A fixture that parses but resolves to NoDataSentinel would leave the gate
    open and the pipeline still dark at Step 2 (`_compute_national_params`
    returns None on an unavailable MELT).
    """
    calculator = rt._build_vol3_melt_calculator()

    tau = calculator.get_melt(EXPECTED_YEAR)

    assert isinstance(tau, float), (
        f"MELT for {EXPECTED_YEAR} resolved to {tau!r} — the committed MELT fixture is "
        "missing GDP and/or employment for the only year qa:regression computes"
    )
    valid, message = calculator.validate_melt(tau)
    assert valid, message
    assert message is None, (
        f"tau={tau} is outside DefaultMELTCalculator's expected band: {message}. "
        "The fixture is wrong — do not widen the band."
    )
