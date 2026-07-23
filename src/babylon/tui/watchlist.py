"""The watchlist — a page of transclusions (design canon S7, WO-37).

S7 (``ai/_inbox/tui/20260719archiveinterfacedesign.md``): *"... pinned
watchlist = a page of transclusions."* :func:`peek` (WO-25) is the single
renderer that, at ``depth=0``, produces exactly the terse one-line form S7
calls a "watchlist row." This module supplies the rest of the watchlist
idiom on top of that one renderer: an ordered, capacity-bounded, pin/unpin
domain state (:class:`WatchlistState`), and the page-level rendering
(:func:`render_watchlist`) that stacks each pinned entity's
``peek(view, depth=0)`` row into one bordered plate — never a baked vault
page (**live-query-backed, not baked**, mirroring :mod:`babylon.tui.peek`'s
own S3 contrast: a watchlist reflects whatever view-model the caller
currently holds, not a materialized snapshot pinned to a ``verified_tick``).

Unit "watchlist-row-nav" (shell-interconnect): :func:`watchlist_rows` is
:func:`render_watchlist`'s row-addressable sibling — the SAME per-row
rendering, kept separate per pinned id (``(entity_id, row_text)`` pairs)
rather than stacked into one blob, so a caller building a navigable widget
(the right rail's own :class:`~textual.widgets.OptionList`,
:mod:`babylon.tui.app`) can key one selectable option to each row.
:func:`render_watchlist` itself is untouched and stays available as the
whole-page, non-interactive render (the standalone snapshot demo,
``tests/unit/tui/snapshots/watchlist_app.py``, still uses it directly).

**Persistence is a documented OPEN QUESTION this WO does not resolve** (S7 §10:
"Watchlist/pin mechanics ... " is listed unresolved in the design brief).
Charter P0 batch already ruled real cross-session persistence lands in a
``babylon_meta`` ``watchlist`` table, created by Program 24 P3 WO-46 — but
that store does not exist yet, and this WO is explicitly barred from creating
any DB table (WO-37 hard rule). :class:`WatchlistState` is therefore
**session-in-memory only**: a frozen value object with no I/O of its own.
:class:`WatchlistPersistence` is the seam WO-46's concrete ``babylon_meta``-backed
store will implement; :func:`load_watchlist`/:func:`save_watchlist` are the
two small functions that thread a :class:`WatchlistState` through *any*
:class:`WatchlistPersistence` implementation — including, today, a plain
in-memory fake (see the contract tests) — so nothing here needs to change
shape when WO-46 lands the real Postgres-backed implementation; only a new
concrete class satisfying the Protocol needs to exist.

**Ordering is FIFO pin order, not recency or alphabetical.** :meth:`WatchlistState.pin`
appends a newly-pinned id at the end; re-pinning an already-pinned id is a
no-op (it keeps its original position, does not move to the end); unpinning
removes an id without disturbing the relative order of what remains; a
later re-pin of a previously-unpinned id is treated as brand new and lands
at the end again. This is fully deterministic (Constitution III.13: no
wall-clock, no randomness) — the pin order is exactly the call order the
caller drove :meth:`WatchlistState.pin` with.

**Capacity is a loud, explicit ceiling, never a silent eviction.** Pinning
past :attr:`WatchlistState.capacity` raises :class:`ValueError` rather than
silently dropping the oldest pin (an LRU-eviction UX is a plausible design,
but a silent one is a Constitution III.11 violation — the player would lose
a pin with no visible cause). The caller decides what to unpin first.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator
from rich.text import Text

from babylon.projection.view_models import ProjectionRecord
from babylon.tui.peek import peek
from babylon.tui.theme import CRIMSON

__all__ = [
    "DEFAULT_WATCHLIST_CAPACITY",
    "WatchlistState",
    "WatchlistPersistence",
    "InMemoryWatchlistPersistence",
    "load_watchlist",
    "save_watchlist",
    "watchlist_title",
    "render_watchlist",
    "watchlist_rows",
]

DEFAULT_WATCHLIST_CAPACITY: Final[int] = 20
"""The session-in-memory pin ceiling, absent an owner UX ruling.

A placeholder-but-documented number (matching the ``CHRONICLE_ROW_CEILING``
precedent in :mod:`babylon.tui.chronicle`): S7 never specifies a watchlist
size, only that its rows are terse (``depth=0``, at most one stat per row).
20 one-line rows plus a bordered plate's own two chrome rows fit inside a
generous-but-plausible terminal height without scrolling. WO-46/an owner
ruling may replace this with a real UX-derived (or player-configurable)
number; every call site accepts ``capacity`` explicitly rather than reading
a hidden global, so that future change is a constructor-argument change, not
a rewrite.
"""


class WatchlistState(BaseModel):
    """An ordered, capacity-bounded set of pinned entity ids — session-scoped.

    Frozen (mirrors :class:`~babylon.projection.fog.ledger.IntelLedger`):
    :meth:`pin` and :meth:`unpin` each return a **new** state rather than
    mutating ``self``, so a state value can be threaded through a session
    loop without aliasing surprises.

    :param capacity: the pin ceiling (see :data:`DEFAULT_WATCHLIST_CAPACITY`).
    :param pinned_ids: the current pin order, oldest-pinned-first.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    capacity: int = Field(gt=0, default=DEFAULT_WATCHLIST_CAPACITY)
    pinned_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _validate_within_capacity(self) -> WatchlistState:
        """Reject a state constructed with more pins than its own capacity allows.

        Only guards *construction* (:meth:`pin` enforces the same ceiling
        separately, since Pydantic's ``model_copy`` bypasses validators —
        see :meth:`pin`'s docstring) — this is the defense for a state
        hydrated directly from a persistence layer (:func:`load_watchlist`)
        whose recorded pin list has drifted past today's capacity.

        :raises ValueError: if ``len(pinned_ids) > capacity``.
        :returns: the validated model (unchanged).
        """
        if len(self.pinned_ids) > self.capacity:
            msg = (
                f"watchlist has {len(self.pinned_ids)} pinned id(s), "
                f"exceeding its own capacity of {self.capacity}"
            )
            raise ValueError(msg)
        return self

    def is_pinned(self, entity_id: str) -> bool:
        """Whether ``entity_id`` currently holds a pin.

        :param entity_id: the entity id to check.
        :returns: ``True`` iff ``entity_id`` is in :attr:`pinned_ids`.
        """
        return entity_id in self.pinned_ids

    def pin(self, entity_id: str) -> WatchlistState:
        """Pin ``entity_id``, appended at the end of the pin order.

        Idempotent: pinning an already-pinned id returns ``self`` unchanged
        (no duplicate, no reordering, no capacity charge for a pin that
        already exists).

        :param entity_id: the entity id to pin.
        :raises ValueError: if ``entity_id`` is not already pinned AND the
            watchlist is already at :attr:`capacity` — checked explicitly
            here (not left to the ``model_validator``) because
            ``model_copy(update=...)`` does not re-run Pydantic validators,
            so the ceiling would silently go unenforced on this path
            otherwise.
        :returns: a new :class:`WatchlistState` with ``entity_id`` appended,
            or ``self`` if it was already pinned.
        """
        if entity_id in self.pinned_ids:
            return self
        if len(self.pinned_ids) >= self.capacity:
            msg = (
                f"watchlist is at capacity ({self.capacity}); "
                f"unpin an entity before pinning {entity_id!r}"
            )
            raise ValueError(msg)
        return self.model_copy(update={"pinned_ids": (*self.pinned_ids, entity_id)})

    def unpin(self, entity_id: str) -> WatchlistState:
        """Unpin ``entity_id``, preserving the relative order of the rest.

        Idempotent: unpinning an id that is not pinned returns ``self``
        unchanged — a redundant unpin (e.g. a double key-press race) is not
        an error.

        :param entity_id: the entity id to unpin.
        :returns: a new :class:`WatchlistState` with ``entity_id`` removed,
            or ``self`` if it was not pinned.
        """
        if entity_id not in self.pinned_ids:
            return self
        remaining = tuple(pinned for pinned in self.pinned_ids if pinned != entity_id)
        return self.model_copy(update={"pinned_ids": remaining})


@runtime_checkable
class WatchlistPersistence(Protocol):
    """The seam Program 24 P3 WO-46's ``babylon_meta``-backed store will implement.

    Structural (``@runtime_checkable``): any object exposing these two
    methods satisfies this Protocol, so tests exercise the seam with a
    trivial in-memory fake (:class:`InMemoryWatchlistPersistence` below, or
    a test-local double) with zero dependency on Postgres/``babylon_meta`` —
    which does not exist yet (charter P0 ruling 3 mandates it; WO-46 creates
    it). WO-46's real implementation persists to the ``watchlist`` table that
    ruling names; this WO commits no DDL, no migration, no schema of any
    kind — only this contract.
    """

    def load(self, session_id: str) -> tuple[str, ...]:
        """Return the recorded pin order for ``session_id``.

        :param session_id: the campaign/session key WO-46's schema scopes
            ``watchlist`` rows by.
        :returns: the recorded pin order, oldest-pinned-first, or ``()`` if
            ``session_id`` has no recorded watchlist (an honest empty
            result, never a fabricated default pin list).
        """
        ...

    def save(self, session_id: str, pinned_ids: tuple[str, ...]) -> None:
        """Persist ``pinned_ids`` (in order) as ``session_id``'s watchlist.

        :param session_id: the campaign/session key to persist under.
        :param pinned_ids: the full current pin order to record.
        """
        ...


class InMemoryWatchlistPersistence:
    """A trivial dict-backed :class:`WatchlistPersistence` — no DB, no disk.

    Proves the Protocol is satisfiable without ``babylon_meta`` (the point
    of the seam) and doubles as the default a session with no cross-session
    persistence at all can use today: a watchlist that lives exactly as long
    as the process, then reverts to empty next launch — an explicit, honest
    non-persistence, not a silent one.
    """

    def __init__(self) -> None:
        self._by_session: dict[str, tuple[str, ...]] = {}

    def load(self, session_id: str) -> tuple[str, ...]:
        """See :meth:`WatchlistPersistence.load`."""
        return self._by_session.get(session_id, ())

    def save(self, session_id: str, pinned_ids: tuple[str, ...]) -> None:
        """See :meth:`WatchlistPersistence.save`."""
        self._by_session[session_id] = pinned_ids


def load_watchlist(
    persistence: WatchlistPersistence,
    session_id: str,
    *,
    capacity: int = DEFAULT_WATCHLIST_CAPACITY,
) -> WatchlistState:
    """Hydrate a :class:`WatchlistState` from whatever ``persistence`` has recorded.

    :param persistence: any :class:`WatchlistPersistence` implementation.
    :param session_id: the session/campaign key to load.
    :param capacity: the bound for the hydrated state — a client-side UX
        setting, not itself part of what ``persistence`` records.
    :raises ValueError: if the recorded pin order already exceeds
        ``capacity`` (``WatchlistState``'s own ``model_validator``) — a
        stored watchlist that no longer fits today's ceiling is a loud
        contradiction to surface, never a silent truncation.
    :returns: the hydrated state, pin order preserved exactly as recorded.
    """
    return WatchlistState(capacity=capacity, pinned_ids=persistence.load(session_id))


def save_watchlist(
    persistence: WatchlistPersistence, session_id: str, state: WatchlistState
) -> None:
    """Persist ``state``'s current pin order via ``persistence``.

    :param persistence: any :class:`WatchlistPersistence` implementation.
    :param session_id: the session/campaign key to save under.
    :param state: the state whose :attr:`~WatchlistState.pinned_ids` to persist.
    """
    persistence.save(session_id, state.pinned_ids)


def _absence_text() -> Text:
    """The honest-absence line for a watchlist with nothing pinned.

    :returns: a styled single-line :class:`~rich.text.Text` (mirrors
        :mod:`babylon.tui.peek`'s and :mod:`babylon.tui.chronicle`'s ``▌``
        absence convention).
    """
    return Text("▌ watchlist — nothing pinned yet", style=f"bold {CRIMSON}")


def _missing_row(entity_id: str) -> Text:
    """The honest-absence row for a pinned id with no resolvable view.

    :param entity_id: the pinned id no view-model was supplied for.
    :returns: a styled single-line :class:`~rich.text.Text` naming the id —
        never silently dropped from the page (Constitution III.11).
    """
    return Text(f"▌ {entity_id} — no longer resolvable", style=f"bold {CRIMSON}")


def watchlist_title(pinned_ids: Sequence[str]) -> str:
    """The rail's dynamic border title: ``"Watchlist (N pinned)"``.

    Unit "selection-unwrap" (shell-interconnect): this text used to be the
    ``title=`` of :func:`render_watchlist`'s own :class:`~rich.panel.Panel`;
    it now lives in ``#watchlist-rail``'s CSS ``border-title-*`` chrome
    instead (:mod:`babylon.tui.app`), set at every repaint alongside the
    body :func:`render_watchlist` still returns.

    :param pinned_ids: the pin order the rail is showing, normally
        :attr:`WatchlistState.pinned_ids`.
    :returns: ``"Watchlist ({len(pinned_ids)} pinned)"``.
    """
    return f"Watchlist ({len(pinned_ids)} pinned)"


def _row_text(entity_id: str, views_by_id: Mapping[str, ProjectionRecord]) -> Text:
    """The single ``peek(view, depth=0)`` row for one pinned id.

    Shared by :func:`render_watchlist` (the whole-page stack) and
    :func:`watchlist_rows` (Unit "watchlist-row-nav": one row per
    :class:`~textual.widgets.OptionList` option) — the same view lookup and
    honest-absence dispatch either caller needs, in exactly one place.

    :param entity_id: the pinned id to render.
    :param views_by_id: caller-resolved view-models keyed by entity id.
    :returns: :func:`peek`'s ``depth=0`` row, or :func:`_missing_row`'s
        named absence line when ``entity_id`` has no entry in
        ``views_by_id``.
    """
    view = views_by_id.get(entity_id)
    if view is None:
        return _missing_row(entity_id)
    row = peek(view, 0)
    if isinstance(row, Text):
        return row
    text = Text()  # pragma: no cover - peek()'s own depth==0 contract always returns Text
    text.append(str(row))
    return text


def watchlist_rows(
    pinned_ids: Sequence[str], views_by_id: Mapping[str, ProjectionRecord]
) -> list[tuple[str | None, Text]]:
    """One ``(entity_id, row_text)`` pair per pinned id (Unit "watchlist-row-nav").

    The row-addressable sibling of :func:`render_watchlist`: instead of one
    combined stacked page, this returns each pinned id's own
    :func:`peek`-``depth=0`` row separately, so a caller building a
    navigable per-row widget (:class:`~textual.widgets.OptionList` — the
    right rail's own shape, :mod:`babylon.tui.app`) can key one selectable
    option to each row.

    Every pinned id renders a row here — INCLUDING one with no resolvable
    view (:func:`_missing_row`'s "no longer resolvable" line) — because
    :attr:`WatchlistState.pinned_ids` is already the exact subject-id form
    :meth:`~babylon.tui.app.ArchiveApp._navigate` consumes: opening ANY
    pinned id, peek-resolvable or not, still reaches a real baked vault page
    (or ``_navigate``'s own honest absence page), so nothing here needs to
    be non-openable except the empty-watchlist case — which this function
    represents as its own single ``(None, absence_text)`` placeholder row
    (never an empty list: a row-addressable widget with literally zero rows
    would be a silent blank space, not a visible absence fence, Constitution
    III.11). The caller marks that ``None``-keyed row disabled/unopenable
    (:mod:`babylon.tui.app`'s own ``Option(..., disabled=entity_id is
    None)``).

    :param pinned_ids: the pin order to render, normally
        :attr:`WatchlistState.pinned_ids`.
    :param views_by_id: caller-resolved view-models, same contract as
        :func:`render_watchlist`.
    :returns: one ``(entity_id, row_text)`` pair per pinned id, in pin
        order; a single ``(None, absence_text)`` placeholder row when
        ``pinned_ids`` is empty.
    """
    if not pinned_ids:
        return [(None, _absence_text())]
    return [(entity_id, _row_text(entity_id, views_by_id)) for entity_id in pinned_ids]


def render_watchlist(
    pinned_ids: Sequence[str], views_by_id: Mapping[str, ProjectionRecord]
) -> Text:
    """Render the watchlist page: ``peek(view, depth=0)`` rows, one per pin.

    **Live-query, not baked** (matches :func:`~babylon.tui.peek.peek`'s own
    contrast with S3): this function does not own id -> view-model
    resolution — the caller supplies whatever it currently holds in
    ``views_by_id``, exactly as :func:`peek` itself does not own that lookup
    either. A pinned id with no entry in ``views_by_id`` (a since-removed or
    not-yet-resolved entity) still renders its own named absence row, rather
    than being silently skipped.

    Unit "selection-unwrap": returns a bare, selectable :class:`~rich.text.
    Text` rather than a :class:`~rich.panel.Panel` — the crimson border/gold
    title (the pin count — :func:`watchlist_title`) moved to CSS chrome
    (border-title), since a ``Panel`` is opaque to ``Widget.get_selection``
    (only bare ``Text``/``Content`` qualify). Unit "watchlist-row-nav"
    (shell-interconnect): the LIVE ``#watchlist-rail`` no longer consumes
    THIS function directly (it is now a row-addressable
    :class:`~textual.widgets.OptionList`, fed by :func:`watchlist_rows`
    instead) — this whole-page render stays available for a non-interactive
    consumer (the standalone snapshot demo,
    ``tests/unit/tui/snapshots/watchlist_app.py``) and as :func:`watchlist_rows`'s
    own shared row-rendering logic (:func:`_row_text`).

    :param pinned_ids: the pin order to render, normally
        :attr:`WatchlistState.pinned_ids`.
    :param views_by_id: caller-resolved view-models keyed by entity id, for
        some or all of ``pinned_ids``.
    :returns: the honest-absence line when ``pinned_ids`` is empty;
        otherwise one ``peek(view, depth=0)`` row per pinned id, stacked.
    """
    if not pinned_ids:
        return _absence_text()

    body = Text()
    for index, entity_id in enumerate(pinned_ids):
        if index:
            body.append("\n")
        body.append_text(_row_text(entity_id, views_by_id))
    return body
