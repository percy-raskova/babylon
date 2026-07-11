"""Tests for H3 mesh edge and vertex enumeration (Feature 036, T005-T008).

Tests verify:
- Edge enumeration produces canonical ordered pairs
- Edge count matches expected for small cell clusters
- Vertex enumeration finds triangle junctions
- Vertex IDs are deterministic (SHA-256 hash)
- Euler's formula V - E + F = 2 for planar graph
"""

from __future__ import annotations

import h3
import pytest

from babylon.domain.geography.h3_mesh import enumerate_edges, enumerate_vertices


@pytest.mark.unit
class TestEnumerateEdges:
    """Tests for enumerate_edges()."""

    def test_single_cell_no_edges(self) -> None:
        """A single cell has no interior edges."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        edges = enumerate_edges({center})
        assert edges == []

    def test_two_adjacent_cells_one_edge(self) -> None:
        """Two adjacent cells share exactly one edge."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        ring = h3.grid_disk(center, 1)
        neighbor = next(c for c in ring if c != center)
        edges = enumerate_edges({center, neighbor})
        assert len(edges) == 1
        assert edges[0][0] < edges[0][1]  # Canonical ordering

    def test_center_plus_ring_edges(self) -> None:
        """Center cell + ring(1) should produce exactly 12 edges.

        A center hex has 6 neighbors. Each neighbor shares an edge with
        center (6 edges) and with 2 other neighbors (6 edges). Total = 12.
        """
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        assert len(edges) == 12

    def test_edges_are_sorted(self) -> None:
        """All edge pairs are lexicographically sorted."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        for a, b in edges:
            assert a < b

    def test_no_duplicate_edges(self) -> None:
        """No duplicate edges in output."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        assert len(edges) == len(set(edges))

    def test_empty_set(self) -> None:
        """Empty cell set produces no edges."""
        edges = enumerate_edges(set())
        assert edges == []

    def test_larger_cluster(self) -> None:
        """Ring(2) cluster should produce consistent edge count."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 2)
        edges = enumerate_edges(cells)
        # 19 cells: interior edges for a 2-ring hex cluster
        # Each interior cell contributes 6 edges, boundary cells fewer
        assert len(edges) > 12
        assert len(edges) == 42  # Known value for ring(2)


@pytest.mark.unit
class TestEnumerateVertices:
    """Tests for enumerate_vertices()."""

    def test_single_cell_no_vertices(self) -> None:
        """A single cell has no vertices (no triangles possible)."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        edges = enumerate_edges({center})
        vertices = enumerate_vertices(edges, {center})
        assert vertices == []

    def test_center_plus_ring_vertices(self) -> None:
        """Center + ring(1) should produce 6 vertices.

        Each vertex is a triangle of 3 mutually adjacent cells.
        A center hex with 6 neighbors forms 6 triangles.
        """
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        vertices = enumerate_vertices(edges, cells)
        assert len(vertices) == 6

    def test_vertex_has_three_adjacent_cells(self) -> None:
        """Each vertex references exactly 3 adjacent cells."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        vertices = enumerate_vertices(edges, cells)
        for v in vertices:
            assert len(v.adjacent_h3) == 3

    def test_vertex_ids_are_deterministic(self) -> None:
        """Same input produces same vertex IDs."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        v1 = enumerate_vertices(edges, cells)
        v2 = enumerate_vertices(edges, cells)
        assert [v.vertex_id for v in v1] == [v.vertex_id for v in v2]

    def test_vertex_positions_are_centroids(self) -> None:
        """Vertex lat/lon is mean of 3 cell centroids."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        vertices = enumerate_vertices(edges, cells)

        vertex = vertices[0]
        lats = []
        lons = []
        for cell in vertex.adjacent_h3:
            lat, lon = h3.cell_to_latlng(cell)
            lats.append(lat)
            lons.append(lon)

        expected_lat = sum(lats) / 3.0
        expected_lon = sum(lons) / 3.0
        assert vertex.lat == pytest.approx(expected_lat, abs=1e-10)
        assert vertex.lon == pytest.approx(expected_lon, abs=1e-10)

    def test_euler_formula_ring1(self) -> None:
        """Verify Euler's formula V - E + F = 2 for ring(1) planar graph.

        F = number of cells (faces) + 1 outer face.
        V = vertex count, E = edge count.
        """
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        vertices = enumerate_vertices(edges, cells)

        v = len(vertices)  # 6
        e = len(edges)  # 12
        f = len(cells) + 1  # 7 cells + 1 outer face = 8

        assert v - e + f == 2

    def test_no_duplicate_vertices(self) -> None:
        """No duplicate vertex IDs in output."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        vertices = enumerate_vertices(edges, cells)
        ids = [v.vertex_id for v in vertices]
        assert len(ids) == len(set(ids))

    def test_adjacent_h3_sorted(self) -> None:
        """Adjacent H3 indices in each vertex are sorted."""
        center = h3.latlng_to_cell(42.33, -83.05, 7)
        cells = h3.grid_disk(center, 1)
        edges = enumerate_edges(cells)
        vertices = enumerate_vertices(edges, cells)
        for v in vertices:
            assert list(v.adjacent_h3) == sorted(v.adjacent_h3)
