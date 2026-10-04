"""Compose the approved bounded hierarchy from source-qualified gateways."""

from __future__ import annotations

import csv
from collections import defaultdict
from typing import Any

import national_transport_graph as graph
import national_transport_sources as source
from make_national_county_reference import ReferenceBuildError

ALL = list(graph.CARGO)
GENERAL = ["general"]


def _county_node(
    builder: graph.GraphBuilder, county: str, row: dict[str, str], prefix: str = "county"
) -> str:
    return builder.node(
        f"{prefix}:{county}",
        prefix,
        f"county:{county}",
        row["internal_point_latitude"],
        row["internal_point_longitude"],
        "county_reference",
        county,
    )


def domestic(
    builder: graph.GraphBuilder,
    counties: dict[str, dict[str, str]],
    zones: dict[str, str],
    airports: dict[str, str],
) -> list[dict[str, str | None]]:
    for county, row in sorted(counties.items()):
        _county_node(builder, county, row)
    trunks = builder.policy["trunk_counties"]
    for county in trunks:
        _county_node(builder, county, counties[county], "trunk")
    for a in trunks:
        for b in trunks:
            if a < b:
                builder.pair(f"trunk:{a}", f"trunk:{b}", "trunk_road", ALL, ["policy"])
    grouped: dict[str, list[str]] = defaultdict(list)
    for county, zone in zones.items():
        grouped[zone].append(county)
    for zone, members in sorted(grouped.items()):
        candidates = [county for county in members if county not in airports]
        host = (
            min(
                candidates,
                key=lambda key: (-int(counties[key]["acs_population_persons_estimate"]), key),
            )
            if candidates
            else {"020": "02020", "151": "15003", "159": "15009"}[zone]
        )
        row = counties[host]
        node = builder.node(
            f"faf:{zone}",
            "faf",
            f"county:{host}",
            row["internal_point_latitude"],
            row["internal_point_longitude"],
            "factors_truck_origin",
            zone,
        )
        if candidates:
            nearest = min(
                trunks,
                key=lambda key: (
                    graph.distance(builder.nodes[node], builder.nodes[f"trunk:{key}"]),
                    key,
                ),
            )
            builder.pair(node, f"trunk:{nearest}", "regional_road", ALL, ["policy"])
        else:
            builder.pair(node, f"airport:{airports[host]}", "airport_handling", GENERAL, ["policy"])
        for county in members:
            if county not in airports:
                builder.pair(f"county:{county}", node, "local_road", ALL, ["policy"])
    return [
        {"county": key, "zone": zones[key], "airport": airports.get(key)}
        for key in sorted(counties)
    ]


def aviation(
    builder: graph.GraphBuilder, rows: list[dict[str, Any]], access: dict[str, str]
) -> list[dict[str, Any]]:
    located = {value: f"county:{key}" for key, value in access.items()}
    located.update(
        {
            "BOS": "county:25025",
            "SEA": "county:53033",
            "LAX": "county:06037",
            "IAH": "county:48201",
            "JFK": "county:36081",
        }
    )
    located.update(
        {
            airport: f"dependency:{key}"
            for key, airport in builder.policy["dependency_airports"].items()
        }
    )
    located["STX"] = "dependency:850"
    facilities = []
    for row in rows:
        key = row["ARPT_ID"]
        builder.node(
            f"airport:{key}",
            "airport",
            located[key],
            str(row["LAT_DECIMAL"]),
            str(row["LONG_DECIMAL"]),
            "airports",
            row["SITE_NO"],
        )
        facilities.append(
            {
                "source_id": "airports",
                "key": row["SITE_NO"],
                "fields": {
                    key: (None if value is None else str(value)) for key, value in row.items()
                },
            }
        )
    for county, airport in sorted(access.items()):
        builder.pair(
            f"county:{county}",
            f"airport:{airport}",
            "airport_handling",
            GENERAL,
            ["airports", "policy"],
        )
        regional = (
            "ANC"
            if county[:2] == "02"
            else "HNL"
            if county[:2] == "15"
            else "SEA"
            if county == "53055"
            else "BOS"
        )
        builder.pair(f"airport:{airport}", f"airport:{regional}", "air_feeder", GENERAL, ["policy"])
    for a, b in [("ANC", "SEA"), ("HNL", "LAX"), *builder.policy["dependency_services"]]:
        builder.pair(f"airport:{a}", f"airport:{b}", "air_trunk", GENERAL, ["policy"])
    for airport, trunk in {
        "BOS": "34013",
        "JFK": "34013",
        "LAX": "06037",
        "SEA": "53033",
        "IAH": "48201",
    }.items():
        builder.pair(
            f"airport:{airport}", f"trunk:{trunk}", "airport_handling", GENERAL, ["policy"]
        )
    return facilities


def marine(builder: graph.GraphBuilder) -> list[dict[str, Any]]:
    rows = source.query(
        source.SEA,
        "Intermodal_Freight_Facilities_Marine_Roll_on_Roll_off",
        "OBJECTID,PORT,TERMINAL,NAV_UNIT_ID,LAT,LON,STATE,ACCESS_RD,RAIL_CO",
    )
    selected = {row["OBJECTID"]: row for row in rows}
    counties = {
        "anchorage": "02020",
        "tacoma": "53053",
        "honolulu": "15003",
        "kahului": "15009",
        "los_angeles": "06037",
        "houston": "48201",
        "newark": "34013",
    }
    trunks = {"tacoma": "53033", "los_angeles": "06037", "houston": "48201", "newark": "34013"}
    facilities = []
    for name, object_id in builder.policy["marine_gateways"].items():
        row = selected[object_id]
        node = builder.node(
            f"marine:{name}",
            "marine",
            f"county:{counties[name]}",
            str(row["LAT"]),
            str(row["LON"]),
            "marine",
            str(object_id),
        )
        target = f"trunk:{trunks[name]}" if name in trunks else f"county:{counties[name]}"
        builder.pair(node, target, "handling", GENERAL, ["marine", "policy"])
        facilities.append(
            {
                "source_id": "marine",
                "key": str(object_id),
                "fields": {
                    key: (None if value is None else str(value)) for key, value in row.items()
                },
            }
        )
    for a, b in [("tacoma", "anchorage"), ("los_angeles", "honolulu"), ("honolulu", "kahului")]:
        builder.pair(f"marine:{a}", f"marine:{b}", "sea_domestic", GENERAL, ["marine", "policy"])
    return facilities


def external(builder: graph.GraphBuilder) -> list[dict[str, str]]:
    for key, gateways in builder.policy["counterpart_gateways"].items():
        node = builder.node(
            f"foreign:{key}",
            "foreign",
            f"foreign:{key}",
            source="international_roster",
            source_key=key,
        )
        for gateway in gateways:
            builder.pair(node, f"marine:{gateway}", "sea_foreign", GENERAL, ["policy"])
        if gateways:
            airport = {"los_angeles": "LAX", "tacoma": "SEA", "newark": "JFK", "houston": "IAH"}[
                gateways[0]
            ]
            builder.pair(node, f"airport:{airport}", "air_trunk", GENERAL, ["policy"])
    for key, airport in builder.policy["dependency_airports"].items():
        node = builder.node(
            f"dependency:{key}",
            "dependency",
            f"dependency:{key}",
            source="international_roster",
            source_key=key,
        )
        builder.pair(node, f"airport:{airport}", "airport_handling", GENERAL, ["policy"])
    return borders(builder)


def borders(builder: graph.GraphBuilder) -> list[dict[str, str]]:
    selected = {
        "3801": ("26163", "canada"),
        "3004": ("53073", "canada"),
        "2304": ("48479", "mexico"),
    }
    rows = []
    with (source.DATA / "bts_border/border_crossing_entry_data.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            if (
                row["Port Code"] in selected
                and "2024" in row["Date"]
                and row["Measure"] == "Trucks"
            ):
                rows.append(row)
    for code, (county, counterpart) in selected.items():
        found = [row for row in rows if row["Port Code"] == code]
        if not found:
            raise ReferenceBuildError("border_source")
        row = sorted(found, key=lambda item: item["Date"])[0]
        node = builder.node(
            f"border:{code}",
            "border",
            f"county:{county}",
            row["Latitude"],
            row["Longitude"],
            "border",
            code,
        )
        builder.pair(node, f"county:{county}", "local_road", ALL, ["border", "policy"])
        builder.pair(node, f"foreign:{counterpart}", "border", ALL, ["border", "policy"])
    return sorted(rows, key=lambda row: (row["Port Code"], row["Date"]))


def bulk(builder: graph.GraphBuilder) -> list[dict[str, Any]]:
    """Source flags are cargo-specific; the TAPS connection is directed crude only."""
    rows = source.query(
        source.PIPE,
        "Intermodal_Freight_Facilities_Pipeline_Terminals",
        "TERM_ID,TERM_NAME,STATE_FIPS,CNTY_FIPS,TRUCK,WATER,CRUDE_OIL,REFINED,LATITUDE,LONGITUDE,VAL_DATE",
    )
    selected = {
        "02185014": ("02185", ["crude_oil"]),
        "02261016": ("02063", ["crude_oil"]),
        "53053014": ("53053", ["crude_oil", "refined_liquid"]),
        "02020005": ("02020", ["refined_liquid"]),
        "02013001": ("02013", ["refined_liquid"]),
        "02016002": ("02016", ["refined_liquid"]),
        "02122012": ("02122", ["refined_liquid"]),
        "15001002": ("15001", ["refined_liquid"]),
        "15003007": ("15003", ["crude_oil", "refined_liquid"]),
    }
    facilities = []
    for row in rows:
        if row["TERM_ID"] not in selected:
            continue
        county, cargo = selected[row["TERM_ID"]]
        if any(row["CRUDE_OIL" if item == "crude_oil" else "REFINED"] != "Y" for item in cargo):
            raise ReferenceBuildError("pipeline_source_commodity")
        key = builder.node(
            f"liquid:{row['TERM_ID']}",
            "liquid",
            f"county:{county}",
            str(row["LATITUDE"]),
            str(row["LONGITUDE"]),
            "pipeline_terminals",
            row["TERM_ID"],
        )
        target = "trunk:53033" if county == "53053" else f"county:{county}"
        builder.pair(key, target, "handling", cargo, ["pipeline_terminals", "policy"])
        facilities.append(
            {
                "source_id": "pipeline_terminals",
                "key": row["TERM_ID"],
                "fields": {
                    key: (None if value is None else str(value)) for key, value in row.items()
                },
            }
        )
    builder.edge(
        "liquid:02185014", "liquid:02261016", "pipeline", ["crude_oil"], ["taps", "policy"]
    )
    builder.pair(
        "liquid:02261016",
        "liquid:53053014",
        "sea_domestic",
        ["crude_oil"],
        ["pipeline_terminals", "taps", "policy"],
    )
    builder.pair(
        "liquid:02020005",
        "liquid:53053014",
        "sea_domestic",
        ["refined_liquid"],
        ["pipeline_terminals", "policy"],
    )
    for terminal in ("02013001", "02016002", "02122012", "15001002", "15003007"):
        builder.pair(
            f"liquid:{terminal}",
            "liquid:53053014",
            "sea_domestic",
            ["refined_liquid"],
            ["pipeline_terminals", "policy"],
        )
    builder.pair(
        "liquid:15003007",
        "liquid:02261016",
        "sea_domestic",
        ["crude_oil"],
        ["pipeline_terminals", "taps", "policy"],
    )
    # Richardson Highway supplies a documented inland bulk connection, not all Alaska roads.
    builder.pair("county:02063", "county:02090", "regional_road", ALL, ["richardson", "policy"])
    red_dog = builder.node(
        "bulk:red_dog", "bulk", "county:02188", source="red_dog_dnr", source_key="DMTS port"
    )
    builder.pair("county:02188", red_dog, "local_road", ["dry_bulk"], ["red_dog_dnr", "policy"])
    los_angeles = builder.node(
        "bulk:los_angeles",
        "bulk",
        "county:06037",
        source="los_angeles_bulk",
        source_key="port complex dry/liquid bulk",
    )
    builder.pair(los_angeles, "trunk:06037", "handling", ALL, ["los_angeles_bulk", "policy"])
    builder.edge(
        red_dog,
        los_angeles,
        "sea_domestic",
        ["dry_bulk"],
        ["red_dog_dnr", "red_dog_season", "policy"],
    )
    for counterpart in builder.policy["counterpart_gateways"]:
        builder.pair(
            los_angeles,
            f"foreign:{counterpart}",
            "sea_foreign",
            list(graph.CARGO[1:]),
            ["los_angeles_bulk", "policy"],
        )
    return facilities
