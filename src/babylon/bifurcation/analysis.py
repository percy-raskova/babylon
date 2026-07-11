"""Full bifurcation analysis orchestrator (US5, Feature 033).

Combines per-axis contradiction analysis, community bridge detection,
legitimation crisis amplification, and topological resilience metrics
into a single BifurcationResult. Uses a weakest-link model: if any
axis is deeply antagonism-dominant, the outcome is "fascist" regardless
of other axes.

The core innovation: solidarity edges are weighted by a nonlinear
sigmoid of community collective_identity, so assimilated solidarity
(the Democratic Party coalition pattern) correctly classifies as
fragile/fascist despite high edge density.

See Also:
    :mod:`babylon.bifurcation.axis`: Per-axis computation.
    :mod:`babylon.bifurcation.bridges`: Bridge detection.
    :mod:`babylon.bifurcation.consciousness`: Consciousness weighting.
    :mod:`babylon.bifurcation.legitimation`: Legitimation amplifier.
    :mod:`babylon.bifurcation.resilience`: Topological resilience.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import xgi  # type: ignore[import-untyped, unused-ignore]

from babylon.bifurcation.axis import compute_axis_tendency, crosses_contradiction_axis
from babylon.bifurcation.bridges import detect_bridges
from babylon.bifurcation.consciousness import consciousness_weighted_solidarity
from babylon.bifurcation.resilience import (
    compute_betti_numbers,
    compute_equivalence_classes,
    compute_purge_resilience,
    find_critical_cutsets,
    find_critical_singletons,
)
from babylon.bifurcation.types import BifurcationResult
from babylon.topology.graph import BabylonUGraph

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonGraph
from babylon.config.defines import BifurcationDefines
from babylon.models.entities.community import (
    MARGINALIZED_COMMUNITIES,
    CommunityState,
)
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType, EdgeType


def _extract_raw_solidarity_subgraph(graph: BabylonGraph) -> BabylonUGraph:
    """Extract undirected solidarity subgraph (all SOLIDARITY edges).

    Args:
        graph: Simulation DiGraph with edge_type attributes.

    Returns:
        Undirected graph with social_class nodes and all SOLIDARITY edges.
    """
    solidarity = BabylonUGraph()

    # Add all social_class nodes
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") == "social_class":
            solidarity.add_node(node_id)

    # Add SOLIDARITY edges
    max_edges = graph.number_of_edges()
    for idx, (src, tgt, edge_data) in enumerate(graph.edges(data=True)):
        if idx >= max_edges:
            break
        edge_type_raw = edge_data.get("edge_type")
        if edge_type_raw is None:
            continue
        if isinstance(edge_type_raw, EdgeType):
            is_solidarity = edge_type_raw == EdgeType.SOLIDARITY
        else:
            is_solidarity = str(edge_type_raw) == EdgeType.SOLIDARITY.value
        if is_solidarity and src in solidarity.nodes and tgt in solidarity.nodes:
            solidarity.add_edge(src, tgt)

    return solidarity


def _extract_filtered_solidarity_subgraph(
    graph: BabylonGraph,
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    defines: BifurcationDefines,
) -> BabylonUGraph:
    """Extract consciousness-filtered solidarity subgraph.

    Only includes SOLIDARITY edges where the consciousness-weighted
    value exceeds the filter threshold.

    Args:
        graph: Simulation DiGraph.
        H: XGI hypergraph for membership lookup.
        community_states: Community consciousness data.
        defines: Filter threshold and sigmoid parameters.

    Returns:
        Undirected graph with only consciousness-significant solidarity edges.
    """
    filtered = BabylonUGraph()

    # Add all social_class nodes
    for node_id, data in graph.nodes(data=True):
        if data.get("_node_type") == "social_class":
            filtered.add_node(node_id)

    # Add edges that pass consciousness filter
    max_edges = graph.number_of_edges()
    for idx, (src, tgt, edge_data) in enumerate(graph.edges(data=True)):
        if idx >= max_edges:
            break
        edge_type_raw = edge_data.get("edge_type")
        if edge_type_raw is None:
            continue
        if isinstance(edge_type_raw, EdgeType):
            is_solidarity = edge_type_raw == EdgeType.SOLIDARITY
        else:
            is_solidarity = str(edge_type_raw) == EdgeType.SOLIDARITY.value

        if not is_solidarity:
            continue
        if src not in filtered.nodes or tgt not in filtered.nodes:
            continue

        ws_result = consciousness_weighted_solidarity(
            source_id=src,
            target_id=tgt,
            graph=graph,
            H=H,
            community_states=community_states,
            defines=defines,
        )
        if ws_result.weight >= defines.consciousness_filter_threshold:
            filtered.add_edge(src, tgt)

    return filtered


def _compute_mean_ci_marginalized(
    community_states: dict[CommunityType, CommunityState],
) -> float:
    """Compute mean collective_identity across marginalized communities.

    Args:
        community_states: Community consciousness data.

    Returns:
        Mean CI for marginalized communities, 0.0 if none present.
    """
    marginalized_cis: list[float] = []
    for comm_type, state in community_states.items():
        if comm_type in MARGINALIZED_COMMUNITIES:
            marginalized_cis.append(float(state.consciousness.collective_identity))

    if not marginalized_cis:
        return 0.0
    return sum(marginalized_cis) / len(marginalized_cis)


def _compute_dominant_tendency_distribution(
    community_states: dict[CommunityType, CommunityState],
) -> dict[str, float]:
    """Compute ConsciousnessTendency distribution across marginalized communities.

    Args:
        community_states: Community consciousness data.

    Returns:
        Dict mapping tendency name to fraction of marginalized communities.
    """
    tendency_counts: Counter[str] = Counter()
    total = 0

    for comm_type, state in community_states.items():
        if comm_type in MARGINALIZED_COMMUNITIES:
            tendency_counts[state.consciousness.dominant_tendency.value] += 1
            total += 1

    if total == 0:
        return {}

    return {k: v / total for k, v in tendency_counts.items()}


def _compute_mean_assimilation_ratio_marginalized(
    community_states: dict[CommunityType, CommunityState],
) -> float:
    """Compute mean assimilation_ratio across marginalized communities.

    Assimilation ratio = f / (l + f): how much of non-revolutionary
    consciousness is fascist. High values indicate fascist-vulnerable
    communities.

    Args:
        community_states: Community consciousness data.

    Returns:
        Mean assimilation_ratio for marginalized communities, 0.0 if none.
    """
    ratios: list[float] = []
    for comm_type, state in community_states.items():
        if comm_type in MARGINALIZED_COMMUNITIES:
            ratios.append(float(state.consciousness.assimilation_ratio))

    if not ratios:
        return 0.0
    return sum(ratios) / len(ratios)


def _compute_edge_counts(
    graph: BabylonGraph,
    agent_memberships: dict[str, set[CommunityType]],
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    contradictions: list[Contradiction],
    defines: BifurcationDefines,
) -> tuple[int, int, float, int]:
    """Count cross-line and within-line solidarity edges, sum weighted cross.

    Args:
        graph: Simulation DiGraph.
        agent_memberships: Agent community memberships.
        H: Hypergraph for consciousness weighting.
        community_states: Community states for consciousness weighting.
        contradictions: List of contradictions to test.
        defines: Bifurcation parameters.

    Returns:
        Tuple of (cross_count, within_count, weighted_cross_total,
        crisis_fragile_count).
    """
    cross_count = 0
    within_count = 0
    weighted_cross_total = 0.0
    crisis_fragile_count = 0

    max_edges = graph.number_of_edges()
    for idx, (src, tgt, edge_data) in enumerate(graph.edges(data=True)):
        if idx >= max_edges:
            break
        edge_type_raw = edge_data.get("edge_type")
        if edge_type_raw is None:
            continue
        if isinstance(edge_type_raw, EdgeType):
            is_solidarity = edge_type_raw == EdgeType.SOLIDARITY
        else:
            is_solidarity = str(edge_type_raw) == EdgeType.SOLIDARITY.value

        if not is_solidarity:
            continue

        # Check if edge crosses any contradiction axis
        crosses_any = False
        for contradiction in contradictions:
            if crosses_contradiction_axis(src, tgt, contradiction, agent_memberships):
                crosses_any = True
                break

        if crosses_any:
            cross_count += 1
            ws_result = consciousness_weighted_solidarity(
                source_id=src,
                target_id=tgt,
                graph=graph,
                H=H,
                community_states=community_states,
                defines=defines,
            )
            weighted_cross_total += ws_result.weight
            if ws_result.crisis_fragile:
                crisis_fragile_count += 1
        else:
            within_count += 1

    return cross_count, within_count, weighted_cross_total, crisis_fragile_count


def _compute_legitimation_index(graph: BabylonGraph) -> float:
    """Extract population-weighted mean legitimation index from territories.

    Args:
        graph: Simulation graph with territory nodes.

    Returns:
        Mean legitimation index in [0.0, 1.0], or 0.5 if no territories.
    """
    total_weighted = 0.0
    total_pop = 0

    for _node_id, data in graph.nodes(data=True):
        if data.get("_node_type") != "territory":
            continue
        legitimation: float = data.get("legitimation_index", 0.5)
        population: int = data.get("population", 1)
        total_weighted += population * legitimation
        total_pop += population

    if total_pop == 0:
        return 0.5
    return total_weighted / total_pop


def _has_cross_axis_antagonism(
    graph: BabylonGraph,
    contradictions: list[Contradiction],
    agent_memberships: dict[str, set[CommunityType]],
) -> bool:
    """Check if any antagonistic edge crosses a contradiction axis.

    Args:
        graph: Simulation DiGraph.
        contradictions: List of contradictions to test.
        agent_memberships: Agent community memberships.

    Returns:
        True if any exploitation/repression/competition edge crosses an axis.
    """
    antagonistic = {EdgeType.EXPLOITATION, EdgeType.REPRESSION, EdgeType.COMPETITION}
    max_edges = graph.number_of_edges()
    for idx, (src, tgt, edge_data) in enumerate(graph.edges(data=True)):
        if idx >= max_edges:
            break
        edge_type_raw = edge_data.get("edge_type")
        if edge_type_raw is None:
            continue
        edge_type = EdgeType(edge_type_raw) if isinstance(edge_type_raw, str) else edge_type_raw
        if edge_type not in antagonistic:
            continue
        for contradiction in contradictions:
            if crosses_contradiction_axis(src, tgt, contradiction, agent_memberships):
                return True
    return False


def _classify_tendency(
    per_axis_tendency: dict[str, float],
    has_any_axis_edges: bool,
    cross_line_count: int,
    weighted_cross: float,
    defines: BifurcationDefines,
) -> str:
    """Classify overall tendency using weakest-link model + assimilation trap.

    Rules:
    - If no axes analyzed or no relevant edges exist → "indeterminate"
    - Assimilation trap: cross-line solidarity edges exist but mean
      consciousness-weighted solidarity per edge < filter threshold → "fascist"
      (high density + low CI = assimilated)
    - If all active axes have tendency_ratio > (1.0 + dead_zone) → "revolutionary"
    - If any active axis has tendency_ratio < (1.0 - dead_zone) → "fascist"
    - Otherwise → "indeterminate"

    Args:
        per_axis_tendency: Axis ID to tendency ratio (active axes only).
        has_any_axis_edges: Whether any axis had solidarity or antagonism edges.
        cross_line_count: Number of raw cross-line solidarity edges.
        weighted_cross: Consciousness-weighted cross-line solidarity sum.
        defines: Contains indeterminate_dead_zone, consciousness_filter_threshold.

    Returns:
        "revolutionary", "fascist", or "indeterminate".
    """
    if not has_any_axis_edges:
        return "indeterminate"

    # No active axes but cross-axis antagonism exists → pure antagonism = fascist
    if not per_axis_tendency:
        return "fascist"

    # Assimilation trap: cross-line edges exist but consciousness weighting
    # collapsed them to near-zero (Democratic Party coalition pattern)
    if cross_line_count > 0:
        mean_weighted = weighted_cross / cross_line_count
        if mean_weighted < defines.consciousness_filter_threshold:
            return "fascist"

    dead_zone = defines.indeterminate_dead_zone
    upper = 1.0 + dead_zone
    lower = 1.0 - dead_zone

    # Weakest-link: if any axis is deeply antagonism-dominant → fascist
    all_above_upper = True
    any_below_lower = False

    for ratio in per_axis_tendency.values():
        if ratio < lower:
            any_below_lower = True
        if ratio <= upper:
            all_above_upper = False

    if any_below_lower:
        return "fascist"
    if all_above_upper:
        return "revolutionary"
    return "indeterminate"


def bifurcation_tendency(
    graph: BabylonGraph,
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    contradictions: list[Contradiction],
    agent_memberships: dict[str, set[CommunityType]],
    defines: BifurcationDefines,
) -> BifurcationResult:
    """Compute full bifurcation analysis — the George Jackson model.

    Combines per-axis contradiction tendency (weakest-link), community
    bridge potential (consciousness-weighted), legitimation crisis
    amplifier, and topological resilience (two-pass Betti numbers).

    The assimilation trap: high cross-line edge density with low CI
    correctly classifies as "fascist" because consciousness weighting
    collapses effective solidarity to near-zero.

    Args:
        graph: Simulation DiGraph with social_class and territory nodes.
        H: XGI hypergraph for community membership lookup.
        community_states: Current community consciousness data.
        contradictions: List of contradictions for this scope.
        agent_memberships: Agent ID to community memberships mapping.
        defines: Configurable parameters for all sub-computations.

    Returns:
        Frozen BifurcationResult with all analysis fields populated.

    See Also:
        :class:`babylon.bifurcation.types.BifurcationResult`: Result type.
        :func:`babylon.bifurcation.axis.compute_axis_tendency`: Per-axis analysis.
    """
    # 1. Per-axis tendency analysis
    per_axis_tendency: dict[str, float] = {}
    active_axis_tendency: dict[str, float] = {}  # Only axes with edges
    total_lateral_count = 0
    total_upward_count = 0
    has_any_axis_edges = False

    for contradiction in contradictions:
        axis_result = compute_axis_tendency(
            graph=graph,
            H=H,
            contradiction=contradiction,
            community_states=community_states,
            agent_memberships=agent_memberships,
            defines=defines,
        )
        per_axis_tendency[contradiction.id] = axis_result.tendency_ratio
        total_lateral_count += axis_result.lateral_edge_count
        total_upward_count += axis_result.upward_edge_count
        axis_edge_total = (
            axis_result.cross_edge_count
            + axis_result.lateral_edge_count
            + axis_result.upward_edge_count
        )
        if axis_edge_total > 0:
            has_any_axis_edges = True
            active_axis_tendency[contradiction.id] = axis_result.tendency_ratio

    # 2. Edge counts and weighted cross-line solidarity
    cross_count, within_count, weighted_cross, crisis_fragile_count = _compute_edge_counts(
        graph, agent_memberships, H, community_states, contradictions, defines
    )

    # Also check for cross-axis antagonistic edges (downward exploitation
    # is not counted in lateral/upward but signals structure on the axis)
    if not has_any_axis_edges and cross_count == 0:
        has_any_axis_edges = _has_cross_axis_antagonism(graph, contradictions, agent_memberships)

    # 3. Community bridge detection
    bridges = detect_bridges(
        H=H,
        community_states=community_states,
        contradictions=contradictions,
        agent_memberships=agent_memberships,
        defines=defines,
    )
    bridge_count = len(bridges)
    bridge_potential = sum(b.weighted_potential for b in bridges)

    # 4. Legitimation index
    legitimation_index = _compute_legitimation_index(graph)

    # 5. Mean CI for marginalized communities
    mean_ci = _compute_mean_ci_marginalized(community_states)

    # 6. Dominant tendency distribution
    tendency_dist = _compute_dominant_tendency_distribution(community_states)

    # 6b. Mean assimilation ratio for marginalized communities (Feature 034)
    mean_assimilation = _compute_mean_assimilation_ratio_marginalized(community_states)

    # 7. Topological resilience — raw solidarity subgraph
    raw_subgraph = _extract_raw_solidarity_subgraph(graph)
    raw_beta_0, raw_beta_1 = compute_betti_numbers(raw_subgraph)

    # 8. Topological resilience — consciousness-filtered subgraph
    filtered_subgraph = _extract_filtered_solidarity_subgraph(graph, H, community_states, defines)
    filtered_beta_0, filtered_beta_1 = compute_betti_numbers(filtered_subgraph)

    # 9. Resilience metrics on filtered subgraph
    resilience = compute_purge_resilience(
        filtered_subgraph, removal_rate=defines.purge_removal_rate, seed=42
    )
    equivalence = compute_equivalence_classes(filtered_subgraph)
    singletons = find_critical_singletons(filtered_subgraph)
    cutsets = find_critical_cutsets(filtered_subgraph)

    # 10. Overall classification (weakest-link + assimilation trap)
    overall_tendency = _classify_tendency(
        active_axis_tendency, has_any_axis_edges, cross_count, weighted_cross, defines
    )

    return BifurcationResult(
        overall_tendency=overall_tendency,  # type: ignore[arg-type]
        per_axis_tendency=per_axis_tendency,
        cross_line_solidarity_count=cross_count,
        within_line_solidarity_count=within_count,
        lateral_antagonism_count=total_lateral_count,
        upward_antagonism_count=total_upward_count,
        consciousness_weighted_cross_solidarity=weighted_cross,
        mean_collective_identity_marginalized=mean_ci,
        dominant_tendency_distribution=tendency_dist,
        community_bridge_count=bridge_count,
        bridge_potential_weighted=bridge_potential,
        legitimation_index=legitimation_index,
        raw_beta_0=raw_beta_0,
        raw_beta_1=raw_beta_1,
        filtered_beta_0=filtered_beta_0,
        filtered_beta_1=filtered_beta_1,
        resilience_under_targeted_purge=resilience,
        equivalence_class_distribution=equivalence,
        critical_singletons=singletons,
        critical_cutsets=cutsets,
        mean_assimilation_ratio_marginalized=mean_assimilation,
        crisis_fragile_edge_count=crisis_fragile_count,
    )


__all__ = [
    "bifurcation_tendency",
]
