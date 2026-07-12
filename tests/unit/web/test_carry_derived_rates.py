"""Program 17 item-25 Fix A: the web-bridge carry must not drop the derived rates.

``write_tick_state_to_graph`` computes ``tick_profit_rate``/``tick_occ``/
``tick_exploitation_rate`` at a year boundary (``graph_bridge.py:122-124``), but
``step()``'s ``WorldState`` round-trip strips every ``tick_*`` attr (``Territory``
is ``extra="forbid"``) and ``_carry_tick_dynamics_flows`` re-applied only a subset
that OMITTED the three derived rates. Net effect: the map's profit_rate/occ/
exploitation_rate lenses read ``None`` on the web session even after a boundary
computed real values — while ``imperial_rent`` (also carried) lit up. This gate
pins that the carry re-stamps the derived rates, recomputed the same way the
engine's own writeback does (``DerivedRateCalculator`` from the carried
``county_states`` + ``national_params``).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.derived_rates import DerivedRateCalculator
from babylon.domain.economics.tick.types import (
    ClassDistribution,
    CountyEconomicState,
    NationalTickParameters,
)
from babylon.models.entities.territory import Territory
from babylon.models.enums import OperationalProfile, SectorType
from babylon.models.world_state import WorldState

WAYNE_FIPS = "26163"


def _boundary_county_and_params() -> tuple[CountyEconomicState, NationalTickParameters]:
    """A post-boundary county with capital_stock > 0 (so profit_rate < exploitation_rate)."""
    dist = ClassDistribution(
        fips=WAYNE_FIPS,
        year=2011,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.40,
        proletariat_share=0.35,
        lumpenproletariat_share=0.15,
    )
    county = CountyEconomicState(
        fips=WAYNE_FIPS,
        year=2011,
        capital_stock=1e9,
        throughput_position=0.90,
        supply_chain_depth=2.1,
        unemployment_rate=0.053,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=dist,
        phi_hour=3.50,
    )
    params = NationalTickParameters(
        year=2011,
        tau=62.0,
        gamma_basket=0.68,
        gamma_basket_raw=0.68,
        gamma_III=0.33,
        gamma_III_raw=0.33,
        tau_effective=42.16,
        v_reproduction=12.0,
        estimated=True,
    )
    return county, params


def _wayne_graph() -> object:
    """A one-territory graph whose node carries the real Wayne FIPS."""
    territory = Territory(
        id="T001",
        name="Wayne County",
        sector_type=SectorType.INDUSTRIAL,
        profile=OperationalProfile.LOW_PROFILE,
        biocapacity=500.0,
        county_fips=WAYNE_FIPS,
    )
    state = WorldState(tick=0, entities={}, territories={"T001": territory}, relationships=[])
    return state.to_graph()


def test_carry_stamps_derived_rates_at_boundary() -> None:
    """A year-boundary carry re-applies the three derived rates onto the node."""
    from game.engine_bridge import _carry_tick_dynamics_flows

    county, params = _boundary_county_and_params()
    new_graph = _wayne_graph()
    old_graph = _wayne_graph()
    ctx = {
        "_tick_dynamics": {
            "county_states": {WAYNE_FIPS: county},
            "national_params": params,
        }
    }

    _carry_tick_dynamics_flows(old_graph, new_graph, ctx)

    expected = DerivedRateCalculator().compute_county_rates(county, params)
    node = new_graph.nodes["T001"]
    assert node["tick_profit_rate"] == pytest.approx(expected.profit_rate)
    assert node["tick_occ"] == pytest.approx(expected.organic_composition)
    assert node["tick_exploitation_rate"] == pytest.approx(expected.exploitation_rate)
    # Real values, and K>0 breaks the degenerate profit==exploitation tie.
    assert node["tick_profit_rate"] is not None
    assert node["tick_profit_rate"] < node["tick_exploitation_rate"]


def test_carry_forwards_derived_rates_between_boundaries() -> None:
    """A non-boundary carry preserves the last boundary's derived rates.

    Between year boundaries no new rates are computed, but the boundary values
    must persist (like ``tick_phi_hour`` does) rather than vanish — otherwise the
    lenses would flicker to ``None`` for the 51 ticks between boundaries.
    """
    from game.engine_bridge import _carry_tick_dynamics_flows

    # old_graph carries a prior boundary's state; new_graph is post-round-trip (bare).
    old_graph = _wayne_graph()
    old_graph.update_node(
        "T001",
        tick_phi_hour=3.50,
        tick_profit_rate=3.85,
        tick_occ=0.08,
        tick_exploitation_rate=4.17,
        tick_median_wage=21.0,
        tick_employment=500_000.0,
        tick_year=2011,
    )
    new_graph = _wayne_graph()
    ctx: dict[str, object] = {}  # no _tick_dynamics => not a boundary

    _carry_tick_dynamics_flows(old_graph, new_graph, ctx)

    node = new_graph.nodes["T001"]
    assert node["tick_profit_rate"] == pytest.approx(3.85)
    assert node["tick_occ"] == pytest.approx(0.08)
    assert node["tick_exploitation_rate"] == pytest.approx(4.17)
