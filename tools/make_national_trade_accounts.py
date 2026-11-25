"""Fold the BEA 2024 supply and use tables into the twelve trades (sources and mapping).

Reads the pinned BEA workbooks only when run by hand against ``--source-root``; the
sheet reader, the industry mapping and the owner-occupied housing shares live here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Final

import make_national_qcew_function_basis as basis
import openpyxl  # type: ignore[import-untyped]
from make_national_county_reference import (
    ROOT,
    ReferenceBuildError,
    _unique_object,
    sha256,
)
from make_national_qcew_function_basis_v2 import FUNCTION_IDS_V2

SOURCES: Final = ROOT / "tools/national_trade_accounts_2024_sources.json"
ACCOUNTS_MAPPING: Final = ROOT / "contracts/national_accounts_trade_mapping_v1.json"
TRADES: Final = FUNCTION_IDS_V2
OWNER: Final = "owner_occupied_housing"
SOURCE_CONTRACT: Final = "NationalTradeAccounts2024SourcesV1"
SOURCE_IDS: Final = ("use_summary", "supply_summary", "use_detail", "supply_detail")
MAPPING_CONTRACT: Final = "NationalAccountsTradeMappingV1"
RESIDUAL_ROWS: Final = {"Used": "scrap_used", "Other": "noncomparable"}
SHARE_NAMES: Final = (
    "intermediate_inputs",
    "compensation",
    "production_taxes",
    "gross_operating_surplus",
    "households",
    "product_subsidies",
)
SUMMARY_INDUSTRY_COUNT: Final = 71


@dataclass(frozen=True)
class BeaSheet:
    """One BEA sheet as integers in USD millions, keyed by row and column code."""

    rows: tuple[str, ...]
    columns: tuple[str, ...]
    cells: dict[tuple[str, str], int]

    def get(self, row: str, column: str) -> int:
        return self.cells.get((row, column), 0)


def verify_accounts_sources(source_root: Path, manifest: Path = SOURCES) -> dict[str, Path]:
    """Refuse a workbook whose size or SHA-256 differs from the pin, before parsing."""
    document = json.loads(manifest.read_bytes(), object_pairs_hook=_unique_object)
    if document.get("contract") != SOURCE_CONTRACT:
        raise ReferenceBuildError("source_manifest_contract")
    found: dict[str, Path] = {}
    for entry in document["sources"]:
        identity, relative = entry["id"], Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or identity in found:
            raise ReferenceBuildError("source_manifest_path_or_duplicate")
        source = source_root / relative
        if source.stat().st_size != entry["bytes"] or sha256(source) != entry["sha256"]:
            raise ReferenceBuildError(f"source_digest: {identity}")
        found[identity] = source
    if set(found) != set(SOURCE_IDS):
        raise ReferenceBuildError("source_manifest_coverage")
    return found


def _code(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_sheet(path: Path, sheet: str, *, code_row: int, first_row: int) -> BeaSheet:
    """Read column codes from ``code_row`` (from column index 2) and rows from ``first_row``.

    Both are 0-based. The header stops at its first empty cell and the rows at the first
    empty row code. A cell is an ``int``, ``None`` or ``"..."``; the last two read 0.
    """
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        grid = list(workbook[sheet].iter_rows(values_only=True))
    finally:
        workbook.close()
    columns: list[str] = []
    for value in grid[code_row][2:]:
        code = _code(value)
        if not code:
            break
        if code in columns:
            raise ReferenceBuildError(f"bea_duplicate_code: {sheet}/{code}")
        columns.append(code)
    rows: list[str] = []
    cells: dict[tuple[str, str], int] = {}
    for line in grid[first_row:]:
        row = _code(line[0] if line else None)
        if not row:
            break
        if row in rows:
            raise ReferenceBuildError(f"bea_duplicate_code: {sheet}/{row}")
        rows.append(row)
        for offset, column in enumerate(columns):
            value = line[2 + offset] if 2 + offset < len(line) else None
            if value is None or (isinstance(value, str) and value.strip() == "..."):
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise ReferenceBuildError(f"bea_cell: {sheet}/{row}/{column}")
            cells[(row, column)] = value
    return BeaSheet(tuple(rows), tuple(columns), cells)


@dataclass(frozen=True)
class AccountsMapping:
    document: dict[str, Any]
    whole: dict[str, str]
    splits: dict[str, dict[str, tuple[str, ...]]]
    owner_shares: dict[str, Fraction]


def _documented_figures(document: dict[str, Any]) -> dict[str, tuple[int, int]]:
    shares = document["owner_occupied_basis"]["shares"]
    if set(shares) != set(SHARE_NAMES):
        raise ReferenceBuildError("accounts_mapping_owner_shares")
    figures: dict[str, tuple[int, int]] = {}
    for name in SHARE_NAMES:
        owner, total = shares[name]["figures"]
        if total == 0:
            raise ReferenceBuildError(f"accounts_mapping_owner_shares: {name}")
        figures[name] = (owner, total)
    return figures


def validate_accounts_mapping(
    document: dict[str, Any], functions: basis.FunctionMapping
) -> AccountsMapping:
    if (
        document.get("contract") != MAPPING_CONTRACT
        or document.get("evidence_class") != "Designed"
        or document.get("source_vintage") != 2024
    ):
        raise ReferenceBuildError("accounts_mapping_identity")
    trades = set(TRADES)
    whole: dict[str, str] = {}
    for entry in document["whole"]:
        code, trade = entry["code"], entry["trade"]
        if trade not in trades:
            raise ReferenceBuildError(f"accounts_mapping_trade: {code}")
        if code in whole:
            raise ReferenceBuildError(f"accounts_mapping_coverage: {code} repeated")
        whole[code] = trade
    owners = [entry["code"] for entry in document["whole"] if entry.get("owner_occupied")]
    if owners != ["HS"] or whole.get("HS") != "construction_housing":
        raise ReferenceBuildError("accounts_mapping_owner")
    splits: dict[str, dict[str, tuple[str, ...]]] = {}
    for entry in document["splits"]:
        code, under = entry["code"], tuple(entry["under"])
        if code in splits or code in whole:
            raise ReferenceBuildError(f"accounts_mapping_coverage: {code} repeated")
        parts = {trade: tuple(naics) for trade, naics in entry["parts"].items()}
        listed: set[str] = set()
        for trade, naics_codes in parts.items():
            if trade not in trades:
                raise ReferenceBuildError(f"accounts_mapping_trade: {code}")
            for naics in naics_codes:
                if (
                    naics in listed
                    or functions.code_to_function.get(naics) != trade
                    or not naics.startswith(under)
                ):
                    raise ReferenceBuildError(f"accounts_split_naics: {code}/{naics}")
                listed.add(naics)
        leaves = {
            naics
            for naics in functions.code_to_function
            if naics.startswith(under) and not naics.startswith("99")
        }
        for naics in sorted(leaves - listed):
            raise ReferenceBuildError(f"accounts_split_naics: {code}/{naics}")
        splits[code] = parts
    codes = document["industry_codes"]
    if (
        len(codes) != SUMMARY_INDUSTRY_COUNT
        or len(set(codes)) != len(codes)
        or set(codes) != set(whole) | set(splits)
        or len(whole) + len(splits) != len(codes)
    ):
        raise ReferenceBuildError("accounts_mapping_coverage")
    if document["residual_rows"] != RESIDUAL_ROWS:
        raise ReferenceBuildError("accounts_mapping_residual")
    shares = {
        name: Fraction(owner, total)
        for name, (owner, total) in _documented_figures(document).items()
    }
    return AccountsMapping(document, whole, splits, shares)


def load_accounts_mapping(path: Path, functions: basis.FunctionMapping) -> AccountsMapping:
    document = json.loads(path.read_bytes(), object_pairs_hook=_unique_object)
    return validate_accounts_mapping(document, functions)


def check_summary_coverage(mapping: AccountsMapping, use_summary: BeaSheet) -> None:
    """The contract's 71 industries must be the summary sheet's, in its column order."""
    sheet_codes = [c for c in use_summary.columns if c in mapping.whole or c in mapping.splits]
    if sheet_codes != list(mapping.document["industry_codes"]) or use_summary.columns[
        : len(sheet_codes)
    ] != tuple(sheet_codes):
        raise ReferenceBuildError("accounts_mapping_coverage")


def owner_occupied_shares(use_detail: BeaSheet, supply_detail: BeaSheet) -> dict[str, Fraction]:
    """Recompute the 2017 owner-occupied shares and refuse any that differ from the contract."""
    document = json.loads(ACCOUNTS_MAPPING.read_bytes(), object_pairs_hook=_unique_object)
    documented = _documented_figures(document)
    sheets = {"use_detail": use_detail, "supply_detail": supply_detail}
    found: dict[str, Fraction] = {}
    for name, spec in document["owner_occupied_basis"]["shares"].items():
        sheet = sheets[spec["sheet"]]
        if "row" in spec:
            owner = sheet.get(spec["row"], spec["column_owner"])
            tenant = sheet.get(spec["row"], spec["column_tenant"])
        else:
            owner = sheet.get(spec["row_owner"], spec["column"])
            tenant = sheet.get(spec["row_tenant"], spec["column"])
        figure = (owner, owner + tenant)
        if figure != documented[name]:
            raise ReferenceBuildError(f"owner_occupied_share: {name}")
        found[name] = Fraction(*figure)
    return found
