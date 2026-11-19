"""Project the original qualified Michigan truck paths into the freight map's distance product."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from tools.capture_michigan_statewide_sources import (
    MAX_MATRIX_BYTES,
    CaptureError,
    _canonical,
    _gzip,
    _json,
    _publish,
)

SCENARIO = Path(__file__).resolve().parents[1] / "content/scenarios/michigan"


def project(matrix: Path, scene: Path, output: Path) -> None:
    """Use CPython 3.12.14 and zlib 1.3.2 to reproduce the published gzip bytes."""
    manifest = _json(scene / "statewide-sources.json")
    qualification = _json(
        scene / "statewide-qualification.json.gz",
        compressed=True,
        expected_sha256=manifest["qualification_sha256"],
    )
    physical = _json(
        scene / "statewide-physical.json.gz",
        compressed=True,
        expected_sha256=manifest["physical_network_sha256"],
    )
    if qualification["schema"] != "MichiganCommodityCircuitV1" or not qualification["qualified"]:
        raise CaptureError("Michigan source has no path qualification")
    original = qualification["paths_sha256"]
    source = _json(matrix, compressed=True, bound=MAX_MATRIX_BYTES, expected_sha256=original)
    road = physical["source"]
    if (
        source["schema"] != "MichiganCountyPathMatrixV1"
        or source["source_pins"]["graph_sha256"] != road["graph_sha256"]
        or source["policy"] != physical["terminal_policy"]
        or source["terminals"] != physical["terminals"]
    ):
        raise CaptureError("path matrix differs from the captured graph, policy or terminals")
    for pair in source["paths"]:
        if pair["path"] is not None:
            del pair["path"]["edge_ids"]
    source["schema"] = "MichiganRegionalRoadDistancesV1"
    payload = _gzip(
        _canonical(
            {k: source[k] for k in ("schema", "source_pins", "policy", "terminals", "paths")}
        )
    )
    metadata = {
        "distances_sha256": hashlib.sha256(payload).hexdigest(),
        "matrix_sha256": original,
        "license": "ODbL-1.0; OpenStreetMap contributors",
        **{
            key: road[key]
            for key in (
                "graph_sha256",
                "pbf_sha256",
                "footprint_sha256",
                "replication_timestamp",
                "routing_profile_version",
            )
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    _publish(
        output,
        {
            "region-road-distances.json.gz": payload,
            "region-road-distances-sources.json": _canonical(metadata),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--scenario", type=Path, default=SCENARIO)
    parser.add_argument("--out", required=True, type=Path)
    options = parser.parse_args()
    project(options.matrix, options.scenario, options.out)


if __name__ == "__main__":
    main()
