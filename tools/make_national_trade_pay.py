#!/usr/bin/env python3
"""The pay of each trade by place (rule O2).

Withheld county jobs are placed under their published parents, and each admitted
cohort group is given the wage that its own county publishes, or else its
state's, its nation's, or the nation's over all ownerships. The table is derived
only from the version 2 jobs basis and the version 2 cohort table; it reads no
raw source. Version 1's files are never edited.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Final

import make_national_cohort_reference_v2 as cohort_v2
import make_national_qcew_function_basis as basis
import make_national_qcew_function_basis_v2 as v2
from make_national_cohort_reference import pinned_input
from make_national_county_reference import (
    ROOT,
    ReferenceBuildError,
    ensure_output_paths,
    provenance_path,
    sha256,
)
from make_national_qcew_function_basis_v2 import SourceRow

ARTIFACT_OUT: Final = ROOT / "src/babylon/data/reference/economy/national_trade_pay_2024.csv.gz"
METADATA_OUT: Final = ARTIFACT_OUT.with_name("national_trade_pay_2024.metadata.json")
COLUMNS: Final = (
    "county_geoid",
    "function_id",
    "ownership_code",
    "jobs",
    "payroll_usd",
    "jobs_rule",
    "wage_rule",
    "wage_jobs",
    "wage_payroll_usd",
)
JOBS_RULES: Final = ("published", "placed", "partial")
WAGE_RULES: Final = ("county", "state", "nation", "nation_all_ownerships")
PLACEMENT_ORDER: Final = ("115", "312", "334", "335", "336", "11", "31-33", "53", "10")
OWNERSHIPS: Final = ("1", "2", "3", "5")


def subtree(parent: str, leaves: Iterable[str]) -> tuple[str, ...]:
    """The leaves a parent code holds, in the order given."""
    if parent == "10":
        return tuple(leaves)
    if parent in basis.SECTORS:
        return tuple(code for code in leaves if basis.parent_sector(code) == parent)
    return tuple(code for code in leaves if len(code) == 4 and code.startswith(parent))


def apportion(total: int, weights: Sequence[tuple[str, int]]) -> dict[str, int]:
    """Share `total` by weight: floors first, then one unit each to the largest remainders."""
    if total < 0 or not weights:
        raise ReferenceBuildError("apportion_input")
    effective = [(code, weight) for code, weight in weights]
    if sum(weight for _, weight in effective) == 0:
        effective = [(code, 1) for code, _ in effective]
    denominator = sum(weight for _, weight in effective)
    shares: dict[str, int] = {}
    remainders: list[tuple[Fraction, str]] = []
    for code, weight in effective:
        quotient, remainder = divmod(total * weight, denominator)
        shares[code] = quotient
        remainders.append((Fraction(remainder, denominator), code))
    left = total - sum(shares.values())
    for _, code in sorted(remainders, key=lambda item: (-item[0], item[1]))[:left]:
        shares[code] += 1
    return shares


def _published(row: SourceRow) -> bool:
    return (
        row.disclosure_code == ""
        and row.annual_avg_jobs is not None
        and row.annual_payroll_usd is not None
    )


def place_withheld(
    leaves: Sequence[SourceRow], parents: Mapping[str, SourceRow]
) -> dict[str, tuple[int, int]]:
    """Place the withheld leaves of one county and ownership under their published parents."""
    codes = tuple(row.naics_code for row in leaves)
    by_code = {row.naics_code: row for row in leaves}
    result: dict[str, tuple[int, int]] = {}
    for code in PLACEMENT_ORDER:
        top = parents.get(code)
        if top is None or not _published(top):
            continue
        members = subtree(code, codes)
        waiting = [c for c in members if not _published(by_code[c]) and c not in result]
        if not waiting:
            continue
        have_jobs = have_pay = 0
        for member in members:
            if member in result:
                have_jobs += result[member][0]
                have_pay += result[member][1]
            elif _published(by_code[member]):
                have_jobs += by_code[member].annual_avg_jobs or 0
                have_pay += by_code[member].annual_payroll_usd or 0
        weights = [(c, by_code[c].annual_avg_establishments) for c in waiting]
        jobs = apportion(max(0, (top.annual_avg_jobs or 0) - have_jobs), weights)
        payroll = apportion(max(0, (top.annual_payroll_usd or 0) - have_pay), weights)
        for member in waiting:
            result[member] = (jobs[member], payroll[member])
    return result


@dataclass(frozen=True)
class TradePay:
    county_geoid: str
    function_id: str
    ownership_code: str
    jobs: int
    payroll_usd: int
    jobs_rule: str
    wage_rule: str
    wage_jobs: int
    wage_payroll_usd: int


def _sum_published(rows: Iterable[SourceRow]) -> tuple[int, int] | None:
    jobs = payroll = 0
    for row in rows:
        if _published(row):
            jobs += row.annual_avg_jobs or 0
            payroll += row.annual_payroll_usd or 0
    return (jobs, payroll) if jobs > 0 and payroll > 0 else None


def pay_rows(rows: Sequence[SourceRow], mapping: basis.FunctionMapping) -> tuple[TradePay, ...]:
    """One row per admitted group, in the cohort table's order."""
    leaves: dict[tuple[str, str], list[SourceRow]] = defaultdict(list)
    parents: dict[tuple[str, str], dict[str, SourceRow]] = defaultdict(dict)
    outside: dict[tuple[str, str, str], list[SourceRow]] = defaultdict(list)
    for row in rows:
        if row.row_role == "county_leaf":
            leaves[(row.area_fips, row.ownership_code)].append(row)
        elif row.row_role == "county_parent":
            parents[(row.area_fips, row.ownership_code)][row.naics_code] = row
        else:
            function = mapping.function_for(row.naics_code)
            if function is not None:
                outside[(row.area_fips, function, row.ownership_code)].append(row)
    groups: dict[tuple[str, str, str], list[SourceRow]] = defaultdict(list)
    placements: dict[tuple[str, str], dict[str, tuple[int, int]]] = {}
    for (county_id, ownership), members in leaves.items():
        members.sort(key=lambda row: row.naics_code)
        placements[(county_id, ownership)] = place_withheld(
            members, parents.get((county_id, ownership), {})
        )
        for row in members:
            function = mapping.function_for(row.naics_code)
            if function is not None:
                groups[(county_id, function, ownership)].append(row)
    result = []
    for (county_id, function, ownership), members in sorted(groups.items()):
        known = [
            sum(value or 0 for value in column)
            for column in (
                [r.annual_avg_establishments for r in members],
                [r.annual_avg_jobs for r in members],
                [r.annual_payroll_usd for r in members],
            )
        ]
        if not any(value > 0 for value in known):
            continue
        placed = placements[(county_id, ownership)]
        jobs = payroll = withheld = unplaced = 0
        for member in members:
            if _published(member):
                jobs += member.annual_avg_jobs or 0
                payroll += member.annual_payroll_usd or 0
                continue
            withheld += 1
            if member.naics_code in placed:
                jobs += placed[member.naics_code][0]
                payroll += placed[member.naics_code][1]
            else:
                unplaced += 1
        jobs_rule = "published" if not withheld else ("partial" if unplaced else "placed")
        wage_rule, pair = _wage(county_id, function, ownership, jobs_rule, jobs, payroll, outside)
        result.append(
            TradePay(county_id, function, ownership, jobs, payroll, jobs_rule, wage_rule, *pair)
        )
    return tuple(result)


def _wage(
    county_id: str,
    function: str,
    ownership: str,
    jobs_rule: str,
    jobs: int,
    payroll: int,
    outside: Mapping[tuple[str, str, str], list[SourceRow]],
) -> tuple[str, tuple[int, int]]:
    if jobs_rule != "partial" and jobs > 0 and payroll > 0:
        return "county", (jobs, payroll)
    found = _sum_published(outside.get((f"{county_id[:2]}000", function, ownership), ()))
    if found:
        return "state", found
    found = _sum_published(outside.get((v2.NATION_AREA, function, ownership), ()))
    if found:
        return "nation", found
    found = _sum_published(
        row for own in OWNERSHIPS for row in outside.get((v2.NATION_AREA, function, own), ())
    )
    if found:
        return "nation_all_ownerships", found
    raise ReferenceBuildError(f"no_wage: {county_id}/{function}/{ownership}")


def _fields(row: TradePay) -> tuple[str, ...]:
    return (
        row.county_geoid,
        row.function_id,
        row.ownership_code,
        str(row.jobs),
        str(row.payroll_usd),
        row.jobs_rule,
        row.wage_rule,
        str(row.wage_jobs),
        str(row.wage_payroll_usd),
    )


def admitted_keys(path: Path) -> list[tuple[str, str, str]]:
    """The (county, function, ownership) keys of the cohort table's admitted groups, by header name."""
    with gzip.open(path, "rt", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
        if "admitted" not in header:
            raise ReferenceBuildError("cohort_header: no admitted column")
        at = {
            name: header.index(name)
            for name in ("admitted", "county_geoid", "function_id", "ownership_code")
        }
        return [
            (r[at["county_geoid"]], r[at["function_id"]], r[at["ownership_code"]])
            for r in reader
            if r[at["admitted"]] == "1"
        ]


def build(
    *, artifact_out: Path = ARTIFACT_OUT, metadata_out: Path = METADATA_OUT
) -> dict[str, Any]:
    inputs = (
        v2.ARTIFACT_OUT,
        v2.METADATA_OUT,
        v2.MAPPING_V2_PATH,
        cohort_v2.ARTIFACT_OUT,
        cohort_v2.METADATA_OUT,
    )
    ensure_output_paths((artifact_out, metadata_out), inputs)
    sources = {
        "leaf_basis": pinned_input(v2.ARTIFACT_OUT, v2.METADATA_OUT),
        "cohort_table": pinned_input(cohort_v2.ARTIFACT_OUT, cohort_v2.METADATA_OUT),
        "function_mapping": {
            "path": provenance_path(v2.MAPPING_V2_PATH),
            "sha256": sha256(v2.MAPPING_V2_PATH),
        },
    }
    mapping = v2.load_mapping_v2()
    basis_rows = v2.read_basis_v2()
    rows = pay_rows(basis_rows, mapping)
    admitted = admitted_keys(cohort_v2.ARTIFACT_OUT)
    if admitted != [(r.county_geoid, r.function_id, r.ownership_code) for r in rows]:
        raise ReferenceBuildError("cohort_keys_differ")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(_fields(row) for row in rows)
    encoded = buffer.getvalue().encode("ascii")
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed,
    ):
        compressed.write(encoded)
    leaf_total = sum(1 for r in basis_rows if r.row_role == "county_leaf")
    placed_jobs = _placed_jobs(basis_rows)
    metadata = {
        "contract": "NationalTradePay2024V1",
        "issue": "PER-371",
        "year": 2024,
        "published_values_evidence_class": "Observed",
        "placed_values_evidence_class": "Derived",
        "artifact": {
            "path": provenance_path(artifact_out),
            "format": "csv.gz",
            "sha256": sha256(artifact_out),
            "bytes": artifact_out.stat().st_size,
            "decoded_bytes": len(encoded),
            "rows": len(rows),
            "columns": list(COLUMNS),
            "ordering": ["county_geoid", "function_id", "ownership_code"],
            "writer": {"gzip_level": 9, "mtime": 0, "line_end": "\\n", "encoding": "ascii"},
        },
        "regeneration": (
            "UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python "
            "tools/make_national_trade_pay.py"
        ),
        "sources": sources,
        "coverage": {
            "groups": len(rows),
            "county_leaf_rows": leaf_total,
            "by_jobs_rule": {k: sum(r.jobs_rule == k for r in rows) for k in JOBS_RULES},
            "by_wage_rule": {k: sum(r.wage_rule == k for r in rows) for k in WAGE_RULES},
            "jobs_placed_in_all": placed_jobs,
            "jobs_in_all": sum(r.jobs for r in rows),
            "payroll_usd_in_all": sum(r.payroll_usd for r in rows),
        },
        "semantics": {
            "placement": "Rule O2. At each published parent in the order 115, 312, 334, 335, 336, 11, 31-33, 53, 10, the jobs and payroll the parent holds beyond its published and already placed leaves are shared over its still withheld leaves by establishments, largest remainder, ties by code. A withheld parent is skipped and its leaves move up. The one clamp is zero when a rounded parent falls below its children. Leaves still withheld after the county total stay unplaced.",
            "group_totals": "A group's jobs and payroll are its published members plus its placed members. partial groups leave out their unplaced members. The pair sets pay and nothing else; where residents work is decided by the cohort table's weights.",
            "wage": "wage_rule county when the group is not partial and has positive jobs and payroll; else the published state leaf rows of the county's state for the same trade and ownership; else the national rows of the same trade and ownership; else the national rows of the trade over ownerships 1, 2, 3 and 5. The hourly wage is wage_payroll_usd / (wage_jobs x 2080), computed by the reader and not stored.",
            "rows": "One row for each admitted group of the version 2 cohort table, in its order. Suppression stays unknown outside the placed amounts, which are derived shares and never observations.",
            "jobs_placed_in_all": "Counts every job placed under a published parent, including jobs placed into leaves of groups that are not admitted and into code 99, so it can exceed the jobs the rows of this table hold from placement.",
            "limits": "No person, household allocation, recipe or capacity follows from this table. The stage 2 native reader is not built yet.",
        },
        "native_readers": [],
        "runtime_consumers": [],
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def _placed_jobs(rows: Sequence[SourceRow]) -> int:
    leaves: dict[tuple[str, str], list[SourceRow]] = defaultdict(list)
    parents: dict[tuple[str, str], dict[str, SourceRow]] = defaultdict(dict)
    for row in rows:
        if row.row_role == "county_leaf":
            leaves[(row.area_fips, row.ownership_code)].append(row)
        elif row.row_role == "county_parent":
            parents[(row.area_fips, row.ownership_code)][row.naics_code] = row
    total = 0
    for key, members in leaves.items():
        members.sort(key=lambda row: row.naics_code)
        total += sum(job for job, _ in place_withheld(members, parents.get(key, {})).values())
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    metadata = build(artifact_out=args.artifact_out, metadata_out=args.metadata_out)
    print(
        json.dumps(
            {"artifact": metadata["artifact"], "coverage": metadata["coverage"]}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
