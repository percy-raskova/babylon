"""Spec-095: bridge endgame-outcome coverage tests.

**Bridge detector wiring (Program 17 / Item 1c)**: ``resolve_tick`` must run
a REAL, per-session-cached ``EndgameDetector`` and surface whichever of the
5 ``GameOutcome`` values it fires in ``snapshot['endgame']``. The old
version of this concern's tests mocked ``event.event_type = "RED_OGV"``
directly on a fake event — a shape no real ``EndgameEvent`` ever has
(``event_type`` is ALWAYS ``EventType.ENDGAME_REACHED``; the outcome lives
in a separate typed ``outcome`` field). These tests now drive a
monkeypatched ``EndgameDetector`` subclass (forcing one ``_check_*``
predicate True) through ``resolve_tick`` and assert on the detector-driven
snapshot block.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from babylon.engine.observers.endgame_detector import EndgameDetector
from babylon.models.enums import GameOutcome
from game.engine_bridge import EngineBridge

pytestmark = pytest.mark.unit

_SESSION = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


@pytest.fixture(autouse=True)
def _clear_endgame_detector_cache() -> Any:
    """``_session_endgame_detectors`` is a module-level, per-process cache
    keyed by session_id (required so cross-tick counters survive separate
    ``resolve_tick`` calls). Every test in this module reuses the same
    ``_SESSION`` UUID, so without clearing the cache a detector that reached
    game-over in one test would leak into the next."""
    from game.engine_bridge import _session_endgame_detectors

    _session_endgame_detectors.clear()
    yield
    _session_endgame_detectors.clear()


def _make_mock_persistence() -> MagicMock:
    mock = MagicMock()
    mock.hydrate_graph.return_value = MagicMock()
    mock.get_metadata.return_value = None
    mock.get_session.return_value = {"scenario": "default"}
    mock.get_pending_turns.return_value = []
    mock.mark_turns_resolved.return_value = 0
    mock.persist_tick.return_value = None
    return mock


def _make_mock_new_state(tick: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.tick = tick
    mock.entities = {}
    mock.territories = {}
    mock.organizations = {}
    mock.institutions = {}
    mock.economy = MagicMock()
    mock.economy.model_dump.return_value = {}
    mock.relationships = []
    mock.events = []
    mock.to_graph.return_value = MagicMock()
    # Program 17 / Item 1c: when the (forced) EndgameDetector fires,
    # resolve_tick does `new_state = new_state.model_copy(update={"events":
    # [...]})` to append the real EndgameEvent. A bare MagicMock's
    # .model_copy(...) would otherwise return an unconfigured child mock,
    # dropping every attribute set up above — return the same mock instead.
    mock.model_copy.return_value = mock
    return mock


# ---------------------------------------------------------------------- #
# 1. Bridge 3-of-5 bug — resolve_tick must surface ALL 5 endgame types
# ---------------------------------------------------------------------- #


def _forced_outcome_detector_class(forced: str) -> type[EndgameDetector]:
    """Build an ``EndgameDetector`` subclass that forces exactly one
    ``_check_*`` predicate True (the rest False), a predicate-isolation
    technique. This drives ``resolve_tick``'s new detector wiring to a known
    outcome without needing to construct real WorldState fixtures for every
    one of the 5 endgames' (often mutually-contradictory) prerequisites.
    """

    class ForcedDetector(EndgameDetector):
        def _check_red_ogv(self, state: Any) -> bool:
            return forced == "red_ogv"

        def _check_fragmented_collapse(self, state: Any) -> bool:
            return forced == "fragmented_collapse"

        def _check_ecological_collapse(self, state: Any) -> bool:
            return forced == "ecological_collapse"

        def _check_fascist_consolidation(self, state: Any) -> bool:
            return forced == "fascist_consolidation"

        def _check_revolutionary_victory(self, state: Any) -> bool:
            return forced == "revolutionary_victory"

    return ForcedDetector


class TestBridgeEndgameCoverage:
    """FR-095-02: resolve_tick must recognize all 5 GameOutcome event types.

    Program 17 / Item 1c: resolve_tick now runs a REAL EndgameDetector — these
    tests monkeypatch ``game.engine_bridge.EndgameDetector`` with a subclass
    that forces exactly one outcome (see
    :func:`_forced_outcome_detector_class`) and assert on the resulting
    detector-driven ``snapshot['endgame']`` block.
    """

    def test_resolve_tick_surfaces_red_ogv_endgame(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RED_OGV endgame must populate snapshot['endgame']."""
        monkeypatch.setattr(
            "game.engine_bridge.EndgameDetector", _forced_outcome_detector_class("red_ogv")
        )
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        with patch("game.engine_bridge.step", return_value=mock_new_state):
            bridge = EngineBridge(mock_persistence)
            result = bridge.resolve_tick(_SESSION)

        assert "endgame" in result, "RED_OGV endgame must surface in snapshot"
        assert result["endgame"]["outcome"] == GameOutcome.RED_OGV.value

    def test_resolve_tick_surfaces_fragmented_collapse_endgame(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FRAGMENTED_COLLAPSE endgame must populate snapshot['endgame']."""
        monkeypatch.setattr(
            "game.engine_bridge.EndgameDetector",
            _forced_outcome_detector_class("fragmented_collapse"),
        )
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        with patch("game.engine_bridge.step", return_value=mock_new_state):
            bridge = EngineBridge(mock_persistence)
            result = bridge.resolve_tick(_SESSION)

        assert "endgame" in result
        assert result["endgame"]["outcome"] == GameOutcome.FRAGMENTED_COLLAPSE.value

    def test_resolve_tick_surfaces_revolutionary_victory_endgame(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """REVOLUTIONARY_VICTORY (already in the set) must still work."""
        monkeypatch.setattr(
            "game.engine_bridge.EndgameDetector",
            _forced_outcome_detector_class("revolutionary_victory"),
        )
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()

        with patch("game.engine_bridge.step", return_value=mock_new_state):
            bridge = EngineBridge(mock_persistence)
            result = bridge.resolve_tick(_SESSION)

        assert "endgame" in result
        assert result["endgame"]["outcome"] == GameOutcome.REVOLUTIONARY_VICTORY.value
