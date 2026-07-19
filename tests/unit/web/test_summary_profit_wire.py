"""spec-116 4d.9: the TopBar PROFIT chip is WIRED (not removed).

``get_game_summary`` hardcoded ``profit_rate: None`` behind a stale docstring
("the engine computes no c/v/s decomposition on the live graph") written
before ``_mean_territory_attr`` existed — while ``get_economy_dashboard``
served the real mean one method below. Honest ``None`` persists until the
first year boundary (tick 52 at weekly cadence): the chip's pre-boundary
"no data" is CORRECT, never fabricated (Constitution III.11).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from babylon.topology.graph import BabylonGraph
from game.engine_bridge import EngineBridge


def _bridge_and_state() -> tuple[EngineBridge, MagicMock]:
    """A bridge with list-returning event queries and an empty-world state.

    G4: ``organizations`` carries a real player org with BOTH veil
    threshold nodes acquired (Tier 2, fully unlocked) — this suite is about
    the ``profit_rate`` WIRING, not veil gating (that's ``TestEconomyDashboardVeil``'s
    job), so it must keep reading real numbers post-boundary.
    """
    persistence = MagicMock()
    persistence.query_tick_events.return_value = []
    bridge = EngineBridge(persistence)
    state = MagicMock()
    state.tick = 60
    state.entities = {}
    state.territories = {}
    state.organizations = {
        "org-player": MagicMock(acquired_doctrine_ids=("class_consciousness", "trade_unionism"))
    }
    state.player_org_id = "org-player"
    state.economy = None
    return bridge, state


@pytest.mark.unit
class TestSummaryProfitRate:
    def test_profit_rate_is_the_territory_mean_after_a_boundary(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T1", node_type="territory", tick_profit_rate=0.10)
        graph.add_node("T2", node_type="territory", tick_profit_rate=0.20)
        bridge, state = _bridge_and_state()

        with patch.object(bridge, "hydrate_state", return_value=(state, graph)):
            out = bridge.get_game_summary(uuid.uuid4())

        assert out["profit_rate"] == pytest.approx(0.15)

    def test_profit_rate_stays_none_before_first_boundary(self) -> None:
        graph = BabylonGraph()
        graph.add_node("T1", node_type="territory")
        bridge, state = _bridge_and_state()

        with patch.object(bridge, "hydrate_state", return_value=(state, graph)):
            out = bridge.get_game_summary(uuid.uuid4())

        assert out["profit_rate"] is None
