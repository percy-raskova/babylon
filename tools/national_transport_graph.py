"""Designed sparse transport graph, with source-qualified access and finite pools."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any

from make_national_county_reference import ReferenceBuildError

CARGO = ("general", "dry_bulk", "crude_oil", "refined_liquid")
MODES = {"handling", "truck", "air", "sea", "pipeline"}


def validate_service(
    mode: str, cargo: list[str], periods: int, capacity: int, cost: int, loss: int
) -> None:
    if mode == "air" and cargo != ["general"]:
        raise ReferenceBuildError("air_bulk")
    if (
        mode not in MODES
        or not cargo
        or len(cargo) != len(set(cargo))
        or not set(cargo) <= set(CARGO)
        or any(type(v) is not int for v in (periods, capacity, cost, loss))
        or not 0 < periods <= 65535
        or not 0 < capacity < 2**64
        or not 0 < cost < 2**63
        or not 0 <= loss <= 1000000
    ):
        raise ReferenceBuildError("service")
    if mode == "pipeline" and cargo != ["crude_oil"]:
        raise ReferenceBuildError("pipeline_commodity")


def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Only a deterministic Designed hub-ranking heuristic, not routed distance."""
    lat1, lon1, lat2, lon2 = map(
        math.radians,
        (float(a["latitude"]), float(a["longitude"]), float(b["latitude"]), float(b["longitude"])),
    )
    value = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * math.asin(math.sqrt(min(1.0, max(0.0, value))))


class GraphBuilder:
    """Mutable build scratch only; the artifact/native capture is immutable."""

    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy
        self.nodes: dict[str, dict[str, Any]] = {}
        self.links: dict[str, dict[str, Any]] = {}
        self.pools: dict[str, dict[str, Any]] = {}

    def node(
        self,
        key: str,
        kind: str,
        location: str | None,
        latitude: str | None = None,
        longitude: str | None = None,
        source: str = "policy",
        source_key: str = "",
    ) -> str:
        row = {
            "id": key,
            "kind": kind,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "source_id": source,
            "source_key": source_key,
        }
        if key in self.nodes and self.nodes[key] != row:
            raise ReferenceBuildError("duplicate_node")
        self.nodes[key] = row
        return key

    def pair(self, a: str, b: str, profile: str, cargo: list[str], evidence: list[str]) -> None:
        self.edge(a, b, profile, cargo, evidence)
        self.edge(b, a, profile, cargo, evidence)

    def edge(self, a: str, b: str, profile: str, cargo: list[str], evidence: list[str]) -> None:
        if a == b:
            return
        service = self.policy["service_profiles"][profile]
        mode = service["mode"]
        validate_service(
            mode,
            cargo,
            service["travel_periods"],
            service["capacity_grams"],
            service["cost_micros_per_tonne"],
            service["loss_ppm"],
        )
        pool = "|".join(["lane", *sorted([a, b]), profile])
        self.pools[pool] = {"id": pool, "capacity_grams": service["capacity_grams"]}
        memberships = [pool]
        for key in (a, b):
            if self.nodes[key]["kind"] in {"airport", "marine", "liquid", "border", "bulk"}:
                terminal = f"terminal|{key}"
                limit = (1000 if self.nodes[key]["kind"] == "airport" else 1000000) * 1000000
                self.pools[terminal] = {"id": terminal, "capacity_grams": limit}
                memberships.append(terminal)
        key = f"{a}>{b}:{mode}"
        row = {
            "id": key,
            "from": a,
            "to": b,
            "mode": mode,
            "cargo": sorted(cargo),
            "profile": profile,
            "pools": sorted(memberships),
            "evidence": sorted(evidence),
        }
        if key in self.links and self.links[key] != row:
            raise ReferenceBuildError("duplicate_link")
        self.links[key] = row


def neighbors(
    links: list[dict[str, Any]], cargo: str, *, reverse: bool = False
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for edge in links:
        if cargo in edge["cargo"]:
            a, b = (edge["to"], edge["from"]) if reverse else (edge["from"], edge["to"])
            result[a].append(b)
    return result


def distances(adjacency: dict[str, list[str]], start: str) -> dict[str, int]:
    result, queue = {start: 0}, deque([start])
    while queue:
        node = queue.popleft()
        for other in adjacency.get(node, []):
            if other not in result:
                result[other] = result[node] + 1
                queue.append(other)
    return result


def audit(
    nodes: list[dict[str, Any]], links: list[dict[str, Any]], counties: list[dict[str, Any]]
) -> dict[str, Any]:
    targets = [n["id"] for n in nodes if n["kind"] in {"county", "foreign", "dependency"}]
    adjacency = neighbors(links, "general")
    diameter = 0
    # All-pairs over a bounded sparse graph; no random/sample reachability claim.
    for origin in targets:
        paths = distances(adjacency, origin)
        if not set(targets) <= paths.keys():
            raise ReferenceBuildError("general_unreachable")
        diameter = max(diameter, max(paths[t] for t in targets))
    unavailable = []
    for cargo in CARGO[1:]:
        inward = distances(neighbors(links, cargo), "county:17031")
        outward = distances(neighbors(links, cargo, reverse=True), "county:17031")
        for row in counties:
            key = "county:" + row["county"]
            if key not in inward or key not in outward:
                unavailable.append(
                    {
                        "county": row["county"],
                        "cargo": cargo,
                        "can_receive": key in inward,
                        "can_supply": key in outward,
                    }
                )
    return {
        "general_diameter": diameter,
        "general_targets": len(targets),
        "unavailable_bulk_counties": unavailable,
    }


def validate_capture(capture: dict[str, Any], *, verify_audit: bool = True) -> None:
    nodes, links, pools = capture["nodes"], capture["links"], capture["pools"]
    ids = [row["id"] for row in nodes]
    if ids != sorted(set(ids)) or len(nodes) > 4000:
        raise ReferenceBuildError("node_identity")
    if [r["id"] for r in links] != sorted({r["id"] for r in links}) or len(links) > 12000:
        raise ReferenceBuildError("link_identity")
    pool_ids = {row["id"] for row in pools}
    if len(pool_ids) != len(pools) or any(
        type(r["capacity_grams"]) is not int or not 0 < r["capacity_grams"] < 2**64 for r in pools
    ):
        raise ReferenceBuildError("pool")
    for row in links:
        service = capture["policy"]["service_profiles"][row["profile"]]
        validate_service(
            row["mode"],
            row["cargo"],
            service["travel_periods"],
            service["capacity_grams"],
            service["cost_micros_per_tonne"],
            service["loss_ppm"],
        )
        if row["mode"] != service["mode"]:
            raise ReferenceBuildError("link_mode")
        if row["from"] not in ids or row["to"] not in ids or row["from"] == row["to"]:
            raise ReferenceBuildError("link_endpoint")
        if (
            not row["pools"]
            or row["pools"] != sorted(set(row["pools"]))
            or not set(row["pools"]) <= pool_ids
        ):
            raise ReferenceBuildError("link_pool")
    counties = capture["county_access"]
    keys = [row["county"] for row in counties]
    if keys != sorted(set(keys)) or len(keys) != 3144:
        raise ReferenceBuildError("county_access")
    if verify_audit and capture["audit"] != audit(nodes, links, counties):
        raise ReferenceBuildError("audit")
    if capture["audit"]["general_diameter"] > 16:
        raise ReferenceBuildError("route_stage_bound")
