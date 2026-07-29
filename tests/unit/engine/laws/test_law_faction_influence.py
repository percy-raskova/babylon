"""Behavioral law suite for FactionInfluenceSystem (P27 Phase-0 coverage-floor
backfill, Task 11 pattern; spec-070 FR-021, FR-022, FR-026, FR-034).

Laws pinned (grounded by reading ``FactionInfluenceSystem.step`` end-to-end,
``src/babylon/engine/systems/faction_influence.py``, plus the pure formulas
it calls in ``src/babylon/formulas/balkanization.py``):

  L1 -- argmax soundness (FR-021): the winning Faction recorded for a
        Territory always holds the maximum summed ``influence_level`` for
        that Territory. ``winning_faction_for_territory`` computes
        ``totals[faction_id] = sum(influence_level)`` per Faction and
        returns a member of the tied-for-max set
        (balkanization.py:194-212); the system writes that value verbatim
        into ``persistent["balkanization.winning_faction_by_territory"]``
        (faction_influence.py:70-71, 96-98). This test avoids near-ties
        (gap > 1e-6) so the incumbent/RNG tiebreak never has to fire,
        isolating the argmax property itself.

  L2 -- unchanged-winner inactivity (FR-022): re-running ``step()`` on an
        UNMODIFIED graph never emits a second TERRITORY_TRANSITION for a
        Territory whose winning Faction did not change.
        ``_emit_territory_transitions`` explicitly skips when
        ``old == new`` (faction_influence.py:112-113), and
        ``persistent[_PREV_WINNING]`` is refreshed every tick
        (faction_influence.py:74), so a stable graph produces a stable
        "previous winner" baseline against which the next tick is a no-op.

  L3 -- FACTION_VICTORY soundness + uniqueness (FR-026): every emitted
        FACTION_VICTORY payload has ``aggregate_influence_share >=
        defines.faction_victory_supermajority_threshold``
        (faction_influence.py:145-157), and because the default threshold
        is 0.66 (> 0.5, `BalkanizationDefines.faction_victory_supermajority_
        threshold`, `ge=0.5`) and per-Faction shares are computed over the
        same total-territory-count denominator (faction_influence.py:139-
        146), at most one Faction can clear it in a single tick (shares
        sum to 1; two disjoint shares > 0.5 is impossible).

  L4 -- inactivity on empty input: a graph with zero Territory nodes and
        zero Faction nodes produces an EMPTY
        ``winning_faction_by_territory`` snapshot and publishes no
        TERRITORY_TRANSITION / FACTION_VICTORY / RED_SETTLER_TRAP_DETECTED
        events. ``_resolve_winning_factions`` iterates
        ``query_nodes(node_type=TERRITORY)`` (faction_influence.py:91-99,
        empty -> ``winning = {}``); ``_emit_faction_victory`` early-returns
        on ``if not winning`` (faction_influence.py:136-137);
        ``_emit_red_settler_trap_events`` iterates
        ``query_nodes(node_type=FACTION)`` (faction_influence.py:166-169,
        empty -> no iterations).

Caveat (recorded, not asserted as a law): the FR-026 uniqueness property in
L3 relies on the *default* threshold (0.66); ``BalkanizationDefines`` only
constrains ``ge=0.5``, so a modder-supplied threshold of exactly 0.5 could
in principle let two Factions tie at 50% share each and both fire. That
edge case is a defines-configuration hazard, not a system-code defect, and
is out of scope for this law file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines.balkanization import BalkanizationDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.faction_influence import FactionInfluenceSystem
from babylon.models.enums import EventType, NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Shared fixture plumbing (mirrors tests/unit/balkanization/test_faction_influence_system.py
# -- the project's real unit-test pattern for this system: BabylonGraph +
# TickContext + a MagicMock ServicesProtocol with a recording event bus).
# ---------------------------------------------------------------------------


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


def _make_services() -> Any:
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    container.defines = _Defines(balkanization=BalkanizationDefines())
    container.rng = None  # System falls back to deterministic per-tick RNG.
    return container


def _events_of(bus: _RecordingEventBus, ev_type: Any) -> list[_CapturedEvent]:
    return [e for e in bus.events if e.type is ev_type]


# ---------------------------------------------------------------------------
# L1 -- argmax soundness
# ---------------------------------------------------------------------------


@given(
    levels=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=4,
    )
)
@settings(max_examples=25, deadline=None)
def test_winning_faction_holds_the_max_influence_total(levels: list[float]) -> None:
    # Space the levels out so no two totals fall within the tiebreak
    # neighborhood -- isolates the argmax property from the
    # incumbent/RNG tiebreak (a separate, already-unit-tested concern).
    spaced = sorted({round(v, 6) for v in levels})
    spaced = [v + i * 0.1 for i, v in enumerate(spaced)]
    if len(spaced) < 2:
        return  # not enough distinct factions to compare; skip trivially.

    graph = BabylonGraph()
    graph.add_node("HEX_L1", NodeType.TERRITORY)
    faction_ids = [f"FAC_{i}" for i in range(len(spaced))]
    for faction_id, level in zip(faction_ids, spaced, strict=True):
        graph.add_node(
            faction_id,
            NodeType.FACTION,
            colonial_stance="ignore",
            class_reduction=0.0,
        )
        graph.add_edge(
            faction_id,
            "HEX_L1",
            "influences",
            influence_level=level,
            support_type="electoral",
        )
    expected_winner = faction_ids[spaced.index(max(spaced))]

    services = _make_services()
    context = TickContext(tick=0, persistent_data={})
    FactionInfluenceSystem().step(graph, services, context)

    winning = context.persistent_data["balkanization.winning_faction_by_territory"]
    assert winning["HEX_L1"] == expected_winner


# ---------------------------------------------------------------------------
# L2 -- unchanged-winner inactivity
# ---------------------------------------------------------------------------


def test_no_transition_when_influence_graph_is_unmodified_between_ticks() -> None:
    graph = BabylonGraph()
    graph.add_node("HEX_L2", NodeType.TERRITORY)
    graph.add_node("FAC_A", NodeType.FACTION, colonial_stance="uphold", class_reduction=0.0)
    graph.add_node("FAC_B", NodeType.FACTION, colonial_stance="abolish", class_reduction=0.0)
    graph.add_edge("FAC_A", "HEX_L2", "influences", influence_level=0.2, support_type="electoral")
    graph.add_edge("FAC_B", "HEX_L2", "influences", influence_level=0.8, support_type="ideological")

    services = _make_services()
    context = TickContext(tick=0, persistent_data={})
    FactionInfluenceSystem().step(graph, services, context)
    first_tick_transitions = len(_events_of(services.event_bus, EventType.TERRITORY_TRANSITION))
    assert first_tick_transitions == 1  # from=None -> FAC_B, the initial claim.

    # Re-tick with ZERO graph mutation: the winner cannot change.
    for tick in (1, 2, 3):
        context.tick = tick
        FactionInfluenceSystem().step(graph, services, context)

    transitions = _events_of(services.event_bus, EventType.TERRITORY_TRANSITION)
    assert len(transitions) == first_tick_transitions


# ---------------------------------------------------------------------------
# L3 -- FACTION_VICTORY soundness + uniqueness
# ---------------------------------------------------------------------------


@given(dominant_territory_count=st.integers(min_value=1, max_value=9))
@settings(max_examples=25, deadline=None)
def test_faction_victory_share_always_meets_threshold_and_is_unique(
    dominant_territory_count: int,
) -> None:
    total_territories = dominant_territory_count + 1
    graph = BabylonGraph()
    graph.add_node("FAC_DOM", NodeType.FACTION, colonial_stance="uphold", class_reduction=0.0)
    graph.add_node("FAC_MIN", NodeType.FACTION, colonial_stance="abolish", class_reduction=0.0)
    for i in range(dominant_territory_count):
        territory_id = f"HEX_DOM_{i:03d}"
        graph.add_node(territory_id, NodeType.TERRITORY)
        graph.add_edge(
            "FAC_DOM", territory_id, "influences", influence_level=0.9, support_type="electoral"
        )
    graph.add_node("HEX_MIN_000", NodeType.TERRITORY)
    graph.add_edge(
        "FAC_MIN", "HEX_MIN_000", "influences", influence_level=0.9, support_type="ideological"
    )

    services = _make_services()
    defines = services.defines.balkanization
    context = TickContext(tick=0, persistent_data={})
    FactionInfluenceSystem().step(graph, services, context)

    victories = _events_of(services.event_bus, EventType.FACTION_VICTORY)
    threshold = defines.faction_victory_supermajority_threshold
    # Soundness: every fired victory really clears the threshold.
    for event in victories:
        assert event.payload["aggregate_influence_share"] >= threshold
    # Uniqueness: shares partition `total_territories` 1:1, so at most one
    # Faction can clear a > 0.5 threshold in the same tick.
    assert len({e.payload["faction_id"] for e in victories}) <= 1

    expected_dom_share = dominant_territory_count / total_territories
    if expected_dom_share >= defines.faction_victory_supermajority_threshold:
        assert any(e.payload["faction_id"] == "FAC_DOM" for e in victories)
    else:
        assert not any(e.payload["faction_id"] == "FAC_DOM" for e in victories)


# ---------------------------------------------------------------------------
# L4 -- inactivity on empty input
# ---------------------------------------------------------------------------


def test_empty_graph_produces_no_snapshot_entries_and_no_events() -> None:
    graph = BabylonGraph()  # zero Territory nodes, zero Faction nodes.
    services = _make_services()
    context = TickContext(tick=0, persistent_data={})

    FactionInfluenceSystem().step(graph, services, context)

    winning = context.persistent_data["balkanization.winning_faction_by_territory"]
    assert winning == {}
    assert _events_of(services.event_bus, EventType.TERRITORY_TRANSITION) == []
    assert _events_of(services.event_bus, EventType.FACTION_VICTORY) == []
    assert _events_of(services.event_bus, EventType.RED_SETTLER_TRAP_DETECTED) == []
