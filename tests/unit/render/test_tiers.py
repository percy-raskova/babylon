"""Tier model + palette contract (ADR097 D1/D5).

The 256-index map is a behavioral golden: it pins the nearest-color math so the
DESIGN_BIBLE §9b row (Task 8) and the widget (Task 7) can cite one source of truth.
"""

from __future__ import annotations

import pytest

from babylon.render.tiers import (
    DEGRADED_256_PALETTE,
    TRUECOLOR_PALETTE,
    PaletteTier,
    RenderTier,
    RoleToken,
    nearest_xterm256,
)

# Nearest xterm-256 index over the 6x6x6 cube + 24-step grayscale (indices 16-255,
# system colors 0-15 excluded), computed from the §9b truecolor hexes.
EXPECTED_256: dict[RoleToken, int] = {
    RoleToken.FIELD: 232,
    RoleToken.TEXT: 254,
    RoleToken.ACCENT_CRIMSON: 161,
    RoleToken.ACCENT_GOLD: 220,
    RoleToken.SELECTION_TEXT: 16,
    RoleToken.MUTED_DIM: 238,
    RoleToken.MUTED_LIGHT: 250,
    RoleToken.MUTED_DARK: 234,
    RoleToken.GREEN_DARK: 28,
    RoleToken.GREEN_BRIGHT: 77,
    RoleToken.ROYAL: 62,
    RoleToken.CYAN: 30,
}


def test_render_tier_values() -> None:
    assert RenderTier.GLYPH.value == "glyph"
    assert RenderTier.PIXEL.value == "pixel"


def test_palette_tier_values() -> None:
    assert PaletteTier.TRUECOLOR.value == "truecolor"
    assert PaletteTier.DEGRADED_256.value == "256"


def test_truecolor_palette_matches_design_bible_9b() -> None:
    assert TRUECOLOR_PALETTE[RoleToken.FIELD] == "#1a0000"
    assert TRUECOLOR_PALETTE[RoleToken.TEXT] == "#e8e8e8"
    assert TRUECOLOR_PALETTE[RoleToken.ACCENT_CRIMSON] == "#dc143c"
    assert TRUECOLOR_PALETTE[RoleToken.ACCENT_GOLD] == "#ffd700"
    assert set(TRUECOLOR_PALETTE) == set(RoleToken)


@pytest.mark.parametrize("token", list(RoleToken))
def test_degraded_index_is_nearest(token: RoleToken) -> None:
    assert DEGRADED_256_PALETTE[token] == EXPECTED_256[token]
    assert DEGRADED_256_PALETTE[token] == nearest_xterm256(TRUECOLOR_PALETTE[token])


@pytest.mark.parametrize(
    ("hex_color", "index"),
    [("#000000", 16), ("#ffffff", 231), ("#808080", 244)],
)
def test_nearest_xterm256_known_points(hex_color: str, index: int) -> None:
    assert nearest_xterm256(hex_color) == index


def test_nearest_xterm256_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="6-digit hex"):
        nearest_xterm256("dc143c")  # missing leading '#'
