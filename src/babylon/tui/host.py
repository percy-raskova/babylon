"""The Rust client's host seam (M0 lobby surface + M1 read surface — ADR150).

:class:`RustClientHost` is THE seam between the Python composition root and
the Rust/Ratatui client: Python remains the single writer, and every read
crosses the FFI as a JSON string of primitives (``model_dump_json()`` /
``json.dumps`` — no Python objects cross except the host handle itself).

Layering: like the rest of ``babylon.tui``, this module never imports
``babylon.engine``, ``babylon.persistence``, or the game session directly
(the import-linter contract) — the session and driver arrive pre-composed
through :meth:`RustClientHost.bind_session` as structural protocols. The M1
read methods (:meth:`RustClientHost.read_page_json` and friends) reuse
exactly the same ``CampaignHandle`` Protocol surface
(:mod:`babylon.tui.app`) the Textual client already reads through —
``read_page``/``known_subjects``/``subject_view`` — never a private
``babylon.game.session.GameSession`` attribute (e.g. a raw vault root),
which would defeat the whole point of the Protocol seam. The backlink index
(:meth:`RustClientHost.backlinks_json`) reuses
:func:`babylon.tui.shell.backlinks.build_backlink_index` verbatim rather
than re-deriving the wikilink inversion a second time (that module already
inverts each page's outbound ``babylon.tui.wikilinks.WIKILINK_RE`` matches
for the Textual Wiki view's own "what links here" panel).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from babylon.tui.shell.backlinks import build_backlink_index
from babylon.tui.watchlist import load_watchlist

if TYPE_CHECKING:
    from uuid import UUID

    from babylon.projection.view_models import ProjectionRecord
    from babylon.tui.app import CampaignHandle, PacedDriverHandle
    from babylon.tui.campaign_menu import CampaignCatalog
    from babylon.tui.watchlist import WatchlistPersistence

__all__ = ["RustClientHost"]


class RustClientHost:
    """Serve frozen view-models to the Rust client as JSON strings.

    :param catalog: The campaign catalog seam (``BabylonMetaStore`` in
        production, ``InMemoryCampaignCatalog`` in tests).
    :param defines_hash: Provenance hash of the loaded :class:`GameDefines`,
        stamped on every lobby row.
    :param engine_version: The running engine version, stamped alongside.
    :param watchlist_persistence: The watchlist's cross-session store (see
        :mod:`babylon.tui.watchlist`) — the SAME seam
        ``ArchiveApp(watchlist_persistence=...)`` accepts on the Textual
        path. ``None`` (the default) is an honest "no watchlist store wired"
        — :meth:`watchlist_json` then always serves ``"[]"``, matching M0's
        ``_run_rust_client`` composition root, which does not thread one in
        yet (pin *writes* land in M2; M1 is read-only).
    """

    def __init__(
        self,
        catalog: CampaignCatalog,
        *,
        defines_hash: str,
        engine_version: str,
        watchlist_persistence: WatchlistPersistence | None = None,
    ) -> None:
        self._catalog = catalog
        self._defines_hash = defines_hash
        self._engine_version = engine_version
        self._watchlist_persistence = watchlist_persistence
        #: The bound campaign session (``None`` until :meth:`bind_session`).
        self.session: CampaignHandle | None = None
        #: The bound paced tick driver (``None`` until :meth:`bind_session`).
        self.driver: PacedDriverHandle | None = None
        #: The backlink index's cache key (``(session_id, tick)``), or
        #: ``None`` before the first :meth:`backlinks_json` call — see
        #: :meth:`_backlink_index`.
        self._backlink_cache_key: tuple[UUID, int] | None = None
        #: The cached backlink index for :attr:`_backlink_cache_key`.
        self._backlink_index_cache: dict[str, list[str]] = {}

    def lobby_catalog_json(self) -> str:
        """The lobby catalog as a JSON array string.

        Each row carries the keys the Rust ``LobbyRow`` deserializer
        requires (``campaign_id``/``name``/``tick``) plus ``status`` and the
        provenance stamps. An empty catalog is ``[]`` — honest absence
        (III.11), never a fabricated row.
        """
        rows = [
            {
                "campaign_id": str(campaign.campaign_id),
                "name": campaign.slug,
                "tick": campaign.last_tick,
                "status": campaign.status,
                "defines_hash": self._defines_hash,
                "engine_version": self._engine_version,
            }
            for campaign in self._catalog.list_campaigns()
        ]
        return json.dumps(rows)

    def bind_session(self, session: CampaignHandle, driver: PacedDriverHandle) -> None:
        """Bind the booted campaign session and its paced driver.

        Called by the composition root's campaign loader once the session
        exists; M1+ read methods serve from these handles.
        """
        self.session = session
        self.driver = driver

    def read_page(self, subject: str) -> str | None:
        """Read one baked vault page for the bound campaign — read-only.

        Thin passthrough to :meth:`~babylon.tui.app.CampaignHandle.read_page`
        (:meth:`~babylon.game.session.GameSession.read_page` in production):
        never bakes or writes anything, just reads whatever the vault has
        already materialized.

        :param subject: the vault-relative subject id (e.g.
            ``"county/26163"``).
        :returns: the page's rendered markdown, or ``None`` when no session
            is bound yet, or the vault hasn't baked ``subject`` — never
            fabricated content (Constitution III.11).
        """
        if self.session is None:
            return None
        return self.session.read_page(subject)

    def read_page_json(self, subject: str) -> str:
        """:meth:`read_page`, JSON-encoded — the Rust seam's actual entry point.

        :param subject: the vault-relative subject id.
        :returns: ``json.dumps`` of :meth:`read_page`'s result — a quoted
            JSON string, or the literal ``"null"`` for honest absence.
        """
        return json.dumps(self.read_page(subject))

    def known_subjects_json(self) -> str:
        """Every subject id the bound campaign's vault has baked, sorted.

        :returns: a sorted JSON array of subject ids, or ``"[]"`` when no
            session is bound — never fabricated (Constitution III.11).
        """
        if self.session is None:
            return json.dumps([])
        return json.dumps(sorted(self.session.known_subjects()))

    def _backlink_index(self) -> dict[str, list[str]]:
        """The bound campaign's ``target -> sorted [linking subjects]`` index.

        Delegates the actual inversion to
        :func:`~babylon.tui.shell.backlinks.build_backlink_index` — the SAME
        function the Textual Wiki view's own "what links here" panel already
        uses — over every page the bound session's vault has baked so far
        (:meth:`~babylon.tui.app.CampaignHandle.known_subjects`, itself
        bounded by :func:`~babylon.game.session.vault_known_subjects`'s own
        ``_MAX_VAULT_PAGES`` static scan ceiling, so this walk is never
        unbounded even though its trip count is runtime-determined).

        Cached per ``(session_id, tick)``: a live campaign's vault only
        grows between ticks (never mutates an already-baked page in place),
        so the index built for a given tick stays valid until the next one
        commits — recomputing it on every :meth:`backlinks_json` call within
        the same tick would re-walk and re-parse every known page for no
        benefit.

        :returns: ``{target: sorted_subjects}``, or ``{}`` when no session
            is bound.
        """
        if self.session is None:
            return {}
        cache_key = (self.session.session_id, self.session.tick)
        if cache_key != self._backlink_cache_key:
            pages = {
                subject: page
                for subject in self.session.known_subjects()
                if (page := self.session.read_page(subject)) is not None
            }
            self._backlink_index_cache = {
                target: list(sources) for target, sources in build_backlink_index(pages).items()
            }
            self._backlink_cache_key = cache_key
        return self._backlink_index_cache

    def backlinks_json(self, subject: str) -> str:
        """Subjects whose pages link to ``subject``, sorted.

        :param subject: the target subject id to look up inbound links for.
        :returns: a sorted JSON array of subject ids, or ``"[]"`` when no
            session is bound, or nothing links to ``subject`` — never
            fabricated (Constitution III.11).
        """
        return json.dumps(sorted(self._backlink_index().get(subject, [])))

    def subject_view_json(self, subject: str) -> str:
        """The bound campaign's live per-subject dossier view-model, as JSON.

        Thin passthrough to
        :meth:`~babylon.tui.app.CampaignHandle.subject_view`
        (:meth:`~babylon.game.session.GameSession.subject_view` in
        production), computed fresh off the live graph every call — never
        cached, unlike :meth:`backlinks_json`'s vault-page index (a
        subject's projected view can change every tick even when its baked
        vault page has not been re-rendered).

        :param subject: the vault-relative subject id.
        :returns: :meth:`~pydantic.BaseModel.model_dump_json` of the
            resolved :data:`~babylon.projection.view_models.ProjectionRecord`,
            or the literal ``"null"`` when no session is bound, or the
            subject resolves to no live view — never a fabricated plate
            (Constitution III.11).
        """
        if self.session is None:
            return "null"
        view: ProjectionRecord | None = self.session.subject_view(subject)
        if view is None:
            return "null"
        return view.model_dump_json()

    def watchlist_json(self) -> str:
        """The bound campaign's persisted watchlist rows, read-only.

        Hydrates via :func:`~babylon.tui.watchlist.load_watchlist` over
        :attr:`_watchlist_persistence` — the SAME seam/function
        ``ArchiveApp._on_campaign_chosen`` already uses to restore a
        resumed campaign's pin order — keyed by the bound session's own
        ``session_id``. Each row is ``{"subject": pinned_id}``, in pin
        order (FIFO — see :class:`~babylon.tui.watchlist.WatchlistState`'s
        own ordering contract, never re-sorted here): the Rust
        ``WatchlistView`` renders generically over whatever keys a row
        carries, requiring only a ``"subject"`` string (``host.rs``'s own
        schema note) — pin/unpin *writes* land in M2, so this module does
        not attempt to reproduce ``watchlist.py``'s own
        ``peek(view, depth=0)`` row prose.

        :returns: a JSON array of ``{"subject": ...}`` rows in pin order, or
            ``"[]"`` when no session is bound, no
            :class:`~babylon.tui.watchlist.WatchlistPersistence` was wired,
            or the watchlist is honestly empty — never fabricated
            (Constitution III.11).
        """
        if self.session is None or self._watchlist_persistence is None:
            return json.dumps([])
        state = load_watchlist(self._watchlist_persistence, str(self.session.session_id))
        return json.dumps([{"subject": subject} for subject in state.pinned_ids])
