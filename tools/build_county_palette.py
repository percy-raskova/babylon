"""Build four stable geographic colors from the committed rendered atlas.

Run ``mise exec -- uv run --frozen python tools/build_county_palette.py``.
Only positive-length shared rendered boundaries constrain colors. The atlas's
causal adjacency, including corner contacts, is deliberately never used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

from shapely.geometry import MultiLineString  # type: ignore[import-untyped]
from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]
from shapely.strtree import STRtree  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]


def load_boundaries(raw: bytes) -> tuple[tuple[str, ...], list[BaseGeometry]]:
    """Validate atlas v1 and decode every ring into integer-grid boundaries."""
    if len(raw) < 128 or raw[:8] != b"BABCTY\0\x01":
        raise ValueError("Missing atlas v1 header")
    if struct.unpack_from("<II", raw, 8) != (1, 0):
        raise ValueError("Unsupported atlas version or flags")
    if raw[16:48] != hashlib.sha256(raw[48:]).digest():
        raise ValueError("Atlas content hash mismatch")
    origin_x, origin_y, scale = struct.unpack_from("<3d", raw, 48)
    if not all(math.isfinite(value) for value in (origin_x, origin_y, scale)) or scale <= 0:
        raise ValueError("Invalid atlas grid transform")
    count, ring_count, vertex_count, csr_count = struct.unpack_from("<4I", raw, 72)
    ring_offset = 128 + count * 28
    vertex_offset = ring_offset + ring_count * 12
    csr_offset = vertex_offset + vertex_count * 4
    name_offset = csr_offset + (count + 1 + csr_count) * 4
    if name_offset + 4 > len(raw):
        raise ValueError("Truncated atlas tables")
    name_length = struct.unpack_from("<I", raw, name_offset)[0]
    if name_offset + 4 + name_length != len(raw):
        raise ValueError("Atlas name length or trailing bytes mismatch")
    names = raw[name_offset + 4 :].decode("utf-8").splitlines()
    if len(names) != count:
        raise ValueError("Atlas name count mismatch")
    offsets = struct.unpack_from(f"<{count + 1}I", raw, csr_offset)
    if (
        offsets[0] != 0
        or offsets[-1] != csr_count
        or any(left > right for left, right in zip(offsets, offsets[1:], strict=False))
    ):
        raise ValueError("Invalid atlas CSR offsets")
    neighbors = struct.unpack_from(f"<{csr_count}I", raw, csr_offset + (count + 1) * 4)
    if any(neighbor >= count for neighbor in neighbors):
        raise ValueError("Invalid atlas CSR neighbor")
    vertices = [struct.unpack_from("<2H", raw, vertex_offset + i * 4) for i in range(vertex_count)]
    rings = []
    for i in range(ring_count):
        start, length, hole = struct.unpack_from("<IIB", raw, ring_offset + i * 12)
        if length < 3 or start + length > vertex_count or hole not in (0, 1):
            raise ValueError("Invalid atlas ring")
        ring = vertices[start : start + length]
        rings.append([*ring, ring[0]])
    fips = []
    boundaries = []
    for i in range(count):
        offset = 128 + i * 28
        identity = raw[offset : offset + 5].decode("ascii")
        if len(identity) != 5 or not identity.isdecimal():
            raise ValueError("Invalid county FIPS")
        fips.append(identity)
        start, length = struct.unpack_from("<IH", raw, offset + 6)
        if not length or start + length > ring_count:
            raise ValueError("Invalid county ring range")
        boundaries.append(MultiLineString(rings[start : start + length]))
    if not fips or fips != sorted(set(fips)):
        raise ValueError("County FIPS must be unique and ordered")
    return tuple(fips), boundaries


def shared_edges(boundaries: list[BaseGeometry]) -> list[tuple[int, ...]]:
    """Return symmetric adjacency for positive-length shared boundaries only."""
    tree = STRtree(boundaries)
    adjacent: list[set[int]] = [set() for _ in boundaries]
    for i, boundary in enumerate(boundaries):
        for j in sorted(map(int, tree.query(boundary, predicate="intersects"))):
            if j > i and boundary.intersection(boundaries[j]).length > 0:
                adjacent[i].add(j)
                adjacent[j].add(i)
    return [tuple(sorted(neighbors)) for neighbors in adjacent]


def four_colors(adjacent: list[tuple[int, ...]]) -> list[int]:
    """Use deterministic DSATUR/backtracking; reject unsatisfiable graphs.

    County indices must follow ascending FIPS. Ties prefer the lowest index;
    candidate colors always follow palette order. Never fall back to a fifth.
    """
    colors = [-1] * len(adjacent)
    counts = [[0] * 4 for _ in adjacent]
    uncolored = set(range(len(adjacent)))

    def visit() -> bool:
        if not uncolored:
            return True
        index = max(
            uncolored, key=lambda i: (sum(value > 0 for value in counts[i]), len(adjacent[i]), -i)
        )
        uncolored.remove(index)
        for color in range(4):
            if counts[index][color]:
                continue
            colors[index] = color
            for neighbor in adjacent[index]:
                counts[neighbor][color] += 1
            if visit():
                return True
            for neighbor in adjacent[index]:
                counts[neighbor][color] -= 1
        colors[index] = -1
        uncolored.add(index)
        return False

    previous_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(max(previous_limit, len(adjacent) + 100))
        if not visit():
            raise ValueError("Rendered boundary graph cannot use four palette indices")
    finally:
        sys.setrecursionlimit(previous_limit)
    if any(color not in range(4) for color in colors) or any(
        colors[i] == colors[j] for i, neighbors in enumerate(adjacent) for j in neighbors
    ):
        raise ValueError("Invalid four-color assignment")
    return colors


def build_palette(raw: bytes) -> bytes:
    """Return deterministic JSON keyed by complete atlas FIPS and file digest."""
    fips, boundaries = load_boundaries(raw)
    colors = four_colors(shared_edges(boundaries))
    payload = {
        "schema_version": 1,
        "atlas_sha256": hashlib.sha256(raw).hexdigest(),
        "counties": [
            {"fips": identity, "color": color} for identity, color in zip(fips, colors, strict=True)
        ],
    }
    return (json.dumps(payload, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def main() -> None:
    """Generate the companion without rebuilding geometry or causal adjacency."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas", type=Path, default=ROOT / "assets/map/county_atlas.bin")
    parser.add_argument("--out", type=Path, default=ROOT / "assets/map/county_palette.json")
    args = parser.parse_args()
    encoded = build_palette(args.atlas.read_bytes())
    args.out.write_bytes(encoded)
    print(f"Wrote {len(encoded)} bytes to {args.out}")


if __name__ == "__main__":
    main()
