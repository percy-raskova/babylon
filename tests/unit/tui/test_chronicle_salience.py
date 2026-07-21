"""Contract tests for :mod:`babylon.tui.chronicle_salience` (Program 24 P3 WO-48).

Pins the WO's four named behaviors: severity-tier classification (with a
Constitution III.11 loud default for unclassified event types), consecutive
dedup (the ported ``first-session.spec.ts`` contract), AMBER autopause on a
critical-tier event, and the two volume floors (informational-tier per-tick
cap, ``ORGANIZATIONAL_ACTION`` rollup). Fixture-fed only — no engine, no
graph, no persistence connection, matching WO-27's own discipline.
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.models.enums.events import EventType
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.chronicle_salience import (
    EVENT_SEVERITY,
    NARRATIVE_EVENT_CEILING_PER_TICK,
    AutopauseState,
    aggregate_organizational_actions,
    apply_volume_floors,
    cap_narrative_events,
    chronicle_subject,
    classify_event_salience,
    compute_autopause_state,
    dedup_key,
    dedupe_consecutive,
    render_autopause_indicator,
)
from babylon.tui.theme import AMBER


def _event(
    tick: int,
    event_type: EventType,
    *,
    summary: str = "an event",
    **data: Any,
) -> ChronicleEvent:
    """Build a :class:`ChronicleEvent` with terser call sites than the constructor."""
    return ChronicleEvent(tick=tick, event_type=event_type, summary=summary, data=data)


class TestSeverityTiers:
    """A classified type resolves to its ported tier, cleanly (not unclassified)."""

    def test_a_critical_type_classifies_critical(self) -> None:
        salience = classify_event_salience(EventType.UPRISING)
        assert salience.tier == "critical"
        assert salience.unclassified is False

    def test_a_warning_type_classifies_warning(self) -> None:
        salience = classify_event_salience(EventType.STATE_REPRESSION)
        assert salience.tier == "warning"
        assert salience.unclassified is False

    def test_an_informational_type_classifies_informational(self) -> None:
        salience = classify_event_salience(EventType.SURPLUS_EXTRACTION)
        assert salience.tier == "informational"
        assert salience.unclassified is False


class TestPortedPerTypeSeverityPins:
    """WO-52b test-port: the specific event-type-to-tier examples the legacy
    ``tests/integration/test_event_serialization.py::TestSeveritySchema``
    pinned against ``web/game/engine_bridge.py::_classify_event``.

    ``TestSeverityTiers`` above and ``test_ported_tier_counts_match_the_
    legacy_bridge`` already prove one example per tier plus the aggregate
    14/20/13 counts, but a count-only check cannot catch two types swapping
    tiers — this class pins the exact named types the legacy suite did, so
    that regression class is caught here too. See
    ``specs/24-archive/test-port-ledger-wo52b.md`` for the full disposition
    (including the one deliberate divergence this class does NOT port: the
    legacy suite's unknown-type default was "informational" — this module's
    ``classify_event_salience`` intentionally surfaces unknown types at
    "warning" + ``unclassified=True`` instead, per Constitution III.11 —
    already pinned by ``TestUnclassifiedSurfacesLoud`` above).
    """

    @pytest.mark.parametrize(
        "event_type",
        [
            EventType.ECONOMIC_CRISIS,
            EventType.CLASS_DECOMPOSITION,
            EventType.SUPERWAGE_CRISIS,
            EventType.UPRISING,
            EventType.ENDGAME_REACHED,
            EventType.RED_BROWN_COUP,
        ],
    )
    def test_named_critical_types_classify_critical(self, event_type: EventType) -> None:
        salience = classify_event_salience(event_type)
        assert salience.tier == "critical", event_type.value
        assert salience.unclassified is False

    @pytest.mark.parametrize(
        "event_type",
        [
            EventType.STATE_REPRESSION,
            EventType.FASCIST_RECRUITMENT,
            EventType.ORGANIZATIONAL_FRACTURE,
            EventType.PATTERN_SHIFT,
        ],
    )
    def test_named_warning_types_classify_warning(self, event_type: EventType) -> None:
        salience = classify_event_salience(event_type)
        assert salience.tier == "warning", event_type.value
        assert salience.unclassified is False

    @pytest.mark.parametrize(
        "event_type",
        [
            EventType.SURPLUS_EXTRACTION,
            EventType.IMPERIAL_SUBSIDY,
            EventType.CONSCIOUSNESS_TRANSMISSION,
        ],
    )
    def test_named_informational_types_classify_informational(self, event_type: EventType) -> None:
        salience = classify_event_salience(event_type)
        assert salience.tier == "informational", event_type.value
        assert salience.unclassified is False


class TestUnclassifiedSurfacesLoud:
    """Constitution III.11: an unclassified type is loud, never buried quiet."""

    def test_an_unclassified_type_surfaces_at_warning_tier_marked_unclassified(self) -> None:
        # POPULATION_DEATH is a real EventType absent from the ported map.
        salience = classify_event_salience(EventType.POPULATION_DEATH)
        assert salience.tier == "warning"
        assert salience.unclassified is True

    def test_unclassified_never_degrades_to_informational(self) -> None:
        salience = classify_event_salience(EventType.ORGANIZATIONAL_ACTION)
        assert salience.tier != "informational"


class TestPortedKeysAreRealEventTypes:
    """The casing-bug regression pin: every ported key is a real lowercase value."""

    def test_every_ported_key_is_a_real_event_type_value(self) -> None:
        valid_values = {member.value for member in EventType}
        for key in EVENT_SEVERITY:
            assert key in valid_values, (
                f"{key!r} does not match any EventType.value — "
                "this is exactly the casing-bug failure mode the porting guards against"
            )

    def test_no_key_is_uppercase(self) -> None:
        for key in EVENT_SEVERITY:
            assert key == key.lower(), f"{key!r} is not lowercase — the frontend's fixed bug"

    def test_ported_tier_counts_match_the_legacy_bridge(self) -> None:
        tiers = list(EVENT_SEVERITY.values())
        assert tiers.count("critical") == 14
        assert tiers.count("warning") == 20
        assert tiers.count("informational") == 13
        assert len(EVENT_SEVERITY) == 47


class TestSubjectResolution:
    """chronicle_subject/dedup_key — ported from eventDedup.ts::eventSubject/dedupKey."""

    def test_node_id_resolves_the_subject(self) -> None:
        event = _event(1, EventType.FASCIST_DRIFT, node_id="C004")
        assert chronicle_subject(event) == "C004"

    def test_org_id_resolves_the_subject(self) -> None:
        event = _event(1, EventType.RED_BROWN_COUP, org_id="tenants-un")
        assert chronicle_subject(event) == "tenants-un"

    def test_source_and_target_fall_back_to_a_pairing(self) -> None:
        event = _event(1, EventType.VALUE_TRANSFER, source_id="t_a", target_id="t_b")
        assert chronicle_subject(event) == "t_a->t_b"

    def test_a_bare_source_falls_back_to_itself(self) -> None:
        event = _event(1, EventType.VALUE_TRANSFER, source_id="t_a")
        assert chronicle_subject(event) == "t_a"

    def test_no_recognizable_field_falls_back_to_global(self) -> None:
        event = _event(1, EventType.ENDGAME_REACHED)
        assert chronicle_subject(event) == "global"

    def test_dedup_key_combines_type_and_subject(self) -> None:
        event = _event(1, EventType.UPRISING, territory_id="t_wayne")
        assert dedup_key(event) == "uprising:t_wayne"


class TestConsecutiveDedup:
    """No two CONSECUTIVE cards share a dedup key (ported first-session.spec.ts contract)."""

    def test_same_type_and_subject_adjacent_collapses_to_one(self) -> None:
        events = [
            _event(845, EventType.UPRISING, summary="first", territory_id="t_wayne"),
            _event(846, EventType.UPRISING, summary="second", territory_id="t_wayne"),
        ]
        collapsed = dedupe_consecutive(events)
        assert len(collapsed) == 1
        assert collapsed[0].summary == "first"

    def test_same_type_different_subject_adjacent_keeps_both(self) -> None:
        events = [
            _event(845, EventType.UPRISING, territory_id="t_wayne"),
            _event(846, EventType.UPRISING, territory_id="t_oakland"),
        ]
        collapsed = dedupe_consecutive(events)
        assert len(collapsed) == 2

    def test_a_b_a_alternation_keeps_all_three(self) -> None:
        events = [
            _event(1, EventType.UPRISING, territory_id="t_wayne"),
            _event(2, EventType.MASS_AWAKENING, target_id="C001"),
            _event(3, EventType.UPRISING, territory_id="t_wayne"),
        ]
        collapsed = dedupe_consecutive(events)
        assert len(collapsed) == 3

    def test_dedup_is_tick_independent_across_a_bulletin_boundary(self) -> None:
        # Same (type, subject), on different ticks, still adjacent in display
        # order — collapses exactly like a same-tick repeat (eventDedup.ts's
        # own "tick-independent dedup identity" rationale).
        events = [
            _event(845, EventType.UPRISING, territory_id="t_wayne"),
            _event(847, EventType.UPRISING, territory_id="t_wayne"),
        ]
        collapsed = dedupe_consecutive(events)
        assert len(collapsed) == 1

    def test_an_empty_sequence_collapses_to_empty(self) -> None:
        assert dedupe_consecutive([]) == ()


class TestAutopause:
    """A critical-tier event sets autopause; warning/informational never do."""

    def test_a_critical_event_fires_autopause(self) -> None:
        events = [_event(1, EventType.UPRISING)]
        state = compute_autopause_state(events)
        assert state.active is True
        assert state.token == AMBER

    def test_a_warning_event_does_not_fire_autopause(self) -> None:
        events = [_event(1, EventType.STATE_REPRESSION)]
        state = compute_autopause_state(events)
        assert state.active is False

    def test_an_informational_event_does_not_fire_autopause(self) -> None:
        events = [_event(1, EventType.SURPLUS_EXTRACTION)]
        state = compute_autopause_state(events)
        assert state.active is False

    def test_no_events_does_not_fire_autopause(self) -> None:
        state = compute_autopause_state([])
        assert state.active is False

    def test_autopause_state_always_exposes_the_amber_token(self) -> None:
        assert compute_autopause_state([]).token == AMBER
        assert compute_autopause_state([_event(1, EventType.UPRISING)]).token == AMBER

    def test_render_returns_none_when_inactive(self) -> None:
        assert render_autopause_indicator(AutopauseState(active=False)) is None

    def test_render_returns_amber_styled_text_when_active(self) -> None:
        rendered = render_autopause_indicator(AutopauseState(active=True, token=AMBER))
        assert rendered is not None
        assert AMBER in rendered.style  # type: ignore[operator]
        assert "AUTOPAUSE" in rendered.plain


class TestVolumeFloors:
    """Narrative (informational) per-tick cap; ORGANIZATIONAL_ACTION rollup."""

    def test_three_informational_events_in_one_tick_cap_to_one_card(self) -> None:
        events = [
            _event(5, EventType.SURPLUS_EXTRACTION, summary="a", source_id="c1"),
            _event(5, EventType.SURPLUS_EXTRACTION, summary="b", source_id="c2"),
            _event(5, EventType.SURPLUS_EXTRACTION, summary="c", source_id="c3"),
        ]
        capped = cap_narrative_events(events)
        assert len(capped) == NARRATIVE_EVENT_CEILING_PER_TICK == 1
        assert capped[0].summary == "a"

    def test_the_cap_is_per_tick_not_global(self) -> None:
        events = [
            _event(5, EventType.SURPLUS_EXTRACTION, source_id="c1"),
            _event(5, EventType.SURPLUS_EXTRACTION, source_id="c2"),
            _event(6, EventType.SURPLUS_EXTRACTION, source_id="c1"),
        ]
        capped = cap_narrative_events(events)
        assert len(capped) == 2
        assert {e.tick for e in capped} == {5, 6}

    def test_critical_and_warning_events_are_never_capped(self) -> None:
        events = [
            _event(5, EventType.SURPLUS_EXTRACTION, source_id="c1"),
            _event(5, EventType.SURPLUS_EXTRACTION, source_id="c2"),
            _event(5, EventType.SURPLUS_EXTRACTION, source_id="c3"),
            _event(5, EventType.UPRISING),
        ]
        capped = cap_narrative_events(events)
        assert len(capped) == 2
        assert capped[-1].event_type == EventType.UPRISING

    def test_four_organizational_action_events_aggregate_to_one_card_with_the_count(
        self,
    ) -> None:
        events = [_event(9, EventType.ORGANIZATIONAL_ACTION) for _ in range(4)]
        aggregated = aggregate_organizational_actions(events)
        assert len(aggregated) == 1
        assert aggregated[0].data["count"] == 4
        assert "4" in aggregated[0].summary

    def test_aggregation_is_per_tick(self) -> None:
        events = [
            _event(9, EventType.ORGANIZATIONAL_ACTION),
            _event(9, EventType.ORGANIZATIONAL_ACTION),
            _event(10, EventType.ORGANIZATIONAL_ACTION),
        ]
        aggregated = aggregate_organizational_actions(events)
        assert len(aggregated) == 2
        by_tick = {e.tick: e.data["count"] for e in aggregated}
        assert by_tick == {9: 2, 10: 1}

    def test_a_lone_organizational_action_is_still_rewritten_singular(self) -> None:
        aggregated = aggregate_organizational_actions([_event(1, EventType.ORGANIZATIONAL_ACTION)])
        assert aggregated[0].data["count"] == 1
        assert "1 organizational action " in aggregated[0].summary
        assert "actions" not in aggregated[0].summary

    def test_non_organizational_action_events_pass_through_untouched(self) -> None:
        events = [_event(1, EventType.UPRISING, summary="mass insurrection")]
        aggregated = aggregate_organizational_actions(events)
        assert aggregated == tuple(events)

    def test_apply_volume_floors_composes_both(self) -> None:
        events = [
            *(_event(3, EventType.ORGANIZATIONAL_ACTION) for _ in range(4)),
            *(_event(3, EventType.SURPLUS_EXTRACTION, source_id=f"c{i}") for i in range(3)),
            _event(3, EventType.UPRISING),
        ]
        floored = apply_volume_floors(events)
        # 1 aggregated org-action card + 1 capped informational + 1 uncapped critical.
        assert len(floored) == 3
        org_cards = [e for e in floored if e.event_type == EventType.ORGANIZATIONAL_ACTION]
        assert len(org_cards) == 1
        assert org_cards[0].data["count"] == 4
