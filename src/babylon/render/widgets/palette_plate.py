"""Seed widget (ADR097 D1/D2/D3): the §9b palette swatch table at Tier 0.

The minimal real deliverable that proves the render estate — one static Textual
widget over a tier-INDEPENDENT plate model (the parity rule: Tier 1 may add no
data Tier 0 lacks), snapshot-tested so it joins the III.13 golden estate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Static

from babylon.render.tiers import (
    DEGRADED_256_PALETTE,
    TRUECOLOR_PALETTE,
    PaletteTier,
    RoleToken,
)


class PaletteRow(BaseModel):
    """One §9b role, carrying BOTH representations (parity: no tier-specific data)."""

    model_config = ConfigDict(frozen=True)

    token: RoleToken
    truecolor_hex: str
    xterm256: int


def plate_model() -> tuple[PaletteRow, ...]:
    """The tier-independent plate data — identical for glyph and pixel paths."""
    return tuple(
        PaletteRow(
            token=token,
            truecolor_hex=TRUECOLOR_PALETTE[token],
            xterm256=DEGRADED_256_PALETTE[token],
        )
        for token in RoleToken
    )


def swatch_cell(row: PaletteRow, palette: PaletteTier) -> str:
    """The cell label for the active palette — selects a representation, not data."""
    if palette is PaletteTier.TRUECOLOR:
        return f"{row.token.value:<16} {row.truecolor_hex}"
    return f"{row.token.value:<16} xterm-{row.xterm256}"


class PalettePlate(Static):
    """Static glyph-canon render of the §9b swatch table (Tier 0)."""

    def __init__(self, palette: PaletteTier = PaletteTier.TRUECOLOR) -> None:
        super().__init__()
        self._palette = palette

    def render(self) -> Text:
        text = Text()
        for row in plate_model():
            color = (
                row.truecolor_hex
                if self._palette is PaletteTier.TRUECOLOR
                else f"color({row.xterm256})"
            )
            text.append("  ██  ", style=color)
            text.append(swatch_cell(row, self._palette) + "\n")
        return text


class PalettePlateApp(App[None]):
    """Snapshot host for the seed widget (deterministic, fixed 80x24 in tests)."""

    def compose(self) -> ComposeResult:
        yield PalettePlate(PaletteTier.TRUECOLOR)
