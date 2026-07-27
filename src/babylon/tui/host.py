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
than re-deriving the wikilink inversion a second time — a shared
``babylon.tui.shell`` helper, not something the Textual client itself
consumes (no Textual "what links here" panel exists today); the Rust
client's wiki footer is :meth:`RustClientHost.backlinks_json`'s only
consumer so far.

:meth:`load_campaign` (M1 wiring) is the seam the Rust lobby actually
calls once a player picks a campaign row: it resolves ``campaign_id``
through the ``campaign_loader`` the constructor now accepts, builds the
paced driver through the optional ``driver_factory``, and binds both via
:meth:`bind_session` — closing the gap where ``bind_session`` shipped
with zero production caller.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

from babylon.tui.campaign_menu import operation_codename
from babylon.tui.shell.backlinks import build_backlink_index
from babylon.tui.watchlist import load_watchlist

if TYPE_CHECKING:
    from babylon.projection.view_models import ProjectionRecord
    from babylon.tui.app import CampaignHandle, CampaignLoader, DriverFactory, PacedDriverHandle
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
    :param campaign_loader: The lobby's boot-or-resume seam (see
        :data:`~babylon.tui.app.CampaignLoader`) — the SAME seam
        ``ArchiveApp(campaign_loader=...)`` accepts on the Textual path.
        ``None`` (the default) is an honest "no loader wired" —
        :meth:`load_campaign` then raises :class:`RuntimeError` rather than
        silently serving absence (Constitution III.11); the real
        ``_run_rust_client`` composition root always wires one.
    :param driver_factory: The booted campaign's pacing-driver seam (see
        :data:`~babylon.tui.app.DriverFactory`) — the SAME seam
        ``ArchiveApp(driver_factory=...)`` accepts. ``None`` (the default)
        is a legal M1 answer too: the read-only M1 surface never calls
        :meth:`~babylon.tui.app.PacedDriverHandle.advance_once` through
        :attr:`driver`, so :meth:`load_campaign` binds a driver-less
        session rather than manufacturing one nothing here needs yet.
    :param watchlist_persistence: The watchlist's cross-session store (see
        :mod:`babylon.tui.watchlist`) — the SAME seam
        ``ArchiveApp(watchlist_persistence=...)`` accepts on the Textual
        path. ``None`` (the default) is an honest "no watchlist store wired"
        — :meth:`watchlist_json` then always serves ``"[]"``.
    """

    def __init__(
        self,
        catalog: CampaignCatalog,
        *,
        defines_hash: str,
        engine_version: str,
        campaign_loader: CampaignLoader | None = None,
        driver_factory: DriverFactory | None = None,
        watchlist_persistence: WatchlistPersistence | None = None,
    ) -> None:
        self._catalog = catalog
        self._defines_hash = defines_hash
        self._engine_version = engine_version
        self._campaign_loader = campaign_loader
        self._driver_factory = driver_factory
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
        requires (``campaign_id``/``name``/``tick``) plus ``status``, the
        provenance stamps, and ``codename`` — the SAME
        :func:`~babylon.projection.briefing.operation_codename` derivation
        the Textual lobby's own ``LobbyRow.codename`` renders (spec-116
        FR-116-3): ``name`` is the machine slug, ``codename`` is the
        player-facing display name, and the Rust lobby must render the
        latter, not the former. An empty catalog is ``[]`` — honest absence
        (III.11), never a fabricated row.
        """
        rows = [
            {
                "campaign_id": str(campaign.campaign_id),
                "name": campaign.slug,
                "codename": operation_codename(campaign.campaign_id),
                "tick": campaign.last_tick,
                "status": campaign.status,
                "defines_hash": self._defines_hash,
                "engine_version": self._engine_version,
            }
            for campaign in self._catalog.list_campaigns()
        ]
        return json.dumps(rows)

    def load_campaign(self, campaign_id: str) -> str:
        """Resolve and bind the campaign the Rust lobby just chose (M1 wiring).

        The Rust shell calls this once the player picks a lobby row.
        Mirrors :meth:`~babylon.tui.app.ArchiveApp._on_campaign_chosen`'s own
        composition: resolves ``campaign_id`` through :attr:`_campaign_loader`
        (:data:`~babylon.tui.app.CampaignLoader`), builds the paced driver
        through :attr:`_driver_factory` when one was wired (``None``
        otherwise — legal for M1's read-only surface), and binds both
        through :meth:`bind_session` — closing the gap where
        ``bind_session`` shipped with zero production caller and every M1
        read method served absence against a never-bound session.

        :param campaign_id: the campaign UUID, as the string the Rust side
            holds.
        :raises RuntimeError: no ``campaign_loader`` was wired at
            construction — unreachable through the real ``babylon play
            --client rust`` composition root (which always wires one);
            never silently served as absence (Constitution III.11).
        :raises ValueError: ``campaign_id`` is not a valid UUID string.
        :raises Exception: whatever the wired ``campaign_loader`` itself
            raises (e.g. a session that fails to boot/resume) — propagated
            verbatim, never caught and re-encoded as a fabricated failure
            payload: the Rust seam propagates Python exceptions loudly by
            design (M1).
        :returns: ``json.dumps({"ok": True, "campaign_id": campaign_id})``
            on success.
        """
        if self._campaign_loader is None:
            msg = (
                "RustClientHost.load_campaign: no campaign_loader was wired "
                "at construction — the Rust lobby has no way to boot this "
                "campaign"
            )
            raise RuntimeError(msg)
        campaign = self._campaign_loader(UUID(campaign_id))
        driver = self._driver_factory(campaign) if self._driver_factory is not None else None
        self.bind_session(campaign, driver)
        return json.dumps({"ok": True, "campaign_id": campaign_id})

    def bind_session(self, session: CampaignHandle, driver: PacedDriverHandle | None) -> None:
        """Bind the booted campaign session and its paced driver.

        Called by :meth:`load_campaign` once the wired ``campaign_loader``
        resolves a session; M1+ read methods serve from these handles.

        :param session: the just-resolved campaign handle.
        :param driver: the campaign's paced tick driver, or ``None`` when no
            ``driver_factory`` was wired (a legal M1 answer — the read-only
            M1 surface never advances a tick through :attr:`driver`).
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
        :func:`~babylon.tui.shell.backlinks.build_backlink_index` — a shared
        ``babylon.tui.shell`` helper, not something any Textual view
        consumes today (no Textual "what links here" panel exists; this
        host method and the Rust client's wiki footer are its only
        consumer) — over every page the bound session's vault has baked so
        far (:meth:`~babylon.tui.app.CampaignHandle.known_subjects`, itself
        bounded by :func:`~babylon.game.session.vault_known_subjects`'s own
        ``_MAX_VAULT_PAGES`` static scan ceiling, so this walk is never
        unbounded even though its trip count is runtime-determined).

        Cached per ``(session_id, tick)``: a live campaign's vault only
        grows between ticks (never mutates an already-baked page in place),
        so the index built for a given tick stays valid until the next one
        commits — recomputing it on every :meth:`backlinks_json` call within
        the same tick would re-walk and re-parse every known page for no
        benefit.

        KNOWN M1 LIMITATION (accepted, not fixed by this cache's semantics):
        :meth:`~babylon.projection.vault.incremental_baker.
        IncrementalArchiveTickBaker.bake_page_on_visit` can bake a page
        MID-tick (the lazy on-demand path for ``community`` dossiers, which
        have no backing graph node to dirty-track), so a page baked that way
        can go unreflected in this index until the NEXT tick commits and
        changes ``self.session.tick`` (and therefore this cache's key) —
        within the same tick, this cache has no signal that a mid-tick bake
        happened at all.

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
