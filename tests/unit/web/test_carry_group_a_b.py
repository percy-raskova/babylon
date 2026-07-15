"""Wave 2 Gap-1 Backend-1: the web-bridge carry must not drop Group A/B tick_* attrs.

``write_tick_state_to_graph`` stamps the crisis-detector family (Group A:
``tick_crisis_phase``/``tick_crisis_duration``/``tick_bifurcation_score``/
``tick_wage_compression``) and the frozen-constant family (Group B:
``tick_class_distribution``/``tick_unemployment_rate``) onto territory nodes at
a year boundary (``graph_bridge.py:108-119``). ``step()``'s ``WorldState``
round-trip strips every ``tick_*`` attr (``Territory`` is ``extra="forbid"``),
and — before this fix — ``_carry_tick_dynamics_flows`` re-applied only
``tick_capital_stock``/``tick_phi_hour``/``tick_median_wage``/
``tick_profit_rate``/``tick_occ``/``tick_exploitation_rate``, omitting Group
A/B entirely. Net effect: the crisis phase/duration/bifurcation score/wage
compression/class distribution/unemployment rate would evaporate from the
web-session graph on the very first post-boundary tick — flickering null
between boundaries and resetting the crisis detector's mid-tick fallback
state. This gate pins that the carry re-stamps Group A/B, mirroring the exact
pattern W1 (Fix A, commit a8918338) used for the derived rates.
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.types import (
    BifurcationRiskMetric,
    ClassDistribution,
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
    NationalTickParameters,
)
from babylon.models.entities.territory import Territory
from babylon.models.enums import OperationalProfile, SectorType
from babylon.models.world_state import WorldState

WAYNE_FIPS = "26163"


def _boundary_county_and_params() -> tuple[CountyEconomicState, NationalTickParameters]:
    """A post-boundary county with a live (non-NORMAL) crisis/bifurcation state."""
    dist = ClassDistribution(
        fips=WAYNE_FIPS,
        year=2011,
        bourgeoisie_share=0.02,
        petit_bourgeoisie_share=0.08,
        labor_aristocracy_share=0.30,
        proletariat_share=0.40,
        lumpenproletariat_share=0.20,
    )
    county = CountyEconomicState(
        fips=WAYNE_FIPS,
        year=2011,
        capital_stock=1e9,
        throughput_position=0.90,
        supply_chain_depth=2.1,
        unemployment_rate=0.081,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=500_000.0,
        class_distribution=dist,
        phi_hour=3.50,
        crisis_state=CrisisState(
            phase=CrisisPhase.DEEP,
            consecutive_below=6,
            crisis_start_period=3,
            crisis_duration=7,
            cumulative_wage_compression=0.22,
        ),
        bifurcation_risk=BifurcationRiskMetric(
            score=-0.65,
            solidarity_density=0.4,
            legitimation=0.3,
            class_burden_ratio=0.5,
        ),
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


def test_carry_stamps_group_a_and_b_at_boundary() -> None:
    """A year-boundary carry re-applies Group A (crisis) + Group B (frozen) attrs."""
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

    node = new_graph.nodes["T001"]
    assert node["tick_crisis_phase"] == "deep"
    assert node["tick_crisis_duration"] == 7
    assert node["tick_bifurcation_score"] == pytest.approx(-0.65)
    assert node["tick_wage_compression"] == pytest.approx(0.22)
    assert node["tick_class_distribution"] == {
        "bourgeoisie": 0.02,
        "petit_bourgeoisie": 0.08,
        "labor_aristocracy": 0.30,
        "proletariat": 0.40,
        "lumpenproletariat": 0.20,
    }
    assert node["tick_unemployment_rate"] == pytest.approx(0.081)


def test_carry_forwards_group_a_and_b_between_boundaries() -> None:
    """A non-boundary carry preserves the last boundary's Group A/B attrs.

    Between year boundaries no new crisis/distribution state is computed, but
    the boundary values must persist (like ``tick_phi_hour`` does) rather than
    evaporate — otherwise the crisis detector's mid-tick fallback would reset
    to NORMAL every single non-boundary tick.
    """
    from game.engine_bridge import _carry_tick_dynamics_flows

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
        tick_crisis_phase="deep",
        tick_crisis_duration=7,
        tick_bifurcation_score=-0.65,
        tick_wage_compression=0.22,
        tick_class_distribution={
            "bourgeoisie": 0.02,
            "petit_bourgeoisie": 0.08,
            "labor_aristocracy": 0.30,
            "proletariat": 0.40,
            "lumpenproletariat": 0.20,
        },
        tick_unemployment_rate=0.081,
    )
    new_graph = _wayne_graph()
    ctx: dict[str, object] = {}  # no _tick_dynamics => not a boundary

    _carry_tick_dynamics_flows(old_graph, new_graph, ctx)

    node = new_graph.nodes["T001"]
    assert node["tick_crisis_phase"] == "deep"
    assert node["tick_crisis_duration"] == 7
    assert node["tick_bifurcation_score"] == pytest.approx(-0.65)
    assert node["tick_wage_compression"] == pytest.approx(0.22)
    assert node["tick_class_distribution"] == {
        "bourgeoisie": 0.02,
        "petit_bourgeoisie": 0.08,
        "labor_aristocracy": 0.30,
        "proletariat": 0.40,
        "lumpenproletariat": 0.20,
    }
    assert node["tick_unemployment_rate"] == pytest.approx(0.081)
