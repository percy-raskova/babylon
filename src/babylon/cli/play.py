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
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

if TYPE_CHECKING:
    from babylon.config.defines import GameDefines
    from babylon.game.pacing import PacedTickDriver
    from babylon.game.session import GameSession
    from babylon.persistence import PostgresRuntime
    from babylon.persistence.babylon_meta import BabylonMetaStore
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.tui.app import CampaignHandle


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
    runtime: PostgresRuntime, catalog: BabylonMetaStore, campaign_id: UUID
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
    :returns: the live, booted/resumed :class:`~babylon.game.session.GameSession`
        (structurally satisfies ``babylon.tui.app.CampaignHandle``).
    """
    from babylon.engine.headless_runner.scopes import DETROIT_TRI_COUNTY_FIPS
    from babylon.engine.scenarios import WayneCountyScenario
    from babylon.game.session import create_new_campaign, resume_campaign, vault_page_source
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.projection.vault.tick_baker import ArchiveTickBaker

    vault_root = _campaign_vault_root(campaign_id)
    materializer = VaultMaterializer(vault_root)
    baker = ArchiveTickBaker(materializer, county_fips=tuple(DETROIT_TRI_COUNTY_FIPS))
    pages = vault_page_source(vault_root)

    session = (
        resume_campaign(
            runtime, campaign_id, tick_commit_observer=baker, pages=pages, progress_store=catalog
        )
        if runtime.get_session(campaign_id) is not None
        else create_new_campaign(
            runtime,
            scenario=WayneCountyScenario(),
            session_id=campaign_id,
            tick_commit_observer=baker,
            pages=pages,
            progress_store=catalog,
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


def run() -> None:
    """Boot the REAL Archive TUI: campaign lobby -> briefing -> campaign shell.

    Requires a reachable Postgres — see :func:`babylon.game.session.open_runtime`.
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

    app = ArchiveApp(
        campaign_menu=menu,
        campaign_loader=partial(_load_campaign, runtime, catalog),
        driver_factory=_driver_factory,
    )
    app.run()


def play() -> None:
    """Play Babylon — the real campaign session, via the composition root."""
    run()
