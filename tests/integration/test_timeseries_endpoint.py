"""Spec 061 T044 / FR-026: /api/games/<id>/timeseries/ shape.

Verifies the bridge's ``get_game_timeseries`` reshape from the
``tick_summary`` rows into the six named arrays the v2 Briefing +
Analysis pages chart. Uses an in-process stub persistence (no live DB
required) so the test stays in the unit-tier even though the spec
catalogs it under tests/integration/.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from web.game.engine_bridge import EngineBridge


class _StubPersistence:
    """Minimal persistence surface satisfying the bridge contract."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def query_tick_summary_series(self, _session_id: uuid.UUID) -> list[dict[str, Any]]:
        return self._rows


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
