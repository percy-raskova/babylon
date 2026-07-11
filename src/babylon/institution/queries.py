"""Graph queries for institution entities (Feature 040).

Provides pure-function queries against the GraphProtocol for
institution-level topology questions (community embeddedness,
territory overlap).

See Also:
    ``specs/040-institution-base-model/spec.md``: FR-013, FR-014.
"""

from __future__ import annotations

from babylon.kernel.graph_protocol import GraphProtocol
from babylon.models.entities.institution import Institution


def community_embeddedness(
    institution: Institution,
    graph: GraphProtocol,
) -> dict[str, float]:
    """Compute institution's embeddedness in community hyperedges.

    For each territory the institution occupies, find community nodes
    reachable via MEMBERSHIP edges and compute overlap scores per
    CommunityType.

    Args:
        institution: The institution to query.
        graph: The simulation graph (GraphProtocol interface).

    Returns:
        Dict mapping CommunityType string to embeddedness score [0, 1].
        Empty dict if institution has no territory presence.
    """
    if not institution.territory_ids:
        return {}

    territory_set = set(institution.territory_ids)

    # Collect community types present in institution territories
    community_counts: dict[str, int] = {}
    community_in_territory: dict[str, int] = {}

    for node in graph.query_nodes(node_type="community"):
        community_type = node.get_attr("community_type", "")
        if not community_type:
            continue

        community_type_str = str(community_type)
        community_counts[community_type_str] = community_counts.get(community_type_str, 0) + 1

        # Check if this community node has MEMBERSHIP edges to institution territories
        node_territory = node.get_attr("territory_id", "")
        if node_territory and str(node_territory) in territory_set:
            community_in_territory[community_type_str] = (
                community_in_territory.get(community_type_str, 0) + 1
            )

    # Compute per-type embeddedness as ratio of territory-linked to total
    result: dict[str, float] = {}
    for ctype, total in community_counts.items():
        if total > 0:
            overlap = community_in_territory.get(ctype, 0)
            score = overlap / total
            result[ctype] = max(0.0, min(1.0, score))

    return result
