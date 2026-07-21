"""Contract tests for :mod:`babylon.tui.chronicle` (Program 24 P2 WO-27).

Pins the WO's three named behaviors: per-tick grouping (newest-tick-first,
row-ceiling pagination), actor resolution (ported from ``web/game/narrator.py``),
and honest "the wire is quiet" absence for a tick (or a whole stream) with no
events. Fixture-fed only — no engine, no graph, no persistence connection.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError
from rich.panel import Panel
from rich.text import Text

from babylon.models.enums.events import EventType
from babylon.tui.chronicle import (
    CHRONICLE_ROW_CEILING,
    ChronicleEvent,
    TickBulletin,
    bulletin_for_tick,
    chronicle_stream,
    render_bulletin,
    render_chronicle,
    resolve_actor,
)


def _event(
    tick: int,
    event_type: EventType,
    *,
    summary: str = "an event",
    class_names: dict[str, str] | None = None,
    org_names: dict[str, str] | None = None,
    **data: Any,
) -> ChronicleEvent:
    """Build a :class:`ChronicleEvent` with terser call sites than the constructor."""
    return ChronicleEvent(
        tick=tick,
        event_type=event_type,
        summary=summary,
        data=data,
        class_names=class_names,
        org_names=org_names,
    )


class TestChronicleEventShape:
    """Frozen, extra-forbid Pydantic shape — a malformed fixture fails loud."""

    def test_it_rejects_an_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            ChronicleEvent(tick=1, event_type=EventType.UPRISING, summary="x", bogus=True)  # type: ignore[call-arg]

    def test_it_rejects_a_negative_tick(self) -> None:
        with pytest.raises(ValidationError):
            ChronicleEvent(tick=-1, event_type=EventType.UPRISING, summary="x")

    def test_it_rejects_an_empty_summary(self) -> None:
        with pytest.raises(ValidationError):
            ChronicleEvent(tick=1, event_type=EventType.UPRISING, summary="")

    def test_it_coerces_a_plain_lowercase_event_type_string(self) -> None:
        event = ChronicleEvent(tick=1, event_type="uprising", summary="x")  # type: ignore[arg-type]
        assert event.event_type == EventType.UPRISING


class TestActorResolution:
    """Ported from web/game/narrator.py: canonical names, overrides, humanization, absence."""

    def test_mass_awakening_resolves_the_canonical_class_name(self) -> None:
        event = _event(1, EventType.MASS_AWAKENING, target_id="C001")
        assert resolve_actor(event) == "the Periphery Proletariat"

    def test_fascist_drift_resolves_the_canonical_class_name_via_node_id(self) -> None:
        event = _event(1, EventType.FASCIST_DRIFT, node_id="C004")
        assert resolve_actor(event) == "the Labor Aristocracy"

    def test_a_real_scenario_name_override_wins_over_the_canonical_map(self) -> None:
        event = _event(
            1,
            EventType.MASS_AWAKENING,
            target_id="C002",
            class_names={"C002": "Suburban Petty Bourgeoisie"},
        )
        assert resolve_actor(event) == "Suburban Petty Bourgeoisie"

    def test_an_unrecognized_class_id_humanizes_from_the_id_string(self) -> None:
        event = _event(1, EventType.MASS_AWAKENING, target_id="custom_scenario_node")
        assert resolve_actor(event) == "Custom Scenario Node"

    def test_a_missing_class_id_on_a_class_scoped_event_resolves_to_none(self) -> None:
        event = _event(1, EventType.MASS_AWAKENING)
        assert resolve_actor(event) is None

    def test_red_brown_coup_resolves_the_org_via_org_id(self) -> None:
        event = _event(1, EventType.RED_BROWN_COUP, org_id="tenants-un")
        assert resolve_actor(event) == "Tenants-Un"

    def test_an_org_name_override_wins_over_humanization(self) -> None:
        event = _event(
            1,
            EventType.RED_BROWN_COUP,
            org_id="tenants-un",
            org_names={"tenants-un": "Tenants Union"},
        )
        assert resolve_actor(event) == "Tenants Union"

    @pytest.mark.parametrize(
        "event_type",
        [
            EventType.DOCTRINE_TRAP_SPRUNG,
            EventType.DOCTRINE_TRAP_ESCAPED,
            EventType.DOCTRINE_PURGE_FAILED,
        ],
    )
    def test_the_three_doctrine_events_resolve_org_scoped(self, event_type: EventType) -> None:
        event = _event(1, event_type, org_id="uaw_9999")
        assert resolve_actor(event) == "Uaw 9999"

    def test_a_missing_org_id_on_an_org_scoped_event_resolves_to_none(self) -> None:
        event = _event(1, EventType.RED_BROWN_COUP)
        assert resolve_actor(event) is None

    def test_a_place_scoped_event_has_no_actor(self) -> None:
        event = _event(1, EventType.UPRISING, territory_id="t_wayne")
        assert resolve_actor(event) is None


class TestPerTickGrouping:
    """chronicle_stream groups events into newest-tick-first dated bulletins."""

    def test_events_group_into_bulletins_by_tick(self) -> None:
        events = [
            _event(845, EventType.UPRISING, summary="a"),
            _event(847, EventType.UPRISING, summary="b"),
            _event(847, EventType.UPRISING, summary="c"),
        ]
        bulletins = chronicle_stream(events)
        assert [b.tick for b in bulletins] == [847, 845]
        assert len(bulletins[0].events) == 2

    def test_bulletins_are_newest_tick_first(self) -> None:
        events = [
            _event(1, EventType.UPRISING),
            _event(3, EventType.UPRISING),
            _event(2, EventType.UPRISING),
        ]
        bulletins = chronicle_stream(events)
        assert [b.tick for b in bulletins] == [3, 2, 1]

    def test_events_within_a_tick_render_newest_emitted_first(self) -> None:
        events = [
            _event(1, EventType.UPRISING, summary="first emitted"),
            _event(1, EventType.UPRISING, summary="second emitted"),
        ]
        bulletins = chronicle_stream(events)
        assert [e.summary for e in bulletins[0].events] == ["second emitted", "first emitted"]

    def test_an_empty_events_list_yields_no_bulletins(self) -> None:
        assert chronicle_stream([]) == ()

    def test_the_pagination_ceiling_keeps_only_the_newest_rows(self) -> None:
        events = [_event(tick, EventType.UPRISING, summary=str(tick)) for tick in range(250)]
        bulletins = chronicle_stream(events)
        total_rows = sum(len(b.events) for b in bulletins)
        assert total_rows == CHRONICLE_ROW_CEILING
        assert bulletins[0].tick == 249
        assert bulletins[-1].tick == 249 - CHRONICLE_ROW_CEILING + 1

    def test_the_ceiling_default_matches_query_session_events_convention(self) -> None:
        assert CHRONICLE_ROW_CEILING == 200

    def test_chronicle_stream_is_deterministic(self) -> None:
        events = [
            _event(1, EventType.UPRISING, summary="a"),
            _event(2, EventType.UPRISING, summary="b"),
        ]
        assert chronicle_stream(events) == chronicle_stream(events)


class TestBulletinForTick:
    """bulletin_for_tick always answers for the requested tick, quiet or not."""

    def test_it_finds_only_events_for_the_requested_tick(self) -> None:
        events = [
            _event(1, EventType.UPRISING, summary="a"),
            _event(2, EventType.UPRISING, summary="b"),
        ]
        bulletin = bulletin_for_tick(events, 2)
        assert bulletin.tick == 2
        assert [e.summary for e in bulletin.events] == ["b"]

    def test_a_tick_with_no_events_still_returns_a_bulletin(self) -> None:
        events = [_event(1, EventType.UPRISING)]
        bulletin = bulletin_for_tick(events, 9)
        assert bulletin.tick == 9
        assert bulletin.events == ()


class TestHonestAbsence:
    """A tick (or the whole stream) with no events renders "the wire is quiet" (III.11)."""

    def test_a_quiet_tick_renders_the_wire_is_quiet_naming_the_tick(self) -> None:
        bulletin = TickBulletin(tick=848, events=())
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Panel)
        assert isinstance(rendered.renderable, Text)
        assert "the wire is quiet" in rendered.renderable.plain
        assert "0848" in rendered.renderable.plain

    def test_an_empty_stream_renders_the_wire_is_quiet(self) -> None:
        rendered = render_chronicle(())
        assert isinstance(rendered, Text)
        assert "the wire is quiet" in rendered.plain


class TestRendering:
    """Populated bulletins show the resolved actor (when any) plus the summary."""

    def test_a_populated_bulletin_shows_the_actor_and_the_summary(self) -> None:
        bulletin = TickBulletin(
            tick=847,
            events=(
                _event(847, EventType.MASS_AWAKENING, summary="stirs to action", target_id="C001"),
            ),
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Panel)
        assert isinstance(rendered.renderable, Text)
        plain = rendered.renderable.plain
        assert "the Periphery Proletariat" in plain
        assert "stirs to action" in plain

    def test_an_actorless_event_shows_only_the_summary(self) -> None:
        bulletin = TickBulletin(
            tick=847, events=(_event(847, EventType.UPRISING, summary="mass insurrection"),)
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Panel)
        assert isinstance(rendered.renderable, Text)
        assert rendered.renderable.plain == "mass insurrection"

    def test_multiple_events_render_one_line_each_in_order(self) -> None:
        bulletin = TickBulletin(
            tick=1,
            events=(
                _event(1, EventType.UPRISING, summary="first"),
                _event(1, EventType.UPRISING, summary="second"),
            ),
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Panel)
        assert isinstance(rendered.renderable, Text)
        assert rendered.renderable.plain.splitlines() == ["first", "second"]

    def test_two_renders_of_the_same_bulletin_are_identical(self) -> None:
        bulletin = TickBulletin(tick=1, events=(_event(1, EventType.UPRISING, summary="x"),))
        first = render_bulletin(bulletin)
        second = render_bulletin(bulletin)
        assert isinstance(first, Panel)
        assert isinstance(second, Panel)
        assert isinstance(first.renderable, Text)
        assert isinstance(second.renderable, Text)
        assert first.renderable.plain == second.renderable.plain
