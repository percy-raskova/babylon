"""`babylon play` — boot a real campaign session through the composition root.

Historically this delegated straight to the bundled two-node demo
(``babylon.__main__``). Since Program v1.0.0's Unit C1 (the campaign
composition root, :mod:`babylon.game.session`) this boots REAL campaigns —
Wayne County (ruling 3: "Wayne stays in lobby") — through the real
30-system engine and a real Postgres runtime.

Unit C2 closes the two gaps C1's docstring used to name here: ``ArchiveApp``
now gets the lobby's own :class:`~babylon.tui.campaign_menu.CampaignMenu`
(over a real :class:`~babylon.persistence.babylon_meta.BabylonMetaStore`)
and a real :data:`~babylon.tui.app.CampaignLoader` — :func:`_load_campaign`
below — so ``babylon play`` now runs the full lobby -> briefing -> campaign
shell flow, with the advance-tick binding (``t``) live in the shell. The
lobby's own ``babylon_meta.campaign_id`` doubles as the engine's
``game_session.id`` (:func:`~babylon.game.session.create_new_campaign`'s
``session_id=`` parameter) — one identity, not a maintained mapping between
two separate ID spaces — and each campaign gets its own vault subdirectory
(``vault/<campaign_id>/``) so concurrent campaigns' baked pages never
collide.

Review fix (same unit): :func:`_load_campaign` also threads the SAME
``BabylonMetaStore`` in as :func:`~babylon.game.session.create_new_campaign`/
:func:`~babylon.game.session.resume_campaign`'s ``progress_store=`` — the
seam that keeps the lobby row's ``Tick N`` live via
:meth:`~babylon.persistence.babylon_meta.BabylonMetaStore.record_progress`,
previously wired to zero production callers.

Review fix (Unit C3): :func:`run` also passes :func:`_driver_factory` in as
``ArchiveApp``'s ``driver_factory=`` — without it ``ArchiveApp.driver``
stayed ``None`` on every real ``babylon play`` boot, so the ``t``/``r``/``a``
bindings never routed through :class:`~babylon.game.pacing.PacedTickDriver`
and the permanent endgame lock it enforces never engaged in the shipped game
(:class:`~babylon.game.pacing.PacedTickDriver` was previously wired to zero
production callers). :func:`_driver_factory` itself is a thin adapter, not
:func:`~babylon.game.pacing.paced_driver_for_session` directly — see its own
docstring for why one is needed.

T5 Unit U1 (the narrator lane) adds the ``--narrator/--no-narrator`` flag on
:func:`play`, threaded through :func:`run` into :func:`_load_campaign`: ON
(the default — the provider chain shipped by :mod:`babylon.intelligence.
providers` ends in a mute lane, so ON is always legal, R4) constructs a real
:class:`~babylon.projection.vault.narrator_cache.NarratorSideProcess` over
this campaign's own vault root and threads it in as
:func:`~babylon.game.session.create_new_campaign`/:func:`~babylon.game.
session.resume_campaign`'s ``narrator=`` (previously wired to zero
production callers); OFF passes ``narrator=None``, so
:meth:`~babylon.game.session.GameSession.advance_tick` never calls
``schedule()`` at all — the exact pre-Unit-U1 byte-identical path.

T6 Unit U4 (the guided opening-arc overlay) adds the ``--tutorial/--no-
tutorial`` flag on :func:`play`, threaded through :func:`run` into
:func:`_tutorial_progress_factory`. Deliberately TRI-STATE (``bool | None``,
default ``None``) rather than the narrator flag's plain bool — the ruling's
own default is "ON for a new campaign, OFF for a resumed one," a decision
that cannot be resolved until a specific campaign is chosen in the lobby,
long after Typer has already parsed the CLI. ``None`` (no flag given) defers
to :func:`_tutorial_progress_factory`'s own first-session heuristic
(``campaign.tick == 0``, an HONEST, DOCUMENTED approximation of "was this
campaign just minted" — see that function's own docstring for the precise
signal it would need instead, and why threading it here would ripple into
``LobbyScreen``'s dismiss contract); ``True``/``False`` (an explicit flag)
always overrides the heuristic outright, for either a fresh or a resumed
campaign.

Program 24 P6 (the right rail) threads the SAME ``catalog``
(:class:`~babylon.persistence.babylon_meta.BabylonMetaStore`) in a second
time, as ``ArchiveApp``'s ``watchlist_persistence=`` — no separate store, no
separate schema: ``BabylonMetaStore.load``/``.save`` structurally satisfy
:data:`~babylon.tui.watchlist.WatchlistPersistence` (the same WO-37 trick
already used for the campaign catalog and, one layer up, for
:class:`~babylon.tui.nav.NavShell`'s own persistence seam), and its DDL is
the same ``babylon_meta`` schema ``catalog.ensure_schema()`` already applies
above — a pinned subject now survives a quit/resume of the same campaign.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

import typer

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from babylon.config.defines import GameDefines
    from babylon.game.pacing import PacedTickDriver
    from babylon.game.session import GameSession
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.babylon_meta import BabylonMetaStore
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.tui.app import CampaignHandle, PacedDriverHandle
    from babylon.tui.tutorial_overlay import TutorialProgress


def play_demo() -> None:
    """Run the legacy bundled two-node demo simulation (pre-Archive).

    Preserved for anyone still scripting against the old behavior directly;
    no longer wired to any CLI entry point.
    """
    from babylon.__main__ import main as run_demo

    run_demo()


def _vault_root() -> Path:
    """The on-disk vault root (design canon: ``~/.local/share/babylon/vault``),
    overridable for tests/dev via ``BABYLON_VAULT_ROOT``."""
    override = os.environ.get("BABYLON_VAULT_ROOT")
    if override:
        return Path(override)
    return Path.home() / ".local" / "share" / "babylon" / "vault"


def _campaign_vault_root(campaign_id: UUID) -> Path:
    """This campaign's own vault subdirectory (``VaultMaterializer``'s
    docstring-documented convention: ``vault/<slug>/``, keyed here on the
    campaign's own UUID rather than a mutable display name — the same
    stable-ID discipline every other vault path follows), so two campaigns'
    baked pages never collide.

    :param campaign_id: the campaign's identity (== ``game_session.id``).
    """
    return _vault_root() / str(campaign_id)


def _defines_hash(defines: GameDefines) -> str:
    """A deterministic fingerprint of one ``GameDefines`` snapshot.

    Stamped on every campaign the lobby mints (``CampaignCatalog.
    create_campaign``'s ``defines_hash``) — sha256 of the canonically
    (key-sorted) serialized coefficients, the same "hash a canonical
    string" shape :func:`babylon.game.session._replay_identity_hash`
    already uses, not a second ad hoc scheme.

    :param defines: the coefficients to fingerprint.
    :returns: a hex digest.
    """
    canonical = json.dumps(defines.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _bake_briefing(materializer: VaultMaterializer, session: GameSession) -> None:
    """Bake this campaign's Scenario Briefing dossier (WO-35, Unit C2 wiring).

    ``VaultMaterializer.bake_briefing`` shipped fully tested with zero
    production callers; this is that wiring. Baked once per boot/resume
    (not per tick): the briefing carries no live tick-progress axes yet
    (a stated non-goal — no ``EndgameDetector`` snapshot is threaded
    through ``GameSession`` today), so re-baking every tick would write the
    same content every time.

    :param materializer: this campaign's vault materializer.
    :param session: the just-booted/resumed campaign.
    """
    from babylon.projection.briefing import project_briefing

    view = project_briefing(session.session_id, tick=session.tick, defines=session.services.defines)
    materializer.bake_briefing(view, tick=session.tick)


def _load_campaign(
    runtime: PostgresRuntime,
    catalog: BabylonMetaStore,
    campaign_id: UUID,
    *,
    narrator_enabled: bool = True,
) -> GameSession:
    """The lobby's ``CampaignLoader`` seam, fulfilled for real (Unit C2).

    Boots a NEW ``game_session`` row the first time this campaign's id is
    chosen (``runtime.get_session`` finds nothing yet), else resumes the
    existing one from its last committed tick — the ``babylon_meta.
    campaign_id`` the lobby chose IS the ``game_session.id`` throughout, by
    construction.

    :param runtime: the open Postgres runtime.
    :param catalog: the lobby's own ``babylon_meta`` catalog store, threaded
        through as ``progress_store=`` so ``create_new_campaign``/
        ``resume_campaign`` keep this campaign's lobby row live (review fix:
        the catalog was previously written only at campaign creation and
        never again, so a resumed campaign's lobby row stayed stuck at
        ``Tick 0``).
    :param campaign_id: the lobby's chosen campaign UUID.
    :param narrator_enabled: T5 Unit U1's ``--narrator/--no-narrator`` flag
        (see :func:`play`); ``True`` (the default) constructs a real
        :class:`~babylon.projection.vault.narrator_cache.NarratorSideProcess`
        over this campaign's own vault root, threaded through as
        ``narrator=``; ``False`` threads ``narrator=None`` so
        :meth:`~babylon.game.session.GameSession.advance_tick` never
        schedules narration at all.
    :returns: the live, booted/resumed :class:`~babylon.game.session.GameSession`
        (structurally satisfies ``babylon.tui.app.CampaignHandle``, now
        including its Unit U1 ``known_subjects`` seam via the same
        ``vault_root`` :func:`~babylon.game.session.vault_known_subjects`
        reads).
    """
    from babylon.engine.headless_runner.scopes import DETROIT_TRI_COUNTY_FIPS
    from babylon.engine.scenarios import WayneCountyScenario
    from babylon.game.session import (
        create_new_campaign,
        resume_campaign,
        vault_known_subjects,
        vault_page_source,
    )
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.projection.vault.narrator_cache import NarratorCache, NarratorSideProcess
    from babylon.projection.vault.tick_baker import ArchiveTickBaker

    vault_root = _campaign_vault_root(campaign_id)
    materializer = VaultMaterializer(vault_root)
    baker = ArchiveTickBaker(materializer, county_fips=tuple(DETROIT_TRI_COUNTY_FIPS))
    pages = vault_page_source(vault_root)
    known_subjects = vault_known_subjects(vault_root)
    narrator = NarratorSideProcess(NarratorCache(vault_root)) if narrator_enabled else None

    session = (
        resume_campaign(
            runtime,
            campaign_id,
            tick_commit_observer=baker,
            pages=pages,
            known_subjects=known_subjects,
            progress_store=catalog,
            narrator=narrator,
        )
        if runtime.get_session(campaign_id) is not None
        else create_new_campaign(
            runtime,
            scenario=WayneCountyScenario(),
            session_id=campaign_id,
            tick_commit_observer=baker,
            pages=pages,
            known_subjects=known_subjects,
            progress_store=catalog,
            narrator=narrator,
        )
    )
    _bake_briefing(materializer, session)
    return session


def _driver_factory(campaign: CampaignHandle) -> PacedTickDriver:
    """The ``babylon.tui.app.DriverFactory`` seam, fulfilled for real (Unit C3).

    A thin adapter over :func:`~babylon.game.pacing.paced_driver_for_session`,
    not that function passed straight through: ``paced_driver_for_session``
    needs a full :class:`~babylon.game.session.GameSession` (specifically
    ``session.services.defines``, for its default
    :class:`~babylon.engine.observers.endgame_detector.EndgameDetector`) —
    strictly more than :class:`~babylon.tui.app.CampaignHandle` structurally
    promises, so mypy correctly refuses to accept
    ``paced_driver_for_session`` itself where a ``DriverFactory`` is expected.
    The cast below is sound ONLY because this composition root is the sole
    caller of ``driver_factory=`` and its own ``campaign_loader=``
    (:func:`_load_campaign`) always resolves to a real ``GameSession`` —
    never any other ``CampaignHandle`` — exactly the invariant
    :data:`~babylon.tui.app.DriverFactory`'s own docstring names.

    :param campaign: the just-booted campaign — always a real
        ``GameSession`` in this composition root.
    :returns: the campaign's paced tick driver.
    """
    from babylon.game.pacing import paced_driver_for_session

    return paced_driver_for_session(cast("GameSession", campaign))


def _tutorial_steps() -> tuple[Any, ...]:
    """The guided opening-arc's step slice the campaign shell can teach.

    Skips the authored arc's first TWO beats (lobby mint + briefing begin):
    the overlay only ever mounts once the campaign shell itself is visible
    (:meth:`~babylon.tui.app.ArchiveApp._on_briefing_dismissed`), by which
    point both are already necessarily true (reaching the shell requires
    having done them), and their own completion (``VerbIssued``) is not
    observable from inside the shell anyway (see
    :class:`~babylon.game.tutorial_runtime.TutorialRuntimeProgress`'s own
    docstring). Computed ONCE and reused as BOTH ``ArchiveApp``'s
    ``tutorial_steps=`` and the same steps :func:`_tutorial_progress_factory`
    builds its evaluator against — a single source of the slice keeps the
    overlay's rendering list and its evaluator's index space identical by
    construction (see :data:`~babylon.tui.app.TutorialProgressFactory`'s own
    docstring on why that alignment matters).

    :returns: the sliced step sequence, typed loosely (``Any``) in this
        function's own signature to avoid importing ``babylon.game.tutorial``
        (and transitively ``babylon.engine``) at module scope — this
        composition root already imports it lazily elsewhere in this file for
        the same reason.
    """
    from babylon.game.tutorial import WAYNE_OPENING_ARC

    return WAYNE_OPENING_ARC.steps[2:]


def _tutorial_progress_factory(
    tutorial_enabled: bool | None, steps: tuple[Any, ...]
) -> Callable[
    [
        CampaignHandle,
        PacedDriverHandle | None,
        Callable[[], str | None],
        Callable[[], str | None],
        Callable[[str], bool],
    ],
    TutorialProgress | None,
]:
    """Build ``ArchiveApp``'s ``tutorial_progress_factory=`` seam (Unit U4;
    extended by Program 24 P8, "the tutorial learns the shell").

    Returns a closure fulfilling :data:`~babylon.tui.app.TutorialProgressFactory`:
    given the just-booted campaign, its paced driver (or ``None``), a
    nav-subject query, a current-pane query, and a watchlist-pin query
    (the last two, P8), decide whether the T6 opening-arc overlay should show
    for THIS campaign, and if so build its
    :class:`~babylon.tui.tutorial_overlay.TutorialProgress` evaluator.

    :param tutorial_enabled: the resolved ``--tutorial``/``--no-tutorial``
        tri-state flag (see :func:`play`); ``True``/``False`` always wins;
        ``None`` (no flag given) falls back to ``campaign.tick == 0`` — an
        HONEST, DOCUMENTED APPROXIMATION of "this campaign was just minted,"
        not a precise new-vs-resumed signal. The precise signal
        (``runtime.get_session(campaign_id) is None``, computed inside
        :func:`_load_campaign`) does not survive past that function's own
        return (``ArchiveApp`` only ever sees the resulting ``GameSession``,
        never the fact that produced it), and threading it through would mean
        either widening :class:`~babylon.tui.app.CampaignHandle` with a new
        REQUIRED member (breaking every existing fake in
        ``tests/unit/tui/test_app_lobby_flow.py``/``test_app_pacing_driver.
        py``) or changing :class:`~babylon.tui.campaign_menu.LobbyScreen`'s
        own ``dismiss`` contract (rippling into ``test_campaign_menu.py`` and
        ``test_tutorial_pilot.py`` too) — both a far larger blast radius than
        this ruling's own "first-session semantics" asks for. Wayne's own
        material state means a genuinely-resumed campaign realistically sits
        at tick >= 1 (it autopauses every tick from tick 1 onward — see
        ``tests/unit/tui/test_tutorial_pilot.py``'s own HONEST GAP docstring),
        so the one false-positive this approximation admits (a resumed
        campaign that was minted but never advanced past tick 0 in its prior
        session) is narrow and self-correcting: the player sees the tutorial
        once more, never a crash or a wrong answer.
    :param steps: the exact step sequence to build the evaluator against —
        :func:`_tutorial_steps`'s own return, so it stays index-aligned with
        whatever ``ArchiveApp`` was given as ``tutorial_steps=``.
    :returns: the ``tutorial_progress_factory`` closure.
    """

    def _factory(
        campaign: CampaignHandle,
        driver: PacedDriverHandle | None,
        current_subject: Callable[[], str | None],
        current_pane: Callable[[], str | None],
        is_pinned: Callable[[str], bool],
    ) -> TutorialProgress | None:
        from babylon.game.tutorial_runtime import TutorialRuntimeProgress

        show = tutorial_enabled if tutorial_enabled is not None else campaign.tick == 0
        if not show:
            return None
        return TutorialRuntimeProgress(
            steps=steps,
            campaign=campaign,
            driver=driver,
            current_subject=current_subject,
            current_pane=current_pane,
            is_pinned=is_pinned,
        )

    return _factory


def run(*, narrator_enabled: bool = True, tutorial_enabled: bool | None = None) -> None:
    """Boot the REAL Archive TUI: campaign lobby -> briefing -> campaign shell.

    Requires a reachable Postgres — see :func:`babylon.game.session.open_runtime`.

    :param narrator_enabled: T5 Unit U1's ``--narrator/--no-narrator`` flag
        (see :func:`play`), threaded straight into every
        :func:`_load_campaign` call this boot makes.
    :param tutorial_enabled: T6 Unit U4's ``--tutorial/--no-tutorial``
        tri-state flag (see :func:`play`), threaded into
        :func:`_tutorial_progress_factory` (see its own docstring for the
        ``None`` default's first-session heuristic).
    """
    from functools import partial

    import babylon
    from babylon.config.defines import GameDefines
    from babylon.game.session import ensure_schema, open_runtime
    from babylon.persistence.babylon_meta import BabylonMetaStore
    from babylon.tui.app import ArchiveApp
    from babylon.tui.campaign_menu import CampaignMenu

    runtime = open_runtime()
    ensure_schema(runtime)

    catalog = BabylonMetaStore(runtime.pool)
    catalog.ensure_schema()
    menu = CampaignMenu(
        catalog,
        engine_version=babylon.__version__,
        defines_hash=_defines_hash(GameDefines.load_default()),
    )

    steps = _tutorial_steps()
    app = ArchiveApp(
        campaign_menu=menu,
        campaign_loader=partial(
            _load_campaign, runtime, catalog, narrator_enabled=narrator_enabled
        ),
        driver_factory=_driver_factory,
        tutorial_steps=steps,
        tutorial_progress_factory=_tutorial_progress_factory(tutorial_enabled, steps),
        watchlist_persistence=catalog,
    )
    app.run()


def play(
    narrator: bool = typer.Option(
        True,
        "--narrator/--no-narrator",
        help=(
            "Enable the async narrator side-process, which writes prose into "
            "the vault's narrative/ channel (T5 Unit U1). ON by default — the "
            "shipped provider chain ends in a mute lane, so ON is always "
            "legal (Constitution R4)."
        ),
    ),
    tutorial: bool | None = typer.Option(
        None,
        "--tutorial/--no-tutorial",
        help=(
            "Show the guided opening-arc overlay (T6 Unit U4). Unset (the "
            "default) shows it for a freshly-minted campaign only, never a "
            "resumed one (first-session semantics); an explicit flag always "
            "wins either way."
        ),
    ),
) -> None:
    """Play Babylon — the real campaign session, via the composition root."""
    run(narrator_enabled=narrator, tutorial_enabled=tutorial)
