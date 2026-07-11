"""Typed graph wrappers for Spec 040 Discipline 5.

Enforces separation between dyadic edges (BabylonGraph) and
hyperedges (XGI Hypergraph). Systems access graph topology through
these typed wrappers, not raw data structures.

DyadicGraph: Wraps BabylonGraph for pairwise (source → target) edges.
CommunityHypergraph: Wraps xgi.Hypergraph for n-ary community membership.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import xgi  # type: ignore[import-untyped, unused-ignore]

from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph


class DyadicGraph:
    """Typed wrapper for BabylonGraph (pairwise edges).

    Provides typed edge operations that enforce EdgeType on all
    edge queries and mutations.

    Attributes:
        raw: The underlying BabylonGraph.
    """

    def __init__(self, graph: BabylonGraph) -> None:
        """Wrap a BabylonGraph.

        Args:
            graph: The directed world graph.
        """
        self._graph = graph

    @property
    def raw(self) -> BabylonGraph:
        """Access the underlying raw graph."""
        return self._graph

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType,
        **attrs: Any,
    ) -> None:
        """Add a typed dyadic edge.

        Args:
            source: Source node ID.
            target: Target node ID.
            edge_type: Type of the edge.
            **attrs: Additional edge attributes.
        """
        self._graph.add_edge(source, target, edge_type=edge_type.value, **attrs)

    def edges_of_type(self, edge_type: EdgeType) -> Iterator[tuple[str, str]]:
        """Iterate edges of a specific type.

        Args:
            edge_type: Filter to this edge type.

        Yields:
            (source, target) tuples for matching edges.
        """
        for source, target, data in self._graph.edges(data=True):
            if data.get("edge_type") == edge_type.value:
                yield (source, target)

    def __len__(self) -> int:
        """Number of nodes in the graph."""
        return len(self._graph)


class CommunityHypergraph:
    """Typed wrapper for XGI Hypergraph (n-ary community membership).

    Provides typed community operations for adding communities,
    querying membership, and computing overlap.
    """

    def __init__(self, hypergraph: xgi.Hypergraph | None = None) -> None:
        """Initialize with an optional existing hypergraph.

        Args:
            hypergraph: Existing XGI Hypergraph, or None for empty.
        """
        self._hypergraph: xgi.Hypergraph = (
            hypergraph if hypergraph is not None else xgi.Hypergraph()  # type: ignore[no-untyped-call, unused-ignore]
        )

    @property
    def raw(self) -> xgi.Hypergraph:
        """Access the underlying raw hypergraph."""
        return self._hypergraph

    def add_community(
        self,
        community_id: str,
        members: list[str],
        **attrs: Any,
    ) -> None:
        """Add a community as a hyperedge.

        Args:
            community_id: Unique community identifier.
            members: List of agent IDs in this community.
            **attrs: Additional community attributes.
        """
        # Ensure all member nodes exist
        for member in members:
            if member not in self._hypergraph.nodes:
                self._hypergraph.add_node(member)  # type: ignore[no-untyped-call, unused-ignore]
        self._hypergraph.add_edge(members, idx=community_id, **attrs)  # type: ignore[no-untyped-call, unused-ignore]

    @property
    def community_ids(self) -> set[Any]:
        """Set of all community IDs (hyperedge IDs)."""
        return set(self._hypergraph.edges)

    def members_of(self, community_id: str) -> list[str]:
        """Get members of a community.

        Args:
            community_id: The community hyperedge ID.

        Returns:
            List of agent IDs in the community.
        """
        if community_id not in self._hypergraph.edges:
            return []
        return list(self._hypergraph.edges.members(community_id))

    def shared_communities(self, agent_a: str, agent_b: str) -> set[Any]:
        """Find communities shared by two agents.

        Args:
            agent_a: First agent ID.
            agent_b: Second agent ID.

        Returns:
            Set of community IDs containing both agents.
        """
        if agent_a not in self._hypergraph.nodes or agent_b not in self._hypergraph.nodes:
            return set()
        memberships_a: set[Any] = self._hypergraph.nodes.memberships(agent_a)
        memberships_b: set[Any] = self._hypergraph.nodes.memberships(agent_b)
        return memberships_a & memberships_b

    def __len__(self) -> int:
        """Number of communities (hyperedges)."""
        return int(self._hypergraph.num_edges)
