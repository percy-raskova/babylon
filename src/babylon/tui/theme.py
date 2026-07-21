"""The ksbc Textual theme (DESIGN_BIBLE section 9b "The Installer").

Owner aesthetic ruling 2026-07-11 (``project/research/16-living-map/DESIGN_BIBLE.md``
section 9b): the Archive's chrome follows the Guix installer's dead-space/plate
anatomy, painted in the owner's Kitty ``ksbc-new`` palette — crimson borders,
gold selection/action, a near-black field. This module is the single source of
truth for those hex values; other ``babylon.tui`` modules import the named
constants rather than re-hardcoding hex (``wikilinks.py``'s redlink/wikilink
spans in particular).
"""

from __future__ import annotations

from typing import Final

from textual.theme import Theme

CRIMSON: Final = "#dc143c"
"""accent-crimson — cursor, active border, urgency accents."""

GOLD: Final = "#ffd700"
"""accent-gold — selection, action, solidarity (Article VII's GOLD)."""

FIELD: Final = "#1a0000"
"""field (dead space) — the near-black background."""

BONE: Final = "#e8e2d4"
"""text foreground."""

DIM: Final = "#8f8778"
"""muted/secondary text."""

AMBER: Final = "#ff8c00"
"""Reserved for the autopause indicator. Not wired to any widget in this
program increment — no autopause feature exists yet to drive it."""

PANEL: Final = "#200404"
"""Plate background, one step up from the field."""

KSBC: Final = Theme(
    name="ksbc",
    primary=CRIMSON,
    secondary="#4169e1",
    accent=GOLD,
    foreground=BONE,
    background=FIELD,
    surface=FIELD,
    panel=PANEL,
    success="#228b22",
    warning=GOLD,
    error=CRIMSON,
    dark=True,
    variables={
        "block-cursor-background": GOLD,
        "block-cursor-foreground": "#000000",
        "footer-key-foreground": GOLD,
        "link-color": GOLD,
        "text-muted": DIM,
        "autopause-amber": AMBER,
    },
)
"""The registered ksbc theme. Callers do ``app.register_theme(KSBC)`` then
``app.theme = "ksbc"`` (see ``babylon.tui.app.ArchiveApp.on_mount``)."""
