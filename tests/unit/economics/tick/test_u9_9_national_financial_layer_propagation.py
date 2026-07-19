"""U9.9 (repaired): the national financial layer is live end to end.

The prior version of this test hand-stamped ``tick_profit_rate`` /
``tick_capital_stock`` / ``reserve_ratio`` directly on a graph and called
``_compute_national_financial_state`` on it — which is exactly the deception the
final review caught: those attrs are stripped by ``state.to_graph()`` at the top
of every real tick and re-stamped only AFTER this layer, so the hand-stamped
graph proved the function works given attrs it never actually has at runtime,
while the endogenous rate was a structural zero in every real run.

The repaired layer reads ``r`` and ``s_r`` from the tick's own ``county_states``
(``r`` = ``Sum(s)/Sum(c+v)`` over the realized surplus/profit-rate tensors;
``s_r`` = employment-weighted U-3). This test drives it through that real source:
varying the county surplus/profit-rate tensors and unemployment changes the
published ``NATIONAL_FINANCIAL_ATTR``, and the live downstream reader
(``ContradictionSystem._credit_fragility``) observes the change.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.economics.tick.graph_bridge import (
    read_national_financial_state_from_graph,
)
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.contradiction import ContradictionSystem
from babylon.engine.systems.market_scissors import _read_fictitious_anchor
from tests.unit.economics.credit.conftest import MockCreditAggregateSource
from tests.unit.economics.tick.conftest import (
    MockFictitiousCapitalCalculator,
    MockTensor,
    MockTensorRegistry,
    build_territory_graph,
)
from tests.unit.economics.tick.test_system import (
    WAYNE_FIPS,
    _make_county,
    _make_services,
    _StubDistributionOkCalculator,
)

TOOLS_DIR = Path(__file__).resolve().parents[4] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import regression_test as rt  # type: ignore[import-not-found]  # noqa: E402

_YEAR = 2015


@pytest.mark.unit
def test_qa_regression_overrides_carry_a_real_distribution_calculator() -> None:
    """The real qa:regression override-building path never yields a None
    distribution calculator, so the ``_compute_financial_layer`` early-return
    guard (``if services.distribution_calculator is None: return``) never fires
    for the 5 qa:regression scenarios."""
    overrides = rt._build_vol3_calculator_overrides(GameDefines.load_default())
    assert overrides["distribution_calculator"] is not None

    services = ServiceContainer.create(**overrides)
    assert services.distribution_calculator is not None


def _services(profit_rate: float, total_s: float) -> object:
    """A calculator estate whose tensor serves a chosen realized (r, s) pair."""
    return _make_services(
        distribution_calculator=_StubDistributionOkCalculator(),
        fictitious_capital_calculator=MockFictitiousCapitalCalculator(),
        credit_aggregate_source=MockCreditAggregateSource(data={_YEAR: (60e12, 18e12, 20e12)}),
        tensor_registry=MockTensorRegistry(
            {(WAYNE_FIPS, _YEAR): MockTensor(profit_rate=profit_rate, total_s=total_s)}
        ),
    )


@pytest.mark.unit
def test_endogenous_national_state_is_live_and_reaches_downstream_consumers() -> None:
    """Varying the realized profit rate / reserve army changes the published
    NATIONAL_FINANCIAL_ATTR, and a live downstream reader observes it — proving
    the computed state is not merely constructed-but-never-observed, and is
    sourced from real county quantities rather than stripped graph attrs."""
    defines = GameDefines.load_default()
    system = TickDynamicsSystem()

    # LOW: a small realized rate of profit and a calm labor market (u3 below the
    # 0.08 reference -> s_r = 0 -> tightness 0 -> interest = r * base).
    low_states = {WAYNE_FIPS: _make_county(year=_YEAR, unemployment_rate=0.03)}
    low_graph = build_territory_graph()
    low_rate, low_spread, _ = system._compute_national_financial_state(
        _services(profit_rate=0.05, total_s=1_000_000.0), _YEAR, low_graph, low_states
    )

    # HIGH: a larger realized rate of profit and a slack labor market (elevated
    # u3 -> non-zero s_r -> tightness -> a real fragility premium).
    high_states = {WAYNE_FIPS: _make_county(year=_YEAR, unemployment_rate=0.60)}
    high_graph = build_territory_graph()
    high_rate, high_spread, _ = system._compute_national_financial_state(
        _services(profit_rate=0.30, total_s=1_000_000.0), _YEAR, high_graph, high_states
    )

    # 1. The computation is not frozen and not inert: different real inputs ->
    #    different, genuinely non-zero outputs.
    assert low_rate > 0.0
    assert high_rate > 0.0
    assert low_rate != high_rate
    assert low_spread == pytest.approx(0.0)  # calm market: base share only
    assert high_spread > 0.0  # slack market: real premium
    assert low_spread != high_spread

    # 2. The state actually landed on the graph both times.
    low_published = read_national_financial_state_from_graph(low_graph)
    high_published = read_national_financial_state_from_graph(high_graph)
    assert low_published is not None and high_published is not None
    assert low_published.endogenous_interest is not None
    assert high_published.endogenous_interest is not None
    assert low_published.endogenous_interest.rate == pytest.approx(low_rate)
    assert high_published.endogenous_interest.rate == pytest.approx(high_rate)

    # 3. A live downstream consumer (ContradictionSystem) reads the published
    #    state and sees the difference, not a frozen/absent value.
    low_fragility = ContradictionSystem._credit_fragility(
        low_graph, defines.capital_vol3.credit_fragility_scale
    )
    high_fragility = ContradictionSystem._credit_fragility(
        high_graph, defines.capital_vol3.credit_fragility_scale
    )
    assert low_fragility is not None and high_fragility is not None
    assert low_fragility != high_fragility

    # 4. The other live downstream consumer (MarketScissorsSystem) reads the
    #    same published state honestly and must not raise.
    low_anchor = _read_fictitious_anchor(low_graph.graph, real_output=1e9)
    high_anchor = _read_fictitious_anchor(high_graph.graph, real_output=1e9)
    assert low_anchor is None or isinstance(low_anchor, float)
    assert high_anchor is None or isinstance(high_anchor, float)
