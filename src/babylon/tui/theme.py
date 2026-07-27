"""The ksbc Textual theme (DESIGN_BIBLE section 9b "The Installer").

Owner aesthetic ruling 2026-07-11 (``project/research/16-living-map/DESIGN_BIBLE.md``
section 9b): the Archive's chrome follows the Guix installer's dead-space/plate
anatomy, painted in the owner's Kitty ``ksbc-new`` palette — crimson borders,
gold selection/action, a near-black field. This module is the single source of
truth for the hex values Textual actually paints; other ``babylon.tui`` modules
import the named constants rather than re-hardcoding hex (``wikilinks.py``'s
redlink/wikilink spans in particular).

**Palette SSOT (Program 24 P7, ADR097 D1/D5):** before this pass, this module and
:mod:`babylon.render.tiers` were two independently-hardcoded copies of the same
§9b table and had drifted on two of seven shared tokens (``BONE`` was
``#e8e2d4`` against the doc's ``text`` row of ``#e8e8e8``; ``DIM`` was a
warm-khaki ``#8f8778`` against the doc's ``muted_dim`` row of ``#404040``) —
and this module was missing named constants for the ``green_bright``/``cyan``
accent roles the doc's supporting row lists. ``tiers.py``'s
``TRUECOLOR_PALETTE`` is the doc-parity-tested source
(``tests/unit/render/test_design_bible_parity.py`` fails if it drifts from
DESIGN_BIBLE §9b); every constant below that corresponds to a §9b role token
is now sourced from that one dict, so a doc/tiers.py drift and a doc/theme.py
drift can no longer diverge from each other. ``AMBER`` and ``PANEL`` are NOT
§9b role tokens (no doc row exists for either) — ``AMBER`` is a
Babylon-specific reserved accent, ``PANEL`` a derived plate tone one step up
from ``FIELD``; both stay hardcoded, there is nothing for them to drift from.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from textual.theme import Theme

from babylon.render.tiers import TRUECOLOR_PALETTE, RoleToken

CRIMSON: Final = TRUECOLOR_PALETTE[RoleToken.ACCENT_CRIMSON]
"""accent-crimson — cursor, active border, urgency accents."""

GOLD: Final = TRUECOLOR_PALETTE[RoleToken.ACCENT_GOLD]
"""accent-gold — selection, action, solidarity (Article VII's GOLD)."""

FIELD: Final = TRUECOLOR_PALETTE[RoleToken.FIELD]
"""field (dead space) — the near-black background."""

BONE: Final = TRUECOLOR_PALETTE[RoleToken.TEXT]
"""text foreground (§9b ``text`` row — was a theme.py-only ``#e8e2d4`` before
the Program 24 P7 palette-SSOT pass)."""

DIM: Final = TRUECOLOR_PALETTE[RoleToken.MUTED_DIM]
"""muted/secondary text (§9b ``muted_dim`` row — was a theme.py-only
warm-khaki ``#8f8778`` before the Program 24 P7 palette-SSOT pass)."""

SELECTION_TEXT: Final = TRUECOLOR_PALETTE[RoleToken.SELECTION_TEXT]
"""inverse-video selection/cursor foreground (§9b ``selection_text`` row)."""

GREEN_DARK: Final = TRUECOLOR_PALETTE[RoleToken.GREEN_DARK]
"""success/positive data accent (§9b supporting-row green)."""

GREEN_BRIGHT: Final = TRUECOLOR_PALETTE[RoleToken.GREEN_BRIGHT]
"""Reserved data accent (§9b supporting-row green). Not wired to any widget
in this program increment."""

ROYAL: Final = TRUECOLOR_PALETTE[RoleToken.ROYAL]
"""Theme ``secondary`` / data accent (§9b supporting-row royal)."""

CYAN: Final = TRUECOLOR_PALETTE[RoleToken.CYAN]
"""Reserved data accent (§9b supporting-row cyan). Not wired to any widget
in this program increment."""

AMBER: Final = "#ff8c00"
"""Reserved for the autopause indicator. Not wired to any widget in this
program increment — no autopause feature exists yet to drive it. NOT a §9b
role token (see module docstring) — hardcoded, nothing to drift from."""

PANEL: Final = "#200404"
"""Plate background, one step up from the field. NOT a §9b role token (see
module docstring) — hardcoded, nothing to drift from."""

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

PARITY_TOKENS: Final[Mapping[RoleToken, str]] = {
    RoleToken.FIELD: FIELD,
    RoleToken.TEXT: BONE,
    RoleToken.ACCENT_CRIMSON: CRIMSON,
    RoleToken.ACCENT_GOLD: GOLD,
    RoleToken.SELECTION_TEXT: SELECTION_TEXT,
    RoleToken.MUTED_DIM: DIM,
    RoleToken.GREEN_DARK: GREEN_DARK,
    RoleToken.GREEN_BRIGHT: GREEN_BRIGHT,
    RoleToken.ROYAL: ROYAL,
    RoleToken.CYAN: CYAN,
}
"""Every §9b role token this module carries a named constant for, keyed for
``tests/unit/render/test_design_bible_parity.py`` to check against the doc's
own truecolor column directly (Program 24 P7) — independent of
:mod:`babylon.render.tiers`, so a future hardcoded regression in *this*
module (bypassing the ``TRUECOLOR_PALETTE`` import above) is still caught.
``MUTED_LIGHT``/``MUTED_DARK`` are absent because no widget in this codebase
renders either tone — only ``tiers.py`` computes them, for the 256-color
degrade math."""
