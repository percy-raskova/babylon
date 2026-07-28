"""The registered ksbc Textual theme — split from ``babylon.tui.theme`` at
the M7 cutover decoupling (the constants module must stay textual-free for
the Rust host's import chain). Dies with the Textual estate at the ceremony.
"""

from __future__ import annotations

from typing import Final

from textual.theme import Theme

from babylon.tui.theme import (
    AMBER,
    BONE,
    CRIMSON,
    DIM,
    FIELD,
    GOLD,
    GREEN_DARK,
    PANEL,
    ROYAL,
    SELECTION_TEXT,
)

__all__ = ["KSBC"]

KSBC: Final = Theme(
    name="ksbc",
    primary=CRIMSON,
    secondary=ROYAL,
    accent=GOLD,
    foreground=BONE,
    background=FIELD,
    surface=FIELD,
    panel=PANEL,
    success=GREEN_DARK,
    warning=GOLD,
    error=CRIMSON,
    dark=True,
    variables={
        "block-cursor-background": GOLD,
        "block-cursor-foreground": SELECTION_TEXT,
        "footer-key-foreground": GOLD,
        "link-color": GOLD,
        "text-muted": DIM,
        "autopause-amber": AMBER,
    },
)
"""The registered ksbc theme. Callers do ``app.register_theme(KSBC)`` then
``app.theme = "ksbc"`` (see ``babylon.tui.app.ArchiveApp.on_mount``)."""
