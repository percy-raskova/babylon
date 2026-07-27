"""Behavioral contract for the P25 electoral event vocabulary (U2, ADR128).

Thirteen new EventTypes with typed payloads, registered builders, and DERIVED
severity (every member classified in SEVERITY_TAXONOMY — none may fall through
to the loud unclassified floor; severity is kind × terminal proximity, never
hand-tiered).
"""

from babylon.engine.event_builders import EVENT_BUILDERS
from babylon.models.enums import EventType
from babylon.models.event_severity import resolve_severity
from babylon.models.events import (
    CapitalStrikeEvent,
    DeliveryGapCrossedEvent,
    ElectionHeldEvent,
    ElectionsSuspendedEvent,
)

P25_EVENT_TYPES = (
    EventType.ELECTION_HELD,
    EventType.GOVERNMENT_FORMED,
    EventType.POLICY_ENACTED,
    EventType.POLICY_STRUCK,
    EventType.POLICY_PREEMPTED,
    EventType.CAPITAL_STRIKE,
    EventType.DELIVERY_GAP_CROSSED,
    EventType.HOPE_SPIKE,
    EventType.DISILLUSION_WINDOW_OPEN,
    EventType.LEGITIMATION_REFRESH,
    EventType.ELECTIONS_SUSPENDED,
    EventType.POPULAR_FRONT_CALLED,
    EventType.LINE_STRUGGLE_SPLIT,
)


def test_all_thirteen_types_have_registered_builders():
    missing = [t for t in P25_EVENT_TYPES if t not in EVENT_BUILDERS]
    assert missing == []


def test_all_thirteen_types_resolve_derived_severity_never_the_loud_floor():
    unclassified = [t.value for t in P25_EVENT_TYPES if resolve_severity(t).unclassified]
    assert unclassified == []


def test_elections_suspended_is_terminal_adjacent_critical():
    # Bonapartist clock suspension is regime->crisis entry (TERMINAL_ADJACENT by
    # the TerminalProximity docstring's own definition) — derives critical.
    assert resolve_severity(EventType.ELECTIONS_SUSPENDED).tier == "critical"


def test_builders_produce_typed_payloads_from_bus_dicts():
    built = EVENT_BUILDERS[EventType.ELECTION_HELD](
        3,
        "2026-01-01T00:00:00",
        {"sovereign_id": "USA", "jurisdiction_level": "federal", "turnout": 0.51},
    )
    assert isinstance(built, ElectionHeldEvent)
    assert built.tick == 3
    assert built.sovereign_id == "USA"
    assert built.turnout == 0.51

    gap = EVENT_BUILDERS[EventType.DELIVERY_GAP_CROSSED](
        7, "2026-01-01T00:00:00", {"class_id": "C001", "gap": 0.4, "betrayal_integral": 1.2}
    )
    assert isinstance(gap, DeliveryGapCrossedEvent)
    assert gap.betrayal_integral == 1.2


def test_payload_defaults_carry_their_event_type():
    assert (
        CapitalStrikeEvent(tick=0, timestamp="2026-01-01T00:00:00", sovereign_id="USA").event_type
        == EventType.CAPITAL_STRIKE
    )
    assert (
        ElectionsSuspendedEvent(
            tick=0, timestamp="2026-01-01T00:00:00", sovereign_id="USA"
        ).event_type
        == EventType.ELECTIONS_SUSPENDED
    )
