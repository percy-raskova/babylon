"""Render tiers and the crimson/gold palette (ADR097 D1/D5).

Tier 0 (GLYPH) is the design target and the sole information carrier; Tier 1
(PIXEL) re-renders Tier-0 content. ``TRUECOLOR_PALETTE`` is the §9b canon; its
256-color fallback ``DEGRADED_256_PALETTE`` is computed here — the single source
of truth the DESIGN_BIBLE §9b row cites, so doc and code cannot drift.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class RenderTier(StrEnum):
    GLYPH = "glyph"
    PIXEL = "pixel"


class PaletteTier(StrEnum):
    TRUECOLOR = "truecolor"
    DEGRADED_256 = "256"


class RoleToken(StrEnum):
    FIELD = "field"
    TEXT = "text"
    ACCENT_CRIMSON = "accent_crimson"
    ACCENT_GOLD = "accent_gold"
    SELECTION_TEXT = "selection_text"
    MUTED_DIM = "muted_dim"
    MUTED_LIGHT = "muted_light"
    MUTED_DARK = "muted_dark"
    GREEN_DARK = "green_dark"
    GREEN_BRIGHT = "green_bright"
    ROYAL = "royal"
    CYAN = "cyan"


# §9b "Kitty ksbc-new, verbatim" (DESIGN_BIBLE §9b, lines 302-310).
TRUECOLOR_PALETTE: Final[dict[RoleToken, str]] = {
    RoleToken.FIELD: "#1a0000",
    RoleToken.TEXT: "#e8e8e8",
    RoleToken.ACCENT_CRIMSON: "#dc143c",
    RoleToken.ACCENT_GOLD: "#ffd700",
    RoleToken.SELECTION_TEXT: "#000000",
    RoleToken.MUTED_DIM: "#404040",
    RoleToken.MUTED_LIGHT: "#c0c0c0",
    RoleToken.MUTED_DARK: "#202020",
    RoleToken.GREEN_DARK: "#228b22",
    RoleToken.GREEN_BRIGHT: "#32cd32",
    RoleToken.ROYAL: "#4169e1",
    RoleToken.CYAN: "#008b8b",
}

# xterm-256 6x6x6 colour cube levels and grayscale ramp (indices 16-255).
_CUBE_LEVELS: Final[tuple[int, ...]] = (0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF)
_CUBE_START: Final[int] = 16
_CUBE_END: Final[int] = 231
_GRAY_START: Final[int] = 232
_GRAY_END: Final[int] = 255


def _index_rgb(index: int) -> tuple[int, int, int]:
    """RGB of an xterm-256 index in the cube (16-231) or grayscale (232-255) range."""
    if _CUBE_START <= index <= _CUBE_END:
        offset = index - _CUBE_START
        return (
            _CUBE_LEVELS[offset // 36],
            _CUBE_LEVELS[(offset // 6) % 6],
            _CUBE_LEVELS[offset % 6],
        )
    if _GRAY_START <= index <= _GRAY_END:
        value = 8 + 10 * (index - _GRAY_START)
        return (value, value, value)
    raise ValueError(f"index {index} outside the searchable 16-255 range")


def nearest_xterm256(hex_color: str) -> int:
    """Nearest xterm-256 index (16-255) to a ``#rrggbb`` colour by squared RGB distance.

    System colours 0-15 are excluded so the mapping is stable across terminal themes.
    """
    if len(hex_color) != 7 or not hex_color.startswith("#"):
        raise ValueError(f"expected a 6-digit hex like '#dc143c', got {hex_color!r}")
    try:
        red = int(hex_color[1:3], 16)
        green = int(hex_color[3:5], 16)
        blue = int(hex_color[5:7], 16)
    except ValueError as exc:
        raise ValueError(f"expected a 6-digit hex like '#dc143c', got {hex_color!r}") from exc

    best_index = _CUBE_START
    best_distance: int | None = None
    for index in range(_CUBE_START, _GRAY_END + 1):  # bounded: 240 iterations
        pr, pg, pb = _index_rgb(index)
        distance = (red - pr) ** 2 + (green - pg) ** 2 + (blue - pb) ** 2
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_index = index
    return best_index


DEGRADED_256_PALETTE: Final[dict[RoleToken, int]] = {
    token: nearest_xterm256(hex_color) for token, hex_color in TRUECOLOR_PALETTE.items()
}
