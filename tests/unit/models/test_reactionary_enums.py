"""Spec-071: fascist EventType + ActionType enum values."""

from __future__ import annotations

import pytest

from babylon.models.enums import ActionType, EventType

pytestmark = pytest.mark.unit

_NEW_EVENTS = {
    "FASCIST_DRIFT": "fascist_drift",
    "FASCIST_RECRUITMENT": "fascist_recruitment",
    "ORGANIZATIONAL_FRACTURE": "organizational_fracture",
    "RED_BROWN_COUP": "red_brown_coup",
    "POGROM": "pogrom",
    "LOCKOUT": "lockout",
    "VIGILANTISM": "vigilantism",
    "SPONTANEOUS_RIOT": "spontaneous_riot",
}

_NEW_ACTIONS = {
    "POGROM": "pogrom",
    "LOCKOUT": "lockout",
    "VIGILANTISM": "vigilantism",
    "RED_BROWN_COUP": "red_brown_coup",
}


class TestReactionaryEventTypes:
    @pytest.mark.parametrize(("name", "value"), list(_NEW_EVENTS.items()))
    def test_event_exists(self, name: str, value: str) -> None:
        assert hasattr(EventType, name)
        assert EventType[name].value == value
        assert EventType(value) == EventType[name]


class TestReactionaryActionTypes:
    @pytest.mark.parametrize(("name", "value"), list(_NEW_ACTIONS.items()))
    def test_action_exists(self, name: str, value: str) -> None:
        assert hasattr(ActionType, name)
        assert ActionType[name].value == value
        assert ActionType(value) == ActionType[name]
