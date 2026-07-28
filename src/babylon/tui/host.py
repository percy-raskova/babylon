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

**M2 "Playable" surface** (contracts:
``docs/superpowers/specs/2026-07-27-m2-seam-contracts.md``): the eleven
write/tick methods below (:meth:`pacing_state_json` through
:meth:`save_nav_state`) widen the seam from read-only to playable. Every
one still crosses only JSON-encoded primitives; write/tick verbs return an
``{"ok": ...}`` envelope mirroring :meth:`load_campaign`'s own convention.
A player-reachable refusal (a Rust-side pre-check that somehow still
raced, a watchlist at capacity, an ineligible verb) is caught and encoded
as ``{"ok": False, "error": ...}``; a system-level failure is never
caught, and propagates to panic loudly (Constitution III.11) — the two
classes are handled differently on purpose, per method docstring below.

**M3 "Tutorial gate" surface** (contract:
``docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md``): three more
methods — :meth:`tutorial_state_json` (Task 27, §1), :meth:`new_campaign`
(§2), and :meth:`load_campaign`'s ack gaining ``home_subject`` (§4). The
constructor's new ``tutorial_steps``/``tutorial_progress_factory`` keyword
pair mirrors :class:`~babylon.tui.app.ArchiveApp`'s own identically-named
parameters (:data:`~babylon.tui.app.TutorialProgressFactory`, widened by
this same contract's ``VerbIssued`` defect fix — see
:mod:`babylon.game.tutorial_runtime`'s own module docstring) — this module
imports that Protocol/type-alias pair from ``babylon.tui.app`` rather than
redeclaring them, and never imports ``babylon.game.tutorial`` directly (the
same layering discipline every other seam in this module already follows).
:attr:`verb_log`/:attr:`completion_log` are the harness's own read surface
(contract §5) — see each attribute's own docstring for exactly what resets
on :meth:`bind_session` and what deliberately does not.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from babylon.models.event_severity import resolve_severity
from babylon.render.config import RenderConfig
from babylon.tui.campaign_menu import CampaignMenu, operation_codename
from babylon.tui.chronicle import (
    CHRONICLE_ROW_CEILING,
    chronicle_stream,
    resolve_actor,
    resolve_navigable_subject,
)
from babylon.tui.chronicle_salience import (
    apply_volume_floors,
    compute_autopause_state,
    dedupe_consecutive,
    render_autopause_indicator,
)
from babylon.tui.nav import HOME_SUBJECT
from babylon.tui.shell.backlinks import build_backlink_index
from babylon.tui.watchlist import load_watchlist, save_watchlist

if TYPE_CHECKING:
    from collections.abc import Sequence

    from babylon.projection.endgame import EndgameStatus
    from babylon.projection.verbs.view_models import VerbPlateView
    from babylon.projection.view_models import FieldStateView, ProjectionRecord
    from babylon.tui.app import (
        CampaignHandle,
        CampaignLoader,
        DriverFactory,
        PacedDriverHandle,
        TickOutcome,
        TutorialProgressFactory,
    )
    from babylon.tui.campaign_menu import CampaignCatalog
    from babylon.tui.chronicle import ChronicleEvent, TickBulletin
    from babylon.tui.nav import NavPersistence
    from babylon.tui.tutorial_overlay import TutorialProgress
    from babylon.tui.watchlist import WatchlistPersistence

__all__ = ["RustClientHost"]


class TutorialStepSource(Protocol):
    """Structural shape of one tutorial step AS THIS HOST consumes it.

    The WO-37 idiom one more time (:class:`~babylon.tui.tutorial_overlay.
    TutorialStepView` renders two derived fields; this host's
    :meth:`RustClientHost.tutorial_state_json` envelope additionally needs
    the step's stable ``id`` and its Director-authored ``patches`` line, so
    it declares its own four-member view rather than widening the overlay's
    narrower Protocol — each consumer names exactly the members it touches,
    and the concrete :class:`~babylon.game.tutorial.TutorialStep` satisfies
    both without either module importing the other).
    """

    @property
    def id(self) -> str:
        """The step's stable machine key (the envelope's ``step_id``)."""
        ...

    @property
    def patches(self) -> str:
        """The step's Director-authored guide line (M3 contract §0/§8)."""
        ...

    @property
    def scenario_name(self) -> str:
        """The one-sentence Given/When/Then summary (the heading tail)."""
        ...

    @property
    def overlay_text(self) -> str:
        """The GIVEN/WHEN/THEN block (the envelope's ``body``)."""
        ...


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
    :param nav_persistence: The nav shell's cross-session store (see
        :mod:`babylon.tui.nav`) — M2's fresh wiring (Task 25): Textual never
        wired nav persistence in production at all (``app.py`` boots a
        throwaway ``uuid4`` + ``InMemoryNavPersistence``), so there is no
        Textual seam to mirror here, unlike ``watchlist_persistence``.
        ``None`` (the default) is an honest "no nav store wired" —
        :meth:`nav_state_json` then always serves an empty jumplist and
        breadcrumb trail.
    :param tutorial_steps: The guided opening-arc step sequence to render
        (Task 27, M3) — the SAME seam
        ``ArchiveApp(tutorial_steps=...)`` accepts on the Textual path, and
        (in the real ``babylon play --client rust`` composition root)
        literally the SAME objects, since :mod:`babylon.cli.play` computes
        the slice once and threads it into both hosts. ``None`` (the
        default) leaves the tutorial permanently inactive for every bound
        session — :meth:`tutorial_state_json` then always serves
        ``{"active": false}``. REQUIRED together with
        ``tutorial_progress_factory`` — giving exactly one without the
        other raises :class:`ValueError` at construction (R14 fix; mirrors
        :class:`~babylon.tui.app.ArchiveApp`'s own
        ``campaign_menu``/``campaign_loader`` guard pattern).
    :param tutorial_progress_factory: The tutorial-progress seam
        (:data:`~babylon.tui.app.TutorialProgressFactory`, widened by the
        M3 ``VerbIssued`` defect fix); when given (and ``tutorial_steps``
        too), :meth:`bind_session` builds this campaign's
        :class:`~babylon.tui.tutorial_overlay.TutorialProgress` evaluator.
        ``None`` (the default, or the factory itself declining for this
        particular campaign — its own new-vs-resumed gating) means
        :meth:`tutorial_state_json` never activates for the bound session.
        REQUIRED together with ``tutorial_steps`` — see that parameter's
        own note on the constructor-time pair guard.
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
        nav_persistence: NavPersistence | None = None,
        tutorial_steps: Sequence[TutorialStepSource] | None = None,
        tutorial_progress_factory: TutorialProgressFactory | None = None,
        render_config: RenderConfig | None = None,
    ) -> None:
        if tutorial_progress_factory is not None and tutorial_steps is None:
            msg = (
                "RustClientHost: tutorial_progress_factory was given but no "
                "tutorial_steps — there would be nothing for tutorial_state_json "
                "to render"
            )
            raise ValueError(msg)
        if tutorial_steps is not None and tutorial_progress_factory is None:
            msg = (
                "RustClientHost: tutorial_steps was given but no "
                "tutorial_progress_factory — there would be no evaluator to "
                "resolve step completion against"
            )
            raise ValueError(msg)
        self._catalog = catalog
        self._defines_hash = defines_hash
        self._engine_version = engine_version
        self._campaign_loader = campaign_loader
        self._driver_factory = driver_factory
        self._watchlist_persistence = watchlist_persistence
        self._nav_persistence = nav_persistence
        self._tutorial_steps = tutorial_steps
        self._tutorial_progress_factory = tutorial_progress_factory
        #: The recorded ``[render]`` verdict (Task 35, contract §7) — read
        #: once by the composition root via
        #: :func:`babylon.render.config.read_render_config`; ``None`` means
        #: no probe was ever recorded and :meth:`render_config_json` reports
        #: the glyph-floor defaults (ADR097 D4: runtime never re-probes).
        self._render_config = render_config if render_config is not None else RenderConfig()
        #: The lobby mint's own controller (§2) — built lazily, once, by
        #: :meth:`new_campaign` (mirrors ``ArchiveApp``'s own
        #: ``campaign_menu`` object, but this host has no constructor
        #: parameter for it: the Rust lobby never needs to LIST through this
        #: seam, only to MINT through it, so a lazy build is simpler than
        #: threading a fourth constructor parameter for one call site).
        self._campaign_menu: CampaignMenu | None = None
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
        #: The host's own running chronicle accumulator (Task 22) — mirrors
        #: :attr:`~babylon.tui.app.ArchiveApp._chronicle_history`, capped at
        #: :data:`~babylon.tui.chronicle.CHRONICLE_ROW_CEILING`; reset by
        #: :meth:`bind_session` (a fresh/resumed campaign never inherits a
        #: prior session's rail).
        self._chronicle_history: tuple[ChronicleEvent, ...] = ()
        #: Every distinct verb/binding-action name dispatched through this
        #: host, for the host's OWN LIFETIME (M3 ``VerbIssued`` defect fix,
        #: contract §0/§1) — :meth:`new_campaign`/:meth:`issue_verb` add to
        #: this on dispatch, before any refusal branch (dispatch-proof,
        #: never outcome-proof — mirrors ``ArchiveApp._verbs_issued``).
        #: Exposed as a public attribute: the M3 parity harness (contract
        #: §5, tier 2) asserts against it directly.
        #:
        #: THE ONE READER: the public :meth:`was_verb_issued` method — the
        #: harness's own tier-2 dispatch-proof surface — reads this LIFETIME
        #: log unioned with :attr:`_tutorial_chrome_verbs`. It deliberately
        #: does NOT read :attr:`_session_verb_log` below: ``new_campaign``
        #: fires from the lobby strictly BEFORE any session is ever bound
        #: (see the "deliberately NOT reset" paragraph just below), so a
        #: harness assertion made after :meth:`bind_session` has already
        #: reset the session-scoped log needs the lifetime one to still see
        #: it. The tutorial EVALUATOR itself never reads this attribute —
        #: see :meth:`_tutorial_was_verb_issued`'s own docstring for why.
        #:
        #: Deliberately NOT reset by :meth:`bind_session` — a friction
        #: against the contract's own "the host's verb log and the
        #: accumulator reset on every bind_session" line (§0): the FIRST
        #: tutorial beat, ``boot_into_lobby``, is
        #: ``VerbIssued(verb="new_campaign")``, dispatched from the LOBBY
        #: via :meth:`new_campaign` strictly BEFORE any session is ever
        #: bound; if this reset on :meth:`bind_session`, ``"new_campaign"``
        #: would already be gone by the time the harness's own end-of-run
        #: assertion ("host verb log contains new_campaign and aid", §5
        #: tier 2) checks it — an unsatisfiable requirement under a literal
        #: reading. :attr:`completion_log` and the tutorial poll's own
        #: per-session accumulator (:attr:`_tutorial_index` and friends,
        #: below) DO reset on :meth:`bind_session`, exactly as written —
        #: those really are session-scoped, unlike this log.
        self.verb_log: set[str] = set()
        #: Every distinct verb/binding-action name dispatched THIS BOUND
        #: SESSION (R5 fix) — :meth:`new_campaign`/:meth:`issue_verb` write
        #: to this alongside :attr:`verb_log` above, on the same dispatch-
        #: proof, before-any-refusal-branch terms. Reset to a fresh empty
        #: set by :meth:`bind_session`, unlike :attr:`verb_log`.
        #:
        #: THE ONE READER: the tutorial EVALUATOR seam,
        #: :meth:`_tutorial_was_verb_issued` — never the public
        #: :meth:`was_verb_issued`, and never read directly by anything else.
        #: This is the fix for a reachable second-campaign false-complete: a
        #: player who finishes campaign A's tutorial (dispatching, say,
        #: ``"aid"``) and then — the Rust client alone can do this, since it
        #: returns to the lobby, unlike Textual — starts a fresh campaign B,
        #: would otherwise have campaign B's very first
        #: ``VerbIssued(verb="aid")`` poll read TRUE off :attr:`verb_log`'s
        #: still-lifetime-populated ``"aid"`` entry, before the player ever
        #: issued Aid in campaign B at all. Session-scoping the evaluator's
        #: own read means each bound session starts this log empty.
        self._session_verb_log: set[str] = set()
        #: The tutorial evaluator's own completion accumulator (M3, contract
        #: §5 tier 1): one ``(step_id, poll_ordinal)`` tuple per step the
        #: running poll loop in :meth:`tutorial_state_json` has observed
        #: complete, in arc order. Reset by :meth:`bind_session` (unlike
        #: :attr:`verb_log` above — see that attribute's own docstring for
        #: why the two differ). Exposed as a public attribute for the same
        #: harness-assertion reason as :attr:`verb_log`.
        self.completion_log: list[tuple[str, int]] = []
        #: This host's own tutorial-progress evaluator — ``None`` until a
        #: ``tutorial_progress_factory``/``tutorial_steps`` pair was wired
        #: AND :meth:`bind_session` has run AND the factory itself did not
        #: decline (its own new-vs-resumed gating). Built fresh by every
        #: :meth:`bind_session` call, mirroring ``ArchiveApp.
        #: _tutorial_progress``'s own per-campaign lifecycle.
        self._tutorial_evaluator: TutorialProgress | None = None
        #: The tutorial poll loop's own running index into
        #: :attr:`_tutorial_steps` — mirrors
        #: :class:`~babylon.tui.tutorial_overlay.TutorialOverlay`'s own
        #: ``_current_index``. Reset by :meth:`bind_session`.
        self._tutorial_index: int = 0
        #: How many :meth:`tutorial_state_json` calls this bound session has
        #: served so far — :attr:`completion_log`'s own ordinal axis. Reset
        #: by :meth:`bind_session`.
        self._tutorial_poll_ordinal: int = 0
        #: The client's own reported wiki-view subject, refreshed by every
        #: :meth:`tutorial_state_json` call — the seam
        #: :class:`~babylon.game.tutorial_runtime.TutorialRuntimeProgress`'s
        #: ``current_subject`` callable closes over (contract §1's own
        #: RECORDED DEVIATION: the host has no truth of its own here, the
        #: client reports its display state each poll). Reset by
        #: :meth:`bind_session`.
        self._tutorial_current_subject: str | None = None
        #: Same idea as :attr:`_tutorial_current_subject`, for the client's
        #: reported current pane.
        self._tutorial_current_pane: str | None = None
        #: The latest poll's cumulative ``chrome_verbs`` report (contract
        #: §1) — consulted by :meth:`_tutorial_was_verb_issued`. Reset by
        #: :meth:`bind_session`.
        self._tutorial_chrome_verbs: frozenset[str] = frozenset()
        #: The bound session's own pinned-subject cache (R13a fix) — hydrated
        #: once by :meth:`bind_session` through the SAME
        #: :func:`~babylon.tui.watchlist.load_watchlist` path
        #: :meth:`watchlist_json` reads, then updated write-through by
        #: :meth:`pin_watchlist` on every successful pin/unpin. Exists so
        #: :meth:`_tutorial_is_pinned` — polled every :meth:`tutorial_state_json`
        #: call — never hits :attr:`_watchlist_persistence` per poll;
        #: :meth:`watchlist_json` itself is UNCHANGED, still reading the store
        #: directly (its own concern, not this cache's).
        self._pinned_subjects: set[str] = set()

    def was_verb_issued(self, name: str) -> bool:
        """Whether ``name``'s dispatch has been observed this HOST'S LIFETIME.

        Reads :attr:`verb_log` (the lifetime log — never resets) unioned
        with the client's latest-reported chrome dispatch log
        (``view_state.chrome_verbs``). Public because it is the parity
        harness's tier-2 read surface (contract §5): ``new_campaign`` fires
        from the lobby strictly BEFORE any session is ever bound, so a
        harness assertion made after :meth:`bind_session` needs a log that
        was never reset to still see it (see :attr:`verb_log`'s own
        docstring).

        R5 fix (deliberate divergence from the tutorial evaluator's own
        seam): this is NOT the same union :meth:`_tutorial_was_verb_issued`
        reads — that private method reads the SESSION-scoped
        :attr:`_session_verb_log` instead, precisely so a second campaign's
        tutorial arc never sees a verb dispatched by a PRIOR campaign as
        already complete. This public method keeps reading the lifetime log
        on purpose; see :attr:`_session_verb_log`'s own docstring for why
        the two readers differ.

        :param name: the dispatch-proof verb/action name (e.g. ``"aid"``,
            ``"new_campaign"``, ``"peek_wikilink"``).
        :returns: ``True`` iff the dispatch has been observed.
        """
        return name in self.verb_log or name in self._tutorial_chrome_verbs

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

    def new_campaign(self) -> str:
        """Mint a fresh campaign through the SAME lobby mint path the
        Textual lobby drives (Task 27, contract §2) — the Rust lobby's own
        ``n`` binding calls this once.

        Lazily constructs (once) a
        :class:`~babylon.tui.campaign_menu.CampaignMenu` over
        :attr:`_catalog` (the SAME catalog seam :meth:`lobby_catalog_json`
        already reads) and calls its
        :meth:`~babylon.tui.campaign_menu.CampaignMenu.new_campaign` — the
        identical call
        :meth:`~babylon.tui.campaign_menu.LobbyScreen.action_new_campaign`
        drives on the Textual path. Records ``"new_campaign"`` into BOTH
        :attr:`verb_log` and :attr:`_session_verb_log` on success (R5 fix)
        — the arc's own ``boot_into_lobby`` beat's
        ``VerbIssued(verb="new_campaign")`` dispatch proof (see
        :attr:`verb_log`'s own docstring for why the LIFETIME record
        deliberately outlives the very next :meth:`bind_session` call; the
        SESSION-scoped record does not, and that is fine — see
        :attr:`_session_verb_log`'s own docstring for why nothing actually
        depends on it surviving that reset).

        :raises Exception: whatever :attr:`_catalog`'s own
            ``create_campaign`` raises — a catalog failure is a SYSTEM
            failure here, by design: no ``{"ok": False, ...}`` refusal
            branch exists for this method, so nothing is ever caught here;
            it propagates and panics loudly (Constitution III.11).
        :returns: ``json.dumps({"ok": True, "campaign_id": "<uuid>",
            "codename": "<operation codename>"})`` (field order pinned).
        """
        if self._campaign_menu is None:
            self._campaign_menu = CampaignMenu(
                self._catalog, engine_version=self._engine_version, defines_hash=self._defines_hash
            )
        row = self._campaign_menu.new_campaign()
        self.verb_log.add("new_campaign")
        self._session_verb_log.add("new_campaign")
        return json.dumps(
            {"ok": True, "campaign_id": str(row.campaign_id), "codename": row.codename}
        )

    def load_campaign(self, campaign_id: str) -> str:
        """Resolve and bind the campaign the Rust lobby just chose (M1 wiring).

        The Rust shell calls this once the player picks a lobby row.
        Mirrors :meth:`~babylon.tui.app.ArchiveApp._on_campaign_chosen`'s own
        composition: resolves ``campaign_id`` through :attr:`_campaign_loader`
        (:data:`~babylon.tui.app.CampaignLoader`), builds the paced driver
        through :attr:`_driver_factory` when one was wired (``None``
        otherwise — reads still serve, tick verbs refuse), and binds both
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
        :returns: ``json.dumps({"ok": True, "campaign_id": campaign_id,
            "tick": <session tick>, "home_subject": "county/26163"})`` on
            success (field order pinned) — the tick rides the ack so the
            Rust HUD's ``T+{tick}`` counter is honest for a RESUMED campaign
            (a zeroed counter over a tick-300 session would be a fabricated
            value, III.11); ``home_subject`` is the M3 addition (contract
            §4), sourced from :data:`~babylon.tui.nav.HOME_SUBJECT` (a leaf
            constant, R10 fix) — Wayne stays the only baked scenario
            (ruling 3), one single source rather than a second hardcoded
            copy of the subject id.
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
        return json.dumps(
            {
                "ok": True,
                "campaign_id": campaign_id,
                "tick": campaign.tick,
                "home_subject": HOME_SUBJECT,
            }
        )

    def bind_session(self, session: CampaignHandle, driver: PacedDriverHandle | None) -> None:
        """Bind the booted campaign session and its paced driver.

        Called by :meth:`load_campaign` once the wired ``campaign_loader``
        resolves a session; M1+ read methods serve from these handles.

        M3 addition (Task 27): also (re)builds the tutorial evaluator
        through :attr:`_tutorial_progress_factory` — the SAME widened
        :data:`~babylon.tui.app.TutorialProgressFactory` seam
        ``ArchiveApp._on_campaign_chosen`` calls on the Textual path — and
        resets the tutorial poll accumulator (:attr:`completion_log`,
        :attr:`_tutorial_index`, the view-state holders below): a freshly-
        bound (or re-bound) session never inherits a prior session's
        tutorial walk, exactly the same reasoning :attr:`_chronicle_history`
        already uses just below. :attr:`verb_log` is DELIBERATELY excluded
        from this reset — see its own docstring for why;
        :attr:`_session_verb_log` is NOT excluded (R5 fix) — it resets here
        exactly like every other per-session accumulator.

        R13a addition: hydrates :attr:`_pinned_subjects` once, through the
        SAME :func:`~babylon.tui.watchlist.load_watchlist` path
        :meth:`watchlist_json` uses — so :meth:`_tutorial_is_pinned` never
        needs to hit :attr:`_watchlist_persistence` again until the next
        :meth:`pin_watchlist` write-through.

        :param session: the just-resolved campaign handle.
        :param driver: the campaign's paced tick driver, or ``None`` when no
            ``driver_factory`` was wired (a legal M1 answer — the read-only
            M1 surface never advances a tick through :attr:`driver`).
        """
        self.session = session
        self.driver = driver
        #: A freshly-bound (or re-bound) session never inherits a prior
        #: session's chronicle rail (Task 22) — reset alongside the handles
        #: themselves, not left for the first :meth:`chronicle_rail_json`
        #: call to notice a stale history.
        self._chronicle_history = ()
        self.completion_log = []
        self._tutorial_index = 0
        self._tutorial_poll_ordinal = 0
        self._tutorial_current_subject = None
        self._tutorial_current_pane = None
        self._tutorial_chrome_verbs = frozenset()
        self._session_verb_log = set()
        if self._watchlist_persistence is None:
            self._pinned_subjects = set()
        else:
            state = load_watchlist(self._watchlist_persistence, str(session.session_id))
            self._pinned_subjects = set(state.pinned_ids)
        if self._tutorial_progress_factory is None or self._tutorial_steps is None:
            self._tutorial_evaluator = None
        else:
            self._tutorial_evaluator = self._tutorial_progress_factory(
                session,
                driver,
                lambda: self._tutorial_current_subject,
                lambda: self._tutorial_current_pane,
                self._tutorial_is_pinned,
                self._tutorial_was_verb_issued,
            )

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
        """The bound campaign's persisted watchlist rows (writes cross
        through :meth:`pin_watchlist`).

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

    # --- M2 "Playable" surface (Tasks 21-25; contracts: docs/superpowers/
    # specs/2026-07-27-m2-seam-contracts.md). ------------------------------

    def pacing_state_json(self) -> str:
        """Paced-driver state for Rust's own pre-checks + the HUD PACING line (Task 21).

        :returns: ``json.dumps`` of a dict literal in the contract's own
            key order — ``attached``, ``locked``, ``lock_reason``,
            ``awaiting_ack``, ``pause_summary``, ``busy`` — mirroring
            :class:`~babylon.tui.app.PacedDriverHandle` (primitives only; a
            :class:`~babylon.models.enums.events.GameOutcome` IS a ``str``,
            so ``lock_reason`` crosses with no cast). ``attached=False``
            (every other field ``False``/``None``) when no paced driver is
            bound — no campaign bound at all, or a ``driver_factory`` was
            never wired (a legal M1 answer).
        """
        if self.driver is None:
            return json.dumps(
                {
                    "attached": False,
                    "locked": False,
                    "lock_reason": None,
                    "awaiting_ack": False,
                    "pause_summary": None,
                    "busy": False,
                }
            )
        return json.dumps(
            {
                "attached": True,
                "locked": self.driver.locked,
                "lock_reason": self.driver.lock_reason,
                "awaiting_ack": self.driver.awaiting_ack,
                "pause_summary": self.driver.pause_summary,
                "busy": self.driver.busy,
            }
        )

    def _accumulate_chronicle(self, events: tuple[ChronicleEvent, ...]) -> None:
        """Append ``events`` onto the host's own running chronicle rail, capped.

        Mirrors :meth:`~babylon.tui.app.ArchiveApp._refresh_chronicle`'s own
        accumulator (``app.py:1663-1694``): growing across ticks, capped at
        :data:`~babylon.tui.chronicle.CHRONICLE_ROW_CEILING`, reset only by
        :meth:`bind_session`.

        :param events: one tick's chronicle events, chronological.
        """
        combined = (*self._chronicle_history, *events)
        self._chronicle_history = combined[-CHRONICLE_ROW_CEILING:]

    @staticmethod
    def _tick_outcome(result: TickOutcome) -> dict[str, object]:
        """Hand-build one ``{"tick", "paused", "chronicle"}`` outcome dict.

        :attr:`~babylon.game.session.TickAdvanceResult`'s own ``__slots__``
        is alphabetical and it is NOT pydantic — this dict literal's key
        order is the contract's own (``tick``, ``paused``, ``chronicle``),
        never derived by introspecting ``result``. ``world``/``events``/
        ``autosaved``/``determinism_hash`` are deliberately excluded (the
        contract's narrower seam).

        :param result: one resolved tick (:class:`~babylon.tui.app.TickOutcome`).
        :returns: the hand-built outcome dict; ``chronicle`` entries are each
            :meth:`~pydantic.BaseModel.model_dump` (``mode="json"``) of one
            :class:`~babylon.tui.chronicle.ChronicleEvent`, declaration order
            (``tick``, ``event_type``, ``summary``, ``data``, ``class_names``,
            ``org_names``).
        """
        return {
            "tick": result.tick,
            "paused": result.paused,
            "chronicle": [event.model_dump(mode="json") for event in result.chronicle],
        }

    def advance_tick(self) -> str:
        """Advance the bound campaign exactly one tick (Task 21).

        Delegates to :meth:`~babylon.tui.app.PacedDriverHandle.advance_once`
        — the same seam Textual's own ``t`` binding drives
        (:meth:`~babylon.tui.app.ArchiveApp.action_advance_tick`). Rust
        pre-checks :meth:`pacing_state_json`'s ``locked``/``awaiting_ack``/
        ``busy`` flags, in that exact order, before ever calling this method
        (the contract's own "established pre-check pattern, NOT exception
        translation") — a :class:`~babylon.game.pacing.PacingError` that
        still escapes here is therefore a BUG, never a player-reachable
        refusal, and is never caught: it propagates and panics loudly
        (Constitution III.11).

        This tick's chronicle feeds :meth:`_accumulate_chronicle` BEFORE
        serialization, so :meth:`chronicle_rail_json`'s next call already
        reflects it.

        :returns: ``json.dumps({"ok": True, "outcome": {...}})`` — see
            :meth:`_tick_outcome` for ``outcome``'s own shape — or a loud
            refusal envelope when no paced driver is attached (no campaign
            bound, or a ``driver_factory`` was never wired).
        """
        if self.driver is None:
            return json.dumps(
                {
                    "ok": False,
                    "error": "advance_tick: no paced driver attached — no live campaign bound",
                }
            )
        result = self.driver.advance_once()
        self._accumulate_chronicle(result.chronicle)
        return json.dumps({"ok": True, "outcome": self._tick_outcome(result)})

    def run_until_paused(self) -> str:
        """Auto-advance until an autopause/lock/limit, in one blocking call (Task 21).

        Delegates to
        :meth:`~babylon.tui.app.PacedDriverHandle.run_until_paused` — the
        SAME blocking call Textual's own ``r`` binding wraps in a worker
        (:meth:`~babylon.tui.app.ArchiveApp.action_run_until_paused`). This
        seam has no incremental FFI callback to report through, so the
        whole batch resolves before this method returns at all — the
        Textual ground truth this contract deliberately preserves (no
        streaming, no spinner).

        :returns: ``json.dumps({"ok": True, "outcomes": [...]})`` — one
            outcome object (:meth:`_tick_outcome`'s shape) per resolved
            tick, in order — or a loud refusal envelope when no paced
            driver is attached. As with :meth:`advance_tick`, a
            :class:`~babylon.game.pacing.PacingError` escaping past Rust's
            own pre-check is a bug and is never caught.
        """
        if self.driver is None:
            return json.dumps(
                {
                    "ok": False,
                    "error": "run_until_paused: no paced driver attached — no live campaign bound",
                }
            )
        outcomes: list[dict[str, object]] = []
        for result in self.driver.run_until_paused():
            self._accumulate_chronicle(result.chronicle)
            outcomes.append(self._tick_outcome(result))
        return json.dumps({"ok": True, "outcomes": outcomes})

    def acknowledge_pause(self) -> str:
        """Clear a pending autopause, permitting the next advance (Task 21).

        Rust pre-checks ``awaiting_ack`` (via :meth:`pacing_state_json`)
        before ever calling this method, mirroring
        :meth:`~babylon.tui.app.ArchiveApp.action_acknowledge_pause`'s own
        pre-check. Delegates to
        :meth:`~babylon.tui.app.PacedDriverHandle.acknowledge_pause` with no
        catch around it — the same "pre-check pattern, NOT exception
        translation" as :meth:`advance_tick`: a
        :class:`~babylon.game.pacing.PacingError` that still escapes here is
        a bug, never a player-reachable refusal.

        :returns: ``json.dumps({"ok": True})`` on success, or a loud refusal
            envelope when no paced driver is attached.
        """
        if self.driver is None:
            return json.dumps({"ok": False, "error": "acknowledge_pause: no paced driver attached"})
        self.driver.acknowledge_pause()
        return json.dumps({"ok": True})

    def chronicle_rail_json(self) -> str:
        """The render-ready chronicle rail: pre-computed salience, Rust only renders (Task 22).

        Runs the EXACT Textual repaint pipeline
        (:meth:`~babylon.tui.app.ArchiveApp._populate_chronicle_options`):
        :func:`~babylon.tui.chronicle_salience.dedupe_consecutive` of
        :func:`~babylon.tui.chronicle_salience.apply_volume_floors` over the
        host's own accumulated :attr:`_chronicle_history`, then
        :func:`~babylon.tui.chronicle_salience.compute_autopause_state` over
        that same salient list, then
        :func:`~babylon.tui.chronicle.chronicle_stream` (capped at
        :data:`~babylon.tui.chronicle.CHRONICLE_ROW_CEILING`) to regroup into
        dated bulletins.

        Rows are hand-built straight from the bulletins (NOT
        :func:`~babylon.tui.chronicle.chronicle_rows`, which returns
        :class:`~rich.text.Text` — the wrong shape to cross the FFI) via
        :meth:`_bulletin_rows`: a bulletin with events contributes its own
        non-navigable ``"header"`` row (``"T{tick:04d}"``) followed by one
        ``"event"`` row per event (:func:`~babylon.tui.chronicle.
        resolve_navigable_subject` for ``subject``,
        :func:`~babylon.models.event_severity.resolve_severity` for
        ``severity``, :func:`~babylon.tui.chronicle.resolve_actor` for
        ``actor``, the bare ``event.summary`` for ``text`` — the actor
        prefix stays OUT of ``text``, unlike
        :func:`~babylon.tui.chronicle._event_line`'s rendered form); a quiet
        bulletin (no events) contributes its own single ``"quiet"`` row
        instead — never both, mirroring
        :func:`~babylon.tui.chronicle.chronicle_rows`'s own per-bulletin
        dispatch.

        :returns: ``json.dumps({"autopause_line": str | None, "rows": [...]})``.
            ``autopause_line`` is
            :func:`~babylon.tui.chronicle_salience.render_autopause_indicator`'s
            plain text (``Text.plain``), or ``None`` when inactive — an
            absence, never a dimmed row (Constitution III.11). ``rows`` is
            ``[]`` for both an unbound host and a bound one with a
            genuinely empty history — Rust renders its own honest-absence
            line for either case; this method never fabricates a
            placeholder row.
        """
        salient = dedupe_consecutive(apply_volume_floors(self._chronicle_history))
        indicator = render_autopause_indicator(compute_autopause_state(salient))
        autopause_line = indicator.plain if indicator is not None else None
        rows: list[dict[str, object]] = []
        for bulletin in chronicle_stream(salient, limit=CHRONICLE_ROW_CEILING):
            rows.extend(self._bulletin_rows(bulletin))
        return json.dumps({"autopause_line": autopause_line, "rows": rows})

    @staticmethod
    def _bulletin_rows(bulletin: TickBulletin) -> list[dict[str, object]]:
        """One :class:`~babylon.tui.chronicle.TickBulletin`'s own contract rows.

        Split out of :meth:`chronicle_rail_json` so the per-bulletin
        header/event dispatch is directly unit-testable against a
        hand-built :class:`~babylon.tui.chronicle.TickBulletin`.

        There is deliberately NO ``"quiet"`` row kind:
        :func:`~babylon.tui.chronicle.chronicle_stream` never emits an
        empty bulletin ("only ticks actually present in ``events`` produce
        a bulletin" — its own contract), so a quiet branch here would be
        dead code behind a hand-built test shape — the exact green-test-
        over-dead-feature class the M1 verify panel caught. An empty RAIL
        (no rows at all) is the honest-absence state and renders
        client-side.

        :param bulletin: one dated bulletin, as produced by
            :func:`~babylon.tui.chronicle.chronicle_stream` — always
            carries at least one event.
        :returns: ``[header_row, *event_rows]``.
        """
        rows: list[dict[str, object]] = [
            {
                "subject": None,
                "kind": "header",
                "tick": bulletin.tick,
                "severity": None,
                "actor": None,
                "text": f"T{bulletin.tick:04d}",
            }
        ]
        for event in bulletin.events:
            rows.append(
                {
                    "subject": resolve_navigable_subject(event),
                    "kind": "event",
                    "tick": bulletin.tick,
                    "severity": resolve_severity(event.event_type).tier,
                    "actor": resolve_actor(event),
                    "text": event.summary,
                }
            )
        return rows

    def verb_plate_view_json(self) -> str:
        """The bound campaign's live verb plate, as JSON (Task 23).

        Thin passthrough to
        :meth:`~babylon.tui.app.CampaignHandle.verb_plate_view` — the same
        live, compute-fresh-every-call projection
        :meth:`~babylon.tui.app.ArchiveApp._refresh_action_bar` already
        renders.

        :returns: :meth:`~pydantic.BaseModel.model_dump_json` of the
            resolved :class:`~babylon.projection.verbs.view_models.VerbPlateView`,
            or the literal ``"null"`` when no session is bound or the
            campaign's graph carries no player-org pointer — never a
            fabricated plate (Constitution III.11).
        """
        if self.session is None:
            return "null"
        view: VerbPlateView | None = self.session.verb_plate_view()
        if view is None:
            return "null"
        return view.model_dump_json()

    def topology_json(self, args_json: str) -> str:
        """The bound campaign's live topology surface, as JSON (Task 30, contract §1).

        Thin passthrough to
        :meth:`~babylon.tui.app.CampaignHandle.topology_view` (
        :meth:`~babylon.game.session.GameSession.topology_view` in
        production) — every per-kind envelope is already a hand-built,
        JSON-serializable ``dict`` (the contract's own "no shared
        discriminated union" ruling), so this method only parses
        ``args_json`` and re-encodes whatever it gets back; it never
        inspects or reshapes the envelope itself.

        :param args_json: ``{"kind": "paoh"|"egotree"|"incidence"|
            "adjacency", "focus": str | None}`` (field order pinned by the
            contract for Rust's own construction; ``json.loads`` here reads
            it as a plain object, so parse-side key order does not matter).
        :returns: ``json.dumps`` of the resolved kind's envelope, or the
            literal ``"null"`` when no session is bound, OR (``egotree``
            only) ``focus`` is ``None``/names no resolvable root/resolves to
            zero bipartite edges — never a fabricated tree, never a
            propagated error for a stale post-tick focus (Constitution
            III.11).
        :raises ValueError: ``args_json`` is malformed, or ``kind`` names
            none of the four RULED kinds — a caller-protocol error, never
            absence.
        """
        args = json.loads(args_json)
        if self.session is None:
            return "null"
        envelope = self.session.topology_view(args["kind"], args.get("focus"))
        if envelope is None:
            return "null"
        return json.dumps(envelope)

    def field_state_json(self) -> str:
        """The bound campaign's live field-state dossier, as JSON (Task 30, contract §2).

        Thin passthrough to
        :meth:`~babylon.tui.app.CampaignHandle.field_state_view` (
        :meth:`~babylon.game.session.GameSession.field_state_view` in
        production, which reads :func:`~babylon.projection.field_state.
        project_field_state` DIRECTLY off the live graph — never a
        ``WorldState.from_graph`` round trip).

        :returns: :meth:`~pydantic.BaseModel.model_dump_json` of the
            resolved :class:`~babylon.projection.view_models.FieldStateView`,
            or the literal ``"null"`` when no session is bound — never a
            fabricated dossier (Constitution III.11).
        """
        if self.session is None:
            return "null"
        field_view: FieldStateView | None = self.session.field_state_view()
        if field_view is None:
            return "null"
        return field_view.model_dump_json()

    def render_config_json(self) -> str:
        """The recorded ``[render]`` verdict, as one JSON object (Task 35, §7).

        The client reads this ONCE at boot and never re-probes (ADR097 D4:
        ``babylon doctor`` probes; runtime honors the record). ``null`` cell
        dimensions and protocol are honest absence — the Rust side treats
        anything short of ``kitty`` + both cell dimensions as the glyph
        floor, with the degradation declared on the pane (never silent).

        :returns: ``{"tier", "palette", "pixel_protocol", "cell_width",
            "cell_height", "in_tmux"}`` from the injected
            :class:`~babylon.render.config.RenderConfig` (glyph-floor
            defaults when the composition root had no recorded probe).
        """
        cfg = self._render_config
        return json.dumps(
            {
                "tier": cfg.tier.value,
                "palette": cfg.palette.value,
                "pixel_protocol": cfg.pixel_protocol,
                "cell_width": cfg.cell_width,
                "cell_height": cfg.cell_height,
                "in_tmux": cfg.in_tmux,
            }
        )

    def issue_verb(self, args_json: str) -> str:
        """Queue one Article V verb through the real write path (Task 23).

        M3 defect fix: records ``verb`` into BOTH :attr:`verb_log` and
        :attr:`_session_verb_log` (R5 fix) as close to METHOD ENTRY as
        ``args_json`` can be parsed — before the session-bound check and
        before the try/except refusal below — dispatch-proof,
        outcome-independent (mirrors
        :meth:`~babylon.tui.app.ArchiveApp.action_issue_verb`'s own
        ordering: contract §1, "records the verb string on METHOD ENTRY").

        :param args_json: ``{"verb": str, "target_id": str | None,
            "target_community": str | None}`` — Rust has already derived an
            honest ``target_id`` exactly like
            :func:`~babylon.tui.app._honest_target_id` (never invented; see
            the contract's own note) before calling this method, so this
            host method threads whatever it receives straight through with
            no second-guessing.
        :returns: ``json.dumps({"ok": True, "turn_id": int})`` on success, or
            a refusal envelope when no session is bound OR
            :meth:`~babylon.tui.app.CampaignHandle.issue_verb` itself raises
            one of the three player-reachable refusal types
            (``RuntimeError``/``ValueError``/``KeyError`` — mirrors
            :meth:`~babylon.tui.app.ArchiveApp.action_issue_verb`'s own
            catch list exactly); any OTHER exception type propagates and
            panics loudly (Constitution III.11 — a system-level failure,
            never laundered into a fabricated refusal).
        """
        args = json.loads(args_json)
        verb = args["verb"]
        self.verb_log.add(verb)
        self._session_verb_log.add(verb)
        if self.session is None:
            return json.dumps(
                {"ok": False, "error": "issue_verb: no live campaign attached — nothing to act on"}
            )
        target_id = args.get("target_id")
        target_community = args.get("target_community")
        try:
            turn_id = self.session.issue_verb(
                verb, target_id=target_id, target_community=target_community
            )
        except (RuntimeError, ValueError, KeyError) as exc:
            return json.dumps({"ok": False, "error": str(exc)})
        return json.dumps({"ok": True, "turn_id": turn_id})

    def endgame_status_json(self) -> str:
        """The bound campaign's live endgame-progress status, as JSON (Task 24).

        :returns: the literal ``"null"`` ONLY when no session is bound (the
            lobby) — tick 0 of a bound campaign is a real all-zero-axes
            payload, never absence. Otherwise
            :meth:`~pydantic.BaseModel.model_dump_json` of the resolved
            :class:`~babylon.projection.endgame.EndgameStatus`, or
            ``"null"`` when this composition root's own
            :meth:`~babylon.tui.app.CampaignHandle.endgame_status` chose not
            to wire a live projection (a test double — never true for a real
            :class:`~babylon.game.session.GameSession`).
        """
        if self.session is None:
            return "null"
        status: EndgameStatus | None = self.session.endgame_status()
        if status is None:
            return "null"
        return status.model_dump_json()

    def pin_watchlist(self, args_json: str) -> str:
        """Pin or unpin one subject, persisting through the M1 watchlist store (Task 25).

        :param args_json: ``{"subject": str, "pinned": bool}``.
        :returns: ``json.dumps({"ok": True, "pinned": bool})`` on success —
            FIFO pin order, idempotent both ways, persisted via the SAME
            :func:`~babylon.tui.watchlist.load_watchlist`/
            :func:`~babylon.tui.watchlist.save_watchlist` path
            :meth:`watchlist_json` already reads. Also write-throughs
            :attr:`_pinned_subjects` (R13a fix) on success, so
            :meth:`_tutorial_is_pinned`'s next call sees this pin/unpin
            without a second store hit. A refusal envelope when no
            session/watchlist store is bound, or when
            :meth:`~babylon.tui.watchlist.WatchlistState.pin`'s capacity
            :class:`ValueError` fires (the ONE player-reachable refusal
            here, mirroring
            :meth:`~babylon.tui.app.ArchiveApp.action_toggle_pin`'s own
            catch) — never a fabricated silent no-op (Constitution III.11).
        """
        if self.session is None or self._watchlist_persistence is None:
            return json.dumps(
                {"ok": False, "error": "pin_watchlist: no live campaign/watchlist store attached"}
            )
        args = json.loads(args_json)
        subject = args["subject"]
        pinned = bool(args["pinned"])
        session_id = str(self.session.session_id)
        try:
            # Hydration sits INSIDE the catch: a persisted list drifted past
            # today's capacity raises the same player-reachable ValueError
            # class as an over-capacity pin, and neither may crash the
            # client (verify-panel note).
            state = load_watchlist(self._watchlist_persistence, session_id)
            state = state.pin(subject) if pinned else state.unpin(subject)
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)})
        save_watchlist(self._watchlist_persistence, session_id, state)
        self._pinned_subjects = set(state.pinned_ids)
        return json.dumps({"ok": True, "pinned": pinned})

    def nav_state_json(self) -> str:
        """The bound campaign's persisted nav state, as JSON (Task 25).

        Campaign-scoped (keyed by the bound session's own ``session_id``) —
        pulled fresh after :meth:`load_campaign`, never through the
        pre-bind ``config_json`` (the contract's own RECORDED DEVIATION:
        nav state is campaign-scoped, and ``config_json`` is built before a
        campaign is even chosen — ``play.py:449-458``). Only ENTRIES
        persist: cursor/capacity are reconstructed on restore, mirroring
        :meth:`~babylon.tui.nav.NavShell.restore`/
        :meth:`~babylon.tui.nav.JumplistState.restore`.

        :returns: ``json.dumps({"jumplist": [...], "breadcrumbs": [...]})``
            — both ``[]`` when no session/nav store is bound, or the store
            honestly has nothing recorded yet.
        """
        if self.session is None or self._nav_persistence is None:
            return json.dumps({"jumplist": [], "breadcrumbs": []})
        session_id = self.session.session_id
        return json.dumps(
            {
                "jumplist": list(self._nav_persistence.load_jumplist(session_id)),
                "breadcrumbs": list(self._nav_persistence.load_breadcrumbs(session_id)),
            }
        )

    def save_nav_state(self, nav_json: str) -> str:
        """Persist nav state — same shape as :meth:`nav_state_json` (Task 25).

        Called by the Rust shell on leaving the campaign (Back to lobby)
        and on quit. Textual never wired nav persistence in production at
        all (the contract's own RECORDED DEVIATION — ``app.py:1185-1187``
        boots a throwaway ``uuid4`` + ``InMemoryNavPersistence``), so this
        is fresh wiring on both sides, not a port.

        :param nav_json: ``{"jumplist": [...], "breadcrumbs": [...]}``.
        :returns: ``json.dumps({"ok": True})`` on success, or a refusal
            envelope when no session/nav store is bound.
        """
        if self.session is None or self._nav_persistence is None:
            return json.dumps(
                {"ok": False, "error": "save_nav_state: no live campaign/nav store attached"}
            )
        nav = json.loads(nav_json)
        session_id = self.session.session_id
        self._nav_persistence.save_jumplist(session_id, tuple(nav["jumplist"]))
        self._nav_persistence.save_breadcrumbs(session_id, tuple(nav["breadcrumbs"]))
        return json.dumps({"ok": True})

    # --- M3 "Tutorial gate" surface (Task 27; contract: docs/superpowers/
    # specs/2026-07-27-m3-tutorial-contracts.md). ---------------------------

    def _tutorial_is_pinned(self, subject: str) -> bool:
        """The tutorial evaluator's ``is_pinned`` callable (contract §1).

        R13a fix: reads :attr:`_pinned_subjects`, the host-side cache
        :meth:`bind_session` hydrates once (through the SAME
        :func:`~babylon.tui.watchlist.load_watchlist` path
        :meth:`watchlist_json` uses) and :meth:`pin_watchlist` keeps
        write-through — never a fresh store hit per poll, since this
        callable is invoked on every :meth:`tutorial_state_json` call.
        :meth:`watchlist_json` itself is UNCHANGED, still reading
        :attr:`_watchlist_persistence` directly (its own concern).

        :param subject: the vault-relative subject id to check.
        :returns: ``False`` when no session/watchlist store was ever bound
            (mirrors :meth:`watchlist_json`'s own honest-absence default —
            :attr:`_pinned_subjects` stays empty in that case), else
            whether ``subject`` currently holds a pin.
        """
        return subject in self._pinned_subjects

    def _tutorial_was_verb_issued(self, verb: str) -> bool:
        """The tutorial evaluator's ``was_verb_issued`` callable (contract
        §0/§1, the M3 ``VerbIssued`` defect fix).

        R5 fix: reads :attr:`_session_verb_log` — this BOUND SESSION's own
        dispatch log, reset by every :meth:`bind_session` — rather than the
        lifetime :attr:`verb_log`. That distinction is deliberate: the
        public :meth:`was_verb_issued` method (the harness's own tier-2
        surface) keeps reading the lifetime log instead, since
        ``new_campaign`` fires strictly before any session is ever bound
        (see :attr:`verb_log`'s own docstring). This evaluator-facing
        method reading the lifetime log instead would let a SECOND
        campaign's tutorial arc see a verb already dispatched by a PRIOR
        campaign as instantly complete — reachable only on the Rust client
        (Textual never returns to the lobby to start a second campaign).

        :param verb: the verb/binding-action name a
            :class:`~babylon.game.tutorial.VerbIssued` step names.
        :returns: dispatch-proof union of :attr:`_session_verb_log` (this
            bound session's own ``issue_verb``/``new_campaign`` dispatch
            log) and the LATEST poll's ``chrome_verbs`` report (the
            client's own cumulative chrome-dispatch log, e.g.
            ``"peek_wikilink"`` — contract §1).
        """
        return verb in self._session_verb_log or verb in self._tutorial_chrome_verbs

    def tutorial_state_json(self, view_state_json: str) -> str:
        """The T6 tutorial overlay's per-poll seam — Rust's own top strip
        (Task 27, contract §1).

        **RECORDED DEVIATION from the plan sketch** (``plan:438`` says
        ``call0``): this is a ``call1`` — the client reports its own
        display state every poll, because the evaluator's
        :class:`~babylon.game.tutorial.OnPage`/:class:`~babylon.game.
        tutorial.PaneShowing` predicates ground on the CLIENT's display
        state (``current_subject``/``current_pane``), which has no
        host-side truth (the host cannot distinguish "read_page for
        display" from "read_page for refresh"). Predicates still evaluate
        Python-side only — the client never reasons about completion
        itself, only reports what it is showing.

        :param view_state_json: ``{"subject": str | None, "pane": str,
            "chrome_verbs": [str, ...]}`` (field order as sent by Rust) —
            the client's CURRENT display state plus its cumulative
            chrome-dispatch log (Rust appends ``"peek_wikilink"`` when ``K``
            is pressed while the play chrome exists; host-side material
            verbs are reported through :attr:`verb_log` instead, never by
            the client).
        :raises ValueError: ``view_state_json`` is not the expected shape —
            a CLIENT bug, never a player-reachable state (Constitution
            III.11); chained from the underlying ``json.JSONDecodeError``/
            ``KeyError``/``TypeError``.
        :raises AssertionError: propagated straight from the evaluator
            itself (e.g. an unrecognized completion-predicate kind) — a
            :class:`~babylon.game.tutorial.VerbIssued` step can no longer
            raise here, since :meth:`bind_session` always wires
            :meth:`_tutorial_was_verb_issued` whenever an evaluator exists
            at all (PyHost panics loudly on any OTHER such assertion,
            III.11).
        :returns: the pinned envelope (field order exactly as below).
            ``{"active": false}`` when no session is bound, no
            ``tutorial_progress_factory``/``tutorial_steps`` pair was
            wired, or the factory itself declined for this campaign (its
            own new-vs-resumed gating). Otherwise an ACTIVE envelope:
            ``heading``/``body`` are the EXACT Textual overlay strings
            (:meth:`~babylon.tui.tutorial_overlay.TutorialOverlay.
            _render_current_step`'s own ``f"Step {i+1}/{N}:
            {step.scenario_name}"``/``step.overlay_text``) plus
            ``patches`` (the Rust-only Director-content line, contract
            §0/§8) — the host renders them, Rust never reassembles prose
            (the U1 no-duplication contract); or the FINISHED envelope,
            its two strings verbatim ("Opening arc complete." / "Press
            Escape to dismiss this tutorial."), ``patches: null``.

            Advance loop = :meth:`~babylon.tui.tutorial_overlay.
            TutorialOverlay.check_progress` verbatim: bounded multi-advance
            through consecutive TRUE predicates, strictly ordered, per
            poll — every step completed THIS poll is appended to
            :attr:`completion_log` as ``(step_id, poll_ordinal)``.
        """
        if self._tutorial_evaluator is None or self._tutorial_steps is None:
            return json.dumps({"active": False})
        try:
            payload = json.loads(view_state_json)
            subject = payload["subject"]
            pane = payload["pane"]
            chrome_verbs = payload["chrome_verbs"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            msg = f"tutorial_state_json: malformed view_state_json {view_state_json!r} — {exc}"
            raise ValueError(msg) from exc
        self._tutorial_current_subject = subject
        self._tutorial_current_pane = pane
        self._tutorial_chrome_verbs = frozenset(chrome_verbs)
        steps = self._tutorial_steps
        evaluator = self._tutorial_evaluator
        total = len(steps)
        for _ in range(total):  # loop bound: _tutorial_index < total each time (Power-of-10 rule 2)
            if self._tutorial_index >= total or not evaluator.is_step_complete(
                self._tutorial_index
            ):
                break
            completed_id = steps[self._tutorial_index].id
            self.completion_log.append((completed_id, self._tutorial_poll_ordinal))
            self._tutorial_index += 1
        self._tutorial_poll_ordinal += 1
        if self._tutorial_index >= total:
            return json.dumps(
                {
                    "active": True,
                    "finished": True,
                    "step_index": total,
                    "total": total,
                    "step_id": None,
                    "heading": "Opening arc complete.",
                    "patches": None,
                    "body": "Press Escape to dismiss this tutorial.",
                }
            )
        step = steps[self._tutorial_index]
        return json.dumps(
            {
                "active": True,
                "finished": False,
                "step_index": self._tutorial_index,
                "total": total,
                "step_id": step.id,
                "heading": f"Step {self._tutorial_index + 1}/{total}: {step.scenario_name}",
                "patches": step.patches,
                "body": step.overlay_text,
            }
        )
