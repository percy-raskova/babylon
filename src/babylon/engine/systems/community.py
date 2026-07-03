"""Community hypergraph system (Feature 022).

Manages the XGI hypergraph layer for n-ary community membership.
Provides builder, query, and overlap matrix operations used by
the CommunitySystem tick handler.

See Also:
    :mod:`babylon.models.entities.community`: Data models.
    :mod:`babylon.formulas.community`: Community formulas.
    Constitution II.7: Edges vs Hyperedges (NetworkX + XGI).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar

import xgi  # type: ignore[import-untyped, unused-ignore]

from babylon.engine.systems.base import SystemBase
from babylon.models.entities.community import (
    LEGAL_STATUS_MULTIPLIERS,
    ROLE_STRENGTH_WEIGHTS,
    CommunityMembership,
    CommunityState,
)
from babylon.models.entities.consciousness import SUBSTRATE_FLOOR_DEFAULTS, OrgContribution
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType, ConsciousnessTendency, HyperedgeCategory, SocialRole

if TYPE_CHECKING:
    from babylon.engine.graph_protocol import GraphProtocol

# Map SocialRole → ClassPosition name for solidarity matrix lookup (Feature 038)
_ROLE_TO_CLASS_POSITION: dict[str, str] = {
    SocialRole.CORE_BOURGEOISIE: "BOURGEOISIE",
    SocialRole.COMPRADOR_BOURGEOISIE: "BOURGEOISIE",
    SocialRole.PETTY_BOURGEOISIE: "PETIT_BOURGEOISIE",
    SocialRole.LABOR_ARISTOCRACY: "LABOR_ARISTOCRACY",
    SocialRole.PERIPHERY_PROLETARIAT: "PROLETARIAT",
    SocialRole.INTERNAL_PROLETARIAT: "PROLETARIAT",
    SocialRole.CARCERAL_ENFORCER: "PROLETARIAT",
    SocialRole.LUMPENPROLETARIAT: "LUMPENPROLETARIAT",
}

logger = logging.getLogger(__name__)


def build_community_hypergraph(
    memberships: list[CommunityMembership],
    community_states: dict[CommunityType, CommunityState],
) -> xgi.Hypergraph:
    """Build XGI hypergraph where communities are hyperedges.

    Each community with at least one member becomes a hyperedge connecting
    all its member agent IDs. Community state attributes are stored as
    hyperedge attributes.

    Args:
        memberships: All community memberships across all agents.
        community_states: State dict keyed by community type.

    Returns:
        XGI Hypergraph with agents as nodes and communities as hyperedges.
    """
    H = xgi.Hypergraph()  # type: ignore[no-untyped-call, unused-ignore]

    # Collect members per community
    community_members: dict[CommunityType, list[str]] = defaultdict(list)
    for membership in memberships:
        community_members[membership.community_type].append(membership.agent_id)
        # Ensure agent node exists
        if membership.agent_id not in H.nodes:
            H.add_node(membership.agent_id)  # type: ignore[no-untyped-call, unused-ignore]

    # Communities become hyperedges with state attributes
    for comm_type, members in community_members.items():
        if len(members) == 0:
            continue
        state = community_states.get(
            comm_type,
            CommunityState(community_type=comm_type),
        )
        # Use idx= (not id=) per XGI 0.10 API
        H.add_edge(  # type: ignore[no-untyped-call, unused-ignore]
            members,
            idx=comm_type.value,
            heat=float(state.heat),
            cohesion=float(state.cohesion),
            infrastructure=float(state.infrastructure),
            visibility=float(state.visibility),
            legal_status=state.legal_status.value,
            reproduction_cost_modifier=state.reproduction_cost_modifier,
            rent_access_modifier=float(state.rent_access_modifier),
            # Feature 029: consciousness and category attributes
            category=state.category.value,
            consciousness_ci=float(state.consciousness.collective_identity),
            consciousness_tendency=state.consciousness.dominant_tendency.value,
            consciousness_contestation=float(state.consciousness.ideological_contestation),
        )

    return H


def shared_communities(
    H: xgi.Hypergraph,
    agent_a: str,
    agent_b: str,
) -> set[Any]:
    """Return community IDs (hyperedge IDs) shared by both agents.

    Args:
        H: Community hypergraph.
        agent_a: First agent ID.
        agent_b: Second agent ID.

    Returns:
        Set of community type value strings shared by both agents.
    """
    if agent_a not in H.nodes or agent_b not in H.nodes:
        return set()
    memberships_a: set[Any] = H.nodes.memberships(agent_a)
    memberships_b: set[Any] = H.nodes.memberships(agent_b)
    return memberships_a & memberships_b


def communities_spanning_axis(
    H: xgi.Hypergraph,
    contradiction: Contradiction,
) -> list[CommunityType]:
    """Find institutional exclusion communities that bridge a contradiction axis.

    A community spans an axis if it contains members who also belong to
    communities on both the hegemonic and marginalized sides of that axis.

    Args:
        H: Community hypergraph.
        contradiction: The contradiction to check bridging for.

    Returns:
        List of CommunityType values that bridge the axis.
    """
    hegemonic_edge_id = contradiction.aspect_a
    marginalized_edge_ids = [contradiction.aspect_b]

    # Collect agents on hegemonic side
    hegemonic_agents: set[str] = set()
    if hegemonic_edge_id in H.edges:
        hegemonic_agents = set(H.edges.members(hegemonic_edge_id))

    # Collect agents on marginalized side
    marginalized_agents: set[str] = set()
    for m_id in marginalized_edge_ids:
        if m_id in H.edges:
            marginalized_agents.update(H.edges.members(m_id))

    # Check each institutional exclusion community for bridging
    bridges: list[CommunityType] = []
    for edge_id in H.edges:
        # Only check institutional exclusion communities
        attrs = H.edges[edge_id]
        if attrs.get("category") != HyperedgeCategory.INSTITUTIONAL_EXCLUSION.value:
            continue

        members = set(H.edges.members(edge_id))
        has_hegemonic = bool(members & hegemonic_agents)
        has_marginalized = bool(members & marginalized_agents)
        if has_hegemonic and has_marginalized:
            bridges.append(CommunityType(edge_id))

    return bridges


def community_overlap_matrix(
    H: xgi.Hypergraph,
) -> tuple[Any, dict[str, int]]:
    """Compute pairwise community overlap matrix for all agents.

    O[i,j] = number of communities containing both agent_i and agent_j.
    O[i,i] = degree of agent_i (number of communities they belong to).

    Args:
        H: Community hypergraph.

    Returns:
        Tuple of (overlap_matrix as dense ndarray, node_index mapping
        agent_id → matrix row/column index).
    """
    I_matrix, rowdict, _coldict = xgi.incidence_matrix(  # type: ignore[no-untyped-call, unused-ignore]
        H,
        sparse=False,
        index=True,
    )
    # rowdict maps matrix_row_index → node_id
    # Invert to node_id → matrix_row_index
    node_index: dict[str, int] = {node_id: row_idx for row_idx, node_id in rowdict.items()}
    # O = I @ I^T: (n_nodes x n_nodes) co-membership count matrix
    overlap = I_matrix @ I_matrix.T
    return overlap, node_index


def legal_status_escalate(state: CommunityState) -> CommunityState:
    """Escalate legal status by one step (one-way ratchet).

    Args:
        state: Current community state.

    Returns:
        New CommunityState with legal_status advanced one step.
        Returns unchanged if already at CRIMINALIZED.
    """
    from babylon.models.entities.community import LEGAL_STATUS_ORDER

    current_idx = LEGAL_STATUS_ORDER.index(state.legal_status)
    max_idx = len(LEGAL_STATUS_ORDER) - 1
    if current_idx >= max_idx:
        return state
    new_status = LEGAL_STATUS_ORDER[current_idx + 1]
    return state.model_copy(update={"legal_status": new_status})


def designate_community(
    state: CommunityState,
    heat_increase: float = 0.3,
) -> CommunityState:
    """State designates community — escalates legal status and raises heat.

    Args:
        state: Current community state.
        heat_increase: Amount to add to heat.

    Returns:
        New CommunityState with escalated legal status and increased heat.
    """
    escalated = legal_status_escalate(state)
    new_heat = min(1.0, float(escalated.heat) + heat_increase)
    return escalated.model_copy(update={"heat": new_heat})


def infiltrate_community(
    state: CommunityState,
    cohesion_reduction: float = 0.2,
) -> CommunityState:
    """State infiltrates community — reduces cohesion.

    Args:
        state: Current community state.
        cohesion_reduction: Amount to subtract from cohesion.

    Returns:
        New CommunityState with reduced cohesion.
    """
    new_cohesion = max(0.0, float(state.cohesion) - cohesion_reduction)
    return state.model_copy(update={"cohesion": new_cohesion})


def disrupt_infrastructure(
    state: CommunityState,
    infrastructure_reduction: float = 0.4,
) -> CommunityState:
    """State disrupts community infrastructure.

    Args:
        state: Current community state.
        infrastructure_reduction: Amount to subtract from infrastructure.

    Returns:
        New CommunityState with reduced infrastructure.
    """
    new_infra = max(0.0, float(state.infrastructure) - infrastructure_reduction)
    return state.model_copy(update={"infrastructure": new_infra})


def _extract_memberships_from_node(node_data: dict[str, Any]) -> list[CommunityMembership]:
    """Extract CommunityMembership objects from a graph node's attributes."""
    raw = node_data.get("community_memberships", [])
    if not raw:
        return []
    result: list[CommunityMembership] = []
    for item in raw:
        if isinstance(item, CommunityMembership):
            result.append(item)
        elif isinstance(item, dict):
            result.append(CommunityMembership(**item))
    return result


def _get_community_states_from_services(
    services: Any,
) -> dict[CommunityType, CommunityState]:
    """Extract community_states from the services container."""
    hypergraph_config = services.community_hypergraph
    if hypergraph_config is None:
        return {}
    if isinstance(hypergraph_config, dict):
        result: dict[CommunityType, CommunityState] = hypergraph_config.get("community_states", {})
        return result
    return {}


class CommunitySystem(SystemBase):
    """Hypergraph community system (Feature 022).

    Manages alpha-smoothed community state decay, solidarity potential
    computation from community overlap, threat score aggregation, and
    reproduction cost modification. Runs before SolidaritySystem in the
    engine pipeline (position 6).
    """

    name: ClassVar[str] = "community"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol | Any,
        services: Any,
        _context: Any,
    ) -> None:
        """Execute community system for one tick."""
        community_states = _get_community_states_from_services(services)
        if not community_states:
            return

        all_memberships, agent_memberships = _collect_memberships(graph)
        if not all_memberships:
            return

        _compute_consciousness_from_orgs(
            graph,
            agent_memberships,
            community_states,
        )

        hypergraph = build_community_hypergraph(all_memberships, community_states)

        _amplify_solidarity_edges(
            graph,
            hypergraph,
            agent_memberships,
            community_states,
            services,
        )
        _compute_threat_scores(
            graph,
            agent_memberships,
            community_states,
            services,
        )
        _compute_cost_modifiers(
            graph,
            agent_memberships,
            community_states,
        )
        _apply_community_decay(
            community_states,
            agent_memberships,
            services,
        )


def _compute_consciousness_from_orgs(
    graph: Any,
    agent_memberships: dict[str, list[CommunityMembership]],
    community_states: dict[CommunityType, CommunityState],
) -> None:
    """Compute ternary consciousness for each community from org landscape.

    For each community:
    1. Find organizations whose members overlap with the community.
    2. Compute each org's density within the community.
    3. Call compute_ternary_consciousness() to derive (r, l, f).
    4. Update CommunityState with new consciousness.

    Modifies community_states dict in place.
    """
    from babylon.formulas.consciousness import compute_ternary_consciousness
    from babylon.models.enums import EdgeType

    # Build community → member agent set
    community_agents: dict[CommunityType, set[str]] = {}
    for agent_id, memberships in agent_memberships.items():
        for mem in memberships:
            if mem.community_type not in community_agents:
                community_agents[mem.community_type] = set()
            community_agents[mem.community_type].add(agent_id)

    # Collect org data from graph
    org_data: list[tuple[str, set[str], ConsciousnessTendency, float, float]] = []
    max_orgs = 500
    org_count = 0
    for node in graph.query_nodes(node_type="organization"):
        attrs = node.attributes
        tendency_raw = attrs.get("consciousness_tendency")
        if tendency_raw is None:
            continue
        if isinstance(tendency_raw, str):
            tendency = ConsciousnessTendency(tendency_raw)
        else:
            tendency = tendency_raw

        cadre = float(attrs.get("cadre_level", 0.0))
        cohesion = float(attrs.get("cohesion", 0.0))

        # Find org's member agents via MEMBERSHIP edges
        member_agents: set[str] = set()
        for edge in graph.query_edges(source_id=node.id, edge_type=EdgeType.MEMBERSHIP):
            member_agents.add(edge.target_id)

        if member_agents:
            org_data.append((node.id, member_agents, tendency, cadre, cohesion))

        org_count += 1
        if org_count >= max_orgs:
            break

    # Compute consciousness for each community
    for comm_type, state in list(community_states.items()):
        agents_in_comm = community_agents.get(comm_type, set())
        if not agents_in_comm:
            continue

        comm_size = len(agents_in_comm)
        org_landscape: list[OrgContribution] = []

        for _org_id, org_members, tendency, cadre, cohesion in org_data:
            overlap = len(org_members & agents_in_comm)
            if overlap == 0:
                continue
            density = overlap / comm_size
            org_landscape.append(
                OrgContribution(
                    tendency=tendency,
                    membership_density=density,
                    cadre_level=cadre,
                    cohesion=cohesion,
                ),
            )

        # Only recompute if we have org data; otherwise keep existing
        if org_landscape:
            floor_entry = SUBSTRATE_FLOOR_DEFAULTS.get(comm_type)
            floor_value = float(floor_entry.floor_value) if floor_entry else 0.0
            new_consciousness = compute_ternary_consciousness(
                community_type=comm_type,
                org_landscape=org_landscape,
                substrate_floor=floor_value,
            )
            community_states[comm_type] = state.model_copy(
                update={"consciousness": new_consciousness},
            )


def _collect_memberships(
    graph: Any,
) -> tuple[list[CommunityMembership], dict[str, list[CommunityMembership]]]:
    """Collect all community memberships from active graph nodes."""
    all_memberships: list[CommunityMembership] = []
    agent_memberships: dict[str, list[CommunityMembership]] = {}

    for node in graph.query_nodes(node_type="social_class"):
        if not node.attributes.get("active", True):
            continue
        memberships = _extract_memberships_from_node(node.attributes)
        agent_memberships[node.id] = memberships
        all_memberships.extend(memberships)

    return all_memberships, agent_memberships


def _build_shared_data(
    comm_ids: set[Any],
    src_memberships: list[CommunityMembership],
    tgt_memberships: list[CommunityMembership],
    community_states: dict[CommunityType, CommunityState],
) -> list[tuple[float, float, float, float]]:
    """Build (infrastructure, cohesion, strength_a, strength_b) tuples for shared communities."""
    shared_data: list[tuple[float, float, float, float]] = []
    for comm_id in comm_ids:
        comm_type = CommunityType(comm_id)
        state = community_states.get(comm_type)
        if state is None:
            continue
        str_a = next(
            (float(m.strength) for m in src_memberships if m.community_type == comm_type),
            0.0,
        )
        str_b = next(
            (float(m.strength) for m in tgt_memberships if m.community_type == comm_type),
            0.0,
        )
        shared_data.append((float(state.infrastructure), float(state.cohesion), str_a, str_b))
    return shared_data


def _get_class_position_name(graph: Any, node_id: str) -> str:
    """Get ClassPosition name for an agent from its SocialRole.

    Maps SocialRole (8 roles) to ClassPosition (5 classes) for
    solidarity matrix lookup. Falls back to "PROLETARIAT" if unknown.

    Args:
        graph: Graph protocol instance.
        node_id: Agent node ID.

    Returns:
        ClassPosition name string (e.g. "PROLETARIAT").
    """
    node = graph.get_node(node_id)
    if node is None:
        return "PROLETARIAT"
    role = node.attributes.get("role", "")
    return _ROLE_TO_CLASS_POSITION.get(str(role), "PROLETARIAT")


def _amplify_solidarity_edges(
    graph: Any,
    hypergraph: Any,
    agent_memberships: dict[str, list[CommunityMembership]],
    community_states: dict[CommunityType, CommunityState],
    services: Any,
) -> None:
    """Amplify solidarity_strength on SOLIDARITY edges via community overlap.

    Feature 038: Uses class-pair solidarity matrix from ClassSystemDefines
    to determine base_solidarity for solidarity potential computation.
    The matrix replaces the flat constant from Feature 022.
    """
    from babylon.models.enums import EdgeType

    calculate_amplification = services.formulas.get("solidarity_amplification")

    # Feature 038: Get class-pair solidarity matrix from defines
    class_system_defines = services.defines.class_system

    for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
        src_mem = agent_memberships.get(edge.source_id, [])
        tgt_mem = agent_memberships.get(edge.target_id, [])
        if not src_mem or not tgt_mem:
            continue

        shared = shared_communities(hypergraph, edge.source_id, edge.target_id)
        if not shared:
            continue

        # Feature 038: Use class-pair matrix for base solidarity
        src_class = _get_class_position_name(graph, edge.source_id)
        tgt_class = _get_class_position_name(graph, edge.target_id)
        class_pair_solidarity = class_system_defines.get_base_solidarity(src_class, tgt_class)

        shared_data = _build_shared_data(shared, src_mem, tgt_mem, community_states)
        # Use class-pair base solidarity instead of flat edge strength
        base_strength = edge.attributes.get("solidarity_strength", class_pair_solidarity)
        amplified = calculate_amplification(
            base_strength=base_strength,
            shared_communities=shared_data,
        )
        # Store class-pair solidarity on edge for downstream systems
        graph.update_edge(
            edge.source_id,
            edge.target_id,
            EdgeType.SOLIDARITY,
            solidarity_strength=amplified,
            class_pair_solidarity=class_pair_solidarity,
        )


def _compute_threat_scores(
    graph: Any,
    agent_memberships: dict[str, list[CommunityMembership]],
    community_states: dict[CommunityType, CommunityState],
    services: Any,
) -> None:
    """Compute per-agent threat scores and write to graph nodes."""
    calculate_threat = services.formulas.get("threat_score")

    for node_id, memberships in agent_memberships.items():
        if not memberships:
            graph.update_node(node_id, threat_score=0.0)
            continue

        threat_tuples: list[tuple[float, float, float, float]] = []
        for mem in memberships:
            comm_state = community_states.get(mem.community_type)
            if comm_state is None:
                continue
            threat_tuples.append(
                (
                    float(comm_state.heat),
                    mem.effective_visibility,
                    ROLE_STRENGTH_WEIGHTS.get(mem.role, 0.4),
                    LEGAL_STATUS_MULTIPLIERS.get(comm_state.legal_status, 0.1),
                )
            )

        score = calculate_threat(memberships=threat_tuples)
        graph.update_node(node_id, threat_score=score)


def _compute_cost_modifiers(
    graph: Any,
    agent_memberships: dict[str, list[CommunityMembership]],
    community_states: dict[CommunityType, CommunityState],
) -> None:
    """Compute per-agent reproduction cost modifiers and write to graph nodes."""
    from babylon.formulas.community import compute_community_cost_modifier

    for node_id, memberships in agent_memberships.items():
        modifier = compute_community_cost_modifier(memberships, community_states)
        graph.update_node(node_id, community_cost_modifier=modifier)


def _apply_community_decay(
    community_states: dict[CommunityType, CommunityState],
    agent_memberships: dict[str, list[CommunityMembership]],
    services: Any,
) -> None:
    """Apply alpha-smoothing decay to community state (heat, cohesion, infrastructure).

    Modifies community_states dict in place with new frozen CommunityState objects.
    Infrastructure decay uses CORE_ORGANIZER count for maintenance factor.
    """
    from babylon.formulas.community import calculate_infrastructure_decay
    from babylon.models.enums import MembershipRole

    defines = services.defines.community

    # Count CORE_ORGANIZERs per community
    organizer_counts: dict[CommunityType, int] = {}
    for memberships in agent_memberships.values():
        for mem in memberships:
            if mem.role == MembershipRole.CORE_ORGANIZER:
                organizer_counts[mem.community_type] = (
                    organizer_counts.get(mem.community_type, 0) + 1
                )

    for comm_type, state in list(community_states.items()):
        # Heat decays toward 0
        new_heat = float(state.heat) * (1.0 - defines.heat_decay_alpha)

        # Cohesion decays toward 0
        new_cohesion = float(state.cohesion) * (1.0 - defines.cohesion_decay_alpha)

        # Infrastructure decays with CORE_ORGANIZER maintenance
        core_count = organizer_counts.get(comm_type, 0)
        new_infra = calculate_infrastructure_decay(
            float(state.infrastructure),
            defines.infrastructure_decay_alpha,
            core_count,
            defines.core_organizer_maintenance_factor,
        )

        # Education pressure decays (Spec 043 — consciousness value integration)
        edu_decay = services.defines.consciousness.education_pressure_decay
        new_edu_pressure = float(state.education_pressure) * (1.0 - edu_decay)

        community_states[comm_type] = state.model_copy(
            update={
                "heat": max(0.0, new_heat),
                "cohesion": max(0.0, new_cohesion),
                "infrastructure": new_infra,
                "education_pressure": max(0.0, new_edu_pressure),
            },
        )
