#!/usr/bin/env python3
"""Capture disjoint 2024 goods trade with a separately dated identity roster.

Build-time evidence only: no production, money, population allocation or runtime
capacity follows from these observations. Read XLSX numeric tokens directly so
source spreadsheet tails survive without a binary-float conversion.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, localcontext
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Final

from make_national_county_reference import (
    ROOT,
    ReferenceBuildError,
    _unique_object,
    ensure_output_paths,
    provenance_path,
    sha256,
)

SOURCE_MANIFEST = ROOT / "tools/international_counterpart_2024_sources.json"
MAPPING_PATH = ROOT / "contracts/international_counterpart_membership_v1.json"
POLICY_PATH = ROOT / "contracts/international_counterpart_policy_v1.json"
ARTIFACT_OUT = (
    ROOT / "src/babylon/data/reference/economy/international_counterpart_reference_2024.csv.gz"
)
METADATA_OUT = ARTIFACT_OUT.with_name("international_counterpart_reference_2024.metadata.json")
COUNTERPARTS: Final = (
    "canada",
    "mexico",
    "china",
    "russia",
    "india",
    "japan",
    "european_union",
    "remaining_europe",
    "latin_america_caribbean",
    "west_asia_north_africa",
    "sub_saharan_africa",
    "remaining_asia_pacific",
)
CONTROLS: Final = frozenset(
    "0003 0004 0007 0009 0010 0012 0013 0014 0015 0016 0017 0018 0019 0021 0022".split()
)
DEPENDENCIES: Final = frozenset("016 316 580 581 630 850".split())
FREELY_ASSOCIATED: Final = frozenset("583 584 585".split())
XML_NS: Final = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MONTHS: Final = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
HEADER: Final = (
    "year",
    "CTY_CODE",
    "CTYNAME",
    *(f"I{x}" for x in MONTHS),
    "IYR",
    *(f"E{x}" for x in MONTHS),
    "EYR",
)
DIRECTIONS: Final = ("us_imports", "us_exports")


@dataclass(frozen=True)
class Membership:
    identity_id: str
    counterpart_id: str
    disposition: str
    us_relationship: str


@dataclass(frozen=True)
class Identity:
    identity_id: str
    identity_kind: str
    population_identity_id: str
    population_aggregation: str
    m49_code: str
    iso_alpha2: str
    area_name: str
    census_code: str = ""
    census_reporter_code: str = ""
    census_area_name: str = ""


@dataclass(frozen=True)
class TradeRow:
    census_code: str
    source_name: str
    us_imports_months: tuple[str, ...]
    us_imports_annual: str
    us_exports_months: tuple[str, ...]
    us_exports_annual: str


class HtmlRows(HTMLParser):
    """Extract literal table cells; identities are checked after extraction."""

    def __init__(self, table_id: str | None = None) -> None:
        super().__init__()
        self.table_id = table_id
        self.active = table_id is None
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table" and self.table_id is not None:
            self.active = dict(attrs).get("id") == self.table_id
        if not self.active:
            return
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self.table_id is not None:
            self.active = False
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def html_rows(path: Path, table_id: str | None = None) -> list[list[str]]:
    if path.stat().st_size > 3_000_000:
        raise ReferenceBuildError("roster_size")
    parser = HtmlRows(table_id)
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.rows


def amount(raw: str) -> Decimal | None:
    if raw == "":
        return None
    if len(raw) > 40 or not re.fullmatch(
        r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,2})?", raw, re.ASCII
    ):
        raise ReferenceBuildError(f"trade_amount: {raw!r}")
    value = Decimal(raw)
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int) or value.adjusted() > 40 or exponent < -40:
        raise ReferenceBuildError(f"trade_amount: {raw!r}")
    return value


def decimal_text(value: Decimal) -> str:
    """Only derived arithmetic uses this spelling; source tokens stay untouched."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def exact_sum(values: Iterable[Decimal]) -> Decimal:
    with localcontext() as context:
        context.prec = 120
        return sum(values, Decimal(0))


def exact_difference(left: Decimal, right: Decimal) -> str:
    with localcontext() as context:
        context.prec = 120
        return decimal_text(left - right)


def validate_membership(rows: Iterable[Membership]) -> tuple[Membership, ...]:
    members: dict[str, Membership] = {}
    for row in rows:
        if row.identity_id in members:
            raise ReferenceBuildError(f"duplicate_membership: {row.identity_id}")
        if not re.fullmatch(r"(?:m49:[0-9]{3}|census:508[23])", row.identity_id, re.ASCII):
            raise ReferenceBuildError("membership_identity")
        if row.disposition not in {"counterpart", "domestic", "us_dependency", "nonmarket"}:
            raise ReferenceBuildError("membership_disposition")
        if (row.disposition == "counterpart") != (row.counterpart_id in COUNTERPARTS):
            raise ReferenceBuildError("membership_counterpart")
        if row.disposition != "counterpart" and row.counterpart_id:
            raise ReferenceBuildError("membership_excluded_counterpart")
        code = row.identity_id.removeprefix("m49:")
        expected = (
            "us_dependency"
            if code in DEPENDENCIES
            else "domestic"
            if code == "840"
            else "nonmarket"
            if code == "010"
            else "counterpart"
        )
        relation = (
            "us_dependency"
            if code in DEPENDENCIES
            else "freely_associated_state"
            if code in FREELY_ASSOCIATED
            else "domestic"
            if code == "840"
            else "none"
        )
        if row.disposition != expected or row.us_relationship != relation:
            raise ReferenceBuildError("membership_us_relationship")
        members[row.identity_id] = row
    return tuple(members[key] for key in sorted(members))


def load_membership(path: Path = MAPPING_PATH) -> tuple[Membership, ...]:
    document = json.loads(path.read_text(), object_pairs_hook=_unique_object)
    if (
        document.get("contract") != "InternationalCounterpartMembershipV1"
        or document.get("evidence_class") != "Designed"
        or not isinstance(document.get("memberships"), list)
    ):
        raise ReferenceBuildError("membership_contract")
    rows = []
    for row in document["memberships"]:
        if (
            not isinstance(row, dict)
            or set(row) != set(Membership.__dataclass_fields__)
            or not all(isinstance(value, str) for value in row.values())
        ):
            raise ReferenceBuildError("membership_row_shape")
        rows.append(Membership(**row))
    return validate_membership(rows)


def read_identities(un_path: Path, census_path: Path) -> tuple[Identity, ...]:
    rows = html_rows(un_path, "downloadTableEN")
    headers = [
        (i, row) for i, row in enumerate(rows) if "Country or Area" in row and "M49 Code" in row
    ]
    if len(headers) != 1 or len(rows) != 249:
        raise ReferenceBuildError("un_roster_header_or_coverage")
    index, header = headers[0]
    identities: dict[str, Identity] = {}
    for row in rows[index + 1 : index + 249]:
        if len(row) != len(header):
            raise ReferenceBuildError("un_roster_row_shape")
        values = dict(zip(header, row, strict=True))
        code, iso = values["M49 Code"], values["ISO-alpha2 Code"]
        if (
            not re.fullmatch(r"[0-9]{3}", code, re.ASCII)
            or not re.fullmatch(r"[A-Z]{2}", iso, re.ASCII)
            or iso in identities
        ):
            raise ReferenceBuildError("un_roster_identity")
        key = f"m49:{code}"
        identities[iso] = Identity(
            key, "geographic_area", key, "independent_area", code, iso, values["Country or Area"]
        )
    if len(identities) != 248 or len({row.m49_code for row in identities.values()}) != 248:
        raise ReferenceBuildError("un_roster_coverage")
    for iso, code, name in (("TW", "158", "Taiwan"), ("KV", "412", "Kosovo")):
        identities[iso] = Identity(
            f"m49:{code}",
            "statistical_extension",
            f"m49:{code}",
            "independent_statistical_area",
            code,
            iso if iso == "TW" else "",
            name,
        )
    for reporter, code in (("GZ", "5082"), ("WE", "5083")):
        identities[reporter] = Identity(
            f"census:{code}",
            "trade_reporting_area",
            "m49:275",
            "trade_only_exclude_from_population",
            "275",
            "",
            "",
        )
    seen: set[str] = set()
    for row in html_rows(census_path):
        if len(row) != 3 or not re.fullmatch(r"[0-9]{4}", row[1], re.ASCII):
            continue
        name, code, reporter = row
        if reporter not in identities or code in seen or identities[reporter].census_code:
            raise ReferenceBuildError(f"census_roster_identity: {row}")
        seen.add(code)
        prior = identities[reporter]
        identities[reporter] = replace(
            prior,
            census_code=code,
            census_reporter_code=reporter,
            census_area_name=name,
            area_name=prior.area_name or name,
        )
    if len(seen) != 240:
        raise ReferenceBuildError("census_roster_coverage")
    return tuple(sorted(identities.values(), key=lambda row: row.identity_id))


def xlsx_rows(path: Path) -> Iterable[tuple[str, ...]]:
    """Pinned workbook has one country sheet and shared strings, no formulas."""
    with zipfile.ZipFile(path) as archive:
        if (
            len(archive.infolist()) != len(set(archive.namelist()))
            or sum(item.file_size for item in archive.infolist()) > 50_000_000
        ):
            raise ReferenceBuildError("workbook_size_or_duplicate_member")
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))  # noqa: S314 -- pinned, size-bounded source
        sheets = workbook.findall("m:sheets/m:sheet", XML_NS)
        if len(sheets) != 1 or sheets[0].get("name") != "country":
            raise ReferenceBuildError("workbook_sheet")
        strings_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))  # noqa: S314 -- pinned, size-bounded source
        strings = ["".join(item.itertext()) for item in strings_root.findall("m:si", XML_NS)]
        with archive.open("xl/worksheets/sheet1.xml") as stream:
            for _, row in ET.iterparse(stream, events=("end",)):  # noqa: S314 -- pinned, size-bounded source
                if row.tag != f"{{{XML_NS['m']}}}row":
                    continue
                cells: dict[str, str] = {}
                for cell in row:
                    column = cell.attrib["r"].rstrip("0123456789")
                    if column in cells or cell.find("m:f", XML_NS) is not None:
                        raise ReferenceBuildError("workbook_duplicate_cell_or_formula")
                    value = cell.find("m:v", XML_NS)
                    text = "" if value is None or value.text is None else value.text
                    kind = cell.get("t", "n")
                    if kind not in {"s", "n"}:
                        raise ReferenceBuildError("workbook_cell_type")
                    cells[column] = strings[int(text)] if kind == "s" else text
                columns = (*"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "AA", "AB", "AC")
                if set(cells) - set(columns):
                    raise ReferenceBuildError("workbook_column")
                yield tuple(cells.get(column, "") for column in columns)
                row.clear()


def validate_trade(rows: Iterable[TradeRow]) -> tuple[TradeRow, ...]:
    seen: dict[str, TradeRow] = {}
    for row in rows:
        if row.census_code in seen:
            raise ReferenceBuildError(f"duplicate_trade: {row.census_code}")
        if not re.fullmatch(r"[0-9]{4}", row.census_code, re.ASCII) or not row.source_name:
            raise ReferenceBuildError("trade_identity")
        for direction in DIRECTIONS:
            months = getattr(row, f"{direction}_months")
            if len(months) != 12:
                raise ReferenceBuildError("trade_month_count")
            for raw in (*months, getattr(row, f"{direction}_annual")):
                amount(raw)
        seen[row.census_code] = row
    return tuple(seen[key] for key in sorted(seen))


def read_trade(path: Path) -> tuple[TradeRow, ...]:
    rows = iter(xlsx_rows(path))
    if next(rows, ()) != HEADER:
        raise ReferenceBuildError("trade_header")
    return validate_trade(
        TradeRow(row[1], row[2], row[3:15], row[15], row[16:28], row[28])
        for row in rows
        if row[0] == "2024"
    )


def check_trade_coverage(rows: Iterable[TradeRow], by_census: Mapping[str, Identity]) -> None:
    for row in rows:
        if row.census_code not in CONTROLS and row.census_code not in by_census:
            raise ReferenceBuildError(f"unmapped_trade: {row.census_code}")


def summarize(rows: Iterable[TradeRow]) -> dict[str, dict[str, Any]]:
    records = tuple(rows)
    summary = {}
    for direction in DIRECTIONS:
        values = [amount(getattr(row, f"{direction}_annual")) for row in records]
        known = [value for value in values if value is not None]
        total = decimal_text(exact_sum(known))
        summary[direction] = {
            "published_sum": total,
            "published_rows": len(known),
            "missing_rows": len(values) - len(known),
            "complete_sum": total if len(values) == len(known) else None,
        }
    return summary


def trade_fields(row: TradeRow | None) -> dict[str, str]:
    fields = {
        "trade_row_status": "published" if row is not None else "not_published",
        "trade_source_name": row.source_name if row is not None else "",
    }
    for direction in DIRECTIONS:
        annual = getattr(row, f"{direction}_annual") if row is not None else ""
        months = getattr(row, f"{direction}_months") if row is not None else ("",) * 12
        values = [amount(raw) for raw in months]
        known = [value for value in values if value is not None]
        monthly = exact_sum(known) if len(known) == 12 else None
        value = amount(annual)
        fields.update(
            {
                f"{direction}_annual_raw": annual,
                f"{direction}_status": "published"
                if value is not None
                else "missing_cell"
                if row is not None
                else "not_published",
                f"{direction}_monthly_sum": "" if monthly is None else decimal_text(monthly),
                f"{direction}_annual_minus_monthly": ""
                if value is None or monthly is None
                else exact_difference(value, monthly),
            }
        )
        fields.update(
            {
                f"{direction}_{month.lower()}_raw": raw
                for month, raw in zip(MONTHS, months, strict=True)
            }
        )
    return fields


def verify_sources(source_root: Path, manifest_path: Path = SOURCE_MANIFEST) -> dict[str, Path]:
    document = json.loads(manifest_path.read_text(), object_pairs_hook=_unique_object)
    if document.get("contract") != "InternationalCounterpartSourcesV1":
        raise ReferenceBuildError("source_contract")
    paths: dict[str, Path] = {}
    for source in document["sources"]:
        path = source_root / source["path"]
        if source["id"] in paths or not path.resolve().is_relative_to(source_root.resolve()):
            raise ReferenceBuildError("source_identity_or_path")
        if (
            not path.is_file()
            or path.stat().st_size != source["bytes"]
            or sha256(path) != source["sha256"]
        ):
            raise ReferenceBuildError(f"source_digest: {source['id']}")
        paths[source["id"]] = path
    return paths


def capture(
    identities: tuple[Identity, ...],
    trades: tuple[TradeRow, ...],
    memberships: tuple[Membership, ...],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    membership = {row.identity_id: row for row in validate_membership(memberships)}
    if set(membership) != {row.identity_id for row in identities}:
        raise ReferenceBuildError("membership_roster_coverage")
    by_census = {row.census_code: row for row in identities if row.census_code}
    trades = validate_trade(trades)
    check_trade_coverage(trades, by_census)
    controls = [row for row in trades if row.census_code in CONTROLS]
    leaves = [row for row in trades if row.census_code not in CONTROLS]
    if {row.census_code for row in controls} != CONTROLS or len(leaves) != 233:
        raise ReferenceBuildError("trade_2024_coverage")
    by_trade = {row.census_code: row for row in leaves}
    output = []
    for identity in identities:
        assigned = membership[identity.identity_id]
        output.append(
            {
                **asdict(identity),
                **asdict(assigned),
                **trade_fields(by_trade.get(identity.census_code)),
            }
        )
    totals = []
    for group in COUNTERPARTS:
        selected = [
            row
            for row in leaves
            if membership[by_census[row.census_code].identity_id].counterpart_id == group
        ]
        area_rows = [row for row in output if row["counterpart_id"] == group]
        totals.append(
            {
                "counterpart_id": group,
                "identity_rows": len(area_rows),
                "identities_without_trade_row": sum(
                    row["trade_row_status"] == "not_published" for row in area_rows
                ),
                "source_leaf_rows": len(selected),
                **summarize(selected),
            }
        )
    world = next(row for row in controls if row.census_code == "0015")
    reconciliation = {}
    for direction in DIRECTIONS:
        leaf_summary = summarize(leaves)[direction]
        leaf_sum = Decimal(leaf_summary["published_sum"])
        group_sum = exact_sum(Decimal(total[direction]["published_sum"]) for total in totals)
        if group_sum != leaf_sum:
            raise ReferenceBuildError("counterpart_sum_conservation")
        world_value = amount(getattr(world, f"{direction}_annual"))
        reconciliation[direction] = {
            "leaf_annual_sum": decimal_text(leaf_sum),
            "leaf_missing_annual_rows": leaf_summary["missing_rows"],
            "counterpart_annual_sum": decimal_text(group_sum),
            "world_nsa_annual_raw": getattr(world, f"{direction}_annual"),
            "leaf_minus_world_nsa": None
            if world_value is None
            else exact_difference(leaf_sum, world_value),
        }
    return output, {
        "controls": [
            {
                "census_code": row.census_code,
                "aggregation_disposition": "control_only_exclude_from_additive_totals",
                **trade_fields(row),
            }
            for row in controls
        ],
        "counterpart_totals": totals,
        "reconciliation": reconciliation,
    }


def build(
    *,
    source_root: Path,
    artifact_out: Path = ARTIFACT_OUT,
    metadata_out: Path = METADATA_OUT,
    source_manifest: Path = SOURCE_MANIFEST,
    mapping_path: Path = MAPPING_PATH,
    policy_path: Path = POLICY_PATH,
) -> dict[str, Any]:
    paths = verify_sources(source_root, source_manifest)
    ensure_output_paths(
        (artifact_out, metadata_out), (*paths.values(), source_manifest, mapping_path, policy_path)
    )
    policy = json.loads(policy_path.read_text(), object_pairs_hook=_unique_object)
    if (
        policy.get("contract") != "InternationalCounterpartPolicyV1"
        or policy.get("evidence_class") != "Designed"
        or policy.get("counterparts") != list(COUNTERPARTS)
    ):
        raise ReferenceBuildError("membership_policy")
    identities = read_identities(paths["un_m49_overview"], paths["census_schedule_c"])
    rows, diagnostics = capture(
        identities, read_trade(paths["census_trade"]), load_membership(mapping_path)
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed,
    ):
        compressed.write(stream.getvalue().encode("utf-8"))
    metadata = {
        "contract": "InternationalCounterpartReference2024V1",
        "issue": "PER-31",
        "trade_year": 2024,
        "identity_snapshot": "2026-09-20",
        "runtime_consumers": [],
        "classifications": {
            "source_identity_and_decimal_tokens": "Observed",
            "crosswalk_sums_digests": "Derived",
            "membership_and_aggregation_policy": "Designed",
        },
        "semantics": policy["semantics"],
        "edge_decisions": policy["edge_decisions"],
        "artifact": {
            "path": provenance_path(artifact_out),
            "bytes": artifact_out.stat().st_size,
            "sha256": sha256(artifact_out),
            "rows": len(rows),
        },
        "membership": {"path": provenance_path(mapping_path), "sha256": sha256(mapping_path)},
        "policy": {"path": provenance_path(policy_path), "sha256": sha256(policy_path)},
        "source_manifest": {
            "path": provenance_path(source_manifest),
            "sha256": sha256(source_manifest),
        },
        **diagnostics,
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("/media/user/data/babylon-data"))
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    metadata = build(
        source_root=args.source_root, artifact_out=args.artifact_out, metadata_out=args.metadata_out
    )
    print(json.dumps(metadata["artifact"], sort_keys=True))


if __name__ == "__main__":
    main()
