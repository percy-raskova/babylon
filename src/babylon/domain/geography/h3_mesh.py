"""H3 mesh edge and vertex enumeration utilities (Feature 036).

Provides functions to enumerate edges (shared boundaries) and vertices
(triple junctions) for a set of H3 hexagonal cells, producing the mesh
topology needed for infrastructure snapping and flow computation.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: FR-009, FR-015
"""

from __future__ import annotations

import hashlib

import h3

from babylon.domain.geography.types import VertexState


def enumerate_edges(cells: set[str]) -> list[tuple[str, str]]:
    """Enumerate all interior edges (shared boundaries) in an H3 cell set.

    For each cell, finds neighbors within the cell set using
    ``h3.grid_disk(cell, 1)``. Each edge is represented as a canonically
    ordered pair ``tuple(sorted([cell, neighbor]))``.

    Args:
        cells: Set of H3 cell index strings (same resolution).

    Returns:
        Deduplicated sorted list of (cell_a, cell_b) edge pairs,
        where cell_a < cell_b lexicographically.
    """
    edges: set[tuple[str, str]] = set()
    for cell in cells:
        neighbors = h3.grid_disk(cell, 1)
        for neighbor in neighbors:
            if neighbor != cell and neighbor in cells:
                edge = tuple(sorted([cell, neighbor]))
                edges.add(edge)
    return sorted(edges)


def enumerate_vertices(
    edges: list[tuple[str, str]],
    cells: set[str],
) -> list[VertexState]:
    """Enumerate all interior vertices (triple junctions) in an H3 mesh.

    A vertex is formed where exactly 3 cells meet. Detected by finding
    triangles in the adjacency graph: for each cell, any pair of its
    neighbors that are also neighbors of each other forms a triangle,
    and that triangle defines one vertex.

    Args:
        edges: List of (cell_a, cell_b) edge pairs from ``enumerate_edges``.
        cells: Set of H3 cell index strings.

    Returns:
        List of VertexState objects with canonical IDs and positions.
    """
    # Build adjacency dict
    adjacency: dict[str, set[str]] = {cell: set() for cell in cells}
    for cell_a, cell_b in edges:
        adjacency[cell_a].add(cell_b)
        adjacency[cell_b].add(cell_a)

    # Find triangles (each vertex = 1 triangle of 3 mutually adjacent cells)
    seen_triples: set[tuple[str, str, str]] = set()
    vertices: list[VertexState] = []

    for cell in sorted(cells):
        neighbors = sorted(adjacency[cell])
        neighbor_count = len(neighbors)
        for i in range(neighbor_count):
            for j in range(i + 1, neighbor_count):
                n1 = neighbors[i]
                n2 = neighbors[j]
                if n2 in adjacency[n1]:
                    triple = tuple(sorted([cell, n1, n2]))
                    if triple not in seen_triples:
                        seen_triples.add(triple)  # type: ignore[arg-type]
                        vertex = _make_vertex(triple[0], triple[1], triple[2])
                        vertices.append(vertex)

    return sorted(vertices, key=lambda v: v.vertex_id)


def _make_vertex(cell_a: str, cell_b: str, cell_c: str) -> VertexState:
    """Create a VertexState from three adjacent H3 cells.

    The vertex ID is a SHA-256 hash of the sorted triple for canonical
    identification. Position is the centroid of the three cell centroids.

    Args:
        cell_a: First H3 cell index.
        cell_b: Second H3 cell index.
        cell_c: Third H3 cell index.

    Returns:
        VertexState with canonical ID and centroid position.
    """
    sorted_cells = tuple(sorted([cell_a, cell_b, cell_c]))
    vertex_id = hashlib.sha256("|".join(sorted_cells).encode()).hexdigest()[:16]

    lat_a, lon_a = h3.cell_to_latlng(sorted_cells[0])
    lat_b, lon_b = h3.cell_to_latlng(sorted_cells[1])
    lat_c, lon_c = h3.cell_to_latlng(sorted_cells[2])

    centroid_lat = (lat_a + lat_b + lat_c) / 3.0
    centroid_lon = (lon_a + lon_b + lon_c) / 3.0

    return VertexState(
        vertex_id=vertex_id,
        adjacent_h3=(sorted_cells[0], sorted_cells[1], sorted_cells[2]),
        lat=centroid_lat,
        lon=centroid_lon,
    )
