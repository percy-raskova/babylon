"""The map room — cell-art choropleth (+ TGP raster behind a capability flag).

Renders a :class:`~babylon.projection.topology.choropleth.ChoroplethCell`
sequence as a small bitmap, then wraps that *same* bitmap in one of two
``textual-image`` widgets (ADR097's sole Tier-1 dependency, already pinned in
``pyproject.toml``): :class:`~textual_image.widget.HalfcellImage` for the
cell-art (glyph) floor, :class:`~textual_image.widget.TGPImage` for the
kitty-graphics-protocol raster upgrade. Building one image and handing it to
either widget is what makes ADR097 D2's information-parity rule ("Tier 1
never carries unique information; it re-renders what Tier 0 shows") true *by
construction* rather than by convention — there is no second code path that
could drift.

Cell-art is the design target, not the fallback (ADR097 D1): every tier must
be fully legible with :func:`render_map_room`'s default ``render_tier="glyph"``.
The TGP raster path is real, working code — not a stub — but per the WO's own
ruling it is **not snapshot-gated** (kitty-protocol bytes are a manual,
eyes-on-a-real-Kitty-terminal check, not an SVG-golden concern); this module's
own tests cover it structurally (image built, correct widget type chosen)
rather than with a byte-for-byte golden.

No capability *detection* lives here (Constitution gotcha: inject dependencies
explicitly, don't discover them at runtime) — ``render_tier`` is a parameter
the caller supplies. ADR097 D4's ``babylon doctor`` probe-once/config-write
mechanism is the eventual, separate source of that value; this module is
agnostic to how the caller obtained it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from PIL import Image as PILImage
from PIL import ImageDraw
from textual_image.widget import HalfcellImage, TGPImage

from babylon.projection.topology.choropleth import ChoroplethCell, RenderTier
from babylon.tui.theme import CRIMSON, DIM, GOLD, PANEL

#: ``textual_image.widget.Image`` (the package's "best available" alias) is a
#: module-level *variable*, not a class — not usable as a type annotation
#: (mypy: "Variable ... is not valid as a type"). :func:`render_map_room`
#: only ever returns one of these two concrete widget classes, so the Union
#: is both accurate and mypy-clean.
MapRoomWidget = HalfcellImage | TGPImage

__all__ = [
    "CELL_PIXELS",
    "MapRoomWidget",
    "build_choropleth_image",
    "render_map_room",
]

CELL_PIXELS: Final[int] = 24
"""Square pixel size of one choropleth cell block in the built bitmap. Purely
an internal rendering constant — it does not encode any game-balance value,
so it is not a :mod:`~babylon.config.defines.GameDefines` coefficient."""

#: Exploitation-rate band thresholds -> ksbc color (theme.py's own named
#: constants — never a new hardcoded hex; the module docstring on
#: ``tui/theme.py`` requires this). Hard-cut bands, not a continuous
#: gradient (``DESIGN_BIBLE`` §11 weather-grammar law 2: qualitative change
#: is a hard cut, never tweened) -- s/v == 1.0 ("half the working day is
#: unpaid") and 2.0 are the natural reference points for low/elevated/extreme.
_LOW_MAX: Final[float] = 1.0
_ELEVATED_MAX: Final[float] = 2.0


def _band_color(exploitation_rate: float | None) -> str:
    """Map one cell's exploitation rate to a ksbc hex color.

    :param exploitation_rate: ``s/v`` for the cell, ``float("inf")`` for a
        present-but-degenerate (``v == 0``) cell, or ``None`` for absence.
    :returns: A ``tui.theme`` hex color: :data:`~babylon.tui.theme.PANEL` for
        absence, :data:`~babylon.tui.theme.DIM` for the low band (``<= 1.0``),
        :data:`~babylon.tui.theme.GOLD` for the elevated band (``<= 2.0``),
        :data:`~babylon.tui.theme.CRIMSON` for the extreme band (``> 2.0`` or
        ``inf``).
    """
    if exploitation_rate is None:
        return PANEL
    if exploitation_rate <= _LOW_MAX:
        return DIM
    if exploitation_rate <= _ELEVATED_MAX:
        return GOLD
    return CRIMSON


def build_choropleth_image(
    cells: Sequence[ChoroplethCell], *, cell_px: int = CELL_PIXELS
) -> PILImage.Image:
    """Build a deterministic bitmap: one colored block per cell, left to right.

    Pure function of ``cells`` (and ``cell_px``) — no wall-clock, no
    randomness — so two calls with the same cells produce byte-identical
    pixel data (the same determinism discipline
    :func:`~babylon.projection.vault.render.render_county` holds for text).

    :param cells: The choropleth cells to draw, in the order they should
        appear (callers pass already-sorted cells — see
        :func:`~babylon.projection.topology.choropleth_aggregation.county_choropleth_cells`).
    :param cell_px: Side length in pixels of each cell's square block.
    :returns: An RGB :class:`PIL.Image.Image`, ``cell_px`` tall and
        ``cell_px * max(len(cells), 1)`` wide (never zero-width, even for an
        empty ``cells`` — an empty choropleth is still a valid, if trivial,
        bitmap).
    """
    width = cell_px * max(len(cells), 1)
    image = PILImage.new("RGB", (width, cell_px), color=PANEL)
    draw = ImageDraw.Draw(image)
    for index, cell in enumerate(cells):
        x0 = index * cell_px
        draw.rectangle(
            (x0, 0, x0 + cell_px - 1, cell_px - 1), fill=_band_color(cell.exploitation_rate)
        )
    return image


def render_map_room(cells: Sequence[ChoroplethCell], *, render_tier: RenderTier) -> MapRoomWidget:
    """Render the map room's choropleth as a Textual widget.

    :param cells: The choropleth cells to render (already tier-aggregated and
        sorted — see :mod:`babylon.projection.topology.choropleth_aggregation`).
    :param render_tier: ``"glyph"`` for the cell-art floor
        (:class:`~textual_image.widget.HalfcellImage`, half-block characters
        — ADR097 Tier 0, the design target) or ``"pixel"`` for the
        kitty-graphics-protocol raster upgrade
        (:class:`~textual_image.widget.TGPImage` — ADR097 Tier 1). Callers
        decide this value via
        :func:`~babylon.projection.topology.choropleth.select_render_tier`;
        this function does not re-derive or override it.
    :returns: A mounted-ready Textual ``Image`` widget wrapping the same
        bitmap :func:`build_choropleth_image` builds regardless of tier —
        the information-parity guarantee.
    """
    image = build_choropleth_image(cells)
    width = max(len(cells), 1)
    widget: MapRoomWidget = TGPImage(image) if render_tier == "pixel" else HalfcellImage(image)
    widget.styles.width = width
    widget.styles.height = 3
    return widget
