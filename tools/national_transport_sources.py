"""Read selected source transport evidence; observed movement is not capacity."""

from __future__ import annotations

import csv
import gzip
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import geopandas as gpd  # type: ignore[import-untyped]
from make_national_county_reference import (
    ARTIFACT_OUT,
    ReferenceBuildError,
    provenance_path,
    sha256,
)
from shapely.geometry import Point  # type: ignore[import-untyped]

COUNTY_REFERENCE_PATH = ARTIFACT_OUT
DATA = Path("/media/user/data/babylon-data")
FAF = DATA / "freight/faf"
AIR = DATA / "dot/NTAD_Aviation_Facilities_698356094499483505.geodatabase"
SEA = (
    DATA
    / "dot/NTAD_Intermodal_Freight_Facilities_Marine_Roll_on_Roll_off_-294017341140200559.geodatabase"
)
PIPE = (
    DATA
    / "dot/NTAD_Intermodal_Freight_Facilities_Pipeline_Terminals_5225567625332244848.geodatabase"
)
TIGER = DATA / "tiger/county/tl_2024_us_county.shp"
FLOW = FAF / "region/FAF5.7.1_2018-2024.csv"
METRICS = ("tons_2024", "value_2024", "current_value_2024", "tmiles_2024")
GROUPS = ("sctg0109", "sctg1014", "sctg1519", "sctg2033", "sctg3499")


def decimal_token(raw: str) -> Decimal | None:
    if raw == "":
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ReferenceBuildError("flow_decimal") from exc
    if raw.strip() != raw or not value.is_finite() or value < 0:
        raise ReferenceBuildError("flow_decimal")
    return value


def group(code: str) -> str:
    if len(code) != 2 or not code.isascii() or not code.isdigit() or not 1 <= int(code) <= 99:
        raise ReferenceBuildError("flow_commodity")
    return GROUPS[next(i for i, limit in enumerate((9, 14, 19, 33, 99)) if int(code) <= limit)]


def aggregate_flows(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    """Top two incoming/outgoing domestic OD rows per zone/mode/SCTG5; full controls."""
    domestic: dict[tuple[str, ...], list[Any]] = {}
    foreign: dict[tuple[str, ...], list[Any]] = {}
    controls: dict[tuple[str, ...], list[Any]] = {}
    count = 0
    for row in rows:
        trade, mode, commodity = row["trade_type"], row["dms_mode"], group(row["sctg2"])
        if trade not in {"1", "2", "3"} or mode not in set("12345678"):
            raise ReferenceBuildError("flow_identity")
        values = [decimal_token(row[key]) for key in METRICS]
        _add(controls, (trade, mode, commodity), values)
        if trade == "1":
            _add(domestic, (row["dms_orig"], row["dms_dest"], mode, commodity), values)
        else:
            region = row["fr_orig" if trade == "2" else "fr_dest"]
            external_mode = row["fr_inmode" if trade == "2" else "fr_outmode"]
            if region not in {str(i) for i in range(801, 809)} or external_mode not in set(
                "12345678"
            ):
                raise ReferenceBuildError("foreign_flow_identity")
            _add(foreign, (trade, region, external_mode, mode, commodity), values)
        count += 1
    selected: set[tuple[str, ...]] = set()
    for endpoint in (0, 1):
        buckets: dict[tuple[str, ...], list[tuple[str, ...]]] = defaultdict(list)
        for key in domestic:
            buckets[(key[endpoint], key[2], key[3])].append(key)
        for keys in buckets.values():
            selected.update(sorted(keys, key=lambda key: (-domestic[key][1][0], key))[:2])
    return {
        "source_rows": count,
        "domestic_aggregate_rows": len(domestic),
        "domestic": _encoded({key: domestic[key] for key in selected}),
        "foreign": _encoded(foreign),
        "controls": _encoded(controls),
    }


def _add(
    target: dict[tuple[str, ...], list[Any]], key: tuple[str, ...], values: list[Decimal | None]
) -> None:
    item = target.setdefault(key, [0, [Decimal(0)] * 4, [0] * 4])
    item[0] += 1
    for index, value in enumerate(values):
        if value is not None:
            item[1][index] += value
            item[2][index] += 1


def _encoded(rows: dict[tuple[str, ...], list[Any]]) -> list[dict[str, Any]]:
    return [
        {
            "key": list(key),
            "rows": value[0],
            "values": [
                {"known_sum": str(total), "published": known}
                for total, known in zip(value[1], value[2], strict=True)
            ],
        }
        for key, value in sorted(rows.items())
    ]


def county_rows() -> dict[str, dict[str, str]]:
    with gzip.open(ARTIFACT_OUT, "rt", newline="") as stream:
        rows = {row["county_geoid"]: row for row in csv.DictReader(stream)}
    if len(rows) != 3144:
        raise ReferenceBuildError("county_roster")
    return rows


def factors(counties: set[str]) -> tuple[list[list[str]], dict[str, str]]:
    result: list[list[str]] = []
    zones: dict[str, str] = {}
    for mode in ("truck", "rail", "water", "pipeline"):
        for direction, short in (("origin", "orig"), ("destination", "dest")):
            with (FAF / f"{mode}_{direction}_factors.csv").open(newline="") as stream:
                for row in csv.DictReader(stream):
                    county = row[f"dms_{short}_cnty"].zfill(5)
                    zone = row[f"dms_{short}"].zfill(3)
                    commodity, factor = row["sctgG5"], row[f"f_{short}"]
                    if (
                        county not in counties
                        or commodity not in GROUPS
                        or decimal_token(factor) is None
                    ):
                        raise ReferenceBuildError("factor")
                    result.append([mode, direction, county, zone, commodity, factor])
                    if mode == "truck":
                        if zones.setdefault(county, zone) != zone:
                            raise ReferenceBuildError("county_zone")
    grouped: dict[tuple[str, ...], tuple[str, int]] = {}
    for factor_row in result:
        key, value = tuple(factor_row[:5]), factor_row[5]
        if key in grouped and grouped[key][0] != value:
            raise ReferenceBuildError("contradictory_factor")
        grouped[key] = (value, grouped.get(key, (value, 0))[1] + 1)
    result = [list(key) + [value, str(count)] for key, (value, count) in sorted(grouped.items())]
    if set(zones) != counties or len(set(zones.values())) != 132:
        raise ReferenceBuildError("factor_coverage")
    return result, zones


def query(path: Path, table: str, columns: str) -> list[dict[str, Any]]:
    """Only fixed trusted table/column literals are supplied by this builder."""
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(f"SELECT {columns} FROM {table}")]  # noqa: S608
    finally:
        connection.close()


def airports(
    counties: dict[str, dict[str, str]], policy: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Spatially admit public/open airports; do not trust obsolete county labels."""
    raw = query(
        AIR,
        "Aviation_Facilities",
        "SITE_NO,ARPT_ID,ICAO_ID,ARPT_NAME,SITE_TYPE_CODE,ARPT_STATUS,FACILITY_USE_CODE,STATE_CODE,COUNTY_NAME,COUNTRY_CODE,LAT_DECIMAL,LONG_DECIMAL,EFF_DATE",
    )
    eligible = {
        row["ARPT_ID"]: row
        for row in raw
        if row["ARPT_STATUS"] == "O"
        and row["FACILITY_USE_CODE"] == "PU"
        and row["SITE_TYPE_CODE"] == "A"
    }
    shape = gpd.read_file(TIGER, columns=["GEOID", "geometry"])
    geometries = dict(zip(shape["GEOID"], shape.geometry, strict=True))
    islands = {key for key in counties if key[:2] in {"02", "15"}} | {"25007", "25019", "53055"}
    selected = dict(policy["airport_overrides"])
    for county in sorted(islands):
        candidates = [
            key
            for key, row in eligible.items()
            if geometries[county].covers(Point(row["LONG_DECIMAL"], row["LAT_DECIMAL"]))
        ]
        if county not in selected:
            if not candidates:
                raise ReferenceBuildError(f"airport_absent:{county}")
            selected[county] = min(candidates)
        if selected[county] not in candidates:
            raise ReferenceBuildError(f"airport_outside_county:{county}")
    ids = set(selected.values()) | set(policy["anchor_airports"])
    if not ids <= eligible.keys():
        raise ReferenceBuildError("gateway_airport_unavailable")
    return [eligible[key] for key in sorted(ids)], selected


def source_record(key: str, path: Path, relation: str) -> dict[str, Any]:
    return {
        "id": key,
        "path": provenance_path(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "relation": relation,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def validate_facility_locations(nodes: list[dict[str, Any]]) -> None:
    """Validate modern county bindings for retained gateway points, including oldFIPS."""
    shape = gpd.read_file(TIGER, columns=["GEOID", "geometry"])
    geometries = dict(zip(shape["GEOID"], shape.geometry, strict=True))
    for row in nodes:
        if row["kind"] not in {"airport", "marine", "liquid", "border"} or not row[
            "location"
        ].startswith("county:"):
            continue
        county = row["location"].split(":", 1)[1]
        if not geometries[county].covers(Point(float(row["longitude"]), float(row["latitude"]))):
            raise ReferenceBuildError(f"gateway_outside_county:{row['id']}:{county}")
