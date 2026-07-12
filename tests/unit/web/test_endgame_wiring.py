"""Program 17 / Item 1c: wire the real EndgameDetector into resolve_tick.

Before this fix, ``resolve_tick`` never ran an ``EndgameDetector`` at all —
the dead ``snapshot['endgame']`` block only matched a literal
``event_type`` string that real ``EndgameEvent``s never carry (the outcome
lives in a separate typed ``outcome`` field; ``event_type`` is ALWAYS
``EventType.ENDGAME_REACHED``). This test drives the REAL detector through
two consecutive ``resolve_tick`` calls under sustained ecological overshoot
and asserts the game actually ends on the second call — genuine RED against
the old code (no detector ever ran, so ``snapshot['endgame']`` never
appeared), genuine GREEN only with real cross-request detector caching (a
naive per-call ``EndgameDetector()`` would reset
``_overshoot_consecutive_ticks`` every call and never fire).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from babylon.models.entities.social_class import SocialClass
from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType, SocialRole
from babylon.models.world_state import WorldState
from game.engine_bridge import EngineBridge

pytestmark = pytest.mark.unit

_SESSION = UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff")


@pytest.fixture(autouse=True)
def _clear_endgame_detector_cache() -> Any:
    """``_session_endgame_detectors`` is a module-level, per-process cache
    keyed by session_id (required so cross-tick counters survive separate
    ``resolve_tick`` calls — see engine_bridge.py). Both tests in this file
    reuse the same ``_SESSION`` UUID, so without clearing the cache a
    detector that reached game-over in one test would leak into the next."""
    from game.engine_bridge import _session_endgame_detectors

    _session_endgame_detectors.clear()
    yield
    _session_endgame_detectors.clear()


def _make_mock_persistence() -> MagicMock:
    mock = MagicMock()
    mock.get_metadata.return_value = None
    mock.get_session.return_value = {
        "game_defines_json": {
            "endgame": {
                # EndgameDefines.ecological_overshoot_threshold is gt=0.0 (a
                # literal 0.0 fails Pydantic validation) — 0.5 sits well
                # below the overshoot fixture's ratio (2.0) and well above
                # the healthy fixture's ratio (0.0001).
                "ecological_overshoot_threshold": 0.5,
                "ecological_sustained_ticks": 2,
            }
        }
    }
    mock.get_pending_turns.return_value = []
    mock.mark_turns_resolved.return_value = 0
    mock.persist_tick.return_value = None
    return mock


def _overshoot_state(tick: int) -> WorldState:
    """A minimal WorldState whose consumption permanently exceeds
    biocapacity (overshoot_ratio == 2.0), so with
    ``ecological_overshoot_threshold=0.0`` every tick counts toward the
    sustained-overshoot window regardless of tick number."""
    entity = SocialClass(
        id="C001",
        name="Workers",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        s_bio=1.0,
        s_class=1.0,
    )
    territory = Territory(
        id="T001",
        name="Zone",
        sector_type=SectorType.RESIDENTIAL,
        biocapacity=1.0,
        max_biocapacity=1.0,
    )
    return WorldState(tick=tick, entities={"C001": entity}, territories={"T001": territory})


class TestResolveTickWiresRealEndgameDetector:
    """resolve_tick must run a REAL, per-session-cached EndgameDetector —
    not a dead literal-string scan — so the game can actually end."""

    def test_ecological_collapse_fires_after_sustained_overshoot(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        # Tracks the "persisted" state across resolve_tick calls, so
        # hydrate_state on call N returns whatever the previous call's
        # step() produced — exactly like a real hydrate->step->persist loop.
        current_state: dict[str, WorldState] = {"state": _overshoot_state(0)}

        def fake_hydrate_state(session_id: UUID) -> tuple[WorldState, Any]:
            return current_state["state"], MagicMock()

        def fake_step(state: WorldState, *_args: Any, **_kwargs: Any) -> WorldState:
            new_state = _overshoot_state(state.tick + 1)
            current_state["state"] = new_state
            return new_state

        monkeypatch.setattr(bridge, "hydrate_state", fake_hydrate_state)
        monkeypatch.setattr("game.engine_bridge.step", fake_step)

        # Tick 1: overshoot has only been sustained 1 tick (threshold needs 2).
        result_1 = bridge.resolve_tick(_SESSION)
        assert result_1.get("endgame") is None

        # Tick 2: a naive fresh-detector-per-call implementation would reset
        # the consecutive-tick counter here and never fire. The real fix
        # caches the detector per session, so this is the 2nd consecutive
        # overshoot tick the SAME detector instance has seen.
        result_2 = bridge.resolve_tick(_SESSION)
        assert result_2["endgame"]["outcome"] == "ecological_collapse"
        assert result_2["endgame"]["tick"] == 2

    def test_no_endgame_stays_absent_when_conditions_never_hold(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A perfectly healthy state (biocapacity comfortably exceeds
        consumption) must never populate snapshot['endgame']."""
        mock_persistence = _make_mock_persistence()
        bridge = EngineBridge(mock_persistence)

        def healthy_state(tick: int) -> WorldState:
            entity = SocialClass(
                id="C001",
                name="Workers",
                role=SocialRole.PERIPHERY_PROLETARIAT,
                s_bio=0.01,
                s_class=0.0,
            )
            territory = Territory(
                id="T001",
                name="Zone",
                sector_type=SectorType.RESIDENTIAL,
                biocapacity=100.0,
                max_biocapacity=100.0,
            )
            return WorldState(tick=tick, entities={"C001": entity}, territories={"T001": territory})

        current_state: dict[str, WorldState] = {"state": healthy_state(0)}

        def fake_hydrate_state(session_id: UUID) -> tuple[WorldState, Any]:
            return current_state["state"], MagicMock()

        def fake_step(state: WorldState, *_args: Any, **_kwargs: Any) -> WorldState:
            new_state = healthy_state(state.tick + 1)
            current_state["state"] = new_state
            return new_state

        monkeypatch.setattr(bridge, "hydrate_state", fake_hydrate_state)
        monkeypatch.setattr("game.engine_bridge.step", fake_step)

        result = bridge.resolve_tick(_SESSION)
        assert result.get("endgame") is None
