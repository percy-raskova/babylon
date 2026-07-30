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

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

import typer

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any

    from babylon.config.defines import GameDefines
    from babylon.game.pacing import PacedTickDriver
    from babylon.game.session import CountyWktSource, GameSession
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.babylon_meta import BabylonMetaStore
    from babylon.projection.narration_envelope import JsonlNarrationSink
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.tui.contract import CampaignHandle, PacedDriverHandle, TutorialProgress


#: Calendar anchor for interactive campaigns' simulated years (P26 U2).
#: Mirrors the headless runner's ``SimulationRunConfig.start_year`` default
#: (``headless_runner/models.py:108``) — a calendar anchor tied to the
#: reference-data window, not a tunable gameplay coefficient (which would
#: belong in ``GameDefines``).
_CAMPAIGN_START_YEAR = 2010

#: Root level for the Rust client's own ``rust-client.log`` sink (Director
#: directive 2026-07-28: "right now in debug mode we want everything" —
#: crossing the FFI as ``AppConfig::log_level``; ``babylon_tui::logging``
#: fails loudly on an unknown value). Infrastructure verbosity, not a
#: gameplay coefficient — deliberately NOT a ``GameDefines`` entry.
_CLIENT_LOG_LEVEL = "debug"

#: Size cap for ``client-capture.log`` (the terminal-takeover raw
#: stdout/stderr capture, PR #318). The capture is an append-mode raw
#: stream — ``logging.handlers`` rotation can't wrap it — so
#: :func:`_rotate_capture` applies the same 10 MB discipline the rotating
#: estates use, with one archived predecessor.
_CAPTURE_LOG_MAX_BYTES = 10 * 1024 * 1024

#: Leontief calculator sessions opened for interactive campaigns
#: (``_build_economics_overrides`` hands ownership to the caller; the
#: headless runner closes its one session in a ``finally`` — the CLI's
#: campaign lives until process exit, so these close atexit).
_LEONTIEF_SESSIONS: list[Any] = []


def _close_leontief_sessions() -> None:
    """atexit hook: close every Leontief session this process opened."""
    while _LEONTIEF_SESSIONS:
        _LEONTIEF_SESSIONS.pop().close()


def _compose_county_wkt() -> CountyWktSource | None:
    """The M5 map's county-geometry seam, composition-root side (Task 37).

    The checked-in SQLite reference DB is the backend
    (:func:`~babylon.persistence.tiger_ingestion.
    fetch_county_geometries_wkt_from_sqlite` — no Postgres ingest needed);
    a missing DB degrades LOUDLY to no provider (the TIGER-probe
    precedent: the map renders geometry absence, creation never crashes).
    """
    import logging

    from babylon.persistence.tiger_ingestion import (
        fetch_county_geometries_wkt_from_sqlite,
    )

    probe = Path("data/sqlite/marxist-data-3NF.sqlite")
    if not probe.exists():
        logging.getLogger(__name__).warning(
            "reference DB absent at %s — the map's county geometry seam is "
            "OFF this session (cells ship wkt: null)",
            probe,
        )
        return None

    def _provider(geoids: frozenset[str]) -> dict[str, str]:
        return fetch_county_geometries_wkt_from_sqlite(geoids, probe)

    return _provider


def _compose_trade(
    runtime: PostgresRuntime,
    campaign_id: UUID,
    *,
    resuming: bool,
    defines: GameDefines,
    event_bus: Any,
) -> tuple[Any, dict[str, Any]]:
    """Build this campaign's trade wiring + economics overrides (P26 U2).

    The interactive twin of the headless runner's boot construction
    (``runner.py:1216,1318-1330``): the SAME reference-DB-backed economics
    overrides (gamma/melt/Leontief/Vol I-III over the Detroit tri-county
    scope) and the SAME spec-101 Φ estate (session initialization,
    external-node bootstrap, county exposure), composed for
    :func:`~babylon.game.session.create_new_campaign` /
    :func:`~babylon.game.session.resume_campaign`.

    LOUD degradation (Constitution III.11, the ``gamma_calculator unwired``
    precedent): when the reference DB is absent, ONE warning names exactly
    what is degraded — never a silent stub — and the campaign boots with
    ``trade=None`` + gamma-only overrides.

    :param runtime: the open Postgres runtime.
    :param campaign_id: the campaign UUID (doubles as the trade session id).
    :param resuming: ``True`` skips the reference bootstrap (done at
        creation); queries only.
    :param defines: this campaign's own ``GameDefines`` (the same object the
        session will run under — the FR-029a alpha invariant is checked
        against it).
    :param event_bus: the bus the Leontief pipeline publishes calibration
        warnings to; the caller assigns the SAME bus onto
        ``services.event_bus`` after the session boots (the runner-twin
        post-``create`` assignment, ``runner.py:1329``).
    :returns: ``(trade, economics_overrides)`` — ``trade`` is a
        :class:`~babylon.game.trade.TradeWiring` or ``None`` when degraded.
    """
    import atexit

    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.engine.headless_runner.scopes import DETROIT_TRI_COUNTY_FIPS
    from babylon.game.trade import TradeDataUnavailableError, build_interactive_trade_wiring
    from babylon.reference.database import NORMALIZED_DB_PATH, get_normalized_session_factory

    db_present = NORMALIZED_DB_PATH.is_file()
    session_factory = get_normalized_session_factory() if db_present else None

    overrides, leontief_session = _build_economics_overrides(
        session_factory=session_factory,
        event_bus=event_bus if db_present else None,
        defines=defines if db_present else None,
        scope_fips=frozenset(DETROIT_TRI_COUNTY_FIPS) if db_present else None,
    )
    if leontief_session is not None:
        if not _LEONTIEF_SESSIONS:
            atexit.register(_close_leontief_sessions)
        _LEONTIEF_SESSIONS.append(leontief_session)

    from babylon.persistence.hex_hydrator import tiger_shapefile_available

    # P26 U5g: tick-0 hex hydration (runner twin, runner.py:1224) populates
    # hex_spatial_map so the Vol II composer below can bind a real
    # hex→county adjunction. data/tiger is a drive symlink — probe first so
    # drive-less machines (CI) degrade loudly instead of crashing creation.
    hydrate_hexes = tiger_shapefile_available()
    if not hydrate_hexes:
        typer.echo(
            "WARNING: TIGER county shapefile unavailable (data/tiger drive "
            "symlink unresolved) — hex hydration skipped; Vol II circulation "
            "stays honestly absent for this campaign.",
            err=True,
        )
    trade = None
    try:
        trade = build_interactive_trade_wiring(
            session_id=campaign_id,
            runtime=runtime,
            defines=defines,
            sqlite_path=NORMALIZED_DB_PATH,
            start_year=_CAMPAIGN_START_YEAR,
            counties=DETROIT_TRI_COUNTY_FIPS,
            bootstrap_reference=not resuming,
            hex_hydration_counties=(frozenset(DETROIT_TRI_COUNTY_FIPS) if hydrate_hexes else None),
        )
    except TradeDataUnavailableError as exc:
        typer.echo(
            "WARNING: interactive trade wiring DEGRADED — no external nodes, "
            f"no imperial-rent Φ distribution, no TRIBUTE inflow data: {exc}",
            err=True,
        )
    if trade is not None:
        # P26 U5g: compose the Vol II circulation sub-stage (ADR162's
        # disclosed inert half). The composer degrades to None LOUDLY on
        # its own (out-of-scope counties / empty adjunction); FileNotFound
        # covers a missing checked-in LODES artifact file specifically.
        from dataclasses import replace as _dc_replace

        from babylon.game.vol2 import build_vol2_circulation_step

        try:
            vol2_step = build_vol2_circulation_step(
                runtime=runtime,
                session_id=campaign_id,
                counties=frozenset(DETROIT_TRI_COUNTY_FIPS),
            )
        except FileNotFoundError as exc:
            vol2_step = None
            typer.echo(
                f"WARNING: Vol II circulation DEGRADED — LODES artifact file missing: {exc}",
                err=True,
            )
        if vol2_step is not None:
            trade = _dc_replace(trade, vol2_step=vol2_step)
    if not db_present:
        typer.echo(
            "WARNING: reference DB absent — economics overrides DEGRADED to "
            "gamma-only (no melt/Leontief/Vol I-III calculators; the "
            "TickDynamics gamma_calculator-unwired precedent, loud by design).",
            err=True,
        )
    return trade, overrides


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
    create_campaign``'s ``defines_hash``) — delegates to
    :func:`babylon.config.defines.canonical_defines_hash`, the one canonical
    implementation (Program 27 spec §7).

    :param defines: the coefficients to fingerprint.
    :returns: a hex digest.
    """
    from babylon.config.defines import canonical_defines_hash

    return canonical_defines_hash(defines)


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
    from babylon.config.defines import GameDefines as _GameDefines
    from babylon.engine.headless_runner.scopes import DETROIT_TRI_COUNTY_FIPS
    from babylon.engine.scenarios import WayneCountyTradeScenario
    from babylon.game.session import (
        create_new_campaign,
        resume_campaign,
        vault_known_subjects,
        vault_page_source,
    )
    from babylon.kernel.event_bus import EventBus

    # ADR176 ruling 32: 1-live-session retention, ENFORCED IN CODE at the
    # one place a second live session would otherwise come into being.
    # Every other session with live runtime rows is exported (fail-closed
    # verified) then purged BEFORE this campaign boots — freeing disk and
    # keeping the partition census at its steady state. A purged campaign
    # keeps its catalog replay identity (rng_seed, ruling 28) and its
    # parquet archive; booting it later finds no game_session row and
    # falls into the create-fresh path below — the v1 rebuild seam
    # (deterministic fast-forward from the seed is the successor story).
    # An ArchiveVerificationError here ABORTS the boot loudly: refusing to
    # play rather than silently growing a second live session.
    from babylon.persistence.retention import (
        check_disk_preflight,
        default_archive_root,
        enforce_single_live_session,
    )
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.projection.vault.narrator_cache import NarratorCache, NarratorSideProcess
    from babylon.projection.vault.tick_baker import ArchiveTickBaker

    # Ruling 32's other half: refuse to boot into a disk that cannot hold a
    # campaign — a player-actionable DiskPreflightError now beats a Postgres
    # ENOSPC PANIC forty hours in. Budget from GameDefines.persistence.
    check_disk_preflight(
        default_archive_root().parent,
        _GameDefines.load_default().persistence.disk_preflight_required_bytes,
    )
    enforce_single_live_session(runtime.pool, keep=campaign_id, archive_root=default_archive_root())

    vault_root = _campaign_vault_root(campaign_id)
    materializer = VaultMaterializer(vault_root)
    baker = ArchiveTickBaker(materializer, county_fips=tuple(DETROIT_TRI_COUNTY_FIPS))
    pages = vault_page_source(vault_root)
    known_subjects = vault_known_subjects(vault_root)
    narrator = NarratorSideProcess(NarratorCache(vault_root)) if narrator_enabled else None
    # Standard §5: the per-committed-tick NarrationEnvelope estate, one
    # append-only JSONL beside this campaign's vault pages.
    narration_sink = JsonlNarrationSink(vault_root / "narration.jsonl")

    # P26 U2 (ADR162): compose this campaign's trade wiring + real economics
    # overrides BEFORE the session boots (they thread into
    # ServiceContainer.create). The defines used here must be the SAME the
    # session runs under: a fresh campaign's come from the scenario's own
    # deterministic build (rebuilt identically inside create_new_campaign —
    # build kwargs are a stated non-goal there); a resumed campaign's come
    # from its persisted game_session row (exactly what resume_campaign
    # itself re-validates).
    existing_row = runtime.get_session(campaign_id)
    resuming = existing_row is not None
    if resuming:
        raw_defines = existing_row["game_defines_json"] if existing_row is not None else {}
        defines = _GameDefines.model_validate(
            raw_defines if isinstance(raw_defines, dict) else json.loads(raw_defines)
        )
    else:
        _world0, _config, defines = WayneCountyTradeScenario().build()
    event_bus = EventBus()
    trade, economics_overrides = _compose_trade(
        runtime,
        campaign_id,
        resuming=resuming,
        defines=defines,
        event_bus=event_bus,
    )

    county_wkt = _compose_county_wkt()
    session = (
        resume_campaign(
            runtime,
            campaign_id,
            tick_commit_observer=baker,
            pages=pages,
            known_subjects=known_subjects,
            progress_store=catalog,
            narrator=narrator,
            narration_sink=narration_sink,
            trade=trade,
            county_wkt=county_wkt,
            economics_overrides=economics_overrides,
        )
        if resuming
        else create_new_campaign(
            runtime,
            scenario=WayneCountyTradeScenario(),
            session_id=campaign_id,
            tick_commit_observer=baker,
            pages=pages,
            known_subjects=known_subjects,
            progress_store=catalog,
            narrator=narrator,
            narration_sink=narration_sink,
            trade=trade,
            county_wkt=county_wkt,
            economics_overrides=economics_overrides,
        )
    )
    # Runner-twin post-create assignment (runner.py:1329): the Leontief
    # pipeline publishes calibration warnings to the bus built above — make
    # it the session's own bus so those events land in tick history.
    session.services.event_bus = event_bus
    # ADR176 ruling 28 (P-J defect 3/3): the campaign catalog carries the
    # replay identity. Fresh campaigns stamp the seed their game_session row
    # was just minted with; campaigns minted before the columns backfill the
    # same way (game_session.rng_seed IS the campaign's seed throughout, by
    # the same Unit-C2 one-identity construction as campaign_id itself). A
    # ValueError here is a REAL identity divergence and must crash the boot.
    session_row = runtime.get_session(campaign_id)
    if session_row is not None and catalog.get_campaign(campaign_id) is not None:
        catalog.stamp_replay_identity(campaign_id, rng_seed=int(session_row["rng_seed"]))
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
        Callable[[str], bool],
    ],
    TutorialProgress | None,
]:
    """Build ``ArchiveApp``'s (and, M3, ``RustClientHost``'s) own
    ``tutorial_progress_factory=`` seam (Unit U4; extended by Program 24 P8,
    "the tutorial learns the shell"; widened again by the M3 ``VerbIssued``
    defect fix, ``docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md``
    §0).

    Returns a closure fulfilling :data:`~babylon.tui.app.TutorialProgressFactory`:
    given the just-booted campaign, its paced driver (or ``None``), a
    nav-subject query, a current-pane query, a watchlist-pin query (P8), and
    a ``was_verb_issued`` dispatch-proof query (M3), decide whether the T6
    opening-arc overlay should show for THIS campaign, and if so build its
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
        was_verb_issued: Callable[[str], bool],
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
            was_verb_issued=was_verb_issued,
        )

    return _factory


def _rotate_capture(path: Path, cap_bytes: int = _CAPTURE_LOG_MAX_BYTES) -> None:
    """Archive ``client-capture.log`` once it reaches the cap (Director
    directive 2026-07-28: every client log rotates at a reasonable size).

    The capture is a raw append-mode stream fed by ``sys.stdout``/``stderr``
    redirection — ``logging.handlers.RotatingFileHandler`` can't wrap it —
    so this applies the estate's 10 MB discipline by hand at session start:
    at or over the cap, the file becomes ``client-capture.log.1``
    (replacing any previous archive) and the session opens a fresh capture.

    :param path: the capture file (need not exist — a fresh install has
        neither the file nor the directory yet).
    :param cap_bytes: rotation threshold, default
        :data:`_CAPTURE_LOG_MAX_BYTES`.
    """
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return
    if size < cap_bytes:
        return
    path.replace(path.with_name(path.name + ".1"))


@contextmanager
def _terminal_takeover() -> Iterator[None]:
    """Make the terminal the Rust client's alone for the duration.

    Gate 3 blocker (2026-07-27): the root logger's console handler kept
    writing to the tty while the Rust client painted the alternate screen
    — dulwich emitted records on every vault touch, and the immediate-mode
    client only repaints on input, so one stray line corrupted the frame
    until the next keypress. The Textual ``App`` captured stdout/stderr
    and print output implicitly while running; this is the Rust lane's
    explicit equivalent:

    - every root handler that streams to the terminal is detached (file
      handlers keep recording everything — nothing is silenced, only
      re-routed);
    - ``sys.stdout``/``sys.stderr`` are redirected into
      ``LOG_DIR/client-capture.log`` so stray ``print``s (and the FFI
      panic path's ``PyErr::print`` traceback) land somewhere auditable.

    The Rust client writes the TUI through the RAW file descriptor, so
    redirecting the PYTHON stream objects never touches its rendering.
    Both the handlers and the streams restore on every exit path — a
    panicking client still hands back a console that logs.
    """
    import logging

    from babylon.config.base import BaseConfig

    root = logging.getLogger()
    tty_streams = {
        stream
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__)
        if stream is not None
    }
    _rotate_capture(BaseConfig.LOG_DIR / "client-capture.log")
    detached = [
        handler
        for handler in root.handlers
        if isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        and getattr(handler, "stream", None) in tty_streams
    ]
    for handler in detached:
        root.removeHandler(handler)
    BaseConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)
    outer_stdout, outer_stderr = sys.stdout, sys.stderr
    with open(BaseConfig.LOG_DIR / "client-capture.log", "a", encoding="utf-8") as capture:
        sys.stdout = capture
        sys.stderr = capture
        try:
            yield
        finally:
            sys.stdout = outer_stdout
            sys.stderr = outer_stderr
            for handler in detached:
                root.addHandler(handler)


def _run_rust_client(*, narrator_enabled: bool, tutorial_enabled: bool | None) -> None:
    """Boot the Rust/Ratatui client lane (M0 lobby hello-frame + M1 read wiring).

    Fails LOUDLY and actionably — before touching Postgres — when the
    extension is absent (default dep since Task 44, but a fresh clone or a
    broken build can still lack it); with it, composes the real catalog into
    a :class:`~babylon.tui.host.RustClientHost` and hands the terminal to
    ``babylon_tui.run`` (the seam the Textual ``ArchiveApp(...).run()``
    occupied before the M7 cutover deleted that lane).

    M1 wiring (review fix): threads the SAME ``campaign_loader``/
    ``driver_factory``/``watchlist_persistence`` seams :func:`run` builds
    for ``ArchiveApp`` on the textual path — :func:`_load_campaign` (partial
    over this ``runtime``/``catalog``), :func:`_driver_factory`, and
    ``catalog`` itself — into ``RustClientHost``, so
    :meth:`~babylon.tui.host.RustClientHost.load_campaign` has a real
    campaign to resolve once the Rust lobby picks one. Before this fix,
    ``RustClientHost`` had no way to bind a session at all: every M1 read
    method served absence against a session that could never exist.

    M3 wiring (Task 27, contract §1): also threads
    :func:`_tutorial_steps`/:func:`_tutorial_progress_factory` — the
    IDENTICAL objects the textual path's :func:`run` gives ``ArchiveApp`` —
    into ``RustClientHost`` as ``tutorial_steps=``/
    ``tutorial_progress_factory=``, so :meth:`~babylon.tui.host.
    RustClientHost.tutorial_state_json` has a real evaluator to poll once a
    campaign is bound.

    :param narrator_enabled: threaded into the client config verbatim, AND
        into :func:`_load_campaign`'s partial (the same flag
        :func:`_load_campaign` already threads on the textual path).
    :param tutorial_enabled: the tri-state flag. Superseding this
        docstring's own earlier, now-stale "the M0 config carries a plain
        bool (tutorial rendering is M3)" note: the M0 config's
        ``tutorial_enabled`` key is now a "possibly on" pre-filter Rust ALSO
        gates polling on (contract §1's own seam-crossing saver) —
        ``tutorial_enabled is not False`` (unset AND an explicit ``True``
        both mean "possibly on"; only an explicit ``--no-tutorial`` turns it
        fully off) — the HOST, via :func:`_tutorial_progress_factory`'s own
        tri-state heuristic, stays the sole arming authority either way.
    """
    try:
        import babylon_tui
    except ImportError as exc:
        msg = (
            "babylon play needs the babylon_tui extension, which ships in "
            "the default install: run `uv sync` (and after Rust edits, "
            "`uvx maturin develop` in rust/)."
        )
        raise RuntimeError(msg) from exc

    from functools import partial

    import babylon
    from babylon.config.defines import GameDefines
    from babylon.game.session import ensure_schema, open_runtime
    from babylon.persistence.babylon_meta import BabylonMetaStore
    from babylon.render.config import (
        read_render_config,
        render_config_path,
        resolve_active_tier,
    )
    from babylon.tui.host import RustClientHost

    # Task 35 (contract §7): the recorded [render] verdict is read ONCE here
    # — `babylon doctor` probes, runtime honors the record (ADR097 D4).
    # A missing config reads back as the glyph-floor defaults.
    render_cfg = read_render_config(render_config_path(os.environ))

    runtime = open_runtime()
    ensure_schema(runtime)
    catalog = BabylonMetaStore(runtime.pool)
    catalog.ensure_schema()
    steps = _tutorial_steps()
    host = RustClientHost(
        catalog,
        defines_hash=_defines_hash(GameDefines.load_default()),
        engine_version=babylon.__version__,
        campaign_loader=partial(
            _load_campaign, runtime, catalog, narrator_enabled=narrator_enabled
        ),
        driver_factory=_driver_factory,
        watchlist_persistence=catalog,
        nav_persistence=catalog,
        tutorial_steps=steps,
        tutorial_progress_factory=_tutorial_progress_factory(tutorial_enabled, steps),
        render_config=render_cfg,
    )
    from babylon.config.base import BaseConfig

    BaseConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)
    config_json = json.dumps(
        {
            "campaign_id": "",
            "campaign_name": "Lobby",
            "render_tier": resolve_active_tier(None, render_cfg).value,
            "tutorial_enabled": tutorial_enabled is not False,
            "narrator_enabled": narrator_enabled,
            "headless": False,
            # Director directive 2026-07-28: the Rust half logs into the
            # SAME estate as the Python half — babylon_tui::logging
            # installs a rolling rust-client.log here at boot.
            "log_dir": str(BaseConfig.LOG_DIR),
            "log_level": _CLIENT_LOG_LEVEL,
        }
    )
    with _terminal_takeover():
        babylon_tui.run(host, config_json)


def run(
    *,
    narrator_enabled: bool = True,
    tutorial_enabled: bool | None = None,
) -> None:
    """Boot the REAL Archive TUI: campaign lobby -> briefing -> campaign shell.

    The Rust/Ratatui client is THE terminal client (M7 cutover, ADR150 —
    Director ruling 2026-07-28: the Textual lane was deleted outright, no
    deprecation window). This delegates to :func:`_run_rust_client`.

    Requires a reachable Postgres — see :func:`babylon.game.session.open_runtime`.

    :param narrator_enabled: T5 Unit U1's ``--narrator/--no-narrator`` flag
        (see :func:`play`), threaded straight into every
        :func:`_load_campaign` call this boot makes.
    :param tutorial_enabled: T6 Unit U4's ``--tutorial/--no-tutorial``
        tri-state flag (see :func:`play`), threaded into
        :func:`_tutorial_progress_factory` (see its own docstring for the
        ``None`` default's first-session heuristic).
    """
    _run_rust_client(narrator_enabled=narrator_enabled, tutorial_enabled=tutorial_enabled)


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
