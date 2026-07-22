"""The Map domain view — choropleth with selectable lenses.

The lens promotes today's fog/class-vision payload gate into a player-selectable overlay, plus
value-band and tension lenses. Rendering reuses ``render_map_room`` (glyph floor + kitty raster
at information parity, ADR097). No engine import — the shell hands lens+cells to the renderer.
"""

from __future__ import annotations

from typing import Literal, get_args

from textual.reactive import reactive
from textual.widget import Widget

MapLens = Literal["value", "tension", "fog"]
_LENSES = frozenset(get_args(MapLens))


class MapView(Widget):
    """Choropleth map with a lens selector."""

    lens: reactive[MapLens] = reactive("value")

    def set_lens(self, lens: MapLens) -> None:
        """Select the active lens; raises ``ValueError`` on an unknown lens (loud failure)."""
        if lens not in _LENSES:
            raise ValueError(f"unknown map lens {lens!r}; known: {sorted(_LENSES)}")
        self.lens = lens
