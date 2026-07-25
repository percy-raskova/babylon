"""Chronicle salience / consecutive dedup / AMBER autopause (Program 24 P3 WO-48).

WO-27's :mod:`babylon.tui.chronicle` renders the raw event stream faithfully
and explicitly defers this layer (its module docstring: *"Salience/dedup/
autopause are out of scope here ... severity-driven filtering,
consecutive-duplicate collapsing, and the AMBER autopause wiring land later,
on top of the shapes this module defines."*). This module is that layer —
pure functions over :class:`~babylon.tui.chronicle.ChronicleEvent` that a
caller applies **before** handing events to
:func:`~babylon.tui.chronicle.chronicle_stream`/
:func:`~babylon.tui.chronicle.bulletin_for_tick`.

**NET-NEW mechanics** (design-canon has no salience/dedup/autopause spec —
work-orders-p2-p4.md WO-48 frame): built from two pieces of prior art instead
of a design doc.

**Salience** (T1.1 U2, ``ai/_inbox/t11-seam-severity-design.md``) delegates to
:func:`babylon.models.event_severity.resolve_severity` — U1's single-sourced
kind x terminal_proximity derivation, shared with
``web/game/engine_bridge.py``'s ``_classify_event``. This module originally
ported that surface's hand-copied ``_EVENT_SEVERITY`` dict (spec-061 FR-012's
three-bucket taxonomy: critical/warning/informational, 47 of 84
:class:`~babylon.models.enums.events.EventType` values classified) verbatim as
its own ``EVENT_SEVERITY`` — a byte-identical twin with no mechanical
guarantee the two stayed equal; both hand-copied dicts are now retired in
favor of the one generated resolver. Constitution III.11 ("Loud Failure")
governs the unclassified case exactly as before: an unclassified
:class:`~babylon.models.enums.events.EventType` renders at **warning**-tier
visibility, and :attr:`EventSalience.unclassified` is ``True`` so the caller
can visibly mark it (never a silent, indistinguishable "informational" — the
legacy web bridge's original quiet default, also retired by this unit).

**Dedup + autopause** port ``src/frontend/src/lib/eventDedup.ts`` (spec-116
FR-116-2's "no two consecutive identical event cards" / autopause-once
core) at the level this WO actually needs: :func:`dedupe_consecutive` is the
ported ``dedupeEvents`` (tick-independent ``{type}:{subject}`` identity,
order-preserving consecutive-run collapse); :func:`compute_autopause_state`
is a client-side-only slice of ``worldSlice.ts``'s autopause wiring — this WO
does not port the frontend's session-scoped once-per-key acknowledgement
machinery (that lives behind WO-46's ``babylon_meta`` store, listed as this
WO's *optional* dependency), only the simpler "a critical-tier event in the
current view sets the autopause state" rule the WO-48 contract tests pin.
:data:`~babylon.tui.theme.AMBER` (reserved in the keel, "not wired to any
widget yet") is the token :class:`AutopauseState` surfaces.

**Volume floors.** Two independent per-tick caps, applied to disjoint event
types so their order of application does not matter:

- :func:`cap_narrative_events` caps the **informational** tier — the legacy
  dict's own docstring calls this bucket "routine flow events" — to
  :data:`NARRATIVE_EVENT_CEILING_PER_TICK` per tick. Critical and warning
  stay individually visible (repetition there is :func:`dedupe_consecutive`'s
  job, not a volume floor's); this is a display-density decision about
  background narrative color, not a hidden material fact (Constitution
  III.11 governs honesty about state, not how many flavor lines render).
- :func:`aggregate_organizational_actions` collapses every
  ``ORGANIZATIONAL_ACTION`` event within one tick into a single rollup card
  carrying the count (ADR086: the engine already emits at most one
  ``ORGANIZATIONAL_ACTION`` summary per tick in practice — OODA aggregates
  per-business layer0 into one bus event — so this is the Chronicle plate's
  own defensive floor against a fixture, or a future engine change, ever
  emitting more than one).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict
from rich.text import Text

from babylon.models.enums.events import EventType
from babylon.models.event_severity import resolve_severity
from babylon.tui.chronicle import ChronicleEvent
from babylon.tui.theme import AMBER

__all__ = [
    "SeverityTier",
    "EventSalience",
    "classify_event_salience",
    "SUBJECT_FIELDS",
    "chronicle_subject",
    "dedup_key",
    "dedupe_consecutive",
    "AutopauseState",
    "compute_autopause_state",
    "render_autopause_indicator",
    "NARRATIVE_TIER",
    "NARRATIVE_EVENT_CEILING_PER_TICK",
    "cap_narrative_events",
    "aggregate_organizational_actions",
    "apply_volume_floors",
]

SeverityTier = Literal["critical", "warning", "informational"]
"""The three-bucket taxonomy (spec-061 FR-012), resolved by
:func:`babylon.models.event_severity.resolve_severity` (T1.1 U1/U2's single
source), not a locally hand-copied dict."""


class EventSalience(BaseModel):
    """One event's resolved tier, plus whether it fell through to the loud floor.

    A thin per-surface adapter over
    :class:`babylon.models.event_severity.EventSeverity` (T1.1 U2): identical
    shape, kept as this module's own type so its public API (and every
    existing caller) is unaffected by the single-sourcing underneath it.

    :param tier: the resolved :data:`SeverityTier`.
    :param unclassified: ``True`` when ``tier`` came from the loud
        unclassified floor (no declared row for this event type) rather than
        a real classification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tier: SeverityTier
    unclassified: bool = False


def classify_event_salience(event_type: EventType) -> EventSalience:
    """Resolve ``event_type``'s salience tier.

    T1.1 U2: delegates to :func:`babylon.models.event_severity.resolve_severity`
    — the single-sourced derivation shared with ``web/game/engine_bridge.py``'s
    ``_classify_event`` — so this surface and the web bridge can never
    silently drift apart the way their two hand-copied dicts could.

    Constitution III.11 ("Loud Failure"): an ``event_type`` with no declared
    classification row (any :class:`EventType` added after T1.1, or one of the
    37 never classified) renders at **warning**-tier visibility — never the
    legacy Python bridge's quiet "informational" degrade — with
    :attr:`EventSalience.unclassified` set so callers can visibly mark it.

    :param event_type: the event type to classify.
    :returns: the resolved :class:`EventSalience`.
    """
    severity = resolve_severity(event_type)
    return EventSalience(tier=severity.tier, unclassified=severity.unclassified)


SUBJECT_FIELDS: Final[tuple[str, ...]] = (
    "node_id",
    "org_id",
    "entity_id",
    "territory_id",
    "territory",
    "fips",
    "county_fips",
    "sovereign_id",
    "faction_id",
    "comprador_id",
    "periphery_id",
    "core_worker_id",
)
"""Subject-field precedence, ported from ``src/frontend/src/lib/eventDedup.ts``'s
``SUBJECT_FIELDS`` — graph-independent payload fields first, matching that
module's own rationale (``uprising`` carries both ``node_id`` and a
bridge-enriched ``territory_id`` that differs by serialization path; keying
on ``node_id`` keeps identity stable across both)."""


def chronicle_subject(event: ChronicleEvent) -> str:
    """Resolve ``event``'s tick-independent dedup subject.

    Ported from ``eventDedup.ts::eventSubject``: the first present
    :data:`SUBJECT_FIELDS` entry in :attr:`ChronicleEvent.data`, else a
    ``source->target`` pairing, else the bare source, else the literal
    ``"global"`` — every event resolves to SOME subject (unlike
    :func:`~babylon.tui.chronicle.resolve_actor`, which returns ``None`` for
    place-scoped/system-wide events; that function answers "who does this
    narrate as," this one answers "what dedup bucket does this belong to,"
    and every event belongs to exactly one bucket).

    :param event: the event to resolve a subject for.
    :returns: the resolved subject string.
    """
    for field in SUBJECT_FIELDS:
        value = event.data.get(field)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, int | float) and not isinstance(value, bool):
            return str(value)
    source = event.data.get("source_id")
    target = event.data.get("target_id")
    if isinstance(source, str) and isinstance(target, str):
        return f"{source}->{target}"
    if isinstance(source, str):
        return source
    return "global"


def dedup_key(event: ChronicleEvent) -> str:
    """The tick-independent salience identity: ``"{event_type}:{subject}"``.

    Ported from ``eventDedup.ts::dedupKey``. Tick-independent by design (see
    that module's docstring): a persisting condition gets a new id every
    tick, but the same ``(event_type, subject)`` pair is "the same thing
    still happening," which is exactly what :func:`dedupe_consecutive` needs
    to collapse.

    :param event: the event to key.
    :returns: the dedup key.
    """
    return f"{event.event_type.value}:{chronicle_subject(event)}"


def dedupe_consecutive(events: Sequence[ChronicleEvent]) -> tuple[ChronicleEvent, ...]:
    """Collapse CONSECUTIVE same-``(event_type, subject)`` cards into one each.

    Ported from ``eventDedup.ts::dedupeEvents`` (spec-116 FR-116-2 acceptance
    gate 2 / the ``first-session.spec.ts`` contract: "no two consecutive
    identical event cards"). Order-preserving: a non-consecutive repeat (the
    same key recurring after a *different* key interrupts the run) stays a
    separate card, and an adjacent pair sharing only the ``event_type`` but
    NOT the subject is never collapsed. The kept card from each run is its
    FIRST event, matching the frontend's own ``representative`` choice. Loop
    bound: ``len(events)``.

    ``events`` should already be in the display order the caller intends to
    render (:func:`dedup_key` is tick-independent, so this also collapses a
    repeat that spans two adjacent tick bulletins, exactly like the ported
    frontend behavior over its own tick-ordered stream).

    :param events: the events to collapse, in display order.
    :returns: one representative event per consecutive run, in order.
    """
    collapsed: list[ChronicleEvent] = []
    last_key: str | None = None
    for event in events:
        key = dedup_key(event)
        if key == last_key:
            continue
        collapsed.append(event)
        last_key = key
    return tuple(collapsed)


class AutopauseState(BaseModel):
    """The Chronicle plate's autopause indicator state.

    :param active: whether a critical-tier event is currently driving
        autopause.
    :param token: the color token the plate renders the indicator in —
        always :data:`~babylon.tui.theme.AMBER` today (the field exists so a
        future tier-specific palette is a data change, not a shape change).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    active: bool = False
    token: str = AMBER


def compute_autopause_state(events: Sequence[ChronicleEvent]) -> AutopauseState:
    """Autopause iff ``events`` contains at least one critical-tier event.

    A pure, client-side-display slice of ``worldSlice.ts``'s autopause
    wiring: THAT module additionally tracks a session-scoped
    once-per-``(event_type, subject)`` acknowledgement set (via
    ``computeAutopauseDecision``) so a critical condition does not re-pause
    every tick it persists — this WO's contract only requires "a
    critical-tier event sets an autopause state" (work-orders-p2-p4.md
    WO-48), so that acknowledgement layer is deliberately NOT ported here;
    WO-46's ``babylon_meta`` store is listed as this WO's *optional*
    dependency for exactly that reason. Warning and informational events
    never fire autopause, regardless of count. Loop bound: ``len(events)``.

    :param events: the tick's (or view's) events to inspect.
    :returns: the resolved :class:`AutopauseState`.
    """
    for event in events:
        if classify_event_salience(event.event_type).tier == "critical":
            return AutopauseState(active=True, token=AMBER)
    return AutopauseState(active=False, token=AMBER)


def render_autopause_indicator(state: AutopauseState) -> Text | None:
    """Render the AMBER autopause indicator, or ``None`` when not active.

    :param state: the current :class:`AutopauseState`.
    :returns: a bold-AMBER :class:`~rich.text.Text` line, or ``None`` — the
        caller renders nothing rather than a dimmed/inactive placeholder
        (Constitution III.11: an inactive indicator is absence, not a
        muted presence).
    """
    if not state.active:
        return None
    return Text("⏸ AUTOPAUSE — THIS CANNOT PASS UNREAD", style=f"bold {state.token}")


NARRATIVE_TIER: Final[SeverityTier] = "informational"
"""The volume-floor's scope: the legacy dict's own "routine flow events"
bucket. Critical and warning are never capped by :func:`cap_narrative_events`
— their repetition is :func:`dedupe_consecutive`'s job."""

NARRATIVE_EVENT_CEILING_PER_TICK: Final[int] = 1
"""At most this many informational-tier events render per tick."""


def cap_narrative_events(events: Sequence[ChronicleEvent]) -> tuple[ChronicleEvent, ...]:
    """Cap :data:`NARRATIVE_TIER` (informational) events to
    :data:`NARRATIVE_EVENT_CEILING_PER_TICK` per tick.

    Every other tier passes through unfiltered. Order-preserving; excess
    informational events beyond the per-tick ceiling are dropped (a
    display-density decision about background narrative color — see the
    module docstring). Loop bound: ``len(events)``.

    :param events: the events to filter, any order/tick mix.
    :returns: the filtered events, original relative order preserved.
    """
    kept: list[ChronicleEvent] = []
    narrative_count_by_tick: dict[int, int] = {}
    for event in events:
        if classify_event_salience(event.event_type).tier != NARRATIVE_TIER:
            kept.append(event)
            continue
        count = narrative_count_by_tick.get(event.tick, 0)
        if count < NARRATIVE_EVENT_CEILING_PER_TICK:
            kept.append(event)
        narrative_count_by_tick[event.tick] = count + 1
    return tuple(kept)


def aggregate_organizational_actions(
    events: Sequence[ChronicleEvent],
) -> tuple[ChronicleEvent, ...]:
    """Collapse each tick's ``ORGANIZATIONAL_ACTION`` events into ONE rollup card.

    Per ADR086: the engine already aggregates per-business layer0 activity
    into a single ``ORGANIZATIONAL_ACTION`` summary event per tick in
    practice, so this is a defensive floor, not a routine occurrence. Every
    other event type passes through unfiltered, in order. The kept card
    (the first ``ORGANIZATIONAL_ACTION`` seen for a tick) is rewritten with
    a count-bearing summary and ``data["count"]``; a lone
    ``ORGANIZATIONAL_ACTION`` (count == 1) is rewritten identically, so the
    function is idempotent. Loop bound: ``2 * len(events)`` (one pass to
    count, one to rewrite the kept placeholders).

    :param events: the events to aggregate, any order/tick mix.
    :returns: the aggregated events, original relative order preserved.
    """
    kept: list[ChronicleEvent] = []
    counts: dict[int, int] = {}
    placeholder_index_by_tick: dict[int, int] = {}
    for event in events:
        if event.event_type is not EventType.ORGANIZATIONAL_ACTION:
            kept.append(event)
            continue
        tick = event.tick
        counts[tick] = counts.get(tick, 0) + 1
        if tick not in placeholder_index_by_tick:
            placeholder_index_by_tick[tick] = len(kept)
            kept.append(event)

    for tick, index in placeholder_index_by_tick.items():
        count = counts[tick]
        original = kept[index]
        summary = f"{count} organizational action{'s' if count != 1 else ''} this tick"
        kept[index] = original.model_copy(
            update={"summary": summary, "data": {**original.data, "count": count}}
        )
    return tuple(kept)


def apply_volume_floors(events: Sequence[ChronicleEvent]) -> tuple[ChronicleEvent, ...]:
    """Apply both volume floors: ``ORGANIZATIONAL_ACTION`` rollup, then the
    informational-tier per-tick cap.

    The two floors touch disjoint event types (:func:`aggregate_organizational_actions`
    only ever touches ``ORGANIZATIONAL_ACTION``, which has no declared
    classification row and so resolves to the unclassified **warning** tier
    — never :data:`NARRATIVE_TIER`), so applying them in either order yields
    the same result; this composes them in the order a caller would normally
    want them evaluated.

    :param events: the raw events to floor, any order/tick mix.
    :returns: the floored events, ready for
        :func:`~babylon.tui.chronicle.chronicle_stream` or
        :func:`dedupe_consecutive`.
    """
    return cap_narrative_events(aggregate_organizational_actions(events))
