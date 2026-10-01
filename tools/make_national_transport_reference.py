#!/usr/bin/env python3
"""Capture bounded source transport evidence and an explicitly Designed network.

No carrier payment, campaign hydration, flow allocation or production is run.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any

import national_transport_graph as graph
import national_transport_network as network
import national_transport_sources as source
from make_national_county_reference import (
    ROOT,
    ReferenceBuildError,
    ensure_output_paths,
    provenance_path,
    sha256,
)

ARTIFACT_OUT = (
    ROOT / "src/babylon/data/reference/transport/national_transport_reference_2024.json.gz"
)
METADATA_OUT = ARTIFACT_OUT.with_name("national_transport_reference_2024.metadata.json")
POLICY_PATH = ROOT / "contracts/national_transport_policy_v1.json"
WEB_MANIFEST = source.DATA / "national_reference_2024/transport_2026-09-20/manifest.json"
SOURCE_MANIFEST = ROOT / "tools/national_transport_2024_sources.json"


def source_records() -> list[dict[str, Any]]:
    paths = [
        (
            "county_reference",
            source.COUNTY_REFERENCE_PATH,
            "Pinned3144county roster/internal points and ACS population hub ranking",
        ),
        (
            "international_roster",
            ROOT / "contracts/international_counterpart_membership_v1.json",
            "Explicit12counterparts and6USdependency scopes",
        ),
        ("faf2024", source.FLOW, "FAF5.7.1 calendar2024 estimated flows; not installed capacities"),
        (
            "faf_metadata",
            source.FAF / "region/FAF5_metadata.xlsx",
            "Source units,132domestic/8foreign zones and native modes",
        ),
        (
            "airports",
            source.AIR,
            "FAA open/public airport points; per-record EFF_DATE including2025-12-25",
        ),
        (
            "marine",
            source.SEA,
            "NTAD RoRo facility evidence, not comprehensive ports or bulk berths",
        ),
        (
            "pipeline_terminals",
            source.PIPE,
            "NTAD2021terminal product/access flags, not pipeline connections or rated capacity",
        ),
        (
            "border",
            source.DATA / "bts_border/border_crossing_entry_data.csv",
            "BTS2024 inbound truck counts; no observed outbound or installed capacity",
        ),
    ]
    for extension in ("shp", "shx", "dbf", "prj"):
        paths.append(
            (
                f"tiger_{extension}",
                source.TIGER.with_suffix("." + extension),
                "TIGER2024geographic spatial admission",
            )
        )
    for mode in ("truck", "rail", "water", "pipeline"):
        for direction in ("origin", "destination"):
            paths.append(
                (
                    f"factors_{mode}_{direction}",
                    source.FAF / f"{mode}_{direction}_factors.csv",
                    "Experimental estimated county allocation factors; not observedcountyOD or physical access",
                )
            )
    records = [source.source_record(*item) for item in paths]
    for row in json.loads(WEB_MANIFEST.read_text()):
        path = Path(row["path"])
        if sha256(path) != row["sha256"]:
            raise ReferenceBuildError("web_source_digest")
        records.append(source.source_record(row["id"], path, row["qualification"]))
    return sorted(records, key=lambda row: row["id"])


def topology(policy: dict[str, Any]) -> dict[str, Any]:
    counties = source.county_rows()
    factors, zones = source.factors(set(counties))
    airports, access = source.airports(counties, policy)
    builder = graph.GraphBuilder(policy)
    for county, row in counties.items():
        network._county_node(builder, county, row)
    for county in policy["trunk_counties"]:
        network._county_node(builder, county, counties[county], "trunk")
    facilities = network.aviation(builder, airports, access)
    county_access = network.domestic(builder, counties, zones, access)
    facilities.extend(network.marine(builder))
    border_rows = network.external(builder)
    facilities.extend(network.bulk(builder))
    result: dict[str, Any] = {
        "schema": "NationalTransportReferenceV1",
        "policy": policy,
        "policy_sha256": sha256(POLICY_PATH),
        "nodes": [builder.nodes[key] for key in sorted(builder.nodes)],
        "links": [builder.links[key] for key in sorted(builder.links)],
        "pools": [builder.pools[key] for key in sorted(builder.pools)],
        "county_access": county_access,
        "county_factors": factors,
        "facilities": sorted(facilities, key=lambda row: (row["source_id"], row["key"])),
        "border_inbound_2024": border_rows,
    }
    source.validate_facility_locations(result["nodes"])
    result["audit"] = graph.audit(result["nodes"], result["links"], county_access)
    graph.validate_capture(result, verify_audit=False)
    return result


def build(
    *, artifact_out: Path = ARTIFACT_OUT, metadata_out: Path = METADATA_OUT
) -> dict[str, Any]:
    ensure_output_paths((artifact_out, metadata_out), (POLICY_PATH, SOURCE_MANIFEST))
    policy = json.loads(POLICY_PATH.read_text())
    records = source_records()
    if SOURCE_MANIFEST.exists():
        if records != json.loads(SOURCE_MANIFEST.read_text())["sources"]:
            raise ReferenceBuildError("source_manifest_drift")
    else:
        source.write_json(
            SOURCE_MANIFEST,
            {
                "contract": "NationalTransportSources2024V1",
                "sources": records,
                "official_pages": json.loads(WEB_MANIFEST.read_text()),
            },
        )
    result = topology(policy)
    print("Source topology validated; streaming FAF2024 once.", flush=True)
    with source.FLOW.open(newline="") as stream:
        result["flows"] = source.aggregate_flows(csv.DictReader(stream))
    result["sources"] = records
    if (
        sum(len(result["flows"][name]) for name in ("domestic", "foreign", "controls"))
        > policy["bounds"]["flow_rows"]
    ):
        raise ReferenceBuildError("flow_row_bound")
    encoded = (json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n").encode("ascii")
    if len(encoded) > policy["bounds"]["decoded_bytes"]:
        raise ReferenceBuildError(f"decoded_bound:{len(encoded)}")
    compressed = gzip.compress(encoded, compresslevel=9, mtime=0)
    if len(compressed) > policy["bounds"]["compressed_bytes"]:
        raise ReferenceBuildError(f"compressed_bound:{len(compressed)}")
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    artifact_out.write_bytes(compressed)
    truck_zones = {row["county"]: row["zone"] for row in result["county_access"]}
    metadata = {
        "contract": "NationalTransportReferenceV1",
        "issue": "PER-40",
        "artifact": {
            "path": provenance_path(artifact_out),
            "sha256": sha256(artifact_out),
            "bytes": len(compressed),
            "decoded_bytes": len(encoded),
            "rows": len(result["nodes"]),
        },
        "sources": records,
        "policy_sha256": sha256(POLICY_PATH),
        "counts": {
            key: len(result[key])
            for key in (
                "nodes",
                "links",
                "pools",
                "county_access",
                "county_factors",
                "facilities",
                "border_inbound_2024",
            )
        },
        "flows": {
            key: value if key.endswith("rows") else len(value)
            for key, value in result["flows"].items()
        },
        "audit": result["audit"],
        "factor_source_rows": sum(int(row[6]) for row in result["county_factors"]),
        "nontruck_factor_zone_differences_from_truck": sum(
            row[0] != "truck" and row[3] != truck_zones[row[2]] for row in result["county_factors"]
        ),
        "factor_zone_qualification": "Mode-specific source zones remain independent. Twelve Connecticut pipeline rows differ from the truck routing-hub basis; neither source identity is normalized or repaired.",
        "factor_duplicate_keys": sum(int(row[6]) > 1 for row in result["county_factors"]),
        "county_rebindings": [
            {
                "source_id": "pipeline_terminals",
                "source_key": "02261016",
                "source_county": "02261",
                "captured_county": "02063",
                "basis": "Retain original source label; current county admitted by TIGER2024 point-in-polygon.",
            }
        ],
        "semantics": policy["semantics"],
        "evidence_classes": {
            "source_facility_records": "Observed",
            "faf_estimates": "Derived",
            "source_aggregation": "Derived",
            "topology_and_service": "Designed",
        },
        "native_readers": ["babylon-persistence::national_transport"],
        "runtime_consumers": [],
    }
    source.write_json(metadata_out, metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    result = build(artifact_out=args.artifact_out, metadata_out=args.metadata_out)
    print(
        json.dumps(
            {"artifact": result["artifact"], "counts": result["counts"], "flows": result["flows"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
