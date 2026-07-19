"""U9.5 (repaired): the reserve-army downturn signal ``s_r`` is read from the
tick's own county states — employment-weighted U-3 unemployment, sorted-FIPS,
honest absence — NOT from ``tick_``-prefixed graph attrs, which
``state.to_graph()`` strips every tick and re-stamps only AFTER the financial
layer runs (the timing hole that structurally zeroed the prior graph reading).

The economy-wide rate of profit ``r`` moved to
``TickDynamicsSystem._economy_wide_profit_rate`` (it must source the realized
surplus/profit-rate tensors, not the county MELT quantities whose
``capital_stock`` is 0); it is pinned by the full-step anti-inertness sentinels
in ``test_system.py`` and the live ``test_vol3_surplus_distribution_live.py``.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.economics.dynamics.types import ClassDistribution
from babylon.domain.economics.tick.graph_bridge import reserve_army_signal
from babylon.domain.economics.tick.types import CountyEconomicState


def _county(fips: str, *, unemployment_rate: float, employment: float) -> CountyEconomicState:
    return CountyEconomicState(
        fips=fips,
        year=2015,
        capital_stock=0.0,  # deliberately 0 — s_r must NOT weight by capital
        throughput_position=1.0,
        supply_chain_depth=2.0,
        unemployment_rate=unemployment_rate,
        u6_rate=0.10,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=21.0,
        employment=employment,
        class_distribution=ClassDistribution(
            fips=fips,
            year=2015,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        ),
        phi_hour=0.0,
    )


@pytest.mark.unit
class TestReserveArmySignal:
    def test_below_reference_is_zero(self) -> None:
        states = {"26163": _county("26163", unemployment_rate=0.05, employment=100.0)}
        assert reserve_army_signal(states, GameDefines.load_default()) == 0.0

    def test_scales_between_reference_and_one(self) -> None:
        # ref=0.08: u3 0.54 -> (0.54-0.08)/(1-0.08) = 0.5.
        states = {"26163": _county("26163", unemployment_rate=0.54, employment=100.0)}
        assert reserve_army_signal(states, GameDefines.load_default()) == pytest.approx(0.5)

    def test_employment_weighted_not_unweighted(self) -> None:
        # A tiny 100-worker county at 0.90 must NOT swing the national reading
        # like the 1,000,000-worker county at 0.10 does: the employment-weighted
        # mean is (0.10*1e6 + 0.90*100)/(1e6+100) ~= 0.1001, well below 0.08? no —
        # above 0.08, so s_r = (0.1001-0.08)/0.92 ~= 0.0219, NOT the unweighted
        # mean 0.50 -> 0.457.
        states = {
            "26163": _county("26163", unemployment_rate=0.10, employment=1_000_000.0),
            "26099": _county("26099", unemployment_rate=0.90, employment=100.0),
        }
        signal = reserve_army_signal(states, GameDefines.load_default())
        assert signal == pytest.approx((0.1001 - 0.08) / 0.92, abs=1e-3)
        assert signal < 0.05  # nowhere near the unweighted-mean artifact

    def test_no_labor_force_is_zero(self) -> None:
        states = {"26163": _county("26163", unemployment_rate=0.54, employment=0.0)}
        assert reserve_army_signal(states, GameDefines.load_default()) == 0.0

    def test_empty_county_states_is_zero(self) -> None:
        assert reserve_army_signal({}, GameDefines.load_default()) == 0.0
