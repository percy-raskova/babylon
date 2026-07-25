"""Behavioral contract for the player driver — the action-bar → submit_verb seam (Task 8)."""

from uuid import uuid4

import pytest

from babylon.game.actions.player_driver import (
    ActionNotLive,
    ActionNotPermitted,
    issue_action,
)
from babylon.topology import BabylonGraph


class _RecordingSink:
    """Journal stub satisfying the real TurnSink protocol shape."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def submit_turn(
        self,
        session_id,
        tick,
        org_id,
        verb,
        *,
        action_type=None,
        target_id=None,
        target_community=None,
        params_json=None,
    ) -> int:
        self.calls.append(
            {
                "session_id": session_id,
                "tick": tick,
                "org_id": org_id,
                "verb": verb,
                "action_type": action_type,
                "target_id": target_id,
            }
        )
        return len(self.calls)


def _issue(action_id: str, agent_type: str, sink: _RecordingSink) -> int:
    return issue_action(
        action_id,
        agent_type,
        "org/vanguard",
        sink,
        session_id=uuid4(),
        tick=3,
        graph=BabylonGraph(),
    )


def test_organizer_can_issue_a_live_verb_through_submit_verb():
    sink = _RecordingSink()
    turn_id = _issue("educate", "organizer", sink)
    assert turn_id == 1
    (call,) = sink.calls
    assert call["org_id"] == "org/vanguard"
    assert call["verb"] == "educate"
    assert call["tick"] == 3
    assert call["action_type"] == "educate"  # the spec's effect_ref passthrough


def test_state_cannot_issue_an_organizer_verb():
    with pytest.raises(ActionNotPermitted):
        _issue("educate", "state", _RecordingSink())


def test_stub_action_is_refused_as_not_live():
    with pytest.raises(ActionNotLive):
        _issue("fund_research", "state", _RecordingSink())


def test_unknown_action_fails_loud():
    with pytest.raises(KeyError):
        _issue("teleport", "organizer", _RecordingSink())
