"""The Map domain view — choropleth with selectable lenses.

The lens promotes today's fog/class-vision payload gate into a player-selectable overlay, plus
value-band and tension lenses. Rendering reuses ``render_map_room`` (glyph floor + kitty raster
at information parity, ADR097). No engine import — the shell hands lens+cells to the renderer.
"""

from __future__ import annotations

from typing import Final, Literal, get_args

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

MapLens = Literal["value", "tension", "fog"]
_LENSES = frozenset(get_args(MapLens))

_PANE_ABSENT: Final[str] = (
    "▌ map: no choropleth cells wired yet (feed wires in at Program 24 P2-P6)."
)
"""Program 24 P1 honest-absence fence: no live territory/choropleth feed exists yet —
never call :func:`~babylon.tui.map_room.render_map_room` with a fabricated empty cell
list to fill this pane (Constitution III.11)."""


class MapView(Widget):
    """Choropleth map with a lens selector."""

    lens: reactive[MapLens] = reactive("value")

    def compose(self) -> ComposeResult:
        yield Static(_PANE_ABSENT, id="map-body")

    def set_lens(self, lens: MapLens) -> None:
        """Select the active lens; raises ``ValueError`` on an unknown lens (loud failure)."""
        if lens not in _LENSES:
            raise ValueError(f"unknown map lens {lens!r}; known: {sorted(_LENSES)}")
        self.lens = lens
