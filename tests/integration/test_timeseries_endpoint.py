"""Spec 061 T044 / FR-026: /api/games/<id>/timeseries/ shape.

Verifies the bridge's ``get_game_timeseries`` reshape from the
``tick_summary`` rows into the six named arrays the v2 Briefing +
Analysis pages chart. Uses an in-process stub persistence (no live DB
required) so the test stays in the unit-tier even though the spec
catalogs it under tests/integration/.

G4 (veil-leak closure): ``get_game_timeseries`` now resolves the player
org's Veil-of-Money tier via a second, best-effort ``hydrate_graph`` call
(``web/game/veil.py``'s module docstring; ``EngineBridge.get_game_
timeseries``'s docstring). ``_StubPersistence`` defaults ``hydrate_graph``
to a FULLY-UNLOCKED (Tier 2) graph so every pre-existing assertion below —
about the reshape/gap-handling logic, not the veil — keeps reading real
numbers unchanged; ``TestVeilGating`` exercises the gate itself with an
explicit ``acquired_doctrine_ids=()`` stub.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from web.game.engine_bridge import EngineBridge, _build_initial_state_for_scenario


class _StubPersistence:
    """Minimal persistence surface satisfying the bridge contract.

    ``acquired_doctrine_ids`` defaults to BOTH veil threshold nodes held
    (Tier 2, fully unlocked) — see module docstring.
    """

    def __init__(
        self,
        rows: list[dict[str, Any]],
        *,
        acquired_doctrine_ids: tuple[str, ...] = ("class_consciousness", "trade_unionism"),
    ) -> None:
        self._rows = rows
        self._acquired_doctrine_ids = acquired_doctrine_ids

    def query_tick_summary_series(self, _session_id: uuid.UUID) -> list[dict[str, Any]]:
        return self._rows

    def hydrate_graph(self, *, tick: int | None, session_id: uuid.UUID) -> Any:
        state = _build_initial_state_for_scenario("default")
        org_id = state.player_org_id
        assert org_id is not None, "default scenario must seed a player_org_id"
        org = state.organizations[org_id].model_copy(
            update={"acquired_doctrine_ids": self._acquired_doctrine_ids}
        )
        state = state.model_copy(update={"organizations": {**state.organizations, org_id: org}})
        return state.to_graph()


class TestTimeseriesShape:
    """FR-026 + contracts/timeseries.yaml shape checks."""

    def test_returns_six_metric_arrays(self) -> None:
        rows = [
            {
                "tick": t,
                "imperial_rent": 100.0 + t,
                "avg_consciousness": 0.4 + (t * 0.01),
                "solidarity_edge_count": 5 + t,
                "total_heat": 0.3 + (t * 0.02),
                "total_wealth": 1000.0 - (t * 5),
                "total_biocapacity": 0.95 - (t * 0.01),
            }
            for t in range(4)
        ]
        bridge = EngineBridge(persistence=_StubPersistence(rows))
        out = bridge.get_game_timeseries(uuid.uuid4())

        for key in (
            "ticks",
            "imperial_rent",
            "consciousness",
            "solidarity",
            "heat",
            "wealth",
            "biocapacity",
        ):
            assert key in out, f"missing array {key!r}"
            assert isinstance(out[key], list)
            assert len(out[key]) == 4

        assert out["ticks"] == [0, 1, 2, 3]
        assert out["imperial_rent"][0] == 100.0
        assert out["consciousness"][3] == pytest.approx(0.43)

    def test_missing_columns_become_none(self) -> None:
        """When a tick_summary row lacks an optional column, the array
        slot is None rather than raising or substituting 0."""
        rows = [
            {"tick": 0, "imperial_rent": None, "avg_consciousness": 0.5},
        ]
        bridge = EngineBridge(persistence=_StubPersistence(rows))
        out = bridge.get_game_timeseries(uuid.uuid4())
        assert out["imperial_rent"] == [None]
        assert out["consciousness"] == [0.5]
        # Columns absent from the row become None too.
        assert out["wealth"] == [None]
        assert out["biocapacity"] == [None]

    def test_empty_session_returns_empty_arrays(self) -> None:
        bridge = EngineBridge(persistence=_StubPersistence([]))
        out = bridge.get_game_timeseries(uuid.uuid4())
        for key in ("ticks", "imperial_rent", "consciousness", "solidarity"):
            assert out[key] == []

    def test_persistence_without_query_method_returns_empty(self) -> None:
        """SQLite-backed RuntimeDatabase doesn't implement query_tick_summary_series.
        get_game_timeseries must degrade gracefully (empty arrays) rather than crash."""

        class _NoQueryPersistence:
            pass

        bridge = EngineBridge(persistence=_NoQueryPersistence())  # type: ignore[arg-type]
        out = bridge.get_game_timeseries(uuid.uuid4())
        assert out["ticks"] == []


class TestScissorsSeries:
    """Program 23 (ADR077): the scissors arrays ride the same payload."""

    def test_scissors_arrays_exp_map_the_persisted_logs(self) -> None:
        import math

        rows = [
            {
                "tick": 0,
                "total_v": 10.0,
                "total_s": 3.0,
                "profit_rate": 0.05,
                "price_log": 0.0,
                "fictitious_log": 0.4,
            },
            {
                "tick": 1,
                "total_v": 11.0,
                "total_s": 3.5,
                "profit_rate": 0.048,
                "price_log": 0.2,
                "fictitious_log": 0.9,
            },
        ]
        bridge = EngineBridge(persistence=_StubPersistence(rows))
        out = bridge.get_game_timeseries(uuid.uuid4())

        assert out["value_produced"] == [10.0, 11.0]
        assert out["surplus"] == [3.0, 3.5]
        assert out["profit_rate"] == [0.05, 0.048]
        assert out["price_index"] == [pytest.approx(1.0), pytest.approx(math.exp(0.2))]
        assert out["fictitious_ratio"][1] == pytest.approx(math.exp(0.9))

    def test_absent_axis_charts_as_gap_not_fabricated_unity(self) -> None:
        rows = [{"tick": 0, "price_log": None, "fictitious_log": None}]
        bridge = EngineBridge(persistence=_StubPersistence(rows))
        out = bridge.get_game_timeseries(uuid.uuid4())
        assert out["price_index"] == [None]
        assert out["fictitious_ratio"] == [None]
        assert out["value_produced"] == [None]
        assert out["market_corrections"] == [None]

    def test_correction_ledger_rides_the_payload(self) -> None:
        """ADR078: cumulative snap counts; the cockpit marks increments."""
        rows = [
            {"tick": 0, "market_corrections": 0},
            {"tick": 1, "market_corrections": 1},
            {"tick": 2, "market_corrections": 1},
        ]
        bridge = EngineBridge(persistence=_StubPersistence(rows))
        out = bridge.get_game_timeseries(uuid.uuid4())
        assert out["market_corrections"] == [0, 1, 1]


class TestCrisisSeries:
    """Task 19 (spec-116 4d.5): the crisis/bifurcation history arrays."""

    def test_series_arrays_ride_the_payload(self) -> None:
        rows = [
            {
                "tick": 0,
                "crisis_pop_share": None,
                "bifurcation_score_mean": None,
                "wage_compression_mean": None,
                "capital_stock_total": None,
                "unemployment_rate_mean": None,
            },
            {
                "tick": 1,
                "crisis_pop_share": 0.75,
                "bifurcation_score_mean": -0.3,
                "wage_compression_mean": 0.15,
                "capital_stock_total": 3e9,
                "unemployment_rate_mean": 0.0875,
            },
        ]
        bridge = EngineBridge(persistence=_StubPersistence(rows))
        out = bridge.get_game_timeseries(uuid.uuid4())

        assert out["crisis_pop_share"] == [None, 0.75]
        assert out["bifurcation_score_mean"] == [None, -0.3]
        assert out["wage_compression_mean"] == [None, 0.15]
        assert out["capital_stock_total"] == [None, 3e9]
        assert out["unemployment_rate_mean"] == [None, 0.0875]

    def test_rows_without_series_columns_chart_as_gaps(self) -> None:
        """Pre-0035 rows (rollout skew) become None slots, never 0.0."""
        rows = [{"tick": 0, "imperial_rent": 1.0}]
        bridge = EngineBridge(persistence=_StubPersistence(rows))
        out = bridge.get_game_timeseries(uuid.uuid4())
        assert out["crisis_pop_share"] == [None]
        assert out["unemployment_rate_mean"] == [None]


@pytest.mark.unit
class TestVeilGating:
    """G4: the Veil of Money masks this endpoint's value-axis arrays
    server-side, independent of the reshape logic every other test class
    in this file exercises against a fully-unlocked stub."""

    _ROWS = [
        {
            "tick": 0,
            "imperial_rent": 100.0,
            "total_v": 10.0,
            "total_s": 3.0,
            "profit_rate": 0.05,
            "price_log": 0.2,
            "fictitious_log": 0.4,
            "market_corrections": 1,
        }
    ]

    def test_tier_zero_masks_tier1_and_tier2_arrays(self) -> None:
        bridge = EngineBridge(persistence=_StubPersistence(self._ROWS, acquired_doctrine_ids=()))
        out = bridge.get_game_timeseries(uuid.uuid4())

        assert out["imperial_rent"] == [None]
        assert out["value_produced"] == [None]
        assert out["surplus"] == [None]
        assert out["profit_rate"] == [None]
        assert out["price_index"] == [None]
        assert out["fictitious_ratio"] == [None]
        assert out["market_corrections"] == [None]
        # Never touched — non-value-axis fields pass through regardless.
        assert out["ticks"] == [0]

    def test_tier_one_unlocks_tier1_but_not_tier2(self) -> None:
        bridge = EngineBridge(
            persistence=_StubPersistence(self._ROWS, acquired_doctrine_ids=("class_consciousness",))
        )
        out = bridge.get_game_timeseries(uuid.uuid4())

        assert out["imperial_rent"] == [100.0]
        assert out["value_produced"] == [10.0]
        assert out["profit_rate"] == [0.05]
        # Scissors still veiled at Tier 1.
        assert out["price_index"] == [None]
        assert out["market_corrections"] == [None]

    def test_tier_two_unlocks_everything(self) -> None:
        bridge = EngineBridge(persistence=_StubPersistence(self._ROWS))
        out = bridge.get_game_timeseries(uuid.uuid4())

        assert out["imperial_rent"] == [100.0]
        assert out["price_index"] == [pytest.approx(1.2214027581601699)]
        assert out["market_corrections"] == [1]

    def test_hydrate_graph_failure_fails_closed_not_open(self) -> None:
        """A persistence that cannot resolve a tier at all (no
        ``hydrate_graph``) must mask, never leak — the same "deny on
        ambiguity" default the spatial fog uses."""

        class _NoGraphPersistence:
            def query_tick_summary_series(self, _session_id: uuid.UUID) -> list[dict[str, Any]]:
                return TestVeilGating._ROWS

        bridge = EngineBridge(persistence=_NoGraphPersistence())  # type: ignore[arg-type]
        out = bridge.get_game_timeseries(uuid.uuid4())

        assert out["imperial_rent"] == [None]
        assert out["price_index"] == [None]
