"""Hex-to-graph bridge: R7 economic substrate → R6 territory graph nodes.

Feature: hex-substrate-graph-bridge

Maps HexGrid R7 economic state to R6 territory nodes in the GraphProtocol
topology, enabling organizational dynamics and player verbs to consume
spatialized economic metrics.

Data flow::

    R8 (geographic truth)  →  immutable reference
        ↓ 7:1 aggregate
    R7 (economic substrate) →  tick-level Marxian decomposition
        ↓ 7:1 aggregate
    R6 (graph territory)   →  what the player sees

Attribute prefix: ``hex_`` to coexist with existing ``tick_`` attributes
from :mod:`babylon.economics.tick.graph_bridge`.

See Also:
    :mod:`babylon.economics.substrate.aggregation`: Aggregator methods.
    :mod:`babylon.economics.tick.graph_bridge`: County-level bridge.
    :mod:`babylon.engine.graph_protocol`: GraphProtocol interface.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.infrastructure.types import TerrainClassification

from babylon.economics.substrate.aggregation import DefaultResolutionAggregator
from babylon.economics.substrate.types import HexGrid

logger = logging.getLogger(__name__)

# Graph attribute key for hex substrate metadata
HEX_SUBSTRATE_KEY: str = "hex_substrate"


# =============================================================================
# R6 Territory State
# =============================================================================


class R6TerritoryState(BaseModel):
    """Aggregated economic state at H3 resolution 6 for a territory node.

    Produced by aggregating R7 hex-level data via the resolution hierarchy.
    Represents the "view" that the graph topology and player see.

    Args:
        h3_index: H3 R6 cell ID (serves as territory node ID).
        county_fips: Majority county FIPS code among R7 children.
        total_capital: c + v + s summed from R7 children.
        constant_capital: Summed constant capital (c) from R7 children.
        variable_capital: Summed variable capital (v) from R7 children.
        surplus_value: Summed surplus value (s) from R7 children.
        employment: Summed employment from R7 children.
        profit_rate: Capital-weighted: Σs / Σ(c+v).
        exploitation_rate: Capital-weighted: Σs / Σv.
        organic_composition: Capital-weighted: Σc / Σv.
        dept_shares: Employment-weighted department shares (I, IIa, IIb, III).
        r7_child_count: Number of R7 hexes in this R6 parent.
        terrain_water_fraction: Water coverage fraction from R8→R7→R6 (optional).
        utility_coverage: Utility name → coverage fraction (optional).
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 R6 cell ID")
    county_fips: str = Field(description="Majority county FIPS code")
    total_capital: float = Field(description="c + v + s summed from R7 children")
    constant_capital: float = Field(ge=0.0, description="Summed constant capital")
    variable_capital: float = Field(ge=0.0, description="Summed variable capital")
    surplus_value: float = Field(ge=0.0, description="Summed surplus value")
    employment: float = Field(ge=0.0, description="Summed employment")
    profit_rate: float = Field(description="Σs / Σ(c+v)")
    exploitation_rate: float = Field(description="Σs / Σv")
    organic_composition: float = Field(description="Σc / Σv")
    dept_shares: tuple[float, float, float, float] = Field(
        description="Employment-weighted (I, IIa, IIb, III)",
    )
    r7_child_count: int = Field(ge=0, description="Number of R7 children")
    terrain_water_fraction: float | None = Field(
        default=None,
        description="Water coverage fraction from R8→R7→R6",
    )
    utility_coverage: dict[str, float] | None = Field(
        default=None,
        description="Utility name → coverage fraction",
    )


# =============================================================================
# R7 → R6 Aggregation
# =============================================================================


def aggregate_r7_to_r6(
    grid: HexGrid,
    *,
    r7_terrain: dict[str, TerrainClassification] | None = None,
    r7_utility_coverage: dict[str, dict[str, float]] | None = None,
) -> dict[str, R6TerritoryState]:
    """Aggregate R7 hex economic state to R6 territory states.

    Uses the res6_children mapping in HexGrid to group R7 hexes
    and compute all R6-level economic fields.

    Args:
        grid: Source HexGrid at resolution 7.
        r7_terrain: Optional R7 terrain classifications (from R8→R7 aggregation).
        r7_utility_coverage: Optional R7 utility coverage fractions.

    Returns:
        Dict mapping R6 h3_index to R6TerritoryState.

    Example:
        >>> r6_states = aggregate_r7_to_r6(hex_grid)
        >>> len(r6_states) < len(hex_grid.hexes)
        True
    """
    aggregator = DefaultResolutionAggregator()

    # Core economic aggregations
    components = aggregator.compute_component_capitals(grid, target_resolution=6)
    profit_rates = aggregator.compute_weighted_profit_rate(grid, target_resolution=6)
    expl_rates = aggregator.compute_weighted_exploitation_rate(grid, target_resolution=6)
    occ_rates = aggregator.compute_weighted_organic_composition(grid, target_resolution=6)
    employment = aggregator.compute_employment(grid, target_resolution=6)
    dept_shares = aggregator.compute_dept_share_weighted(grid, target_resolution=6)

    result: dict[str, R6TerritoryState] = {}

    for r6_id in components:
        c, v, s = components[r6_id]
        child_ids = grid.res6_children.get(r6_id, frozenset())

        # Determine majority county FIPS
        county_fips = _majority_county(grid, child_ids)

        # Optional terrain forwarding: average water fraction of R7 children
        terrain_wf: float | None = None
        if r7_terrain is not None:
            water_count = 0
            total_with_terrain = 0
            for cid in child_ids:
                if cid in r7_terrain:
                    total_with_terrain += 1
                    if r7_terrain[cid].terrain_type == "WATER":
                        water_count += 1
            if total_with_terrain > 0:
                terrain_wf = water_count / total_with_terrain

        # Optional utility coverage forwarding: average across R7 children
        util_cov: dict[str, float] | None = None
        if r7_utility_coverage is not None:
            util_accum: dict[str, float] = {}
            util_count: dict[str, int] = {}
            for cid in child_ids:
                if cid in r7_utility_coverage:
                    for util_name, frac in r7_utility_coverage[cid].items():
                        util_accum[util_name] = util_accum.get(util_name, 0.0) + frac
                        util_count[util_name] = util_count.get(util_name, 0) + 1
            if util_accum:
                util_cov = {name: util_accum[name] / util_count[name] for name in util_accum}

        result[r6_id] = R6TerritoryState(
            h3_index=r6_id,
            county_fips=county_fips,
            total_capital=c + v + s,
            constant_capital=c,
            variable_capital=v,
            surplus_value=s,
            employment=employment.get(r6_id, 0.0),
            profit_rate=profit_rates.get(r6_id, 0.0),
            exploitation_rate=expl_rates.get(r6_id, 0.0),
            organic_composition=occ_rates.get(r6_id, 0.0),
            dept_shares=dept_shares.get(r6_id, (0.25, 0.25, 0.25, 0.25)),
            r7_child_count=len(child_ids),
            terrain_water_fraction=terrain_wf,
            utility_coverage=util_cov,
        )

    logger.info(
        "Aggregated %d R7 hexes to %d R6 territory states",
        len(grid.hexes),
        len(result),
    )

    return result


def _majority_county(grid: HexGrid, child_ids: frozenset[str]) -> str:
    """Determine the majority county FIPS among R7 children.

    Args:
        grid: HexGrid with hex economic states.
        child_ids: Set of R7 hex IDs belonging to one R6 parent.

    Returns:
        The county FIPS that occurs most often, or "00000" if no children.
    """
    if not child_ids:
        return "00000"

    county_counter: Counter[str] = Counter()
    for cid in child_ids:
        if cid in grid.hexes:
            county_counter[grid.hexes[cid].county_fips] += 1

    if not county_counter:
        return "00000"

    return county_counter.most_common(1)[0][0]


# =============================================================================
# Graph I/O
# =============================================================================


def write_hex_state_to_graph(
    graph: GraphProtocol,
    r6_states: dict[str, R6TerritoryState],
) -> None:
    """Write R6 territory states to graph territory nodes.

    For each R6 state, writes aggregated economic metrics to the
    corresponding Territory node using ``graph.update_node()``.
    Attributes use the ``hex_`` prefix to coexist with ``tick_`` attributes.

    Only writes to existing territory nodes; never creates new ones.

    Args:
        graph: Mutable GraphProtocol instance.
        r6_states: Dict of R6 h3_index → R6TerritoryState.
    """
    written = 0
    for r6_id, state in r6_states.items():
        node = graph.get_node(r6_id)
        if node is None:
            continue
        if node.node_type != "territory":
            continue

        attrs: dict[str, Any] = {
            "hex_total_capital": state.total_capital,
            "hex_constant_capital": state.constant_capital,
            "hex_variable_capital": state.variable_capital,
            "hex_surplus_value": state.surplus_value,
            "hex_employment": state.employment,
            "hex_profit_rate": state.profit_rate,
            "hex_exploitation_rate": state.exploitation_rate,
            "hex_organic_composition": state.organic_composition,
            "hex_dept_shares": state.dept_shares,
            "hex_r7_child_count": state.r7_child_count,
            "hex_county_fips": state.county_fips,
        }

        if state.terrain_water_fraction is not None:
            attrs["hex_water_fraction"] = state.terrain_water_fraction

        if state.utility_coverage is not None:
            for util_name, frac in state.utility_coverage.items():
                attrs[f"hex_utility_{util_name}"] = frac

        graph.update_node(r6_id, **attrs)
        written += 1

    logger.info(
        "Wrote hex state to %d/%d territory nodes",
        written,
        len(r6_states),
    )


def read_hex_state_from_graph(
    graph: GraphProtocol,
) -> dict[str, R6TerritoryState]:
    """Read R6 territory states from graph territory nodes.

    Inverse of ``write_hex_state_to_graph()``. Reads ``hex_``-prefixed
    attributes from territory nodes and reconstructs R6TerritoryState.

    Args:
        graph: GraphProtocol instance to read from.

    Returns:
        Dict of R6 h3_index → R6TerritoryState for nodes with hex_ data.
    """
    result: dict[str, R6TerritoryState] = {}

    for node in graph.query_nodes(node_type="territory"):
        attrs = node.attributes
        if "hex_total_capital" not in attrs:
            continue

        r6_id = str(node.id)

        # Reconstruct utility coverage from hex_utility_* attributes
        util_cov: dict[str, float] = {}
        for key, val in attrs.items():
            if key.startswith("hex_utility_") and isinstance(val, (int, float)):
                util_name = key[len("hex_utility_") :]
                util_cov[util_name] = float(val)

        result[r6_id] = R6TerritoryState(
            h3_index=r6_id,
            county_fips=attrs.get("hex_county_fips", "00000"),
            total_capital=attrs["hex_total_capital"],
            constant_capital=attrs.get("hex_constant_capital", 0.0),
            variable_capital=attrs.get("hex_variable_capital", 0.0),
            surplus_value=attrs.get("hex_surplus_value", 0.0),
            employment=attrs.get("hex_employment", 0.0),
            profit_rate=attrs.get("hex_profit_rate", 0.0),
            exploitation_rate=attrs.get("hex_exploitation_rate", 0.0),
            organic_composition=attrs.get("hex_organic_composition", 0.0),
            dept_shares=attrs.get("hex_dept_shares", (0.25, 0.25, 0.25, 0.25)),
            r7_child_count=attrs.get("hex_r7_child_count", 0),
            terrain_water_fraction=attrs.get("hex_water_fraction"),
            utility_coverage=util_cov if util_cov else None,
        )

    return result


# =============================================================================
# Feedback stub hooks (Phase 2: graph → economics)
# =============================================================================


@runtime_checkable
class GraphFeedback(Protocol):
    """Protocol for reading organizational pressure from graph back to economics.

    Stub for Phase 2 integration. When organizations act on territory nodes
    (via verbs like ORGANIZE, REPRESS, INVEST), they create pressure signals
    that the economic engine should consume on the next tick.

    Example:
        >>> class MyFeedback:
        ...     def read_organizational_pressure(
        ...         self, graph: GraphProtocol,
        ...     ) -> dict[str, float]:
        ...         return {}
    """

    def read_organizational_pressure(
        self,
        graph: GraphProtocol,
    ) -> dict[str, float]:
        """Read organizational pressure signals from territory nodes.

        Args:
            graph: GraphProtocol instance to read from.

        Returns:
            Dict mapping R6 territory ID to pressure magnitude.
            Positive = revolutionary pressure, negative = repressive.
        """
        ...


def read_organizational_pressure(
    graph: GraphProtocol,  # noqa: ARG001 — stub for Phase 2
) -> dict[str, float]:
    """Stub: Read organizational pressure from graph territory nodes.

    Phase 2 implementation will read SOLIDARITY edge weights, community
    threat scores, and organizational verb outcomes to produce a pressure
    signal for each territory.

    Args:
        graph: GraphProtocol instance.

    Returns:
        Empty dict (stub — no feedback path implemented yet).
    """
    # TODO(Phase 2): Iterate territory nodes, compute pressure from:
    #   - Incoming SOLIDARITY edge weights
    #   - Community threat scores (from CommunitySystem)
    #   - Recent verb outcomes (ORGANIZE, REPRESS, INVEST)
    return {}


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "GraphFeedback",
    "HEX_SUBSTRATE_KEY",
    "R6TerritoryState",
    "aggregate_r7_to_r6",
    "read_hex_state_from_graph",
    "read_organizational_pressure",
    "write_hex_state_to_graph",
]
