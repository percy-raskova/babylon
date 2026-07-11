"""Community bridge detection (US3, Feature 033).

Detects INSTITUTIONAL_EXCLUSION communities that span contradiction
axes -- their members include agents from both hegemonic and
marginalized sides. These bridges create cross-line solidarity
potential weighted by community infrastructure and consciousness.

Bridge potential = infrastructure * sigmoid(collective_identity).
Only INSTITUTIONAL_EXCLUSION communities are candidates because their
membership is orthogonal to the contradiction axis structure (e.g. a
disabled community can include both settlers and New Afrikans).

See Also:
    :class:`babylon.domain.bifurcation.types.BridgeInfo`: Result type.
    :mod:`babylon.models.entities.community`: Category taxonomy.
    :func:`babylon.domain.bifurcation.consciousness.consciousness_sigmoid`: Weighting.
"""

from __future__ import annotations

from typing import Any

import xgi  # type: ignore[import-untyped, unused-ignore]

from babylon.config.defines import BifurcationDefines
from babylon.domain.bifurcation.consciousness import consciousness_sigmoid
from babylon.domain.bifurcation.types import BridgeInfo
from babylon.models.entities.community import (
    COMMUNITY_CATEGORY_MAP,
    CommunityState,
)
from babylon.models.entities.contradiction import Contradiction
from babylon.models.enums import CommunityType, HyperedgeCategory


def _community_spans_axis(
    members: frozenset[Any],
    contradiction: Contradiction,
    agent_memberships: dict[str, set[CommunityType]],
) -> bool:
    """Check if a community's members collectively span a contradiction axis.

    A community spans an axis if among its hyperedge members:
    - At least one member belongs to the contradiction.aspect_a community type
    - At least one member belongs to any of the contradiction.aspect_b community types

    Args:
        members: Set of agent IDs in this community hyperedge.
        contradiction: The contradiction to check against.
        agent_memberships: Mapping of agent ID to their community memberships.

    Returns:
        True if the community spans this axis, False otherwise.
    """
    has_hegemonic = False
    has_marginalized = False
    marginalized_set = frozenset([contradiction.aspect_b])

    for agent_id in members:
        agent_id_str = str(agent_id)
        agent_communities = agent_memberships.get(agent_id_str, set())
        if contradiction.aspect_a in agent_communities:
            has_hegemonic = True
        if agent_communities & marginalized_set:
            has_marginalized = True
        # Early exit once both sides found
        if has_hegemonic and has_marginalized:
            return True

    return False


def detect_bridges(
    H: xgi.Hypergraph,
    community_states: dict[CommunityType, CommunityState],
    contradictions: list[Contradiction],
    agent_memberships: dict[str, set[CommunityType]],
    defines: BifurcationDefines,
) -> list[BridgeInfo]:
    """Detect communities spanning contradiction axes, weighted by consciousness.

    Iterates over all hyperedges in the hypergraph. For each
    INSTITUTIONAL_EXCLUSION community, checks whether its members
    collectively include agents from both the hegemonic and marginalized
    sides of each contradiction axis. If so, computes the bridge
    potential as infrastructure * sigmoid(collective_identity).

    Args:
        H: XGI hypergraph with communities as indexed hyperedges.
        community_states: Current community consciousness and infrastructure.
        contradictions: Contradictions to check spanning against.
        agent_memberships: Agent ID to set of CommunityType memberships.
        defines: Configurable parameters (sigmoid midpoint/steepness).

    Returns:
        List of BridgeInfo for each community that spans at least one axis.
        Empty list if no bridges are found or hypergraph is empty.
    """
    bridges: list[BridgeInfo] = []

    for edge_id in H.edges:
        # Convert edge ID to CommunityType
        try:
            comm_type = CommunityType(edge_id)
        except ValueError:
            continue

        # Only INSTITUTIONAL_EXCLUSION communities qualify as bridges
        category = COMMUNITY_CATEGORY_MAP.get(comm_type)
        if category != HyperedgeCategory.INSTITUTIONAL_EXCLUSION:
            continue

        # Get members of this hyperedge
        members: frozenset[Any] = H.edges.members(edge_id)
        if not members:
            continue

        # Check which axes this community spans
        axes_spanned: list[str] = []
        for contradiction in contradictions:
            if _community_spans_axis(members, contradiction, agent_memberships):
                axes_spanned.append(contradiction.id)

        if not axes_spanned:
            continue

        # Get community state for CI and infrastructure
        state = community_states.get(comm_type)
        if state is None:
            continue

        ci = float(state.consciousness.collective_identity)
        infra = float(state.infrastructure)

        # Compute sigmoid-transformed CI
        sigmoid_ci = consciousness_sigmoid(
            collective_identity=ci,
            midpoint=defines.consciousness_sigmoid_midpoint,
            steepness=defines.consciousness_sigmoid_steepness,
        )

        weighted_potential = infra * sigmoid_ci

        bridge = BridgeInfo(
            community_type=comm_type,
            axes_spanned=axes_spanned,
            collective_identity=ci,
            sigmoid_ci=sigmoid_ci,
            infrastructure=infra,
            weighted_potential=weighted_potential,
            member_count=len(members),
        )
        bridges.append(bridge)

    return bridges


__all__ = [
    "detect_bridges",
]
