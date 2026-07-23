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
from rich.text import Text

from babylon.models.enums.events import EventType
from babylon.tui.chronicle import (
    CHRONICLE_ROW_CEILING,
    ChronicleEvent,
    TickBulletin,
    bulletin_for_tick,
    chronicle_rows,
    chronicle_stream,
    render_bulletin,
    render_chronicle,
    resolve_actor,
    resolve_navigable_subject,
)
from babylon.tui.theme import AMBER, BONE, CRIMSON


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
        assert isinstance(rendered, Text)
        assert "the wire is quiet" in rendered.plain
        assert "0848" in rendered.plain

    def test_an_empty_stream_renders_the_wire_is_quiet(self) -> None:
        rendered = render_chronicle(())
        assert isinstance(rendered, Text)
        assert "the wire is quiet" in rendered.plain


class TestRendering:
    """Populated bulletins show the resolved actor (when any) plus the summary.

    Unit "selection-unwrap" (shell-interconnect): ``render_bulletin`` returns a bare,
    selectable ``Text`` rather than a ``Panel`` — the crimson-box/gold-title chrome moved
    to ``#chronicle-rail``'s own CSS (``babylon.tui.app``); the tick number that used to
    live ONLY in the Panel's ``title`` is now the body's own first line instead ("T0847"),
    bold gold, so a bulletin rendered standalone never loses its date.
    """

    def test_a_populated_bulletin_shows_the_actor_and_the_summary(self) -> None:
        bulletin = TickBulletin(
            tick=847,
            events=(
                _event(847, EventType.MASS_AWAKENING, summary="stirs to action", target_id="C001"),
            ),
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        plain = rendered.plain
        assert "T0847" in plain
        assert "the Periphery Proletariat" in plain
        assert "stirs to action" in plain

    def test_an_actorless_event_shows_only_the_tick_header_and_the_summary(self) -> None:
        bulletin = TickBulletin(
            tick=847, events=(_event(847, EventType.UPRISING, summary="mass insurrection"),)
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        assert rendered.plain == "T0847\nmass insurrection"

    def test_multiple_events_render_one_line_each_in_order_after_the_tick_header(self) -> None:
        bulletin = TickBulletin(
            tick=1,
            events=(
                _event(1, EventType.UPRISING, summary="first"),
                _event(1, EventType.UPRISING, summary="second"),
            ),
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        assert rendered.plain.splitlines() == ["T0001", "first", "second"]

    def test_two_renders_of_the_same_bulletin_are_identical(self) -> None:
        bulletin = TickBulletin(tick=1, events=(_event(1, EventType.UPRISING, summary="x"),))
        first = render_bulletin(bulletin)
        second = render_bulletin(bulletin)
        assert isinstance(first, Text)
        assert isinstance(second, Text)
        assert first.plain == second.plain


class TestRenderChronicleStacksSelectableText:
    """``render_chronicle`` concatenates bulletins into ONE bare ``Text`` (never a
    ``rich.console.Group`` of Panels — both a ``Panel`` and a ``Group`` are opaque to
    ``Widget.get_selection``, per ``render_bulletin``'s own "selection-unwrap" docstring)."""

    def test_multiple_bulletins_stack_newest_first_each_keeping_its_own_tick_header(self) -> None:
        bulletins = (
            TickBulletin(tick=2, events=(_event(2, EventType.UPRISING, summary="second tick"),)),
            TickBulletin(tick=1, events=(_event(1, EventType.UPRISING, summary="first tick"),)),
        )
        rendered = render_chronicle(bulletins)
        assert isinstance(rendered, Text)
        plain = rendered.plain
        assert plain.index("T0002") < plain.index("second tick") < plain.index("T0001")
        assert "first tick" in plain

    def test_two_renders_of_the_same_stream_are_identical(self) -> None:
        bulletins = (TickBulletin(tick=1, events=(_event(1, EventType.UPRISING, summary="x"),)),)
        first = render_chronicle(bulletins)
        second = render_chronicle(bulletins)
        assert isinstance(first, Text)
        assert isinstance(second, Text)
        assert first.plain == second.plain


class TestSeverityColoring:
    """Program 24 P3: the summary is colored by its resolved severity tier —
    the flat-BONE styling this unit fixes (every event used to render
    identically regardless of tier)."""

    def test_a_critical_tier_event_renders_bold_crimson(self) -> None:
        # UPRISING is a declared CROSSING/TERMINAL_ADJACENT row -> critical.
        bulletin = TickBulletin(
            tick=1, events=(_event(1, EventType.UPRISING, summary="mass insurrection"),)
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        styles = [span.style for span in rendered.spans]
        assert f"bold {CRIMSON}" in styles

    def test_a_warning_tier_event_renders_amber(self) -> None:
        # STATE_REPRESSION is a declared ACT row with salience_floor="warning".
        bulletin = TickBulletin(
            tick=1, events=(_event(1, EventType.STATE_REPRESSION, summary="crackdown ordered"),)
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        styles = [span.style for span in rendered.spans]
        assert AMBER in styles

    def test_an_informational_tier_event_renders_plain_bone(self) -> None:
        # SURPLUS_EXTRACTION is a declared FLOW row with salience_floor="informational".
        bulletin = TickBulletin(
            tick=1, events=(_event(1, EventType.SURPLUS_EXTRACTION, summary="value flows"),)
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        styles = [span.style for span in rendered.spans]
        assert BONE in styles

    def test_an_unclassified_event_type_renders_at_the_loud_amber_warning_floor(self) -> None:
        # CONSCIOUSNESS_SHIFT carries no SEVERITY_TAXONOMY row (Constitution III.11's
        # loud unclassified floor resolves it to "warning", never a silent informational).
        bulletin = TickBulletin(
            tick=1, events=(_event(1, EventType.CONSCIOUSNESS_SHIFT, summary="a shift"),)
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        styles = [span.style for span in rendered.spans]
        assert AMBER in styles

    def test_different_tiers_in_the_same_bulletin_are_colored_independently(self) -> None:
        bulletin = TickBulletin(
            tick=1,
            events=(
                _event(1, EventType.UPRISING, summary="critical line"),
                _event(1, EventType.SURPLUS_EXTRACTION, summary="informational line"),
            ),
        )
        rendered = render_bulletin(bulletin)
        assert isinstance(rendered, Text)
        styles = [span.style for span in rendered.spans]
        assert f"bold {CRIMSON}" in styles
        assert BONE in styles


class TestResolveNavigableSubject:
    """Unit "chronicle-row-nav-salience" (shell-interconnect):
    ``resolve_actor``'s id-preserving sibling — resolves a real, dispatchable
    subject id rather than a display name."""

    def test_mass_awakening_resolves_a_social_class_subject_id(self) -> None:
        event = _event(1, EventType.MASS_AWAKENING, target_id="C001")
        assert resolve_navigable_subject(event) == "social_class/C001"

    def test_fascist_drift_resolves_a_social_class_subject_id_via_node_id(self) -> None:
        event = _event(1, EventType.FASCIST_DRIFT, node_id="C004")
        assert resolve_navigable_subject(event) == "social_class/C004"

    def test_red_brown_coup_resolves_an_organization_subject_id(self) -> None:
        event = _event(1, EventType.RED_BROWN_COUP, org_id="tenants-un")
        assert resolve_navigable_subject(event) == "organization/tenants-un"

    @pytest.mark.parametrize(
        "event_type",
        [
            EventType.DOCTRINE_TRAP_SPRUNG,
            EventType.DOCTRINE_TRAP_ESCAPED,
            EventType.DOCTRINE_PURGE_FAILED,
        ],
    )
    def test_the_three_doctrine_events_resolve_an_organization_subject_id(
        self, event_type: EventType
    ) -> None:
        event = _event(1, event_type, org_id="uaw_9999")
        assert resolve_navigable_subject(event) == "organization/uaw_9999"

    def test_a_missing_class_id_on_a_class_scoped_event_resolves_to_none(self) -> None:
        event = _event(1, EventType.MASS_AWAKENING)
        assert resolve_navigable_subject(event) is None

    def test_a_missing_org_id_on_an_org_scoped_event_resolves_to_none(self) -> None:
        event = _event(1, EventType.RED_BROWN_COUP)
        assert resolve_navigable_subject(event) is None

    def test_a_place_scoped_event_with_a_county_fips_bearing_anchor_resolves_a_county_subject(
        self,
    ) -> None:
        event = _event(
            1,
            EventType.UPRISING,
            node_id="C001",
            anchor={
                "territory_id": "T001",
                "territory_name": "Wayne County",
                "county_fips": "26163",
            },
        )
        assert resolve_navigable_subject(event) == "county/26163"

    def test_a_place_scoped_event_with_an_anchor_but_no_county_fips_resolves_to_none(self) -> None:
        """The VERIFIED-honest-gap case (see ``territory_anchor.py``'s own
        docstring): every one of Wayne's live territory nodes anchors with
        ``county_fips=None`` today — this must stay a visible, non-navigable
        row, never a fabricated ``"county/None"`` subject."""
        event = _event(
            1,
            EventType.UPRISING,
            node_id="C001",
            anchor={"territory_id": "T001", "territory_name": "Wayne County", "county_fips": None},
        )
        assert resolve_navigable_subject(event) is None

    def test_an_event_with_no_actor_and_no_anchor_resolves_to_none(self) -> None:
        event = _event(1, EventType.SURPLUS_EXTRACTION, source_id="C001", target_id="C003")
        assert resolve_navigable_subject(event) is None

    def test_class_org_resolution_takes_priority_over_an_anchor(self) -> None:
        """FASCIST_DRIFT can carry BOTH a class-scoped ``node_id`` (resolve_actor's
        own table) AND a chronicle_adapter-stamped territory anchor (the same
        field) — the class subject wins, matching the actor ``resolve_actor``
        itself would print for this event."""
        event = _event(
            1,
            EventType.FASCIST_DRIFT,
            node_id="C002",
            anchor={
                "territory_id": "T001",
                "territory_name": "Wayne County",
                "county_fips": "26163",
            },
        )
        assert resolve_navigable_subject(event) == "social_class/C002"


class TestChronicleRows:
    """Unit "chronicle-row-nav-salience" (shell-interconnect):
    ``render_chronicle``'s row-addressable sibling."""

    def test_an_empty_stream_yields_one_placeholder_row(self) -> None:
        rows = chronicle_rows(())
        assert len(rows) == 1
        subject, text = rows[0]
        assert subject is None
        assert isinstance(text, Text)
        assert "the wire is quiet" in text.plain

    def test_a_quiet_bulletin_yields_one_non_navigable_row_naming_its_tick(self) -> None:
        rows = chronicle_rows((TickBulletin(tick=848, events=()),))
        assert len(rows) == 1
        subject, text = rows[0]
        assert subject is None
        assert "0848" in text.plain
        assert "the wire is quiet" in text.plain

    def test_a_populated_bulletin_yields_a_header_row_then_one_row_per_event(self) -> None:
        bulletin = TickBulletin(
            tick=1,
            events=(
                _event(1, EventType.MASS_AWAKENING, summary="stirs", target_id="C001"),
                _event(1, EventType.UPRISING, summary="mass insurrection"),
            ),
        )
        rows = chronicle_rows((bulletin,))
        assert len(rows) == 3
        header_subject, header_text = rows[0]
        assert header_subject is None
        assert header_text.plain == "T0001"
        awakening_subject, awakening_text = rows[1]
        assert awakening_subject == "social_class/C001"
        assert "stirs" in awakening_text.plain
        uprising_subject, uprising_text = rows[2]
        assert uprising_subject is None  # UPRISING with no anchor: no dispatchable subject
        assert "mass insurrection" in uprising_text.plain

    def test_multiple_bulletins_stay_newest_tick_first(self) -> None:
        bulletins = (
            TickBulletin(tick=2, events=(_event(2, EventType.UPRISING, summary="second"),)),
            TickBulletin(tick=1, events=(_event(1, EventType.UPRISING, summary="first"),)),
        )
        rows = chronicle_rows(bulletins)
        headers = [text.plain for subject, text in rows if subject is None and "T" in text.plain]
        assert headers[0] == "T0002"
        assert headers[1] == "T0001"

    def test_row_text_matches_render_bulletins_own_per_line_content(self) -> None:
        """Stacking ``chronicle_rows``' own text bodies reproduces
        ``render_bulletin``'s output line-for-line."""
        bulletin = TickBulletin(
            tick=7,
            events=(
                _event(7, EventType.UPRISING, summary="first"),
                _event(7, EventType.UPRISING, summary="second"),
            ),
        )
        rows = chronicle_rows((bulletin,))
        row_lines = [text.plain for _subject, text in rows]
        assert row_lines == ["T0007", "first", "second"]
        assert render_bulletin(bulletin).plain == "\n".join(row_lines)
