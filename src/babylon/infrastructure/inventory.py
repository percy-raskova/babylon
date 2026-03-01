"""Infrastructure inventory management (Feature 036, US2/US3).

Manages infrastructure links on H3 mesh edges, junction state at
vertices, and nonlocal edges. All edge keys are canonically ordered
via ``tuple(sorted([source, target]))``.

See Also:
    :mod:`babylon.infrastructure.protocols`: InfrastructureInventory.
    ``specs/036-infrastructure-topology/spec.md``: FR-009 through FR-018.
"""

from __future__ import annotations

from babylon.infrastructure.types import (
    InfrastructureLinkState,
    JunctionState,
    NonlocalEdgeState,
    VertexState,
)


class DefaultInfrastructureInventory:
    """Manages infrastructure links, vertices, and nonlocal edges.

    Internal storage uses canonical edge ordering: keys are always
    ``tuple(sorted([source_h3, target_h3]))`` to avoid A→B vs B→A
    duplication.

    See Also:
        :mod:`babylon.infrastructure.protocols`: InfrastructureInventory.
    """

    def __init__(self) -> None:
        self._edge_links: dict[tuple[str, str], list[InfrastructureLinkState]] = {}
        self._link_index: dict[str, tuple[str, str]] = {}  # link_id → edge key
        self._vertices: dict[str, VertexState] = {}
        self._nonlocal_edges: list[NonlocalEdgeState] = []

    @staticmethod
    def _canonical_key(source_h3: str, target_h3: str) -> tuple[str, str]:
        """Canonical edge key: lexicographically sorted pair."""
        a, b = sorted([source_h3, target_h3])
        return (a, b)

    def get_edge_links(
        self,
        source_h3: str,
        target_h3: str,
    ) -> list[InfrastructureLinkState]:
        """Get all infrastructure links on an edge.

        Args:
            source_h3: Source hex H3 index.
            target_h3: Target hex H3 index.

        Returns:
            List of infrastructure links on the edge (empty if none).
        """
        key = self._canonical_key(source_h3, target_h3)
        return list(self._edge_links.get(key, []))

    def add_edge_link(
        self,
        source_h3: str,
        target_h3: str,
        link: InfrastructureLinkState,
    ) -> None:
        """Add an infrastructure link to an edge.

        Args:
            source_h3: Source hex H3 index.
            target_h3: Target hex H3 index.
            link: The infrastructure link to add.
        """
        key = self._canonical_key(source_h3, target_h3)
        if key not in self._edge_links:
            self._edge_links[key] = []
        self._edge_links[key].append(link)
        self._link_index[link.link_id] = key

    def degrade_link(
        self,
        link_id: str,
        condition_delta: float,
    ) -> InfrastructureLinkState:
        """Degrade an infrastructure link's condition.

        Args:
            link_id: Unique identifier of the link to degrade.
            condition_delta: Amount to reduce condition by (positive value).

        Returns:
            Updated link state after degradation.

        Raises:
            KeyError: If link_id not found in inventory.
        """
        if link_id not in self._link_index:
            msg = f"Link not found: {link_id!r}"
            raise KeyError(msg)

        edge_key = self._link_index[link_id]
        links = self._edge_links[edge_key]

        for i, link in enumerate(links):
            if link.link_id == link_id:
                new_condition = max(0.0, link.condition - condition_delta)
                updated = link.model_copy(update={"condition": new_condition})
                links[i] = updated
                return updated

        msg = f"Link not found in edge links: {link_id!r}"
        raise KeyError(msg)  # pragma: no cover

    def get_all_edges(self) -> list[tuple[str, str]]:
        """Get all edge keys that have infrastructure links.

        Returns:
            List of canonical (source_h3, target_h3) edge pairs.
        """
        return list(self._edge_links.keys())

    def get_vertex(self, vertex_id: str) -> VertexState | None:
        """Get vertex state by ID.

        Args:
            vertex_id: Canonical vertex identifier.

        Returns:
            Vertex state, or None if vertex not found.
        """
        return self._vertices.get(vertex_id)

    def add_vertex(self, vertex: VertexState) -> None:
        """Add a vertex to the inventory.

        Args:
            vertex: Vertex state to store.
        """
        self._vertices[vertex.vertex_id] = vertex

    def add_junction(self, vertex_id: str, junction: JunctionState) -> None:
        """Add a junction to a vertex.

        Args:
            vertex_id: Vertex to add junction to.
            junction: Junction state to add.

        Raises:
            KeyError: If vertex not found.
        """
        vertex = self._vertices.get(vertex_id)
        if vertex is None:
            msg = f"Vertex not found: {vertex_id!r}"
            raise KeyError(msg)

        updated_junctions = list(vertex.junctions) + [junction]
        self._vertices[vertex_id] = vertex.model_copy(
            update={"junctions": updated_junctions},
        )

    def degrade_junction(
        self,
        vertex_id: str,
        junction_type: str,
        condition_delta: float,
    ) -> list[tuple[str, str]]:
        """Degrade a junction, cascading to adjacent edges.

        Reduces junction condition and capacity contribution of all
        links on adjacent edges by a fraction of the condition delta.

        Args:
            vertex_id: Vertex containing the junction.
            junction_type: Type of junction to degrade.
            condition_delta: Amount to reduce condition by.

        Returns:
            List of (source_h3, target_h3) edge pairs affected by cascade.

        Raises:
            KeyError: If vertex or junction type not found.
        """
        vertex = self._vertices.get(vertex_id)
        if vertex is None:
            msg = f"Vertex not found: {vertex_id!r}"
            raise KeyError(msg)

        # Find and degrade the junction
        updated_junctions = list(vertex.junctions)
        found = False
        for i, junction in enumerate(updated_junctions):
            if junction.junction_type == junction_type:
                new_condition = max(0.0, junction.condition - condition_delta)
                updated_junctions[i] = junction.model_copy(
                    update={"condition": new_condition},
                )
                found = True
                break

        if not found:
            msg = f"Junction type {junction_type!r} not found on vertex {vertex_id!r}"
            raise KeyError(msg)

        self._vertices[vertex_id] = vertex.model_copy(
            update={"junctions": updated_junctions},
        )

        # Cascade: degrade all links on edges formed by pairs of adjacent cells
        affected_edges: list[tuple[str, str]] = []
        cells = vertex.adjacent_h3
        cell_pairs = [
            (cells[0], cells[1]),
            (cells[0], cells[2]),
            (cells[1], cells[2]),
        ]

        cascade_delta = condition_delta * 0.5  # 50% cascade ratio
        for source, target in cell_pairs:
            key = self._canonical_key(source, target)
            if key in self._edge_links:
                affected_edges.append(key)
                links = self._edge_links[key]
                for j, link in enumerate(links):
                    new_condition = max(0.0, link.condition - cascade_delta)
                    links[j] = link.model_copy(update={"condition": new_condition})

        return affected_edges

    def get_nonlocal_edges(self) -> list[NonlocalEdgeState]:
        """Get all nonlocal edges in the mesh.

        Returns:
            List of nonlocal edge states.
        """
        return list(self._nonlocal_edges)

    def add_nonlocal_edge(self, edge: NonlocalEdgeState) -> None:
        """Add a nonlocal edge to the inventory.

        Args:
            edge: Nonlocal edge state to store.
        """
        self._nonlocal_edges.append(edge)

    def to_dict(self) -> dict[str, object]:
        """Serialize inventory state for tick-snapshot compatibility.

        Returns:
            Dict with edge_links, vertices, and nonlocal_edges.
        """
        edge_links: dict[str, list[dict[str, object]]] = {}
        for (src, tgt), links in self._edge_links.items():
            key = f"{src}|{tgt}"
            edge_links[key] = [link.model_dump() for link in links]

        vertices: dict[str, dict[str, object]] = {}
        for vid, vertex in self._vertices.items():
            vertices[vid] = vertex.model_dump()

        nonlocal_edges: list[dict[str, object]] = [
            edge.model_dump() for edge in self._nonlocal_edges
        ]

        return {
            "edge_links": edge_links,
            "vertices": vertices,
            "nonlocal_edges": nonlocal_edges,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DefaultInfrastructureInventory:
        """Deserialize inventory state from tick-snapshot data.

        Args:
            data: Serialized state from ``to_dict()``.

        Returns:
            Reconstructed DefaultInfrastructureInventory.
        """
        inventory = cls()

        edge_links_data = data.get("edge_links", {})
        for key_str, links_data in edge_links_data.items():  # type: ignore[attr-defined]
            src, tgt = str(key_str).split("|")
            for link_dict in links_data:
                link = InfrastructureLinkState.model_validate(link_dict)
                inventory.add_edge_link(src, tgt, link)

        vertices_data = data.get("vertices", {})
        for _vid, vertex_dict in vertices_data.items():  # type: ignore[attr-defined]
            vertex = VertexState.model_validate(vertex_dict)
            inventory.add_vertex(vertex)

        nonlocal_data = data.get("nonlocal_edges", [])
        for edge_dict in nonlocal_data:  # type: ignore[attr-defined]
            edge = NonlocalEdgeState.model_validate(edge_dict)
            inventory.add_nonlocal_edge(edge)

        return inventory
