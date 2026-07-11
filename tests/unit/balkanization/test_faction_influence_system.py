"""Spec-070 FactionInfluenceSystem unit tests (T049 + T048 + T051 +
T055, FR-021, FR-022, FR-026, FR-034, FR-029a/b/c).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.engine.systems.faction_influence import FactionInfluenceSystem
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


@dataclass
class _Defines:
    balkanization: BalkanizationDefines


@pytest.fixture
def services() -> Any:
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    container.defines = _Defines(balkanization=BalkanizationDefines())
    container.rng = None  # System falls back to deterministic per-tick RNG.
    return container


def _events_of(bus: _RecordingEventBus, ev_type: Any) -> list[_CapturedEvent]:
    return [e for e in bus.events if e.type is ev_type]


def _seed_two_factions_one_territory(adapter: BabylonGraph) -> None:
    adapter.add_node(
        "FAC_A",
        "balkanization_faction",
        colonial_stance="uphold",
        class_reduction=0.0,
    )
    adapter.add_node(
        "FAC_B",
        "balkanization_faction",
        colonial_stance="abolish",
        class_reduction=0.5,
    )
    adapter.add_node("HEX_001", "territory")
    adapter.add_edge(
        "FAC_A",
        "HEX_001",
        "influences",
        influence_level=0.3,
        support_type="electoral",
    )
    adapter.add_edge(
        "FAC_B",
        "HEX_001",
        "influences",
        influence_level=0.7,
        support_type="ideological",
    )


def test_winning_faction_resolution_writes_persistent_snapshot(
    services: Any,
) -> None:
    adapter = BabylonGraph()
    _seed_two_factions_one_territory(adapter)
    context: dict[str, Any] = {"tick": 0, "persistent_data": {}}

    FactionInfluenceSystem().step(adapter, services, context)

    winning = context["persistent_data"]["balkanization.winning_faction_by_territory"]
    assert winning == {"HEX_001": "FAC_B"}


def test_territory_transition_emits_on_flip(services: Any) -> None:
    """FR-022: TERRITORY_TRANSITION fires when the winning Faction
    changes between ticks."""

    adapter = BabylonGraph()
    _seed_two_factions_one_territory(adapter)
    persistent: dict[str, Any] = {}
    context: dict[str, Any] = {"tick": 0, "persistent_data": persistent}

    FactionInfluenceSystem().step(adapter, services, context)
    # No prior winner ⇒ event fires with from=None.
    transitions = _events_of(services.event_bus, EventType.TERRITORY_TRANSITION)
    assert len(transitions) == 1
    assert transitions[0].payload["to_winning_faction_id"] == "FAC_B"

    # Now FLIP the influence: FAC_A becomes the winner.
    adapter.update_edge("FAC_A", "HEX_001", "influences", influence_level=0.9)
    context2: dict[str, Any] = {"tick": 1, "persistent_data": persistent}
    FactionInfluenceSystem().step(adapter, services, context2)
    transitions = _events_of(services.event_bus, EventType.TERRITORY_TRANSITION)
    assert len(transitions) == 2
    assert transitions[1].payload["from_winning_faction_id"] == "FAC_B"
    assert transitions[1].payload["to_winning_faction_id"] == "FAC_A"


def test_no_transition_when_winner_unchanged(services: Any) -> None:
    adapter = BabylonGraph()
    _seed_two_factions_one_territory(adapter)
    persistent: dict[str, Any] = {}
    context: dict[str, Any] = {"tick": 0, "persistent_data": persistent}
    FactionInfluenceSystem().step(adapter, services, context)
    bus: _RecordingEventBus = services.event_bus
    transitions_before = len(_events_of(bus, EventType.TERRITORY_TRANSITION))
    # Re-tick with no graph mutation — winning faction unchanged.
    context2: dict[str, Any] = {"tick": 1, "persistent_data": persistent}
    FactionInfluenceSystem().step(adapter, services, context2)
    transitions_after = len(_events_of(bus, EventType.TERRITORY_TRANSITION))
    assert transitions_after == transitions_before


def test_faction_victory_fires_on_supermajority(services: Any) -> None:
    """FR-026: FACTION_VICTORY fires when a Faction holds ≥
    supermajority threshold (default 0.66) across territories."""

    adapter = BabylonGraph()
    adapter.add_node(
        "FAC_DOM",
        "balkanization_faction",
        colonial_stance="uphold",
        class_reduction=0.0,
    )
    adapter.add_node(
        "FAC_MIN",
        "balkanization_faction",
        colonial_stance="abolish",
        class_reduction=0.0,
    )
    # 7 territories all dominated by FAC_DOM; 1 by FAC_MIN (87.5% > 0.66).
    for i in range(7):
        territory_id = f"HEX_{i:03d}"
        adapter.add_node(territory_id, "territory")
        adapter.add_edge(
            "FAC_DOM",
            territory_id,
            "influences",
            influence_level=0.9,
            support_type="electoral",
        )
    adapter.add_node("HEX_007", "territory")
    adapter.add_edge(
        "FAC_MIN",
        "HEX_007",
        "influences",
        influence_level=0.9,
        support_type="ideological",
    )
    context: dict[str, Any] = {"tick": 0, "persistent_data": {}}

    FactionInfluenceSystem().step(adapter, services, context)

    victories = _events_of(services.event_bus, EventType.FACTION_VICTORY)
    assert any(e.payload["faction_id"] == "FAC_DOM" for e in victories)


def test_red_settler_trap_event_emits_for_high_class_reduction_ignore(
    services: Any,
) -> None:
    """FR-034: a Faction with class_reduction ≥ 0.6 and colonial_stance
    ∈ {UPHOLD, IGNORE} triggers RED_SETTLER_TRAP_DETECTED."""

    adapter = BabylonGraph()
    adapter.add_node(
        "FAC_TRAP",
        "balkanization_faction",
        colonial_stance="ignore",
        class_reduction=0.7,
    )
    adapter.add_node(
        "FAC_SAFE",
        "balkanization_faction",
        colonial_stance="abolish",
        class_reduction=0.7,  # ABOLISH skips trap.
    )
    context: dict[str, Any] = {"tick": 0, "persistent_data": {}}

    FactionInfluenceSystem().step(adapter, services, context)

    traps = _events_of(services.event_bus, EventType.RED_SETTLER_TRAP_DETECTED)
    detected_ids = {e.payload["faction_id"] for e in traps}
    assert "FAC_TRAP" in detected_ids
    assert "FAC_SAFE" not in detected_ids


def test_winning_faction_for_unclaimed_territory_returns_no_entry(
    services: Any,
) -> None:
    adapter = BabylonGraph()
    adapter.add_node("HEX_ORPHAN", "territory")
    context: dict[str, Any] = {"tick": 0, "persistent_data": {}}

    FactionInfluenceSystem().step(adapter, services, context)

    winning = context["persistent_data"]["balkanization.winning_faction_by_territory"]
    assert "HEX_ORPHAN" not in winning
