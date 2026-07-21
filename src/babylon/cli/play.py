"""`babylon play` — boot a real campaign session through the composition root.

Historically this delegated straight to the bundled two-node demo
(``babylon.__main__``). Since Program v1.0.0's Unit C1 (the campaign
composition root, :mod:`babylon.game.session`), this boots a REAL campaign —
create-or-resume a Wayne County session (ruling 3: "Wayne stays in lobby") —
through the real 30-system engine and a real Postgres runtime, wires its
vault into a real ``ArchiveApp``, and runs the TUI.

HONEST GAPS (later units, not fabricated here): the lobby's campaign picker
and the lobby->briefing->campaign multi-screen flow are unbuilt
(``ArchiveApp`` is still single-page; ``tui/app.py``'s Screen-mode split is
named future work in the program plan) — this boots straight into the live
dossier view. No advance-tick keybinding is wired yet either (that lands
with the paced Textual-worker driver, also named future work); the booted
``GameSession`` is attached to the running app as ``app.session`` so that
unit can drive it without touching this file again.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID


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


def run() -> None:
    """Boot the REAL Archive TUI over a real campaign session.

    Resumes the campaign named by ``BABYLON_CAMPAIGN_ID`` (a ``game_session``
    UUID) if set, else starts a fresh Wayne County session. Requires a
    reachable Postgres — see :func:`babylon.game.session.open_runtime`.
    """
    from babylon.engine.headless_runner.scopes import DETROIT_TRI_COUNTY_FIPS
    from babylon.engine.scenarios import WayneCountyScenario
    from babylon.game.session import (
        create_new_campaign,
        ensure_schema,
        open_runtime,
        resume_campaign,
        vault_page_source,
    )
    from babylon.projection.vault.materializer import VaultMaterializer
    from babylon.projection.vault.tick_baker import ArchiveTickBaker
    from babylon.tui.app import ArchiveApp

    runtime = open_runtime()
    ensure_schema(runtime)

    vault_root = _vault_root()
    baker = ArchiveTickBaker(
        VaultMaterializer(vault_root), county_fips=tuple(DETROIT_TRI_COUNTY_FIPS)
    )

    campaign_id = os.environ.get("BABYLON_CAMPAIGN_ID")
    session = (
        resume_campaign(runtime, UUID(campaign_id), tick_commit_observer=baker)
        if campaign_id
        else create_new_campaign(
            runtime, scenario=WayneCountyScenario(), tick_commit_observer=baker
        )
    )

    app = ArchiveApp(pages=vault_page_source(vault_root))
    # Forward seam for the tick-advance binding (later unit): ArchiveApp
    # declares no `session` attribute of its own yet, so this is a plain
    # dynamic attach, not a documented constructor parameter.
    app.session = session  # type: ignore[attr-defined]
    app.run()


def play() -> None:
    """Play Babylon — the real campaign session, via the composition root."""
    run()
