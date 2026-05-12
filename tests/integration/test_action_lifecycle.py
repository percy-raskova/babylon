"""Spec 061 T075 + T076 / FR-021 + FR-022: action submit → resolve → result.

The action lifecycle has three phases:

1. **Submit** (T075 / FR-021): ``EngineBridge.submit_action()`` performs an
   affordability check and writes a turn row via ``persistence.submit_turn``.
   The turn is unresolved at this point.
2. **Resolve** (T076 / FR-022): ``EngineBridge.resolve_tick()`` reads
   pending turns, runs the engine ``step()`` with the player actions
   injected via ``persistent_context``, and writes ``ActionResult``
   rows with computed deltas. The original turn rows are marked
   ``resolved=True``.

The engine ``step`` function itself is pre-existing engine code, not new
spec-061 work. These tests verify the *bridge wiring* — that submit and
resolve correctly delegate to persistence with the right arguments.
A live-DB end-to-end harness would also exercise the engine's actual
delta computation, but that requires a seeded scenario, a running
engine, and a real ``RuntimePersistence`` implementation — gated on
T125 staging readiness.

Gated behind ``mise run test:int`` via ``pytest.mark.integration``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import networkx as nx
import pytest

pytestmark = pytest.mark.integration


def _empty_state_and_graph() -> tuple[Any, nx.DiGraph]:
    """A WorldState with zero entities, used to skip the affordability check."""
    from babylon.models.world_state import WorldState

    graph: nx.DiGraph = nx.DiGraph()
    graph.graph["tick"] = 0
    state = WorldState.from_graph(graph, tick=0)
    return state, graph


def _make_bridge(monkeypatch: pytest.MonkeyPatch, *, pending_actions=None) -> Any:
    """Build an EngineBridge with hydrate_state stubbed and persistence mocked."""
    from web.game.engine_bridge import EngineBridge

    persistence = MagicMock()
    persistence.submit_turn = MagicMock(return_value=1234)
    persistence.get_pending_turns = MagicMock(return_value=pending_actions or [])
    persistence.persist_tick = MagicMock()
    persistence.get_metadata = MagicMock(return_value=None)

    bridge = EngineBridge(persistence=persistence)
    monkeypatch.setattr(
        bridge,
        "hydrate_state",
        lambda _session_id, tick=None: _empty_state_and_graph(),  # noqa: ARG005
    )
    return bridge


class TestSubmitActionPersists:
    """T075 / FR-021: ``submit_action`` writes a turn row via persistence."""

    def test_submit_calls_persistence_submit_turn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The bridge delegates to ``persistence.submit_turn`` and returns the row id."""
        bridge = _make_bridge(monkeypatch)
        session_id = uuid4()

        turn_id = bridge.submit_action(
            session_id=session_id,
            tick=0,
            org_id="org-test",
            verb="educate",
            target_id="terr-test",
        )

        # Returned row id is forwarded from persistence.submit_turn
        assert turn_id == 1234

        # persistence.submit_turn was called with the structured kwargs
        bridge._persistence.submit_turn.assert_called_once()  # type: ignore[attr-defined]
        kwargs = bridge._persistence.submit_turn.call_args.kwargs  # type: ignore[attr-defined]
        assert kwargs["session_id"] == session_id
        assert kwargs["tick"] == 0
        assert kwargs["org_id"] == "org-test"
        assert kwargs["verb"] == "educate"
        assert kwargs["target_id"] == "terr-test"

    def test_submit_records_in_action_history(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The submit path appends to in-memory action history for trap detection."""
        from web.game.engine_bridge import _session_action_history

        bridge = _make_bridge(monkeypatch)
        session_id = uuid4()
        _session_action_history.pop(session_id, None)

        bridge.submit_action(
            session_id=session_id,
            tick=0,
            org_id="org-test",
            verb="educate",
            target_id="terr-test",
        )

        history = _session_action_history.get(session_id, [])
        assert len(history) >= 1
        assert history[-1]["verb"] == "educate"
        assert history[-1]["org_id"] == "org-test"
        assert history[-1]["target_id"] == "terr-test"


class TestResolveTickProcessesActions:
    """T076 / FR-022: ``resolve_tick`` reads pending actions and writes ActionResult rows."""

    def test_resolve_reads_pending_actions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``resolve_tick`` calls ``persistence.get_pending_turns`` to fetch the work list."""
        pending = [
            {
                "session_id": str(uuid4()),
                "tick": 0,
                "org_id": "org-1",
                "verb": "educate",
                "target_id": "terr-1",
                "params_json": {},
            }
        ]
        bridge = _make_bridge(monkeypatch, pending_actions=pending)
        session_id = uuid4()

        # Stub the engine step so we don't need a full scenario in play.

        monkeypatch.setattr(
            "web.game.engine_bridge.step",
            lambda state, _config, persistent_context=None, defines=None: state.model_copy(  # noqa: ARG005
                update={"tick": state.tick + 1}
            ),
        )
        # Disable trap-detection side effects on the empty state.
        monkeypatch.setattr(
            "web.game.engine_bridge._compute_traps",
            lambda _state, _session_id: None,
        )

        bridge.resolve_tick(session_id)

        # The bridge must have fetched pending actions for the current tick.
        bridge._persistence.get_pending_turns.assert_called()  # type: ignore[attr-defined]

    def test_resolve_persists_new_tick(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """After step(), the new tick's graph + events are persisted."""
        bridge = _make_bridge(monkeypatch, pending_actions=[])
        session_id = uuid4()

        monkeypatch.setattr(
            "web.game.engine_bridge.step",
            lambda state, _config, persistent_context=None, defines=None: state.model_copy(  # noqa: ARG005
                update={"tick": state.tick + 1}
            ),
        )
        monkeypatch.setattr(
            "web.game.engine_bridge._compute_traps",
            lambda _state, _session_id: None,
        )

        bridge.resolve_tick(session_id)

        bridge._persistence.persist_tick.assert_called_once()  # type: ignore[attr-defined]
        kwargs = bridge._persistence.persist_tick.call_args.kwargs  # type: ignore[attr-defined]
        assert kwargs["session_id"] == session_id
        assert kwargs["tick"] == 1  # advanced from 0 → 1
