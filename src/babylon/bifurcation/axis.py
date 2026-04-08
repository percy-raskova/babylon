"""Per-axis contradiction analysis (US2, Feature 033).

Analyzes solidarity vs antagonism balance along each structural
contradiction axis (colonial, patriarchal). Cross-line solidarity
is consciousness-weighted; lateral antagonism uses raw edge weight.

See Also:
    :class:`babylon.models.enums.ContradictionType`: Axis definitions.
    :mod:`babylon.bifurcation.consciousness`: Consciousness weighting functions.
"""

from __future__ import annotations

from typing import Literal

import networkx as nx
import xgi  # type: ignore[import-untyped]

from babylon.bifurcation.consciousness import consciousness_weighted_solidarity
from babylon.bifurcation.types import AxisTendency
from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import CommunityState
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType, EdgeType

# Antagonistic edge types: value extraction, state violence, market rivalry
_ANTAGONISTIC_EDGE_TYPES: frozenset[EdgeType] = frozenset(
    {EdgeType.EXPLOITATION, EdgeType.REPRESSION, EdgeType.COMPETITION}
)


def _agent_axis_side(
    agent_id: str,
    contradiction: Contradiction,
    agent_memberships: dict[str, set[CommunityType]],
) -> Literal["hegemonic", "marginalized", "none"]:
    """Determine which side of a contradiction axis an agent is on.

    Args:
        agent_id: Agent node ID.
        contradiction: The contradiction to check.
        agent_memberships: Agent ID to community memberships mapping.

    Returns:
        ``"hegemonic"`` if agent has the hegemonic community type,
        ``"marginalized"`` if agent has any of the marginalized community types,
        ``"none"`` if agent is not on this axis.
    """
    communities = agent_memberships.get(agent_id, set())
    if not communities:
        return "none"

    has_hegemonic = contradiction.aspect_a in communities
    marginalized_set = frozenset([contradiction.aspect_b])
    has_marginalized = bool(communities & marginalized_set)

    # Hegemonic takes precedence if agent has both (exclusive axis)
    if has_hegemonic:
        return "hegemonic"
    if has_marginalized:
        return "marginalized"
    return "none"


def crosses_contradiction_axis(
    source_id: str,
    target_id: str,
    contradiction: Contradiction,
    agent_memberships: dict[str, set[CommunityType]],
) -> bool:
    """Check if an edge crosses the given contradiction axis.

    An edge crosses when one endpoint is on the hegemonic side and the
    other is on the marginalized side of the same axis.

    Args:
        source_id: Source agent node ID.
        target_id: Target agent node ID.
        contradiction: The contradiction to check.
        agent_memberships: Agent ID to community memberships mapping.

    Returns:
        True if the edge spans hegemonic and marginalized sides.
    """
    source_side = _agent_axis_side(source_id, contradiction, agent_memberships)
    target_side = _agent_axis_side(target_id, contradiction, agent_memberships)

    if source_side == "none" or target_side == "none":
        return False

    return source_side != target_side


def classify_edge_antagonism(
    source_id: str,
    target_id: str,
    graph: nx.DiGraph,  # type: ignore[type-arg]
    contradiction: Contradiction,
    agent_memberships: dict[str, set[CommunityType]],
) -> Literal["lateral", "upward", "downward", "none"]:
    """Classify the antagonistic direction of an edge along a contradiction axis.

    Only antagonistic edge types (EXPLOITATION, REPRESSION, COMPETITION) are
    classified. SOLIDARITY and other edge types return ``"none"``.

    Args:
        source_id: Source agent node ID.
        target_id: Target agent node ID.
        graph: The simulation DiGraph (for edge attribute access).
        contradiction: The contradiction to classify against.
        agent_memberships: Agent ID to community memberships mapping.

    Returns:
        ``"lateral"`` if both endpoints are on the same side (within-group),
        ``"upward"`` if from marginalized toward hegemonic,
        ``"downward"`` if from hegemonic toward marginalized,
        ``"none"`` if neither endpoint is on this axis or edge is non-antagonistic.
    """
    # Check edge type is antagonistic
    edge_data = graph.edges.get((source_id, target_id), {})
    edge_type_raw = edge_data.get("edge_type")
    if edge_type_raw is None:
        return "none"

    edge_type = EdgeType(edge_type_raw) if isinstance(edge_type_raw, str) else edge_type_raw
    if edge_type not in _ANTAGONISTIC_EDGE_TYPES:
        return "none"

    # Determine sides
    source_side = _agent_axis_side(source_id, contradiction, agent_memberships)
    target_side = _agent_axis_side(target_id, contradiction, agent_memberships)

    # Both must be on the axis
    if source_side == "none" or target_side == "none":
        return "none"

    # Same side = lateral
    if source_side == target_side:
        return "lateral"

    # Cross-axis direction
    if source_side == "hegemonic" and target_side == "marginalized":
        return "downward"
    # source_side == "marginalized" and target_side == "hegemonic"
    return "upward"


def compute_axis_tendency(
    graph: nx.DiGraph,  # type: ignore[type-arg]
    H: xgi.Hypergraph,
    contradiction: Contradiction,
    community_states: dict[CommunityType, CommunityState],
    agent_memberships: dict[str, set[CommunityType]],
    defines: BifurcationDefines,
) -> AxisTendency:
    """Compute solidarity vs antagonism balance along a single contradiction axis.

    For each edge in the graph:
    - SOLIDARITY edges that cross the axis are weighted by
      ``consciousness_weighted_solidarity`` and summed.
    - Antagonistic edges (EXPLOITATION, REPRESSION, COMPETITION) are classified
      by direction and their weights summed for lateral antagonism.

    The tendency ratio = cross_solidarity_weighted / (lateral_antagonism_weighted + epsilon).

    Args:
        graph: The simulation DiGraph with edge attributes.
        H: XGI hypergraph for community membership lookup.
        contradiction: The contradiction to analyze.
        community_states: Current community consciousness data.
        agent_memberships: Agent ID to community memberships mapping.
        defines: Configurable parameters (sigmoid, epsilon).

    Returns:
        AxisTendency with all counts and weighted totals.

    See Also:
        :func:`crosses_contradiction_axis`: Edge crossing detection.
        :func:`classify_edge_antagonism`: Direction classification.
    """
    cross_solidarity_weighted: float = 0.0
    lateral_antagonism_weighted: float = 0.0
    cross_edge_count: int = 0
    lateral_edge_count: int = 0
    upward_edge_count: int = 0

    max_edges = graph.number_of_edges()
    for idx, (src, tgt, edge_data) in enumerate(graph.edges(data=True)):
        if idx >= max_edges:
            break  # Safety bound (should never trigger for finite graphs)

        edge_type_raw = edge_data.get("edge_type")
        if edge_type_raw is None:
            continue

        edge_type = EdgeType(edge_type_raw) if isinstance(edge_type_raw, str) else edge_type_raw

        # SOLIDARITY edges: check for cross-axis solidarity
        if edge_type == EdgeType.SOLIDARITY:
            if crosses_contradiction_axis(src, tgt, contradiction, agent_memberships):
                ws_result = consciousness_weighted_solidarity(
                    source_id=src,
                    target_id=tgt,
                    graph=graph,
                    H=H,
                    community_states=community_states,
                    defines=defines,
                )
                cross_solidarity_weighted += ws_result.weight
                cross_edge_count += 1

        # Antagonistic edges: classify direction
        elif edge_type in _ANTAGONISTIC_EDGE_TYPES:
            direction = classify_edge_antagonism(
                source_id=src,
                target_id=tgt,
                graph=graph,
                contradiction=contradiction,
                agent_memberships=agent_memberships,
            )

            if direction == "lateral":
                weight: float = edge_data.get("weight", 1.0)
                lateral_antagonism_weighted += weight
                lateral_edge_count += 1
            elif direction == "upward":
                upward_edge_count += 1
            # "downward" and "none" do not contribute to lateral antagonism

    tendency_ratio = cross_solidarity_weighted / (
        lateral_antagonism_weighted + defines.axis_tendency_epsilon
    )

    return AxisTendency(
        axis_id=contradiction.id,
        cross_solidarity_weighted=cross_solidarity_weighted,
        lateral_antagonism_weighted=lateral_antagonism_weighted,
        tendency_ratio=tendency_ratio,
        cross_edge_count=cross_edge_count,
        lateral_edge_count=lateral_edge_count,
        upward_edge_count=upward_edge_count,
    )


__all__ = [
    "classify_edge_antagonism",
    "compute_axis_tendency",
    "crosses_contradiction_axis",
]
