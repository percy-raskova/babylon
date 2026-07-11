"""Hex-county-state diagnostics for TerritorySystem (Spec 062 T053).

Constitution II.6: state is data, engine is transformation. Aggregation
is a *read* operation on the graph — never a write — so this module
provides pure functions that compute county/state/national rollups for
diagnostic display. Primary state remains hex-level (FR-018).

These helpers are the in-memory complement to the Postgres v_*_aggregate
views. The view is authoritative; this module covers the case where the
engine wants to report per-county production rates inside the same tick,
before the envelope commits to Postgres.

See Also:
    :mod:`babylon.persistence.postgres_aggregation`: persisted variant.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from babylon.kernel.system_base import SystemBase

if TYPE_CHECKING:
    from collections.abc import Iterable

    from babylon.kernel.graph_protocol import GraphProtocol


@dataclass(frozen=True)
class HexCountyRollup:
    """Per-county aggregation of hex-level c/v/s/k + substrate stocks."""

    county_fips: str
    c_sum: float
    v_sum: float
    s_sum: float
    k_sum: float
    biocapacity_sum: float
    hex_count: int


def aggregate_hexes_by_county(
    graph: GraphProtocol,
) -> dict[str, HexCountyRollup]:
    """Compute per-county totals from in-memory hex nodes.

    Only nodes with ``_node_type == "hex"`` AND a ``county_fips`` attribute
    are counted. Other node types (external, county, state) are skipped.

    Args:
        graph: World graph with hex nodes carrying c/v/s/k.

    Returns:
        ``{county_fips: HexCountyRollup}`` map. Empty when no hex nodes
        carry county_fips attributes (e.g., a fresh empty graph).
    """
    protocol = SystemBase._wrap_graph(graph)
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "c": 0.0,
            "v": 0.0,
            "s": 0.0,
            "k": 0.0,
            "biocapacity": 0.0,
            "count": 0.0,
        }
    )
    for node in protocol.query_nodes(node_type="hex"):
        attrs = node.attributes
        county_fips = attrs.get("county_fips")
        if not county_fips:
            continue
        t = totals[county_fips]
        t["c"] += float(attrs.get("c", 0.0))
        t["v"] += float(attrs.get("v", 0.0))
        t["s"] += float(attrs.get("s", 0.0))
        t["k"] += float(attrs.get("k", 0.0))
        t["biocapacity"] += float(attrs.get("biocapacity_stock", 0.0))
        t["count"] += 1.0
    return {
        county_fips: HexCountyRollup(
            county_fips=county_fips,
            c_sum=t["c"],
            v_sum=t["v"],
            s_sum=t["s"],
            k_sum=t["k"],
            biocapacity_sum=t["biocapacity"],
            hex_count=int(t["count"]),
        )
        for county_fips, t in totals.items()
    }


def aggregate_counties_by_state(
    county_rollups: Iterable[HexCountyRollup],
    county_to_state: dict[str, str] | None = None,
) -> dict[str, HexCountyRollup]:
    """Aggregate county rollups into state-level rollups.

    Args:
        county_rollups: Iterable of per-county totals.
        county_to_state: Optional ``{county_fips: state_fips}`` map. When
            None, the canonical Census rule ``state_fips = county_fips[:2]``
            applies per FR-023.

    Returns:
        ``{state_fips: HexCountyRollup}`` where ``county_fips`` field
        carries the 2-digit state FIPS (the model is reused; the field is
        polymorphic for diagnostic display).
    """
    by_state: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "c": 0.0,
            "v": 0.0,
            "s": 0.0,
            "k": 0.0,
            "biocapacity": 0.0,
            "count": 0.0,
        }
    )
    for r in county_rollups:
        state_fips = (county_to_state or {}).get(r.county_fips, r.county_fips[:2])
        t = by_state[state_fips]
        t["c"] += r.c_sum
        t["v"] += r.v_sum
        t["s"] += r.s_sum
        t["k"] += r.k_sum
        t["biocapacity"] += r.biocapacity_sum
        t["count"] += r.hex_count
    return {
        state_fips: HexCountyRollup(
            county_fips=state_fips,
            c_sum=t["c"],
            v_sum=t["v"],
            s_sum=t["s"],
            k_sum=t["k"],
            biocapacity_sum=t["biocapacity"],
            hex_count=int(t["count"]),
        )
        for state_fips, t in by_state.items()
    }


__all__ = [
    "HexCountyRollup",
    "aggregate_hexes_by_county",
    "aggregate_counties_by_state",
]
