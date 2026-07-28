"""Per-county epistemic fog status — the map's fog lens producer.

One verdict per county, rolled up from the two existing, already-tested
primitives (spec-117 §5a's ledger model, Constitution III.11): organizing
reach wins outright (the same precedence rule
:func:`~babylon.projection.fog.filter.apply_fog` enforces per field), and
everything outside reach is judged by
:func:`~babylon.projection.fog.ledger.read_intel`'s aged tier over the
``territory:political`` field group. A county that exists but was never
observed gets a keyed, explicit ``"unknown"`` — never omitted, never a stale
color. Territories without a ``county_fips`` have no county identity and are
never emitted.

Pure function of ``(graph, ledger, tick)`` — the engine is untouched and the
player's knowledge never enters the tick hash (fog is EPISTEMIC, the engine
is MATERIAL). Types against
:class:`~babylon.kernel.graph_protocol.GraphProtocol` only, like its
siblings in this package.
"""

from __future__ import annotations

from babylon.kernel.graph_protocol import GraphProtocol
from babylon.models.enums import NodeType
from babylon.projection.fog.filter import political_field_group
from babylon.projection.fog.ledger import IntelLedger, VisibilityTier, read_intel
from babylon.projection.fog.reach import organizing_reach

__all__ = ["county_fog_status"]

#: Most-informed-wins rank for the multi-territory-county fold: any single
#: territory in reach lights its whole county ``exact``.
_TIER_RANK: dict[VisibilityTier, int] = {"exact": 2, "approximate": 1, "unknown": 0}


def county_fog_status(
    graph: GraphProtocol,
    player_org_id: str | None,
    ledger: IntelLedger,
    tick: int,
    *,
    radius: int,
    staleness_ticks: int,
    unknown_ticks: int,
) -> dict[str, VisibilityTier]:
    """Roll the fog model up to one epistemic tier per county.

    :param graph: Any graph-protocol implementer; read-only.
    :param player_org_id: The session's canonical player org, or ``None``
        (no org — reach is empty and every county is judged by the ledger
        alone, the reach primitive's own sentinel convention).
    :param ledger: The session's intel ledger (event-sourced from
        INVESTIGATE results; an empty ledger is honest — everything outside
        reach is ``"unknown"``).
    :param tick: The current tick intel ages against.
    :param radius: SOLIDARITY-hop radius for
        :func:`~babylon.projection.fog.reach.organizing_reach`
        (``GameDefines.epistemic_horizon.organizing_reach_radius``).
    :param staleness_ticks: Age bound for ``"exact"`` intel
        (``GameDefines.epistemic_horizon.intel_staleness_ticks``).
    :param unknown_ticks: Age bound past which intel is ``"unknown"``
        (``GameDefines.epistemic_horizon.intel_unknown_ticks``).
    :returns: ``county_fips -> tier`` for every county-bearing territory in
        the graph; counties absent from the graph are absent from the dict
        (honest absence), counties present but unobserved are explicit
        ``"unknown"`` entries.
    """
    reach = organizing_reach(graph, player_org_id, radius)
    field_group = political_field_group(NodeType.TERRITORY.value)

    status: dict[str, VisibilityTier] = {}
    for node in graph.query_nodes(node_type=NodeType.TERRITORY.value):
        fips = node.get_attr("county_fips")
        if fips is None:
            continue
        tier: VisibilityTier
        if node.id in reach:
            tier = "exact"
        else:
            tier = read_intel(
                ledger, node.id, field_group, tick, staleness_ticks, unknown_ticks
            ).tier
        if fips not in status or _TIER_RANK[tier] > _TIER_RANK[status[fips]]:
            status[fips] = tier
    return status
