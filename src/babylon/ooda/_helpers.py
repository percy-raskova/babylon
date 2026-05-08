"""Shared helpers for OODA action evaluation (Spec 058 / FR-003).

This module is the canonical home for helpers that need to be shared
between :mod:`babylon.ooda.action_costs` and
:mod:`babylon.ooda.action_effects`. Per Spec 058 User Story 5,
``_compute_membership_overlap`` was previously duplicated in both action
modules (flagged by the file-analyzer in the project knowledge graph as a
``duplication`` instance); the canonical implementation now lives here.

The version below is extracted verbatim from
``babylon.ooda.action_effects.py`` (the richer of the two pre-Bundle-1
duplicates) — it includes the cross-reference fallback that scans graph
nodes for ``community_id`` membership when the community node lacks a
populated ``member_node_ids`` attribute. The historical
``babylon.ooda.action_costs`` copy lacked this fallback; consolidating
to the richer version is intentional per Spec 058 acceptance scenario 1
("the ``_helpers`` version is the more complete implementation, retaining
the safer-fallback ``community_id`` cross-reference logic from
``action_effects.py``").

See Also:
    :mod:`babylon.ooda.action_costs`
    :mod:`babylon.ooda.action_effects`
    ``specs/058-adr-bundle-1-pre-spec-057/spec.md`` — FR-003 / SC-003
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.models.enums import EdgeType

if TYPE_CHECKING:
    import networkx as nx


__all__ = ["_compute_membership_overlap"]


def _compute_membership_overlap(
    org_id: str,
    community_id: str,
    graph: nx.DiGraph[str],
) -> float:
    """Compute membership overlap between an org and a target community.

    Args:
        org_id: Organization node ID.
        community_id: Community node ID.
        graph: World graph.

    Returns:
        Overlap ratio in ``[0, 1]``: the fraction of community members
        that are also org members. Returns ``0.0`` when either side has
        no members.
    """
    # Get org member IDs via MEMBERSHIP edges
    org_members: set[str] = set()
    for _, target, data in graph.out_edges(org_id, data=True):
        edge_type = data.get("edge_type", "")
        if edge_type == EdgeType.MEMBERSHIP.value or edge_type == EdgeType.MEMBERSHIP:
            org_members.add(target)

    if not org_members:
        return 0.0

    # Get community member IDs
    community_data = graph.nodes.get(community_id, {})
    community_member_ids: list[str] = community_data.get("member_node_ids", [])

    # Also find nodes that reference this community (cross-reference fallback)
    if not community_member_ids:
        community_members: set[str] = set()
        max_nodes = 1000
        count = 0
        for node_id, node_data in graph.nodes(data=True):
            if node_data.get("community_id") == community_id:
                community_members.add(node_id)
            count += 1  # noqa: SIM113 — enumerate breaks mypy with NodeView unpacking
            if count >= max_nodes:
                break
    else:
        community_members = set(community_member_ids)

    if not community_members:
        return 0.0

    overlap_count = len(org_members & community_members)
    return overlap_count / len(community_members)
