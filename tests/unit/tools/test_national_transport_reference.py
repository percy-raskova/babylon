"""Sparse access must conserve source distinctions and refuse fictional bulk air."""

from __future__ import annotations

import copy
import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import national_transport_graph as graph  # type: ignore[import-not-found]  # noqa: E402
import national_transport_sources as sources  # type: ignore[import-not-found]  # noqa: E402
from make_national_county_reference import (  # type: ignore[import-not-found]  # noqa: E402
    ReferenceBuildError,
)


def test_air_never_admits_bulk_and_pools_are_finite() -> None:
    with pytest.raises(ReferenceBuildError, match="air_bulk"):
        graph.validate_service("air", ["general", "dry_bulk"], 1, 100, 1, 0)
    for capacity in (0, -1, True, 2**64):
        with pytest.raises(ReferenceBuildError, match="service"):
            graph.validate_service("truck", ["general"], 1, capacity, 1, 0)
    graph.validate_service("air", ["general"], 1, 100, 1, 0)


def test_direction_and_missing_flow_values_are_not_zero_or_net() -> None:
    assert sources.decimal_token("") is None
    assert sources.decimal_token("0.000000") == 0
    with pytest.raises(ReferenceBuildError, match="flow_decimal"):
        sources.decimal_token("NaN")
    rows = [
        {
            "trade_type": "2",
            "fr_orig": "801",
            "fr_dest": "",
            "dms_orig": "011",
            "dms_dest": "012",
            "fr_inmode": "1",
            "dms_mode": "1",
            "fr_outmode": "",
            "sctg2": "10",
            "tons_2024": "1.000001",
            "value_2024": "",
            "current_value_2024": "3.100000",
            "tmiles_2024": "2.000000",
        },
        {
            "trade_type": "3",
            "fr_orig": "",
            "fr_dest": "801",
            "dms_orig": "012",
            "dms_dest": "011",
            "fr_inmode": "",
            "dms_mode": "1",
            "fr_outmode": "1",
            "sctg2": "10",
            "tons_2024": "7.000000",
            "value_2024": "0.000000",
            "current_value_2024": "4.100000",
            "tmiles_2024": "2.000000",
        },
    ]
    capture = sources.aggregate_flows(rows)
    assert len(capture["foreign"]) == 2
    assert capture["foreign"][0]["values"][0] == {"known_sum": "1.000001", "published": 1}
    assert capture["foreign"][0]["values"][1] == {"known_sum": "0", "published": 0}
    assert capture["foreign"][1]["values"][1] == {"known_sum": "0.000000", "published": 1}


def test_committed_graph_keeps_all_counties_islands_and_external_scopes() -> None:
    path = ROOT / "src/babylon/data/reference/transport/national_transport_reference_2024.json.gz"
    with gzip.open(path, "rt") as stream:
        capture = json.load(stream)
    graph.validate_capture(capture)
    assert len(capture["county_access"]) == 3144
    assert len([row for row in capture["nodes"] if row["kind"] == "foreign"]) == 12
    assert len([row for row in capture["nodes"] if row["kind"] == "dependency"]) == 6
    access = {row["county"]: row for row in capture["county_access"]}
    assert access["15005"]["airport"] == "LUP"
    for county in ("25007", "25019", "53055"):
        assert access[county]["airport"]
    assert all(row["mode"] != "air" or row["cargo"] == ["general"] for row in capture["links"])
    assert capture["audit"]["general_diameter"] <= 16
    assert capture["audit"]["unavailable_bulk_counties"]
    factors = capture["county_factors"]
    assert sum(int(row[6]) > 1 for row in factors) == 5
    assert all(row[2] == "09140" and row[0] == "water" for row in factors if int(row[6]) > 1)


def test_refuse_island_ground_shortcut_and_duplicate_identity() -> None:
    path = ROOT / "src/babylon/data/reference/transport/national_transport_reference_2024.json.gz"
    with gzip.open(path, "rt") as stream:
        capture = json.load(stream)
    mutated = copy.deepcopy(capture)
    mutated["nodes"].append(mutated["nodes"][0])
    with pytest.raises(ReferenceBuildError, match="node"):
        graph.validate_capture(mutated)
    mutated = copy.deepcopy(capture)
    link = next(
        row for row in mutated["links"] if row["mode"] == "air" and row["from"] == "airport:LUP"
    )
    link["mode"] = "truck"
    with pytest.raises(ReferenceBuildError, match="island|mode"):
        graph.validate_capture(mutated)
