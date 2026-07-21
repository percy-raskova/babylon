"""Navigation-shell state: jumplist, breadcrumbs, persistence seam (WO-47).

Design canon S7: the Archive navigates like a wiki in vim — ``Ctrl-O``
walks back through the jumplist, ``Ctrl-I`` walks forward, and a
breadcrumb trail shows the path that led here. The state values here are
frozen Pydantic models (mutation returns a new value, house watchlist
idiom); :class:`NavShell` owns the mutable session and persists every
change through the :class:`NavPersistence` seam.

The seam is structural on purpose (the WO-37 trick): its method names and
signatures exactly match :class:`babylon.persistence.babylon_meta.
BabylonMetaStore`, so the composition root can inject the real
``babylon_meta``-backed store while ``babylon.tui`` never imports the
persistence layer (the import-linter contract stays intact).
:class:`InMemoryNavPersistence` is the honest no-database default: state
lives exactly as long as the process.

Cross-session cursor semantics: only the ENTRIES are persisted. A
restored jumplist resumes at its newest entry (``Ctrl-O`` then walks back
exactly as before the restart); unretraced forward depth does not survive
a restart, which is an explicit choice, not an accident.
"""

from __future__ import annotations

from typing import Protocol, Self, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.tui.router import REDLINK_KIND, BabylonTarget

__all__ = [
    "DEFAULT_TRAIL_CAPACITY",
    "BreadcrumbTrail",
    "InMemoryNavPersistence",
    "JumplistState",
    "NavPersistence",
    "NavShell",
    "subject_for",
]

#: Breadcrumb ceiling — a display trail, not an archive; the jumplist is
#: the full back-stack. Client display constant, not a ``GameDefines``.
DEFAULT_TRAIL_CAPACITY = 20


def subject_for(target: BabylonTarget) -> str:
    """Rebuild the known-set subject id (``"<kind>/<id>"``) for a target.

    :param target: a parsed ``babylon://`` navigation target.
    :raises ValueError: for a redlink — an unresolved target has no page
        to navigate to (the caller shows status, never a blank page).
    :returns: ``"<kind>/<id>"`` for an explicit-kind target, or the bare
        id for a ``babylon://<id>`` wikilink-form target.
    """
    if target.redlink or target.kind == REDLINK_KIND:
        msg = f"redlink target has no navigable subject: {target.entity_id!r}"
        raise ValueError(msg)
    if target.kind == "wikilink":
        return target.entity_id
    return f"{target.kind}/{target.entity_id}"


class JumplistState(BaseModel):
    """A vim-style back-stack of visited subjects with a cursor.

    :param entries: visited subject ids, oldest first.
    :param cursor: index of the current position, or ``-1`` when empty.
    """

    model_config = ConfigDict(frozen=True)

    entries: tuple[str, ...] = ()
    cursor: int = Field(ge=-1, default=-1)

    @model_validator(mode="after")
    def check_cursor_in_range(self) -> Self:
        """Reject a cursor outside ``[-1, len(entries))`` — loud, not clamped."""
        if self.cursor >= len(self.entries) or (self.cursor == -1 and self.entries):
            msg = f"cursor {self.cursor} out of range for {len(self.entries)} entries"
            raise ValueError(msg)
        return self

    @classmethod
    def restore(cls, entries: tuple[str, ...]) -> JumplistState:
        """Rebuild a persisted jumplist, resuming at the newest entry.

        :param entries: the persisted stack, oldest first.
        :returns: a state whose current position is the last entry (or an
            empty state for an empty stack).
        """
        return cls(entries=entries, cursor=len(entries) - 1)

    @property
    def current(self) -> str | None:
        """The subject at the cursor, or ``None`` for an empty jumplist."""
        return self.entries[self.cursor] if self.cursor >= 0 else None

    def visit(self, subject: str) -> JumplistState:
        """Jump to ``subject``: truncate forward history and push.

        Idempotent for the current subject — re-opening the page you are
        on records nothing.

        :param subject: the subject id being visited.
        :returns: the new state, or ``self`` for a redundant visit.
        """
        if self.current == subject:
            return self
        kept = self.entries[: self.cursor + 1]
        return self.model_copy(update={"entries": (*kept, subject), "cursor": len(kept)})

    def back(self) -> JumplistState:
        """Walk one step back (``Ctrl-O``); idempotent at the oldest entry.

        :returns: the new state, or ``self`` if there is nowhere to go.
        """
        if self.cursor <= 0:
            return self
        return self.model_copy(update={"cursor": self.cursor - 1})

    def forward(self) -> JumplistState:
        """Walk one step forward (``Ctrl-I``); idempotent at the newest entry.

        :returns: the new state, or ``self`` if there is nowhere to go.
        """
        if self.cursor < 0 or self.cursor >= len(self.entries) - 1:
            return self
        return self.model_copy(update={"cursor": self.cursor + 1})


class BreadcrumbTrail(BaseModel):
    """An append-only, consecutive-deduped, capacity-bounded visited path.

    :param entries: the trail, oldest first, at most ``capacity`` long.
    :param capacity: the trail ceiling (see :data:`DEFAULT_TRAIL_CAPACITY`).
    """

    model_config = ConfigDict(frozen=True)

    entries: tuple[str, ...] = ()
    capacity: int = Field(gt=0, default=DEFAULT_TRAIL_CAPACITY)

    @classmethod
    def restore(
        cls, entries: tuple[str, ...], *, capacity: int = DEFAULT_TRAIL_CAPACITY
    ) -> BreadcrumbTrail:
        """Rebuild a persisted trail, keeping the newest ``capacity`` entries.

        :param entries: the persisted trail, oldest first.
        :param capacity: the ceiling to re-bound against.
        :returns: the rebuilt trail.
        """
        return cls(entries=entries[-capacity:], capacity=capacity)

    def push(self, subject: str) -> BreadcrumbTrail:
        """Append ``subject``, deduping a consecutive repeat.

        :param subject: the subject id just visited.
        :returns: the new trail, or ``self`` if ``subject`` is already the
            newest crumb.
        """
        if self.entries and self.entries[-1] == subject:
            return self
        return self.model_copy(update={"entries": (*self.entries, subject)[-self.capacity :]})


@runtime_checkable
class NavPersistence(Protocol):
    """The seam the ``babylon_meta``-backed store satisfies structurally.

    Method names and signatures mirror
    ``babylon.persistence.babylon_meta.BabylonMetaStore`` exactly — that
    correspondence IS the contract (pinned by ``tests/unit/tui/
    test_nav_shell.py``), so neither module imports the other.
    """

    def load_jumplist(self, campaign_id: UUID) -> tuple[str, ...]:
        """Return the persisted jumplist stack, oldest entry first.

        :param campaign_id: the campaign whose stack to load.
        :returns: the stack, or ``()`` if none was recorded.
        """
        ...

    def save_jumplist(self, campaign_id: UUID, entity_ids: tuple[str, ...]) -> None:
        """Replace the persisted jumplist stack.

        :param campaign_id: the campaign to save under.
        :param entity_ids: the full stack, oldest entry first.
        """
        ...

    def load_breadcrumbs(self, campaign_id: UUID) -> tuple[str, ...]:
        """Return the persisted breadcrumb trail, oldest entry first.

        :param campaign_id: the campaign whose trail to load.
        :returns: the trail, or ``()`` if none was recorded.
        """
        ...

    def save_breadcrumbs(self, campaign_id: UUID, entity_ids: tuple[str, ...]) -> None:
        """Replace the persisted breadcrumb trail.

        :param campaign_id: the campaign to save under.
        :param entity_ids: the full trail, oldest entry first.
        """
        ...


class InMemoryNavPersistence:
    """Dict-backed :class:`NavPersistence` — no database, no disk.

    The honest no-persistence default (state dies with the process) and
    the unit-test double for :class:`NavShell`'s persistence choreography.
    """

    def __init__(self) -> None:
        self._jumplists: dict[UUID, tuple[str, ...]] = {}
        self._breadcrumbs: dict[UUID, tuple[str, ...]] = {}

    def load_jumplist(self, campaign_id: UUID) -> tuple[str, ...]:
        """See :meth:`NavPersistence.load_jumplist`."""
        return self._jumplists.get(campaign_id, ())

    def save_jumplist(self, campaign_id: UUID, entity_ids: tuple[str, ...]) -> None:
        """See :meth:`NavPersistence.save_jumplist`."""
        self._jumplists[campaign_id] = entity_ids

    def load_breadcrumbs(self, campaign_id: UUID) -> tuple[str, ...]:
        """See :meth:`NavPersistence.load_breadcrumbs`."""
        return self._breadcrumbs.get(campaign_id, ())

    def save_breadcrumbs(self, campaign_id: UUID, entity_ids: tuple[str, ...]) -> None:
        """See :meth:`NavPersistence.save_breadcrumbs`."""
        self._breadcrumbs[campaign_id] = entity_ids


class NavShell:
    """The mutable navigation session: jumplist + trail + persistence.

    :param campaign_id: the campaign this session navigates within.
    :param persistence: where cross-session state lives.
    :param jumplist: the starting jumplist (defaults to empty).
    :param trail: the starting breadcrumb trail (defaults to empty).
    """

    def __init__(
        self,
        *,
        campaign_id: UUID,
        persistence: NavPersistence,
        jumplist: JumplistState | None = None,
        trail: BreadcrumbTrail | None = None,
    ) -> None:
        self._campaign_id = campaign_id
        self._persistence = persistence
        self.jumplist = jumplist if jumplist is not None else JumplistState()
        self.trail = trail if trail is not None else BreadcrumbTrail()

    @classmethod
    def restore(cls, *, campaign_id: UUID, persistence: NavPersistence) -> NavShell:
        """Rebuild the shell from persisted state (cross-session resume).

        :param campaign_id: the campaign to restore.
        :param persistence: the store to load from.
        :returns: a shell resuming at the newest persisted position, or an
            honestly empty one for a fresh campaign.
        """
        return cls(
            campaign_id=campaign_id,
            persistence=persistence,
            jumplist=JumplistState.restore(persistence.load_jumplist(campaign_id)),
            trail=BreadcrumbTrail.restore(persistence.load_breadcrumbs(campaign_id)),
        )

    @property
    def current(self) -> str | None:
        """The subject currently navigated to, or ``None`` before any visit."""
        return self.jumplist.current

    def visit(self, subject: str) -> None:
        """Record a jump to ``subject`` and persist both structures.

        :param subject: the subject id being visited.
        """
        self.jumplist = self.jumplist.visit(subject)
        self.trail = self.trail.push(subject)
        self._persistence.save_jumplist(self._campaign_id, self.jumplist.entries)
        self._persistence.save_breadcrumbs(self._campaign_id, self.trail.entries)

    def back(self) -> str | None:
        """``Ctrl-O``: walk back, persisting nothing (entries are unchanged).

        :returns: the new current subject, or ``None`` at the edge.
        """
        moved = self.jumplist.back()
        if moved is self.jumplist:
            return None
        self.jumplist = moved
        return moved.current

    def forward(self) -> str | None:
        """``Ctrl-I``: walk forward, persisting nothing (entries are unchanged).

        :returns: the new current subject, or ``None`` at the edge.
        """
        moved = self.jumplist.forward()
        if moved is self.jumplist:
            return None
        self.jumplist = moved
        return moved.current
