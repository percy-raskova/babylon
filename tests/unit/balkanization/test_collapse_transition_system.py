"""Spec-070 CollapseTransitionSystem unit test (T059, FR-023, FR-024)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.engine.systems.collapse_transition import CollapseTransitionSystem
from babylon.models.enums import EventType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


@dataclass
class _CapturedEvent:
    type: Any
    tick: int
    payload: dict[str, Any]


class _RecordingEventBus:
    def __init__(self) -> None:
        self.events: list[_CapturedEvent] = []

    def publish(self, event: Any) -> None:
        self.events.append(_CapturedEvent(type=event.type, tick=event.tick, payload=event.payload))


@pytest.fixture
def services() -> Any:
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    return container


def _events_of(bus: _RecordingEventBus, ev: Any) -> list[_CapturedEvent]:
    return [e for e in bus.events if e.type is ev]


def test_legitimacy_zero_triggers_sovereign_collapse(services: Any) -> None:
    """FR-023: legitimacy <= 0.0 fires SOVEREIGN_COLLAPSE."""

    adapter = BabylonGraph()
    adapter.add_node("SOV_USA_FED", "sovereign", legitimacy=0.0)
    adapter.add_node("HEX_001", "territory")
    adapter.add_edge(
        "SOV_USA_FED",
        "HEX_001",
        "claims",
        control_level=1.0,
        legal_status="de_jure",
    )
    context: dict[str, Any] = {"tick": 7, "persistent_data": {}}

    CollapseTransitionSystem().step(adapter, services, context)

    collapses = _events_of(services.event_bus, EventType.SOVEREIGN_COLLAPSE)
    assert len(collapses) == 1
    assert collapses[0].payload["sovereign_id"] == "SOV_USA_FED"
    assert collapses[0].payload["trigger"] == "legitimacy_zero"
    assert collapses[0].payload["claimed_territories_count"] == 1


def test_territory_transition_per_claimed_territory(services: Any) -> None:
    """FR-024 / FR-025: each claimed Territory emits a TERRITORY_TRANSITION
    with reason=collapse_partition when its Sovereign collapses."""

    adapter = BabylonGraph()
    adapter.add_node("SOV_USA_FED", "sovereign", legitimacy=0.0)
    for i in range(3):
        territory_id = f"HEX_{i:03d}"
        adapter.add_node(territory_id, "territory")
        adapter.add_edge(
            "SOV_USA_FED",
            territory_id,
            "claims",
            control_level=1.0,
            legal_status="de_jure",
        )
    context: dict[str, Any] = {"tick": 7, "persistent_data": {}}

    CollapseTransitionSystem().step(adapter, services, context)

    transitions = _events_of(services.event_bus, EventType.TERRITORY_TRANSITION)
    assert len(transitions) == 3
    for event in transitions:
        assert event.payload["reason"] == "collapse_partition"
        assert event.payload["from_sovereign_id"] == "SOV_USA_FED"


def test_collapse_removes_claims_edges(services: Any) -> None:
    """FR-024 step 5: CLAIMS edges removed after the collapse event."""

    adapter = BabylonGraph()
    adapter.add_node("SOV_USA_FED", "sovereign", legitimacy=0.0)
    adapter.add_node("HEX_001", "territory")
    adapter.add_edge(
        "SOV_USA_FED",
        "HEX_001",
        "claims",
        control_level=1.0,
        legal_status="de_jure",
    )
    context: dict[str, Any] = {"tick": 7, "persistent_data": {}}

    CollapseTransitionSystem().step(adapter, services, context)

    # The CLAIMS edge has been stripped.
    assert adapter.get_edge("SOV_USA_FED", "HEX_001", "claims") is None


def test_external_trigger_via_persistent_data(services: Any) -> None:
    """External triggers (ECOLOGICAL_OVERSHOOT, NUCLEAR_EXCHANGE) flow
    in via ``persistent_data["balkanization.collapse_triggers"]``."""

    adapter = BabylonGraph()
    adapter.add_node("SOV_DOOMED", "sovereign", legitimacy=0.9)  # Still legit.
    adapter.add_node("HEX_001", "territory")
    adapter.add_edge(
        "SOV_DOOMED",
        "HEX_001",
        "claims",
        control_level=1.0,
        legal_status="de_jure",
    )
    context: dict[str, Any] = {
        "tick": 11,
        "persistent_data": {
            "balkanization.collapse_triggers": {
                "SOV_DOOMED": "ecological_overshoot",
            }
        },
    }

    CollapseTransitionSystem().step(adapter, services, context)

    collapses = _events_of(services.event_bus, EventType.SOVEREIGN_COLLAPSE)
    assert len(collapses) == 1
    assert collapses[0].payload["trigger"] == "ecological_overshoot"


def test_healthy_sovereign_does_not_collapse(services: Any) -> None:
    adapter = BabylonGraph()
    adapter.add_node("SOV_USA_FED", "sovereign", legitimacy=1.0)
    context: dict[str, Any] = {"tick": 0, "persistent_data": {}}

    CollapseTransitionSystem().step(adapter, services, context)

    bus: _RecordingEventBus = services.event_bus
    assert _events_of(bus, EventType.SOVEREIGN_COLLAPSE) == []


def test_triggers_cleared_after_processing(services: Any) -> None:
    """Triggers are single-shot to avoid double-collapse on next tick."""

    adapter = BabylonGraph()
    adapter.add_node("SOV_DOOMED", "sovereign", legitimacy=0.9)
    triggers = {"SOV_DOOMED": "ecological_overshoot"}
    context: dict[str, Any] = {
        "tick": 11,
        "persistent_data": {"balkanization.collapse_triggers": triggers},
    }

    CollapseTransitionSystem().step(adapter, services, context)

    assert context["persistent_data"]["balkanization.collapse_triggers"] == {}
