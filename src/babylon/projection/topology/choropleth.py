"""The map-room choropleth — tier selection + the cell view-model (WO-33).

Transport-neutral *and* persistence-neutral by construction: no Textual, no
PIL, no database connection, and — deliberately — no import of
:mod:`babylon.persistence` at all. That last point is load-bearing, not
incidental: ``import-linter``'s ``"tui client reads projections only"``
contract (``pyproject.toml``) forbids ``babylon.tui`` from importing
``babylon.persistence`` *even transitively*. :mod:`babylon.tui.directives`
and :mod:`babylon.tui.map_room` need only the tier/renderer selection logic
and the :class:`ChoroplethCell` shape below — never the aggregate-fetching
functions that actually touch persistence row-models
(:class:`~babylon.persistence.hex_state.DynamicHexState`,
:class:`~babylon.persistence.postgres_aggregation.CountyValueAggregate`) — so
those functions live in the sibling module
:mod:`babylon.projection.topology.choropleth_aggregation` instead. Splitting
the module this way is what makes the boundary a fact of the import graph,
not a promise kept by convention.

This module answers one question the TUI's map room
(:mod:`babylon.tui.map_room`) needs answered before it draws anything:
**which renderer for which tier?** (:func:`select_render_tier`) — the
charter's P0 batch ruling (``project/programs/24-the-archive.md``
§"Map-room tiers") is binding: cell-art choropleths at the EA and state
tiers, unconditionally; kitty-graphics-protocol (TGP) raster only at the
county tier, and only when the caller's runtime capability flag requests it
(default is the cell-art floor — Tier 0 is the *design target*, not a
fallback, per ADR097 D1).

See :mod:`babylon.projection.topology.choropleth_aggregation` for how a
:class:`ChoroplethCell` sequence is actually produced per tier (the
"one producer per tier" rulings, including the ``ea`` tier's honest
absence — no BEA Economic Area producer exists yet).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ChoroplethCell",
    "MapTier",
    "RenderTier",
    "select_render_tier",
]

MapTier = Literal["ea", "state", "county"]
"""The three map-room tiers the charter's P0 batch ruling names. ``hex`` (the
finest spatial-lattice rung, ``SPATIAL_LEVEL_NAMES`` in
``babylon.domain.dialectics.instances.levels``) and ``nation`` (a single
aggregate, no map needed) are deliberately excluded — the map room never
renders at either."""

RenderTier = Literal["glyph", "pixel"]
"""ADR097's own vocabulary (D1 "Tier 0 -- glyph canon", D2 "Tier 1 -- pixel
plates"), reused verbatim rather than inventing parallel naming — when
ADR097 D4's ``babylon doctor`` capability probe lands and writes
``render_tier`` to config, that value plugs into :func:`select_render_tier`
without a rename."""

_GLYPH_ONLY_TIERS: frozenset[MapTier] = frozenset({"ea", "state"})
"""Tiers the charter ruling pins to cell-art unconditionally — the capability
flag is never consulted for these; only ``county`` ever considers ``pixel``."""


class ChoroplethCell(BaseModel):
    """One map-room cell: a region id and its exploitation-rate fill value.

    :param region_id: The region's stable identifier — a county FIPS, state
        FIPS, or EA code, depending on the tier that produced this cell (the
        cell itself is tier-agnostic; the caller already knows which tier it
        asked for).
    :param exploitation_rate: ``s/v`` for this region, or ``None`` when the
        region has no attributed data (honest absence, never a fabricated
        zero). ``float("inf")`` is a *present*, mathematically well-defined
        value for ``v == 0`` (mirrors
        :attr:`~babylon.domain.economics.tensor.ValueTensor4x3.exploitation_rate`'s
        own convention) — distinct from absence, and rendered as the most
        intense band, never dropped.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    region_id: str = Field(min_length=1)
    exploitation_rate: float | None = None


def select_render_tier(tier: MapTier, *, requested: RenderTier) -> RenderTier:
    """Pick the renderer for a map-room tier (charter P0 batch ruling, binding).

    :param tier: The map-room tier being rendered.
    :param requested: The caller's requested render tier — the eventual home
        for ADR097 D4's probed/config-declared ``render_tier``, or an
        explicit override. Ignored for ``ea``/``state`` (always ``"glyph"``);
        honored as-is for ``county``.
    :returns: ``"glyph"`` for ``ea``/``state`` unconditionally; ``requested``
        for ``county`` (so ``requested="glyph"`` keeps the default-OFF
        cell-art fallback, and only an explicit ``requested="pixel"``
        upgrades the county tier to TGP raster).
    """
    if tier in _GLYPH_ONLY_TIERS:
        return "glyph"
    return requested
