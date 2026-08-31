"""The Chronicle event record — a ``WorldState.events``-shaped read model.

Relocated from ``babylon.tui.chronicle`` by the Amendment AF (ADR186)
deletion ceremony: that module split "the Chronicle stream" into a data
half (this file's contents) and a Rich/terminal-rendering half
(``render_bulletin``/``render_chronicle``/``chronicle_rows``, the
severity-colored line formatting for the deleted Ratatui client). Only the
data half survives — :class:`ChronicleEvent` and :func:`resolve_actor` are
real, durable dependencies of :mod:`babylon.game.session` (the campaign
composition root), :mod:`babylon.game.chronicle_adapter`, and
:mod:`babylon.game.pacing`, independent of any specific client; the
rendering half had no consumer outside the deleted client's own host/tests
and did not survive the move.

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
import-free of ``babylon.*``, and it is legacy (web/ is superseded) — so the
two functions are copied here, not reused via import.

**Pagination ceiling, newest-first.** :func:`chronicle_stream` preserves the
retired Python event-query convention's ``limit=200`` bound (spec-092):
rows sort newest-first (``tick`` descending, then latest-emitted within a
tick), then a hard :data:`CHRONICLE_ROW_CEILING` caps the total — a
browsable stream is never an unbounded scroll.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums.events import EventType

__all__ = [
    "CHRONICLE_ROW_CEILING",
    "ChronicleEvent",
    "TickBulletin",
    "resolve_actor",
    "resolve_navigable_subject",
    "chronicle_stream",
    "bulletin_for_tick",
]

CHRONICLE_ROW_CEILING: Final[int] = 200
"""Newest-first pagination ceiling from the frozen spec-092 event contract."""


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
    """One dated page: every event for a single tick, stream order.

    :param tick: the tick this bulletin is dated to — the "daily note" (S8).
    :param events: the tick's events, newest-emitted-first; empty when the
        tick has genuinely nothing recorded.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tick: int = Field(ge=0)
    events: tuple[ChronicleEvent, ...] = ()


# --------------------------------------------------------------------------- #
# Actor resolution — ported from web/game/narrator.py (not imported: that
# module is import-free of babylon.* by Constitution III, and legacy/web/ is
# superseded).
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


def resolve_navigable_subject(event: ChronicleEvent) -> str | None:
    """Resolve ``event``'s dispatchable subject id, or ``None`` if it has none.

    :func:`resolve_actor`'s id-preserving sibling: where that function
    answers "what do I print as this event's actor" (a display NAME), this
    one answers "what real subject id (``"<kind>/<id>"``) does this event
    open" — the same class-scoped/org-scoped dispatch
    (:data:`_CLASS_SCOPED_SUBJECT_FIELD`/:data:`_ORG_SCOPED_SUBJECT_FIELD`),
    reused rather than re-derived, PLUS a place-scoped fallback through
    ``event.data["anchor"]`` for the event types :func:`resolve_actor` has no
    actor for at all.

    A class/org-scoped event whose id field is missing or malformed resolves
    to ``None`` here too — the same honest-absence discipline
    :func:`resolve_actor` already follows, never a fabricated or
    best-guess subject (Constitution III.11).

    :param event: the event to resolve.
    :returns: the resolved subject id, or ``None`` when the event has no
        dispatchable subject.
    """
    class_field = _CLASS_SCOPED_SUBJECT_FIELD.get(event.event_type)
    if class_field is not None:
        class_id = event.data.get(class_field)
        if isinstance(class_id, str) and class_id:
            return f"social_class/{class_id}"
        return None

    org_field = _ORG_SCOPED_SUBJECT_FIELD.get(event.event_type)
    if org_field is not None:
        org_id = event.data.get(org_field)
        if isinstance(org_id, str) and org_id:
            return f"organization/{org_id}"
        return None

    anchor = event.data.get("anchor")
    if isinstance(anchor, dict):
        county_fips = anchor.get("county_fips")
        if isinstance(county_fips, str) and county_fips:
            return f"county/{county_fips}"

    return None


# --------------------------------------------------------------------------- #
# Per-tick grouping + pagination.
# --------------------------------------------------------------------------- #


def chronicle_stream(
    events: Sequence[ChronicleEvent], *, limit: int = CHRONICLE_ROW_CEILING
) -> tuple[TickBulletin, ...]:
    """Group a raw event stream into newest-tick-first dated bulletins.

    Preserves the frozen event-query convention: rows sort newest-first
    (highest tick, then latest-emitted
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
    :returns: bulletins newest-tick-first; ``()`` when ``events`` is empty.
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
