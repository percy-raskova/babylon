"""Spec-095 / Spec-116 Task 4: bridge endgame-outcome coverage tests.

**Bridge detector wiring (Program 17 / Item 1c)**: ``resolve_tick`` must run
a REAL, per-session-cached ``EndgameDetector`` and surface whichever of the
5 ``GameOutcome`` values it recognizes. The old version of this concern's
tests mocked ``event.event_type = "RED_OGV"`` directly on a fake event — a
shape no real ``EndgameEvent`` ever has (``event_type`` is ALWAYS
``EventType.ENDGAME_REACHED``; the outcome lives in a separate typed
``outcome`` field). These tests drive a monkeypatched ``EndgameDetector``
subclass (forcing one ``_axis_*`` evaluator to report ``(1.0, True)``, the
rest ``(0.0, False)``) through ``resolve_tick`` and assert on the
detector-driven snapshot block.

Spec-116 FR-116-1: the detector's per-axis predicates were renamed from
``_check_<axis>(state) -> bool`` to ``_axis_<axis>(state, graph) ->
tuple[float, bool]`` (progress, matched) as part of the adjudicator ->
recognizer rework; this fixture's forced-outcome technique follows suit.

Spec-116 Task 4 (owner ruling 2026-07-17): recognizing a pattern no longer
ends the game — it only populates ``snapshot['endgame_progress']['pattern']``
(the live HUD signal). ``snapshot['endgame']`` appears only once the fixed
century horizon is reached (``tick >= horizon_tick``), with ``outcome`` =
the recognized pattern at that tick (or ``"unresolved"`` if none). The
below-horizon tests in :class:`TestBridgeEndgameCoverage` assert on
``endgame_progress``; :class:`TestHorizonReachedWithRecognizedPattern`
closes the loop by forcing the SAME axis at a tick at/past the horizon.
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
    ``_axis_*`` evaluator to report matched (the rest unmatched), a
    predicate-isolation technique. This drives ``resolve_tick``'s new
    detector wiring to a known outcome without needing to construct real
    WorldState fixtures for every one of the 5 endgames' (often
    mutually-contradictory) prerequisites.
    """

    def _forced(name: str) -> tuple[float, bool]:
        return (1.0, True) if forced == name else (0.0, False)

    class ForcedDetector(EndgameDetector):
        def _axis_red_ogv(self, state: Any, graph: Any) -> tuple[float, bool]:
            return _forced("red_ogv")

        def _axis_fragmented_collapse(self, state: Any, graph: Any) -> tuple[float, bool]:
            return _forced("fragmented_collapse")

        def _axis_ecological_collapse(self, state: Any, graph: Any) -> tuple[float, bool]:
            return _forced("ecological_collapse")

        def _axis_fascist_consolidation(self, state: Any, graph: Any) -> tuple[float, bool]:
            return _forced("fascist_consolidation")

        def _axis_revolutionary_victory(self, state: Any, graph: Any) -> tuple[float, bool]:
            return _forced("revolutionary_victory")

    return ForcedDetector


class TestBridgeEndgameCoverage:
    """FR-095-02: resolve_tick must recognize all 5 GameOutcome patterns.

    Program 17 / Item 1c: resolve_tick now runs a REAL EndgameDetector — these
    tests monkeypatch ``game.engine_bridge.EndgameDetector`` with a subclass
    that forces exactly one outcome (see
    :func:`_forced_outcome_detector_class`) and assert on the resulting
    detector-driven ``snapshot['endgame_progress']`` block.

    Spec-116 Task 4: recognizing a pattern below the horizon (tick=1, the
    default fixture tick) never populates ``snapshot['endgame']`` — see
    :class:`TestHorizonReachedWithRecognizedPattern` for the horizon-reached
    case using the same forced-detector technique.
    """

    def test_resolve_tick_surfaces_red_ogv_endgame(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RED_OGV must populate snapshot['endgame_progress']['pattern']."""
        monkeypatch.setattr(
            "game.engine_bridge.EndgameDetector", _forced_outcome_detector_class("red_ogv")
        )
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        with patch("game.engine_bridge.step", return_value=mock_new_state):
            bridge = EngineBridge(mock_persistence)
            result = bridge.resolve_tick(_SESSION)

        assert "endgame" not in result, "recognition alone must not end the game (spec-116)"
        assert result["endgame_progress"]["pattern"] == GameOutcome.RED_OGV.value

    def test_resolve_tick_surfaces_fragmented_collapse_endgame(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FRAGMENTED_COLLAPSE must populate endgame_progress['pattern']."""
        monkeypatch.setattr(
            "game.engine_bridge.EndgameDetector",
            _forced_outcome_detector_class("fragmented_collapse"),
        )
        mock_persistence = _make_mock_persistence()
        mock_new_state = _make_mock_new_state()
        with patch("game.engine_bridge.step", return_value=mock_new_state):
            bridge = EngineBridge(mock_persistence)
            result = bridge.resolve_tick(_SESSION)

        assert "endgame" not in result
        assert result["endgame_progress"]["pattern"] == GameOutcome.FRAGMENTED_COLLAPSE.value

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

        assert "endgame" not in result
        assert result["endgame_progress"]["pattern"] == GameOutcome.REVOLUTIONARY_VICTORY.value


class TestHorizonReachedWithRecognizedPattern:
    """Spec-116 Task 4: at/past the horizon tick, snapshot['endgame'] carries
    whichever pattern the detector recognizes (falling back to
    GameOutcome.UNRESOLVED when none does — covered in
    tests/unit/web/test_endgame_wiring.py)."""

    def test_horizon_reached_surfaces_ecological_collapse_outcome(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "game.engine_bridge.EndgameDetector",
            _forced_outcome_detector_class("ecological_collapse"),
        )
        mock_persistence = _make_mock_persistence()
        # Default GameDefines: campaign_horizon_years=100 * weeks_per_year=52
        # => horizon_tick=5200.
        mock_new_state = _make_mock_new_state(tick=5200)
        with patch("game.engine_bridge.step", return_value=mock_new_state):
            bridge = EngineBridge(mock_persistence)
            result = bridge.resolve_tick(_SESSION)

        assert result["endgame"]["outcome"] == GameOutcome.ECOLOGICAL_COLLAPSE.value
        assert result["endgame"]["tick"] == 5200
        assert result["endgame_progress"]["pattern"] == GameOutcome.ECOLOGICAL_COLLAPSE.value
