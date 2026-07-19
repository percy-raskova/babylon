"""Regression test for the faction ``node_type`` query mismatch.

``WorldState.to_graph()`` stamps ``BalkanizationFaction`` nodes with
``_node_type="faction"`` (``world_state.py::_add_political_nodes``), but
``FactionInfluenceSystem`` and ``ReactionarySystem`` queried
``node_type="balkanization_faction"`` -- a string that never matches, so
faction enumeration silently returned zero nodes at those call sites
(``RED_SETTLER_TRAP_DETECTED``, secession-eligibility, and
``_find_fascist_faction`` were all dead code paths).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.faction_influence import FactionInfluenceSystem
from babylon.models.entities.balkanization_faction import BalkanizationFaction
from babylon.models.enums import ColonialStance, EventType
from babylon.models.world_state import WorldState

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


def _make_faction(**overrides: object) -> BalkanizationFaction:
    base: dict[str, object] = {
        "id": "FAC_TRAP",
        "name": "Red Settler Trap Faction",
        "ideology": "settler-restorationism",
        "colonial_stance": ColonialStance.UPHOLD,
        "is_settler_formation": True,
        "extraction_modifier": 1.5,
        "violence_modifier": 2.0,
        "class_reduction": 0.7,
        "metabolic_reduction": -0.5,
        "color_hex": "#aa0000",
        "founded_tick": 0,
    }
    base.update(overrides)
    return BalkanizationFaction.model_validate(base)


def test_faction_node_type_is_queryable_as_faction_not_balkanization_faction() -> None:
    """Pin the canonical ``_node_type`` string stamped by ``to_graph()``.

    ``query_nodes(node_type="faction")`` must find the real
    ``BalkanizationFaction`` node; the historically (mis)used
    ``"balkanization_faction"`` string must match nothing.
    """
    faction = _make_faction()
    state = WorldState(tick=0, factions={faction.id: faction})
    graph = state.to_graph()

    found = list(graph.query_nodes(node_type="faction"))
    assert [n.id for n in found] == [faction.id]

    not_found = list(graph.query_nodes(node_type="balkanization_faction"))
    assert not_found == []


def test_red_settler_trap_fires_through_real_world_state_graph(services: Any) -> None:
    """FR-034: RED_SETTLER_TRAP_DETECTED must fire for a faction built via
    the real ``WorldState.to_graph()`` path (not a hand-stamped adapter
    node), proving ``FactionInfluenceSystem`` enumerates faction nodes
    under the same ``_node_type`` the production serializer emits.
    """
    faction = _make_faction(
        colonial_stance=ColonialStance.UPHOLD,
        class_reduction=0.7,
    )
    state = WorldState(tick=0, factions={faction.id: faction})
    graph = state.to_graph()
    context = TickContext(tick=0, persistent_data={})

    FactionInfluenceSystem().step(graph, services, context)

    traps = _events_of(services.event_bus, EventType.RED_SETTLER_TRAP_DETECTED)
    detected_ids = {e.payload["faction_id"] for e in traps}
    assert faction.id in detected_ids
