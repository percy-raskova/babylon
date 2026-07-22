"""Hex-grain habitability by county inheritance — T3 U6, the habitability signal.

There is no hex-native habitability column anywhere in the substrate:
``dynamic_hex_state``/``v_hex_state_asof`` (:class:`~babylon.persistence.
hex_state.DynamicHexState`) carry ``c``/``v``/``s``/``k`` and the three
substrate stocks, never ``habitability``. ``habitability`` lives ONLY on the
live in-memory graph, written onto ``territory`` node attrs by
``MetabolismSystem`` (``engine/systems/metabolism.py``) — a graph-only
transient ``TERRITORY_EXCLUDED_FIELDS`` (``world_state.py:88``) drops on
every ``WorldState.from_graph()`` reconstruction. Adding a per-hex column is
a physics/persistence change, out of T3 scope (see the county dossier's own
``habitability`` field, :func:`babylon.projection.county.project_county`,
for the same live-graph-only read one scale up).

This module fills the gap the *only* honest way available today: **G-inherited
county-grain read, read-only.** Each hex row already carries its parent
``county_fips`` (the crosswalk the hex substrate ships on every row); this
function resolves that county's territory node on the LIVE graph and hands
every hex under it the SAME value — the ``allocate`` leg of
:class:`~babylon.domain.dialectics.instances.scale.ScaleAdjunction`'s
``allocate ⊣ aggregate`` adjunction, broadcasting one parent reading down to
its children, not splitting a divisible quantity by share (there is only one
number to inherit, not a sum to partition, so no ``ScaleAdjunction`` instance
is actually constructed here — the analogy is the adjunction's *shape*, not
its extensive-quantity machinery). The result is explicitly labelled
county-grain, not hex-native: two hexes in the same county read identically
today, and will keep doing so until a real per-hex habitability physics
lands.

Absence discipline (Constitution III.11): a hex whose county has no
territory node, or whose territory has never had ``habitability`` written
onto it (tick 0 / MetabolismSystem has not run this session), projects
``None`` — never a fabricated ``0.0`` (nor the ``1.0`` some aggregators, e.g.
``endgame_detector.py``, default an unattributed *mean* reading to; that
convention belongs to that aggregator, not this per-hex honest read).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from babylon.models.enums.topology import NodeType
from babylon.models.types import Probability
from babylon.persistence.hex_state import DynamicHexState

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.graph import GraphNode

__all__ = ["HexHabitabilityCell", "hex_habitability_by_county_inheritance"]


class HexHabitabilityCell(BaseModel):
    """One hex's county-inherited habitability read.

    :param h3_index: The hex's stable H3 identifier (``v_hex_state_asof``'s
        ``h3_index`` column).
    :param county_fips: The hex's parent county FIPS, read straight off the
        hex row itself — never re-derived spatially by this function.
    :param habitability: The parent county's territory node's LIVE
        ``habitability`` graph attribute, inherited verbatim (G-inherited
        county-grain read, not hex-native data) — or ``None`` when the county
        has no territory node, or the territory carries no ``habitability``
        attribute yet. Honest absence, never a fabricated ``0.0``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    h3_index: str = Field(min_length=15, max_length=15)
    county_fips: str = Field(pattern=r"^\d{5}$")
    habitability: Probability | None = None


def _territory_by_county_fips(graph: GraphProtocol, county_fips: str) -> GraphNode | None:
    """Resolve the territory node carrying ``county_fips``, deterministically.

    Mirrors :func:`babylon.projection.county._resolve_territory`'s
    lexicographically-smallest tie-break for the (currently unseeded)
    multi-territory-per-county case. A small module-local copy rather than
    reaching into ``county.py``'s private helper, matching this codebase's
    existing per-module resolver convention (:mod:`babylon.projection.
    social_class` and :mod:`babylon.projection.state` each carry their own
    equivalent instead of sharing one).

    :param graph: The live post-tick graph.
    :param county_fips: Five-digit county FIPS code.
    :returns: The matching territory node, or ``None`` if none carries the code.
    """
    matches = [
        node
        for node in graph.query_nodes(node_type=NodeType.TERRITORY)
        if node.attributes.get("county_fips") == county_fips
    ]
    if not matches:
        return None
    return min(matches, key=lambda node: node.id)


def hex_habitability_by_county_inheritance(
    rows: Sequence[DynamicHexState],
    *,
    graph: GraphProtocol,
) -> tuple[HexHabitabilityCell, ...]:
    """Hex-grain habitability, G-inherited from each hex's parent county.

    Reads ``habitability`` straight off the LIVE ``graph`` object's territory
    nodes — never through a ``WorldState`` round-trip, since
    ``TERRITORY_EXCLUDED_FIELDS`` drops the attribute on reconstruction
    (world_state.py:88). Every distinct ``county_fips`` among ``rows`` is
    resolved to its territory node at most once (cached), so a caller handing
    in thousands of hexes under a handful of counties pays one graph query
    per county, not one per hex.

    :param rows: Hex-level rows carrying ``h3_index``/``county_fips`` — any
        ``v_hex_state_asof`` as-of read. Unlike
        :func:`~babylon.projection.topology.choropleth_aggregation.
        state_choropleth_cells_from_hex_rows`, this function never reads
        ``row.tick`` and does no cross-hex summation (it is a 1:1 per-hex
        map, not an aggregation), so it places no single-tick constraint on
        ``rows``.
    :param graph: The live post-tick graph, read directly.
    :returns: One cell per input row, sorted by ``h3_index`` ascending
        (Constitution III.13: every projection ends in an explicit order).
    """
    territory_by_county: dict[str, GraphNode | None] = {}
    cells: list[HexHabitabilityCell] = []
    for row in sorted(rows, key=lambda row: row.h3_index):
        county_fips = row.county_fips
        if county_fips not in territory_by_county:
            territory_by_county[county_fips] = _territory_by_county_fips(graph, county_fips)
        territory = territory_by_county[county_fips]
        habitability = territory.attributes.get("habitability") if territory is not None else None
        cells.append(
            HexHabitabilityCell(
                h3_index=row.h3_index,
                county_fips=county_fips,
                habitability=habitability,
            )
        )
    return tuple(cells)
