"""The Chronicle — tick bulletins as dated pages (design canon S8).

S8 (``ai/_inbox/tui/20260719archiveinterfacedesign.md``): *"Tick bulletins as
dated pages — the daily-notes idiom where the daily note IS the tick. Event
ledger as a browsable stream."* This module renders that stream from a
fixture list of events — no engine, no graph, no persistence connection —
matching the keel's fixture-first discipline for Lane W widgets.

**No unified actor field.** ``WorldState.events`` holds heterogeneous
``SimulationEvent`` subclasses (Sprint 3.1) that each declare their own
fields — a class-scoped event names its subject via ``target_id``/``node_id``,
an org-scoped one via ``org_id``, a place-scoped one via ``territory_id``,
and many events have no single-entity subject at all. :func:`resolve_actor`
below **ports** (not re-derives) ``web/game/narrator.py``'s
``_subject_from_class_id``/``_subject_from_org_id`` prior art and its
per-event-type field dispatch: the same canonical class-id names, the same
"a real per-scenario name overrides the canonical map, else humanize the raw
id" resolution order, reimplemented against the frozen :class:`ChronicleEvent`
shape instead of a raw ``dict``. ``narrator.py`` itself is not imported —
Constitution III's "AI observes, never controls" boundary keeps that module
import-free of ``babylon.*``, and it is legacy (web/ is superseded by this
client) — so the two functions are copied here, not reused via import.

**Pagination ceiling, newest-first.** :func:`chronicle_stream` mirrors the
``PostgresRuntime.query_session_events(limit=200)`` convention (spec-092):
rows sort newest-first (``tick`` descending, then latest-emitted within a
tick), then a hard :data:`CHRONICLE_ROW_CEILING` caps the total — a
browsable stream is never an unbounded scroll.

**Honest absence (Constitution III.11).** A tick with nothing recorded — or
a wholly empty fixture — renders the literal line "the wire is quiet",
naming the tick it was asked about rather than an unattributable blank
panel. This mirrors :mod:`babylon.tui.peek`'s "no attributed data" marker
and :mod:`babylon.tui.directives`'s ``▌`` absence convention.

**Severity-tier coloring is wired** (Program 24 P3): :func:`_event_line`
colors each event's summary by its resolved
:data:`~babylon.models.event_severity.SeverityTier` — critical bold
:data:`~babylon.tui.theme.CRIMSON`, warning
:data:`~babylon.tui.theme.AMBER` (including the loud unclassified floor),
informational plain :data:`~babylon.tui.theme.BONE` — reading
:func:`~babylon.models.event_severity.resolve_severity` directly (NOT
through :mod:`babylon.tui.chronicle_salience`, which itself imports
:class:`ChronicleEvent` from here; importing back would cycle).

**Dedup/volume-floor/autopause-indicator wiring remain out of scope here**
(WO-48's remaining pieces): :mod:`babylon.tui.chronicle_salience`'s
:func:`~babylon.tui.chronicle_salience.dedupe_consecutive`,
:func:`~babylon.tui.chronicle_salience.apply_volume_floors`, and
:func:`~babylon.tui.chronicle_salience.compute_autopause_state` are not
applied by any caller yet — this unit renders the raw (severity-colored)
stream faithfully, on top of the shapes this module defines.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field
from rich.text import Text

from babylon.models.enums.events import EventType
from babylon.models.event_severity import resolve_severity
from babylon.tui.theme import AMBER, BONE, CRIMSON, GOLD

__all__ = [
    "CHRONICLE_ROW_CEILING",
    "ChronicleEvent",
    "TickBulletin",
    "resolve_actor",
    "chronicle_stream",
    "bulletin_for_tick",
    "render_bulletin",
    "render_chronicle",
]

CHRONICLE_ROW_CEILING: Final[int] = 200
"""Newest-first pagination ceiling, matching
``PostgresRuntime.query_session_events(limit=200)`` (spec-092): a browsable
stream is never an unbounded scroll."""

_WIRE_QUIET: Final[str] = "the wire is quiet"
"""The honest-absence line for a tick (or a whole stream) with no events —
never a blank plate (Constitution III.11)."""


class ChronicleEvent(BaseModel):
    """One event the Chronicle stream renders — a ``WorldState.events``-shaped record.

    :param tick: the simulation tick the event occurred on.
    :param event_type: the :class:`~babylon.models.enums.events.EventType`
        this event carries.
    :param summary: a human-readable one-line summary (mirrors
        ``tick_event.summary``).
    :param data: the event's structured payload — the same shape
        ``SimulationEvent`` subclasses (and ``tick_event.detail``) carry,
        keyed by whatever fields that event type declares (``target_id``,
        ``node_id``, ``org_id``, ``territory_id``, ...). There is no unified
        actor field across event types, so :func:`resolve_actor` reads a
        named key out of this bag per event type rather than a fixed field.
    :param class_names: real per-scenario social-class id -> display name
        overrides (mirrors the legacy bridge's ``meta["class_names"]``,
        stamped onto each event as ``_class_names``); wins over the
        canonical map when present.
    :param org_names: real per-scenario organization id -> display name
        overrides (mirrors ``meta["org_names"]``/``_org_names``);
        organizations have no small fixed canonical set the way social
        classes do, so without this every org id humanizes from its raw
        string.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tick: int = Field(ge=0)
    event_type: EventType
    summary: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)
    class_names: dict[str, str] | None = None
    org_names: dict[str, str] | None = None


class TickBulletin(BaseModel):
    """One dated page: every rendered event for a single tick, stream order.

    :param tick: the tick this bulletin is dated to — the "daily note" (S8).
    :param events: the tick's events, newest-emitted-first; empty when the
        tick has genuinely nothing recorded (the honest "wire is quiet" case
        :func:`render_bulletin` renders).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tick: int = Field(ge=0)
    events: tuple[ChronicleEvent, ...] = ()


# --------------------------------------------------------------------------- #
# Actor resolution — ported from web/game/narrator.py (not imported: that
# module is import-free of babylon.* by Constitution III, and legacy/web/ is
# superseded by this client).
# --------------------------------------------------------------------------- #

_CLASS_ID_NAMES: Final[dict[str, str]] = {
    "C001": "the Periphery Proletariat",
    "C002": "the Comprador Bourgeoisie",
    "C003": "the Core Bourgeoisie",
    "C004": "the Labor Aristocracy",
    "C005": "the Carceral Enforcers",
    "C006": "the Internal Proletariat",
}
"""Canonical social-class node id -> display name (ported verbatim from
``web/game/narrator.py::_CLASS_ID_NAMES`` — the six imperial-circuit
scenario entities reused across scenarios under this name unless a
:attr:`ChronicleEvent.class_names` override says otherwise)."""


def _subject_from_class_id(class_id: str, names: dict[str, str] | None = None) -> str:
    """Resolve a social-class node id to a display subject — never a place.

    Ported from ``web/game/narrator.py::_subject_from_class_id``. ``names``
    (a scenario's real per-run entity names) wins outright — scenarios reuse
    canonical ids under different names, and a confidently wrong canonical
    name is a fabrication. Without a real name, known canonical ids
    (C001-C006) get their registry class name; unrecognized ids (a
    custom-scenario class node) are humanized from the id string itself
    rather than guessing.

    :param class_id: the social-class node id to resolve.
    :param names: the event's real per-scenario override map, or ``None``.
    :returns: the resolved display subject.
    """
    if names and class_id in names:
        return names[class_id]
    if class_id in _CLASS_ID_NAMES:
        return _CLASS_ID_NAMES[class_id]
    return class_id.replace("_", " ").title()


def _subject_from_org_id(org_id: str, names: dict[str, str] | None = None) -> str:
    """Resolve an organization node id to a display subject — never a place.

    Ported from ``web/game/narrator.py::_subject_from_org_id``. Mirrors
    :func:`_subject_from_class_id`, but organizations have no small fixed
    canonical set the way social classes do — every scenario creates its
    own — so there is no hardcoded fallback map here, only an honest
    humanization of the raw id when no real name is available.

    :param org_id: the organization node id to resolve.
    :param names: the event's real per-scenario override map, or ``None``.
    :returns: the resolved display subject.
    """
    if names and org_id in names:
        return names[org_id]
    return org_id.replace("_", " ").title()


_CLASS_SCOPED_SUBJECT_FIELD: Final[dict[EventType, str]] = {
    EventType.MASS_AWAKENING: "target_id",
    EventType.FASCIST_DRIFT: "node_id",
}
"""EventType -> the :attr:`ChronicleEvent.data` key holding the affected
social-class node id (ported from
``web/game/narrator.py::_CLASS_SCOPED_SUBJECT_FIELD``). MASS_AWAKENING and
FASCIST_DRIFT have no place to report — resolving through here keeps their
narration honest instead of inventing a location."""

_ORG_SCOPED_SUBJECT_FIELD: Final[dict[EventType, str]] = {
    EventType.RED_BROWN_COUP: "org_id",
    EventType.DOCTRINE_TRAP_SPRUNG: "org_id",
    EventType.DOCTRINE_TRAP_ESCAPED: "org_id",
    EventType.DOCTRINE_PURGE_FAILED: "org_id",
}
"""EventType -> the :attr:`ChronicleEvent.data` key holding the affected
organization node id (ported from
``web/game/narrator.py::_ORG_SCOPED_SUBJECT_FIELD``). RED_BROWN_COUP has no
place to report; the three ADR073 Doctrine Tree events are org-scoped the
same way — a party's trap/congress outcome has no place, only the
organization it happened to."""


def resolve_actor(event: ChronicleEvent) -> str | None:
    """Resolve ``event``'s subject/actor, or ``None`` if it carries none.

    ``WorldState.events`` has no unified actor field — ``SimulationEvent``
    subclasses vary their own fields — so this mirrors ``narrator.py``'s
    ``_resolve_location`` dispatch: class-scoped and org-scoped event types
    (:data:`_CLASS_SCOPED_SUBJECT_FIELD`, :data:`_ORG_SCOPED_SUBJECT_FIELD`)
    resolve through their own named ``data`` field; every other event type —
    place-scoped or system-wide — has no single-entity actor to report and
    resolves to ``None``. A class/org-scoped event type whose id field is
    missing or malformed *also* resolves to ``None`` rather than a fabricated
    "unidentified" placeholder (Constitution III.11: an honest absence, not
    a plausible-looking default).

    :param event: the event to resolve.
    :returns: the resolved subject string, or ``None`` when the event has no
        actor to report.
    """
    class_field = _CLASS_SCOPED_SUBJECT_FIELD.get(event.event_type)
    if class_field is not None:
        class_id = event.data.get(class_field)
        if isinstance(class_id, str) and class_id:
            return _subject_from_class_id(class_id, event.class_names)
        return None

    org_field = _ORG_SCOPED_SUBJECT_FIELD.get(event.event_type)
    if org_field is not None:
        org_id = event.data.get(org_field)
        if isinstance(org_id, str) and org_id:
            return _subject_from_org_id(org_id, event.org_names)
        return None

    return None


# --------------------------------------------------------------------------- #
# Per-tick grouping + pagination.
# --------------------------------------------------------------------------- #


def chronicle_stream(
    events: Sequence[ChronicleEvent], *, limit: int = CHRONICLE_ROW_CEILING
) -> tuple[TickBulletin, ...]:
    """Group a raw event stream into newest-tick-first dated bulletins.

    Mirrors the ``PostgresRuntime.query_session_events(limit=200)``
    convention: rows sort newest-first (highest tick, then latest-emitted
    within a tick — the ``ORDER BY tick DESC, event_id DESC`` shape, with a
    fixture's list position standing in for ``event_id`` since fixtures
    carry no primary key), then the top ``limit`` rows are kept before
    grouping. Only ticks actually present in ``events`` produce a bulletin —
    this function has no notion of "the full tick range", so a genuinely
    quiet tick between two active ones is simply absent from the result
    (see :func:`bulletin_for_tick` for looking up one specific tick, quiet
    or not).

    :param events: the raw fixture event list, in emission order.
    :param limit: the row ceiling (default :data:`CHRONICLE_ROW_CEILING`).
    :returns: bulletins newest-tick-first; ``()`` when ``events`` is empty —
        the "nothing has happened yet" case :func:`render_chronicle` renders
        honestly.
    """
    ranked = sorted(enumerate(events), key=lambda item: (item[1].tick, item[0]), reverse=True)
    capped = ranked[:limit]

    bulletins: list[TickBulletin] = []
    current_tick: int | None = None
    current_events: list[ChronicleEvent] = []
    for _, event in capped:
        if event.tick != current_tick:
            if current_tick is not None:
                bulletins.append(TickBulletin(tick=current_tick, events=tuple(current_events)))
            current_tick = event.tick
            current_events = []
        current_events.append(event)
    if current_tick is not None:
        bulletins.append(TickBulletin(tick=current_tick, events=tuple(current_events)))
    return tuple(bulletins)


def bulletin_for_tick(
    events: Sequence[ChronicleEvent], tick: int, *, limit: int = CHRONICLE_ROW_CEILING
) -> TickBulletin:
    """Build one dated page for exactly ``tick`` — always returns a bulletin.

    Unlike :func:`chronicle_stream` (which only ever produces bulletins for
    ticks that have events), this always answers for the requested tick,
    even one with nothing recorded: the daily-note idiom (S8) means a tick
    can have its own blank page, distinct from "the whole vault has no
    history yet" (:func:`chronicle_stream` returning ``()``).

    :param events: the raw fixture event list.
    :param tick: the tick to page to.
    :param limit: the row ceiling within this one tick.
    :returns: the tick's bulletin, newest-emitted-first, ``events=()`` when
        the tick has nothing recorded.
    """
    matching = [event for event in events if event.tick == tick]
    matching.reverse()  # newest-emitted-first, matching chronicle_stream's tie-break
    return TickBulletin(tick=tick, events=tuple(matching[:limit]))


# --------------------------------------------------------------------------- #
# Rendering.
# --------------------------------------------------------------------------- #


_SEVERITY_STYLE: Final[dict[str, str]] = {
    "critical": f"bold {CRIMSON}",
    "warning": AMBER,
    "informational": BONE,
}
"""Summary-text style per resolved :data:`~babylon.models.event_severity.SeverityTier`
(Program 24 P3). The loud unclassified floor (:attr:`~babylon.models.event_severity.
EventSeverity.unclassified`) resolves its tier to ``"warning"`` already
(Constitution III.11), so it renders :data:`~babylon.tui.theme.AMBER` here with no
separate branch — an unclassified event is never silently indistinguishable from a
real informational one."""


def _event_line(event: ChronicleEvent) -> Text:
    """Render one event's line: ``"{actor}: {summary}"`` or bare ``summary``.

    The summary is colored by :func:`~babylon.models.event_severity.resolve_severity`'s
    resolved tier (Program 24 P3) — critical bold :data:`~babylon.tui.theme.CRIMSON`,
    warning :data:`~babylon.tui.theme.AMBER`, informational plain
    :data:`~babylon.tui.theme.BONE` — so the loudest "the world is alive" signal (a
    critical event) is visually distinct from routine flow, not flatly uniform. The
    actor prefix (the "who," not the "what") stays bold :data:`~babylon.tui.theme.GOLD`
    regardless of tier.

    :param event: the event to render.
    :returns: the formatted line; no actor prefix when :func:`resolve_actor`
        returns ``None`` (never a fabricated one).
    """
    line = Text()
    actor = resolve_actor(event)
    if actor is not None:
        line.append(f"{actor}: ", style=f"bold {GOLD}")
    tier = resolve_severity(event.event_type).tier
    line.append(event.summary, style=_SEVERITY_STYLE[tier])
    return line


def render_bulletin(bulletin: TickBulletin) -> Text:
    """Render one dated page for ``bulletin`` as a bare, selectable :class:`~rich.text.Text`.

    Unit "selection-unwrap" (shell-interconnect): this used to return a
    :class:`~rich.panel.Panel` with the tick number as its ``title`` — a
    Rich renderable :meth:`~babylon.tui.widget.Widget.get_selection`
    (``widget.py:4213-4232``) cannot extract text from, since ``_render()``
    only recognizes bare :class:`~rich.text.Text`/:class:`~textual.content.
    Content`. The crimson box + gold title moved to ``#chronicle-rail``'s own
    CSS ``border``/``border-title-*`` (:mod:`babylon.tui.app`); the tick
    number that used to live ONLY in the Panel title is now the first
    inline line of the returned body instead, bold gold, so a bulletin
    rendered standalone (or stacked by :func:`render_chronicle`) never loses
    its own date. An empty bulletin already named its own tick inline in the
    honest "the wire is quiet" line (Constitution III.11: the absence always
    names what was looked up), so no separate header line is added there —
    doing so would repeat the tick number for no reason.

    :param bulletin: the tick's bulletin to render.
    :returns: the bulletin's selectable body text.
    """
    if not bulletin.events:
        return Text(f"▌ T{bulletin.tick:04d} — {_WIRE_QUIET}", style=f"bold {CRIMSON}")
    body = Text()
    body.append(f"T{bulletin.tick:04d}\n", style=f"bold {GOLD}")
    for index, event in enumerate(bulletin.events):
        if index:
            body.append("\n")
        body.append(_event_line(event))
    return body


def render_chronicle(bulletins: Sequence[TickBulletin]) -> Text:
    """Render the full browsable stream: bulletins stacked newest-tick-first.

    Unit "selection-unwrap": returns one bare :class:`~rich.text.Text` (each
    bulletin's own :func:`render_bulletin` text concatenated, separated by a
    blank line) rather than a :class:`~rich.console.Group` of Panels — a
    ``Group`` is, like a ``Panel``, opaque to ``Widget.get_selection`` (only
    ``Text``/``Content`` qualify), so stacking Panels used to make the whole
    ``#chronicle-rail`` unselectable even though each bulletin's own body was
    plain text underneath.

    :param bulletins: the tick bulletins to render (as produced by
        :func:`chronicle_stream`).
    :returns: the concatenated, selectable stream text, or the bare
        "the wire is quiet" line when ``bulletins`` is empty.
    """
    if not bulletins:
        return Text(f"▌ {_WIRE_QUIET}", style=f"bold {CRIMSON}")
    combined = Text()
    for index, bulletin in enumerate(bulletins):
        if index:
            combined.append("\n\n")
        combined.append_text(render_bulletin(bulletin))
    return combined
