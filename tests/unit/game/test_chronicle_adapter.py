"""Unit tests for the bus->Chronicle adapter (Program v1.0.0, Unit T4-core/C4).

Pins the three properties the program plan asked for: :func:`summarize_event`
is a deterministic, pure function of ``(event_type, payload)``; an
``EventType`` with no bespoke builder still renders — loudly, never
dropped; and :func:`chronicle_events_from_bus` is a stateless per-call
mapping (no cumulative state leaks between two calls, mirroring
``WorldState.events``'s own per-tick-not-cumulative contract). No real
engine, Postgres, or ``WorldState`` is needed — plain
:class:`~babylon.kernel.event_bus.Event` fixtures only.
"""

from __future__ import annotations

import pytest

from babylon.game.chronicle_adapter import (
    chronicle_events_from_bus,
    summarize_event,
)
from babylon.kernel.event_bus import Event
from babylon.models.enums.events import EventType

pytestmark = [pytest.mark.unit]


# --------------------------------------------------------------------------- #
# summarize_event: determinism + real per-EventType content.                  #
# --------------------------------------------------------------------------- #


def test_summarize_event_is_deterministic_over_repeated_calls() -> None:
    """The SAME ``(event_type, tick, payload)`` always renders the SAME text."""
    payload = {"source_id": "C001", "target_id": "C002", "amount": 12.5, "mechanism": "wage_gap"}
    first = summarize_event(EventType.SURPLUS_EXTRACTION, 3, payload)
    second = summarize_event(EventType.SURPLUS_EXTRACTION, 3, dict(payload))
    assert first == second
    assert first == "C001 yields 12.50 in surplus to C002 via wage_gap"


def test_summarize_event_reflects_real_payload_not_a_constant() -> None:
    """Different payloads for the SAME EventType render DIFFERENT summaries —
    a pure function of the payload, not a canned string."""
    low = summarize_event(EventType.UPRISING, 1, {"node_id": "T000", "agitation": 0.1})
    high = summarize_event(EventType.UPRISING, 1, {"node_id": "T000", "agitation": 0.9})
    assert low != high
    assert "0.10" in low
    assert "0.90" in high


def test_summarize_event_covers_every_family_without_crashing() -> None:
    """A representative event from each documented family renders without
    raising and without falling through to the generic form (real coverage,
    not just the economic core)."""
    covered_samples: tuple[tuple[EventType, dict[str, object]], ...] = (
        (EventType.DOCTRINE_TRAP_SPRUNG, {"org_id": "rev_workers", "node_id": "C001"}),
        (EventType.SOVEREIGN_COLLAPSE, {"sovereign_id": "sov1", "trigger": "legitimacy_zero"}),
        (EventType.FASCIST_DRIFT, {"node_id": "C004", "fascist_pull": 0.4}),
        (EventType.ORGANIZATIONAL_ACTION, {"org_count": 2, "action_count": 3, "layer0_count": 1}),
        (
            EventType.CALIBRATION_QCEW_CARRY_FORWARD,
            {"county_fips": "26163", "look_back_year": 2019},
        ),
    )
    for event_type, payload in covered_samples:  # loop bound: len(covered_samples)
        summary = summarize_event(event_type, 5, payload)
        assert summary
        # None of these render through the generic "(tick N) — fields:" shape.
        assert "— fields:" not in summary
        assert "— no payload recorded" not in summary


def test_summarize_event_handles_missing_optional_field_honestly() -> None:
    """A field ``EVENT_BUILDERS`` itself reads with no default (e.g.
    ``profit_rate``) renders as an honest ``"?"`` when absent, never a
    fabricated number (Constitution III.11)."""
    summary = summarize_event(
        EventType.CRISIS_PHASE_TRANSITION,
        7,
        {"fips": "26163", "previous_phase": "boom", "new_phase": "bust"},
    )
    assert "profit rate ?" in summary


# --------------------------------------------------------------------------- #
# Unknown EventType: loud generic form, never dropped.                        #
# --------------------------------------------------------------------------- #


def test_unknown_event_type_gets_the_loud_generic_form() -> None:
    """An ``EventType`` with no bespoke builder (a genuinely never-emitted
    value, e.g. ``ENDGAME_REACHED`` — see the module docstring) still renders
    a real, honest summary naming the raw type and the fields present."""
    summary = summarize_event(EventType.ENDGAME_REACHED, 42, {"outcome": "unresolved"})
    assert "endgame_reached" in summary
    assert "42" in summary
    assert "outcome" in summary


def test_unknown_event_type_with_no_payload_says_so_honestly() -> None:
    """An unclassified type with a genuinely empty payload renders the
    honest "no payload recorded" form rather than a blank/fabricated line."""
    summary = summarize_event(EventType.PATTERN_SHIFT, 9, {})
    assert summary == "pattern_shift (tick 9) — no payload recorded"


def test_unknown_event_type_is_never_dropped_from_the_chronicle() -> None:
    """A bus event of an unclassified-but-real EventType still produces a
    ChronicleEvent — the Chronicle never silently drops it."""
    raw = [Event(type=EventType.ENDGAME_REACHED.value, tick=1, payload={"outcome": "unresolved"})]
    result = chronicle_events_from_bus(raw)
    assert len(result) == 1
    assert result[0].event_type is EventType.ENDGAME_REACHED
    assert result[0].summary  # non-empty, real content


# --------------------------------------------------------------------------- #
# chronicle_events_from_bus: shape, malformed-type loudness, per-tick semantics. #
# --------------------------------------------------------------------------- #


def test_chronicle_events_from_bus_preserves_order_and_data() -> None:
    """One ``ChronicleEvent`` per input event, same order, payload preserved
    verbatim in ``.data``."""
    raw = [
        Event(type=EventType.LIFECYCLE_TRANSITION.value, tick=4, payload={"territory_id": "T000"}),
        Event(type=EventType.ORGANIZATIONAL_ACTION.value, tick=4, payload={"org_count": 1}),
    ]
    result = chronicle_events_from_bus(raw)
    assert [ev.event_type for ev in result] == [
        EventType.LIFECYCLE_TRANSITION,
        EventType.ORGANIZATIONAL_ACTION,
    ]
    assert result[0].data == {"territory_id": "T000"}
    assert result[1].data == {"org_count": 1}
    assert all(ev.tick == 4 for ev in result)


def test_chronicle_events_from_bus_empty_history_is_empty() -> None:
    """A tick with genuinely no events yields ``()`` — never fabricated."""
    assert chronicle_events_from_bus([]) == ()


def test_chronicle_events_from_bus_raises_on_a_malformed_event_type() -> None:
    """A bus event carrying a non-``EventType`` string is a bug elsewhere —
    it raises loudly (Constitution III.11) rather than being silently
    dropped from the Chronicle."""
    raw = [Event(type="not_a_real_event_type", tick=1, payload={})]
    with pytest.raises(ValueError, match="not_a_real_event_type"):
        chronicle_events_from_bus(raw)


def test_chronicle_events_from_bus_is_per_tick_not_cumulative() -> None:
    """Two independent calls never leak state into each other — mirrors
    ``WorldState.events``'s own per-tick, never-cumulative contract. The
    adapter has no memory: tick 2's result contains ONLY tick 2's events."""
    tick1_events = [
        Event(type=EventType.LIFECYCLE_TRANSITION.value, tick=1, payload={"territory_id": "T000"})
    ]
    tick2_events = [
        Event(type=EventType.ORGANIZATIONAL_ACTION.value, tick=2, payload={"org_count": 1})
    ]

    first_call = chronicle_events_from_bus(tick1_events)
    second_call = chronicle_events_from_bus(tick2_events)

    assert len(first_call) == 1
    assert len(second_call) == 1
    assert second_call[0].event_type is EventType.ORGANIZATIONAL_ACTION
    assert second_call[0].tick == 2
    # No trace of tick 1's event survives into tick 2's result.
    assert all(ev.event_type is not EventType.LIFECYCLE_TRANSITION for ev in second_call)

    # And re-processing tick 1's own (unchanged) events again reproduces the
    # exact same result — determinism, not first-call-wins caching.
    replayed_tick1 = chronicle_events_from_bus(tick1_events)
    assert replayed_tick1 == first_call
