"""Playability Spine Task 20 (spec-116 4d.5): serialize Groups C/D declared-dark.

``write_tick_state_to_graph`` stamps the circulation family (Group C, Feature
023) and the financial-distribution family (Group D, Feature 024) onto
territory nodes at a year boundary (``graph_bridge.py:128-197``), but both
families were in NEITHER arm of ``_carry_tick_dynamics_flows`` — so on the
web path they evaporated on the very next ``WorldState`` round-trip
(``Territory`` is ``extra="forbid"``) — and ``_serialize_territory`` never
read them. The gating services (``turnover_profile_source`` /
``interest_calculator``) are still unwired, so the carried values are the
write-site FALLBACK CONSTANTS: declared-dark (the SEAM_REGISTRY rows were
STRUCTURALLY_IMPOSSIBLE, relabeled NOT_YET_COMPUTED by the Task 20 de-mock
correction — computable via a FRED-backed sibling implementation, just not
wired into this pipeline yet — never relabeled live) — but the wire must
exist and be honest so that wiring the services later lights the data with
zero serialization work.
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

#: wire key -> the value graph_bridge.py's fallback expressions produce for a
#: default CountyEconomicState (circulation defaults + absent financial
#: state). tick_housing_fictitious_fraction is the one honest-None fallback.
GROUP_C_D_FALLBACKS: dict[str, object] = {
    "tick_realization_crisis": False,
    "tick_turnover_crisis": False,
    "tick_reproduction_crisis": False,
    "tick_interest_burden": 0.0,
    "tick_ground_rent": 0.0,
    "tick_rentier_share": 0.0,
    "tick_profit_of_enterprise": 0.0,
    "tick_financialization_share": 0.0,
    "tick_accumulated_debt": 0.0,
    "tick_claims_exceed_surplus": False,
    "tick_housing_fictitious_fraction": None,
    "tick_financial_crisis_signals": 0,
}


def _boundary_county_and_params() -> tuple[CountyEconomicState, NationalTickParameters]:
    """A post-boundary county (default circulation state, absent financial state)."""
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
        real_wage_deflator=0.87,
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


def test_boundary_carry_stamps_group_c_and_d() -> None:
    """A year-boundary carry re-applies Groups C/D — write-site expressions
    mirrored byte-for-byte, fallback constants included."""
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
    circuit = county.circulation_state.circuit_state
    assert node["tick_liquidity_ratio"] == pytest.approx(circuit.liquidity_ratio)
    assert node["tick_commodity_overhang"] == pytest.approx(circuit.commodity_overhang)
    assert (
        node["tick_replacement_cycle"]
        == county.circulation_state.depreciation_fund.replacement_cycle_position.value
    )
    assert (
        node["tick_inventory_diagnosis"]
        == county.circulation_state.inventory_state.inventory_problem.value
    )
    for key, expected in GROUP_C_D_FALLBACKS.items():
        assert node[key] == expected, f"{key} must carry the write-site fallback constant"


def test_non_boundary_carry_forwards_group_c_and_d() -> None:
    """Between boundaries the last boundary's Group C/D values persist
    byte-identical (like tick_phi_hour), never evaporating to a flicker."""
    from game.engine_bridge import _carry_tick_dynamics_flows

    old_graph = _wayne_graph()
    old_graph.update_node(
        "T001",
        tick_phi_hour=3.50,
        tick_median_wage=21.0,
        tick_employment=500_000.0,
        tick_year=2011,
        tick_liquidity_ratio=0.42,
        tick_commodity_overhang=0.13,
        tick_replacement_cycle="mid_cycle",
        tick_inventory_diagnosis="balanced",
        tick_realization_crisis=True,
        tick_turnover_crisis=False,
        tick_reproduction_crisis=True,
        tick_interest_burden=120.5,
        tick_ground_rent=44.0,
        tick_rentier_share=0.31,
        tick_profit_of_enterprise=-12.0,
        tick_financialization_share=0.27,
        tick_accumulated_debt=9_000.0,
        tick_claims_exceed_surplus=True,
        tick_housing_fictitious_fraction=0.55,
        tick_financial_crisis_signals=3,
    )
    new_graph = _wayne_graph()
    ctx: dict[str, object] = {}  # no _tick_dynamics => not a boundary

    _carry_tick_dynamics_flows(old_graph, new_graph, ctx)

    node = new_graph.nodes["T001"]
    assert node["tick_liquidity_ratio"] == pytest.approx(0.42)
    assert node["tick_commodity_overhang"] == pytest.approx(0.13)
    assert node["tick_replacement_cycle"] == "mid_cycle"
    assert node["tick_inventory_diagnosis"] == "balanced"
    assert node["tick_realization_crisis"] is True
    assert node["tick_reproduction_crisis"] is True
    assert node["tick_interest_burden"] == pytest.approx(120.5)
    assert node["tick_ground_rent"] == pytest.approx(44.0)
    assert node["tick_rentier_share"] == pytest.approx(0.31)
    # Negative profit-of-enterprise is a debt-spiral signal — never clamp.
    assert node["tick_profit_of_enterprise"] == pytest.approx(-12.0)
    assert node["tick_financialization_share"] == pytest.approx(0.27)
    assert node["tick_accumulated_debt"] == pytest.approx(9_000.0)
    assert node["tick_claims_exceed_surplus"] is True
    assert node["tick_housing_fictitious_fraction"] == pytest.approx(0.55)
    assert node["tick_financial_crisis_signals"] == 3


def test_serialize_territory_emits_group_c_and_d_wire_keys() -> None:
    """The 16 keys ride every territory row; un-stamped attrs are honest None."""
    from game.engine_bridge import _serialize_territory

    territory = Territory(
        id="T001",
        name="Wayne County",
        sector_type=SectorType.INDUSTRIAL,
        profile=OperationalProfile.LOW_PROFILE,
        biocapacity=500.0,
        county_fips=WAYNE_FIPS,
    )
    state = WorldState(tick=0, entities={}, territories={"T001": territory}, relationships=[])
    graph = state.to_graph()
    graph.update_node("T001", tick_liquidity_ratio=0.42, tick_financial_crisis_signals=2)

    row = _serialize_territory(territory, graph=graph)

    assert row["tick_liquidity_ratio"] == pytest.approx(0.42)
    assert row["tick_financial_crisis_signals"] == 2
    for key in (
        "tick_commodity_overhang",
        "tick_replacement_cycle",
        "tick_inventory_diagnosis",
        "tick_realization_crisis",
        "tick_turnover_crisis",
        "tick_reproduction_crisis",
        "tick_interest_burden",
        "tick_ground_rent",
        "tick_rentier_share",
        "tick_profit_of_enterprise",
        "tick_financialization_share",
        "tick_accumulated_debt",
        "tick_claims_exceed_surplus",
        "tick_housing_fictitious_fraction",
    ):
        assert row[key] is None, f"{key} must be honest None when un-stamped, never a default"
