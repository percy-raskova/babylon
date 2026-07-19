"""U9.5: domain-side extraction of the average rate of profit r and the
reserve-army downturn signal s_r from the shared graph (capital-weighted,
sorted-id, honest absence)."""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.economics.tick.graph_bridge import (
    economy_wide_profit_rate,
    reserve_army_signal,
)
from babylon.topology import BabylonGraph


def _graph_with(territories: list[dict[str, object]]) -> BabylonGraph:
    g = BabylonGraph()
    for i, attrs in enumerate(territories):
        g.add_node(f"terr_{i}", _node_type="territory", **attrs)
    return g


@pytest.mark.unit
class TestEconomyWideProfitRate:
    def test_capital_weighted_not_unweighted(self) -> None:
        # 0.10 @ K=100 and 0.20 @ K=900 -> weighted 0.19, not the mean 0.15.
        g = _graph_with(
            [
                {"active": True, "tick_profit_rate": 0.10, "tick_capital_stock": 100.0},
                {"active": True, "tick_profit_rate": 0.20, "tick_capital_stock": 900.0},
            ]
        )
        assert economy_wide_profit_rate(g) == pytest.approx(0.19)

    def test_no_rate_present_is_none(self) -> None:
        g = _graph_with([{"active": True, "tick_capital_stock": 100.0}])
        assert economy_wide_profit_rate(g) is None

    def test_inactive_territories_are_excluded(self) -> None:
        g = _graph_with(
            [
                {"active": False, "tick_profit_rate": 0.99, "tick_capital_stock": 1e9},
                {"active": True, "tick_profit_rate": 0.05, "tick_capital_stock": 10.0},
            ]
        )
        assert economy_wide_profit_rate(g) == pytest.approx(0.05)


@pytest.mark.unit
class TestReserveArmySignal:
    def test_below_reference_is_zero(self) -> None:
        g = _graph_with([{"active": True, "reserve_ratio": 0.05, "tick_capital_stock": 100.0}])
        assert reserve_army_signal(g, GameDefines.load_default()) == 0.0

    def test_scales_between_reference_and_one(self) -> None:
        # ref=0.08: reserve 0.54 -> (0.54-0.08)/(1-0.08) = 0.5.
        g = _graph_with([{"active": True, "reserve_ratio": 0.54, "tick_capital_stock": 100.0}])
        assert reserve_army_signal(g, GameDefines.load_default()) == pytest.approx(0.5)

    def test_no_reserve_data_is_zero(self) -> None:
        g = _graph_with([{"active": True, "tick_capital_stock": 100.0}])
        assert reserve_army_signal(g, GameDefines.load_default()) == 0.0
