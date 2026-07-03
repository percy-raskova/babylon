"""Spec 061 T077 / FR-023 / SC-004: action resolution is RNG-seed deterministic.

``EngineBridge.resolve_tick()`` threads ``session.rng_seed`` into the
``SimulationConfig`` it passes to the engine ``step()`` function. With
the same seed and the same action sequence, two replays must produce
byte-identical engine state.

This file pins three contract properties of the determinism wiring:

1. ``_fetch_session_rng_seed_from_pool`` reads ``rng_seed`` from
   ``game_session`` correctly (T080 helper).
2. The bridge constructs ``SimulationConfig(rng_seed=N)`` using the
   value returned by the helper (not a hardcoded default).
3. The fetch helper falls back to 0 gracefully when the pool is None
   or the query fails — non-fatal during transient outages.

End-to-end byte-identity (two full replays of the same scenario)
requires a live engine + DB, gated on T125 staging readiness; the
indirect assertions here exercise the same wiring without the full
scenario cost.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import networkx as nx
import pytest

from babylon.engine.graph import BabylonGraph

pytestmark = pytest.mark.integration


class TestSimulationConfigAcceptsRngSeed:
    """The engine ``SimulationConfig`` exposes an ``rng_seed`` field."""

    def test_simulation_config_has_rng_seed_field(self) -> None:
        from babylon.models.config import SimulationConfig

        config = SimulationConfig(rng_seed=12345)
        assert config.rng_seed == 12345

    def test_simulation_config_rng_seed_defaults_to_zero(self) -> None:
        from babylon.models.config import SimulationConfig

        config = SimulationConfig()
        assert config.rng_seed == 0, (
            "spec 061 added rng_seed: int = Field(default=0) to SimulationConfig"
        )

    def test_two_configs_with_same_seed_are_equal(self) -> None:
        from babylon.models.config import SimulationConfig

        a = SimulationConfig(rng_seed=42)
        b = SimulationConfig(rng_seed=42)
        # Pydantic equality is structural — same seed → same SimulationConfig.
        assert a.rng_seed == b.rng_seed


class TestFetchSessionRngSeedFromPool:
    """T080 / FR-024: the helper reads ``rng_seed`` from game_session."""

    def test_returns_seed_from_pool_query(self) -> None:
        from web.game.engine_bridge import _fetch_session_rng_seed_from_pool

        cursor = MagicMock()
        cursor.fetchone = MagicMock(return_value=(7777,))
        cursor.__enter__ = lambda _self: cursor
        cursor.__exit__ = lambda _self, *_args: False  # noqa: ARG005

        conn = MagicMock()
        conn.cursor = MagicMock(return_value=cursor)
        conn.__enter__ = lambda _self: conn
        conn.__exit__ = lambda _self, *_args: False  # noqa: ARG005

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        seed = _fetch_session_rng_seed_from_pool(pool, uuid4())
        assert seed == 7777
        cursor.execute.assert_called_once()
        assert "rng_seed" in cursor.execute.call_args.args[0]

    def test_falls_back_to_zero_on_none_pool(self) -> None:
        """A None pool (no Postgres bridge yet) returns 0 instead of crashing."""
        from web.game.engine_bridge import _fetch_session_rng_seed_from_pool

        seed = _fetch_session_rng_seed_from_pool(None, uuid4())
        assert seed == 0

    def test_falls_back_to_zero_on_connection_error(self) -> None:
        """Connection failures are logged and the helper returns 0."""
        from web.game.engine_bridge import _fetch_session_rng_seed_from_pool

        pool = MagicMock()
        pool.connection = MagicMock(side_effect=ConnectionRefusedError("simulated"))

        seed = _fetch_session_rng_seed_from_pool(pool, uuid4())
        assert seed == 0

    def test_falls_back_to_zero_when_row_missing(self) -> None:
        """Querying a non-existent session UUID returns 0."""
        from web.game.engine_bridge import _fetch_session_rng_seed_from_pool

        cursor = MagicMock()
        cursor.fetchone = MagicMock(return_value=None)
        cursor.__enter__ = lambda _self: cursor
        cursor.__exit__ = lambda _self, *_args: False  # noqa: ARG005

        conn = MagicMock()
        conn.cursor = MagicMock(return_value=cursor)
        conn.__enter__ = lambda _self: conn
        conn.__exit__ = lambda _self, *_args: False  # noqa: ARG005

        pool = MagicMock()
        pool.connection = MagicMock(return_value=conn)

        seed = _fetch_session_rng_seed_from_pool(pool, uuid4())
        assert seed == 0


def _empty_state_and_graph() -> tuple[Any, nx.DiGraph]:
    from babylon.models.world_state import WorldState

    graph: nx.DiGraph = BabylonGraph()
    graph.graph["tick"] = 0
    state = WorldState.from_graph(graph, tick=0)
    return state, graph


class TestResolveTickThreadsRngSeed:
    """``resolve_tick`` calls ``step()`` with a SimulationConfig built from the session seed."""

    def test_step_receives_simulation_config_with_session_seed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The seed reaches the engine via SimulationConfig.rng_seed (FR-024)."""
        from web.game.engine_bridge import EngineBridge

        captured_config: list[Any] = []

        def _capturing_step(state, config, persistent_context=None, defines=None):  # noqa: ARG001
            captured_config.append(config)
            return state.model_copy(update={"tick": state.tick + 1})

        monkeypatch.setattr("web.game.engine_bridge.step", _capturing_step)
        monkeypatch.setattr(
            "web.game.engine_bridge._compute_traps",
            lambda _state, _session_id: None,
        )
        monkeypatch.setattr(
            "web.game.engine_bridge._fetch_session_rng_seed_from_pool",
            lambda _pool, _session_id: 9999,
        )

        persistence = MagicMock()
        persistence.get_pending_turns = MagicMock(return_value=[])
        persistence.persist_tick = MagicMock()
        persistence.get_metadata = MagicMock(return_value=None)

        bridge = EngineBridge(persistence=persistence)
        monkeypatch.setattr(
            bridge,
            "hydrate_state",
            lambda _session_id, tick=None: _empty_state_and_graph(),  # noqa: ARG005
        )

        bridge.resolve_tick(uuid4())

        assert len(captured_config) == 1, "step() must be called exactly once per tick"
        sim_config = captured_config[0]
        assert sim_config.rng_seed == 9999, (
            f"step() received rng_seed={sim_config.rng_seed}; "
            "expected 9999 (the value the helper returned). "
            "If the test fails with rng_seed=0, the bridge is "
            "no longer threading the session seed through."
        )

    def test_two_resolves_with_same_seed_produce_equal_configs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SC-004 byte-identity foundation: two configs with the same fetched
        seed are structurally equal."""
        from web.game.engine_bridge import EngineBridge

        captured: list[Any] = []

        def _capturing_step(state, config, persistent_context=None, defines=None):  # noqa: ARG001
            captured.append(config)
            return state.model_copy(update={"tick": state.tick + 1})

        monkeypatch.setattr("web.game.engine_bridge.step", _capturing_step)
        monkeypatch.setattr(
            "web.game.engine_bridge._compute_traps",
            lambda _state, _session_id: None,
        )
        monkeypatch.setattr(
            "web.game.engine_bridge._fetch_session_rng_seed_from_pool",
            lambda _pool, _session_id: 42,
        )

        persistence = MagicMock()
        persistence.get_pending_turns = MagicMock(return_value=[])
        persistence.persist_tick = MagicMock()
        persistence.get_metadata = MagicMock(return_value=None)

        bridge = EngineBridge(persistence=persistence)
        monkeypatch.setattr(
            bridge,
            "hydrate_state",
            lambda _session_id, tick=None: _empty_state_and_graph(),  # noqa: ARG005
        )

        bridge.resolve_tick(uuid4())
        bridge.resolve_tick(uuid4())

        assert len(captured) == 2
        assert captured[0].rng_seed == captured[1].rng_seed == 42
