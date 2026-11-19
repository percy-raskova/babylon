"""Rendered boundary coloring, independent of the simulation adjacency graph."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest
from shapely.geometry import MultiLineString, Polygon
from tools import build_county_palette as palette

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_positive_length_boundaries_exclude_corner_contacts() -> None:
    squares = [
        Polygon([(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)])
        for x, y in [(0, 0), (1, 0), (1, 1)]
    ]
    graph = palette.shared_edges([shape.boundary for shape in squares])
    assert graph == [(1,), (0, 2), (1,)]
    colors = palette.four_colors(graph)
    assert colors[0] == colors[2]
    assert colors[0] != colors[1]


@pytest.mark.unit
def test_holes_and_disconnected_parts_share_one_county_identity() -> None:
    county = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)], holes=[[(1, 1), (2, 1), (2, 2), (1, 2)]])
    island = Polygon([(8, 0), (9, 0), (9, 1), (8, 1)])
    boundary = MultiLineString([county.exterior, *county.interiors, island.exterior])
    enclave = Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])
    neighbor = Polygon([(9, 0), (10, 0), (10, 1), (9, 1)])
    graph = palette.shared_edges([boundary, enclave.boundary, neighbor.boundary])
    assert graph == [(1, 2), (0,), (0,)]
    assert palette.four_colors(graph) == [0, 1, 1]


@pytest.mark.unit
def test_four_color_search_rejects_five_clique() -> None:
    graph = [tuple(j for j in range(5) if j != i) for i in range(5)]
    with pytest.raises(ValueError, match="four"):
        palette.four_colors(graph)


@pytest.mark.unit
def test_search_backtracks_deterministically_in_fips_order() -> None:
    # Greedy DSATUR needs a fifth color here; undoing earlier choices finds four.
    graph = [
        (1, 2, 3, 4, 7),
        (0, 3, 4, 5, 6),
        (0, 3, 4, 5, 7),
        (0, 1, 2, 5, 6, 7),
        (0, 1, 2, 6),
        (1, 2, 3, 6, 7),
        (1, 3, 4, 5, 7),
        (0, 2, 3, 5, 6),
    ]
    assert palette.four_colors(graph) == [1, 2, 3, 0, 0, 1, 3, 2]
    assert palette.four_colors(graph) == [1, 2, 3, 0, 0, 1, 3, 2]


@pytest.mark.unit
def test_atlas_rejects_tampering_and_truncation() -> None:
    raw = (ROOT / "assets/map/county_atlas.bin").read_bytes()
    tampered = bytearray(raw)
    tampered[-1] ^= 1
    for invalid in [bytes(tampered), raw[:127]]:
        with pytest.raises(ValueError):
            palette.load_boundaries(invalid)


@pytest.mark.unit
@pytest.mark.parametrize("field", ["scale", "fips", "county_ring", "ring_vertex"])
def test_rehashed_invalid_atlas_fields_are_still_refused(field: str) -> None:
    raw = bytearray((ROOT / "assets/map/county_atlas.bin").read_bytes())
    if field == "scale":
        struct.pack_into("<d", raw, 64, float("nan"))
    elif field == "fips":
        raw[128:133] = b"abcde"
    elif field == "county_ring":
        struct.pack_into("<I", raw, 128 + 6, 2**32 - 1)
    else:
        count = struct.unpack_from("<I", raw, 72)[0]
        struct.pack_into("<I", raw, 128 + count * 28, 2**32 - 1)
    raw[16:48] = hashlib.sha256(raw[48:]).digest()
    with pytest.raises(ValueError):
        palette.load_boundaries(bytes(raw))


@pytest.mark.unit
def test_committed_palette_is_complete_adjacent_and_reproducible() -> None:
    raw = (ROOT / "assets/map/county_atlas.bin").read_bytes()
    fips, boundaries = palette.load_boundaries(raw)
    graph = palette.shared_edges(boundaries)
    first = palette.build_palette(raw)
    second = palette.build_palette(raw)
    assert first == second == (ROOT / "assets/map/county_palette.json").read_bytes()
    payload = json.loads(first)
    assert payload["schema_version"] == 1
    assert payload["atlas_sha256"] == hashlib.sha256(raw).hexdigest()
    assert [row["fips"] for row in payload["counties"]] == list(fips)
    colors = [row["color"] for row in payload["counties"]]
    assert set(colors) == {0, 1, 2, 3}
    assert len(colors) == 3222
    assert sum(map(len, graph)) // 2 == 6071
    assert all(colors[i] != colors[j] for i, neighbors in enumerate(graph) for j in neighbors)
