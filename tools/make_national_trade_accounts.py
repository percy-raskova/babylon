"""Fold the BEA 2024 supply and use tables into the twelve trades.

Reads the pinned BEA workbooks only when run by hand against ``--source-root``; the
sheet reader, the industry mapping, the owner-occupied housing shares, the folding,
the source identities and the writer live here.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Final

import make_national_qcew_function_basis as basis
import make_national_qcew_function_basis_v2 as v2
import openpyxl  # type: ignore[import-untyped]
from make_national_cohort_reference import pinned_input
from make_national_county_reference import (
    ROOT,
    ReferenceBuildError,
    _unique_object,
    ensure_output_paths,
    provenance_path,
    sha256,
)
from make_national_qcew_function_basis_v2 import FUNCTION_IDS_V2, SourceRow

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
ARTIFACT_OUT: Final = (
    ROOT / "src/babylon/data/reference/economy/national_trade_accounts_2024.csv.gz"
)
METADATA_OUT: Final = ARTIFACT_OUT.with_name("national_trade_accounts_2024.metadata.json")
COLUMNS: Final = ("block", "row_key", "column_key", "unit", "value")
PRODUCTS: Final = (*TRADES, OWNER, "scrap_used", "noncomparable")
INDUSTRIES: Final = (*TRADES, OWNER)
FINAL_USES: Final = {
    "households": ("F010",),
    "investment_structures": ("F02S",),
    "investment_equipment": ("F02E",),
    "investment_intellectual_property": ("F02N",),
    "investment_residential": ("F02R",),
    "inventories": ("F030",),
    "exports": ("F040",),
    "federal_consumption": ("F06C", "F07C"),
    "federal_investment": ("F06S", "F06E", "F06N", "F07S", "F07E", "F07N"),
    "state_local_consumption": ("F10C",),
    "state_local_investment": ("F10S", "F10E", "F10N"),
}
SUPPLY: Final = {
    "commodity_output": ("T007",),
    "imports": ("MCIF", "MADJ"),
    "trade_margins": ("Trade",),
    "transport_margins": ("Trans",),
    "import_duties": ("MDTY",),
    "product_taxes": ("TOP",),
    "product_subsidies": ("SUB",),
    "total_supply": ("T016",),
}
INDUSTRY: Final = (
    "gross_output",
    "intermediate_inputs",
    "compensation",
    "production_taxes_less_subsidies",
    "gross_operating_surplus",
    "value_added_basic",
)
JOBS: Final = ("jobs", "annual_payroll_usd", "jobs_public", "annual_payroll_public_usd")
JOBS_UNITS: Final = {
    "jobs": "jobs",
    "annual_payroll_usd": "usd",
    "jobs_public": "jobs",
    "annual_payroll_public_usd": "usd",
}
BLOCK_ORDER: Final = ("use", "supply", "make", "industry", "jobs", "split")
OWNERSHIPS: Final = ("1", "2", "3", "5")
PUBLIC_OWNERSHIPS: Final = ("1", "2", "3")
HOUSING: Final = "HS"
GAP_BOUND_MILLIONS: Final = 10
GDP_TOLERANCE: Final = Fraction(1, 10000)
CHECK_NAMES: Final = (
    "use_total",
    "use_row",
    "use_column",
    "supply_parts",
    "use_supply",
    "industry_output",
    "value_added",
    "make_row",
    "make_column",
    "make_use_output",
)


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
        if (
            not source.is_file()
            or source.stat().st_size != entry["bytes"]
            or sha256(source) != entry["sha256"]
        ):
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
        pair = shares[name].get("figures") if isinstance(shares[name], dict) else None
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in pair)
        ):
            raise ReferenceBuildError(f"accounts_mapping_owner_shares: {name}")
        owner, total = pair
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
        try:
            sheet = sheets[spec["sheet"]]
            if "row" in spec:
                owner = sheet.get(spec["row"], spec["column_owner"])
                tenant = sheet.get(spec["row"], spec["column_tenant"])
            else:
                owner = sheet.get(spec["row_owner"], spec["column"])
                tenant = sheet.get(spec["row_tenant"], spec["column"])
        except (KeyError, TypeError) as error:
            raise ReferenceBuildError(f"accounts_mapping_owner_shares: {name}") from error
        figure = (owner, owner + tenant)
        if figure != documented[name]:
            raise ReferenceBuildError(f"owner_occupied_share: {name}")
        found[name] = Fraction(*figure)
    return found


@dataclass(frozen=True)
class AccountCell:
    block: str
    row_key: str
    column_key: str
    unit: str
    value: int


def split_cell(value_thousands: int, shares: Sequence[tuple[str, Fraction]]) -> dict[str, int]:
    """Share a cell by largest remainder on its absolute value; ties by key; sign restored."""
    if not shares or sum(share for _, share in shares) != 1 or any(s < 0 for _, s in shares):
        raise ReferenceBuildError("accounts_split_shares")
    magnitude = abs(value_thousands)
    parts: dict[str, int] = {}
    remainders: list[tuple[Fraction, str]] = []
    for key, share in shares:
        if key in parts:
            raise ReferenceBuildError(f"accounts_split_shares: {key} repeated")
        exact = magnitude * share
        parts[key] = exact.numerator // exact.denominator
        remainders.append((exact - parts[key], key))
    left = magnitude - sum(parts.values())
    for _, key in sorted(remainders, key=lambda item: (-item[0], item[1]))[:left]:
        parts[key] += 1
    sign = -1 if value_thousands < 0 else 1
    return {key: sign * amount for key, amount in parts.items()}


def _published_jobs(row: SourceRow) -> int:
    return row.annual_avg_jobs or 0


def _nation(nation: Sequence[SourceRow]) -> list[SourceRow]:
    return [
        row
        for row in nation
        if row.row_role == "nation_leaf"
        and row.area_fips == v2.NATION_AREA
        and row.ownership_code in OWNERSHIPS
    ]


def _split_jobs(nation: Sequence[SourceRow], mapping: AccountsMapping) -> dict[str, dict[str, int]]:
    by_code: dict[str, int] = {}
    for row in _nation(nation):
        by_code[row.naics_code] = by_code.get(row.naics_code, 0) + _published_jobs(row)
    jobs: dict[str, dict[str, int]] = {}
    for code, parts in mapping.splits.items():
        jobs[code] = {
            trade: sum(by_code.get(n, 0) for n in naics) for trade, naics in parts.items()
        }
        if sum(jobs[code].values()) == 0:
            raise ReferenceBuildError(f"accounts_split_jobs: {code}")
    return jobs


def split_shares(
    nation: Sequence[SourceRow], mapping: AccountsMapping
) -> dict[str, dict[str, Fraction]]:
    """Each split industry's shares: national published jobs of its NAICS leaves by trade."""
    return {
        code: {trade: Fraction(count, sum(parts.values())) for trade, count in parts.items()}
        for code, parts in _split_jobs(nation, mapping).items()
    }


def split_cells(nation: Sequence[SourceRow], mapping: AccountsMapping) -> tuple[AccountCell, ...]:
    """The jobs behind each split, in the contract's order."""
    return tuple(
        AccountCell("split", code, trade, "jobs", count)
        for code, parts in _split_jobs(nation, mapping).items()
        for trade, count in parts.items()
    )


def jobs_cells(
    nation: Sequence[SourceRow], functions: basis.FunctionMapping
) -> tuple[AccountCell, ...]:
    """Published national jobs and payroll by trade, all ownerships and the public three."""
    totals = {trade: dict.fromkeys(JOBS, 0) for trade in TRADES}
    for row in _nation(nation):
        trade = functions.function_for(row.naics_code)
        if trade is None:
            continue
        jobs, payroll = _published_jobs(row), row.annual_payroll_usd or 0
        totals[trade]["jobs"] += jobs
        totals[trade]["annual_payroll_usd"] += payroll
        if row.ownership_code in PUBLIC_OWNERSHIPS:
            totals[trade]["jobs_public"] += jobs
            totals[trade]["annual_payroll_public_usd"] += payroll
    return tuple(
        AccountCell("jobs", trade, column, JOBS_UNITS[column], totals[trade][column])
        for trade in TRADES
        for column in JOBS
    )


Parts = tuple[tuple[str, Fraction], ...]


def _spread(value: int, parts: Parts) -> dict[str, int]:
    return {parts[0][0]: value} if len(parts) == 1 else split_cell(value, parts)


class _Folder:
    """Row and column parts of each source code, with housing divided by its own shares."""

    def __init__(
        self, mapping: AccountsMapping, shares: Mapping[str, Mapping[str, Fraction]]
    ) -> None:
        self.mapping = mapping
        self.parts: dict[str, Parts] = {}
        for code, trade in mapping.whole.items():
            self.parts[code] = ((trade, Fraction(1)),)
        for code in mapping.splits:
            if code not in shares:
                raise ReferenceBuildError(f"accounts_split_jobs: {code}")
            self.parts[code] = tuple((trade, shares[code][trade]) for trade in mapping.splits[code])
        self.residual = {code: ((key, Fraction(1)),) for code, key in RESIDUAL_ROWS.items()}

    def product(self, code: str) -> Parts:
        return self.residual.get(code) or self.parts[code]

    def housing(self, name: str) -> Parts:
        share = self.mapping.owner_shares[name]
        return ((OWNER, share), (self.mapping.whole[HOUSING], 1 - share))


def _final_total(sheet: BeaSheet, row: str, name: str) -> int:
    return sum(sheet.get(row, code) for code in FINAL_USES[name])


def _supply_total(sheet: BeaSheet, row: str, name: str) -> int:
    return sum(sheet.get(row, code) for code in SUPPLY[name])


def fold(
    use: BeaSheet,
    supply: BeaSheet,
    mapping: AccountsMapping,
    shares: Mapping[str, Mapping[str, Fraction]],
) -> tuple[AccountCell, ...]:
    """Fold the summary use and supply sheets (USD millions) into the twelve trades and housing.

    Returns the ``use``, ``supply``, ``make`` and ``industry`` blocks, dense and in order,
    in USD thousands.
    """
    folder = _Folder(mapping, shares)
    industry_codes: list[str] = list(mapping.document["industry_codes"])
    product_codes = [*industry_codes, *RESIDUAL_ROWS]

    use_cells: dict[tuple[str, str], int] = {
        (row, column): 0 for row in PRODUCTS for column in (*INDUSTRIES, *FINAL_USES)
    }
    for code in product_codes:
        if code == HOUSING:
            for column in industry_codes:
                if use.get(code, column):
                    raise ReferenceBuildError(f"accounts_housing_row: {column}")
            for name in FINAL_USES:
                value = _final_total(use, code, name) * 1000
                if name != "households" and value:
                    raise ReferenceBuildError(f"accounts_housing_row: {name}")
                for key, part in _spread(value, folder.housing("households")).items():
                    use_cells[(key, name)] += part
            continue
        row_parts = folder.product(code)
        for column in industry_codes:
            value = use.get(code, column) * 1000
            if not value:
                continue
            column_parts = (
                folder.housing("intermediate_inputs") if column == HOUSING else folder.parts[column]
            )
            for row_key, row_value in _spread(value, row_parts).items():
                for column_key, part in _spread(row_value, column_parts).items():
                    use_cells[(row_key, column_key)] += part
        for name in FINAL_USES:
            value = _final_total(use, code, name) * 1000
            if value:
                for row_key, part in _spread(value, row_parts).items():
                    use_cells[(row_key, name)] += part

    supply_cells = _fold_supply(supply, folder, use_cells, product_codes)
    make_cells = _fold_make(supply, folder, supply_cells, industry_codes, product_codes)
    industry_cells = _fold_industry(use, folder, industry_codes)

    cells: list[AccountCell] = []
    for row in PRODUCTS:
        for column in (*INDUSTRIES, *FINAL_USES):
            cells.append(AccountCell("use", row, column, "usd_thousands", use_cells[(row, column)]))
    for row in PRODUCTS:
        for column in SUPPLY:
            cells.append(
                AccountCell("supply", row, column, "usd_thousands", supply_cells[(row, column)])
            )
    for industry in INDUSTRIES:
        for product in PRODUCTS:
            cells.append(
                AccountCell(
                    "make", industry, product, "usd_thousands", make_cells[(industry, product)]
                )
            )
    for industry in INDUSTRIES:
        for measure in INDUSTRY:
            cells.append(
                AccountCell(
                    "industry",
                    industry,
                    measure,
                    "usd_thousands",
                    industry_cells[(industry, measure)],
                )
            )
    return tuple(cells)


def _fold_supply(
    supply: BeaSheet,
    folder: _Folder,
    use_cells: Mapping[tuple[str, str], int],
    product_codes: Sequence[str],
) -> dict[tuple[str, str], int]:
    housing_trade = folder.mapping.whole[HOUSING]
    cells = {(row, column): 0 for row in PRODUCTS for column in SUPPLY}
    for code in product_codes:
        if code == HOUSING:
            owner = dict.fromkeys(SUPPLY, 0)
            owner["total_supply"] = use_cells[(OWNER, "households")]
            owner["product_subsidies"] = split_cell(
                _supply_total(supply, code, "product_subsidies") * 1000,
                folder.housing("product_subsidies"),
            )[OWNER]
            owner["commodity_output"] = owner["total_supply"] - owner["product_subsidies"]
            for name in SUPPLY:
                total = _supply_total(supply, code, name) * 1000
                cells[(OWNER, name)] += owner[name]
                cells[(housing_trade, name)] += total - owner[name]
            continue
        for name in SUPPLY:
            value = _supply_total(supply, code, name) * 1000
            if value:
                for key, part in _spread(value, folder.product(code)).items():
                    cells[(key, name)] += part
    return cells


def _fold_make(
    supply: BeaSheet,
    folder: _Folder,
    supply_cells: Mapping[tuple[str, str], int],
    industry_codes: Sequence[str],
    product_codes: Sequence[str],
) -> dict[tuple[str, str], int]:
    housing_trade = folder.mapping.whole[HOUSING]
    cells = {(industry, product): 0 for industry in INDUSTRIES for product in PRODUCTS}
    for product in product_codes:
        for industry in industry_codes:
            value = supply.get(product, industry) * 1000
            if not value:
                continue
            if industry == HOUSING:
                industry_parts: Parts = ((housing_trade, Fraction(1)),)
            else:
                industry_parts = folder.parts[industry]
            if product == HOUSING:
                product_parts: Parts = ((housing_trade, Fraction(1)),)
            else:
                product_parts = folder.product(product)
            for product_key, product_value in _spread(value, product_parts).items():
                for industry_key, part in _spread(product_value, industry_parts).items():
                    cells[(industry_key, product_key)] += part
    owner_made = supply_cells[(OWNER, "commodity_output")]
    cells[(OWNER, OWNER)] = owner_made
    cells[(housing_trade, housing_trade)] -= owner_made
    return cells


def _fold_industry(
    use: BeaSheet, folder: _Folder, industry_codes: Sequence[str]
) -> dict[tuple[str, str], int]:
    mapping = folder.mapping
    housing_trade = mapping.whole[HOUSING]
    sources = {
        "go": "T018",
        "ii": "T005",
        "comp": "V001",
        "otop": "T00OTOP",
        "osub": "T00OSUB",
        "gos": "V003",
        "vab": "VABAS",
    }
    parts: dict[tuple[str, str], int] = {
        (industry, element): 0 for industry in INDUSTRIES for element in sources
    }
    for code in industry_codes:
        if code == HOUSING:
            continue
        for element, row in sources.items():
            value = use.get(row, code) * 1000
            if value:
                for key, part in _spread(value, folder.parts[code]).items():
                    parts[(key, element)] += part
    if use.get("T00OSUB", HOUSING):
        raise ReferenceBuildError("owner_occupied_share: other_subsidies")
    home = {element: use.get(row, HOUSING) * 1000 for element, row in sources.items()}
    owner = {
        "ii": split_cell(home["ii"], folder.housing("intermediate_inputs"))[OWNER],
        "comp": split_cell(home["comp"], folder.housing("compensation"))[OWNER],
        "otop": split_cell(home["otop"], folder.housing("production_taxes"))[OWNER],
        "osub": 0,
        "gos": split_cell(home["gos"], folder.housing("gross_operating_surplus"))[OWNER],
    }
    owner["vab"] = owner["comp"] + owner["otop"] - owner["osub"] + owner["gos"]
    owner["go"] = owner["ii"] + owner["vab"]
    for element in sources:
        parts[(OWNER, element)] += owner[element]
        parts[(housing_trade, element)] += home[element] - owner[element]
    result: dict[tuple[str, str], int] = {}
    for industry in INDUSTRIES:
        result[(industry, "gross_output")] = parts[(industry, "go")]
        result[(industry, "intermediate_inputs")] = parts[(industry, "ii")]
        result[(industry, "compensation")] = parts[(industry, "comp")]
        result[(industry, "production_taxes_less_subsidies")] = (
            parts[(industry, "otop")] - parts[(industry, "osub")]
        )
        result[(industry, "gross_operating_surplus")] = parts[(industry, "gos")]
        result[(industry, "value_added_basic")] = parts[(industry, "vab")]
    return result


def _until(columns: Sequence[str], stop: str) -> tuple[str, ...]:
    return tuple(columns[: columns.index(stop)])


def check(cells: Sequence[AccountCell], use: BeaSheet, supply: BeaSheet) -> dict[str, Any]:
    """Test the source's own identities per code, before folding, and the fold's exact totals.

    Gaps are in USD millions. A gap above ``GAP_BOUND_MILLIONS`` is refused.
    """
    products = _until(use.rows, "T005")
    industries = _until(use.columns, "T001")
    supply_products = _until(supply.rows, "T017")
    supply_industries = _until(supply.columns, "T007")
    finals = [code for codes in FINAL_USES.values() for code in codes]
    gaps = dict.fromkeys(CHECK_NAMES, 0)

    def gap(name: str, code: str, value: int) -> None:
        if abs(value) > GAP_BOUND_MILLIONS:
            raise ReferenceBuildError(f"accounts_identity: {name}/{code}")
        gaps[name] = max(gaps[name], abs(value))

    for code in products:
        gap(
            "use_total",
            code,
            use.get(code, "T019")
            - use.get(code, "T001")
            - sum(use.get(code, final) for final in finals),
        )
        gap("use_row", code, sum(use.get(code, c) for c in industries) - use.get(code, "T001"))
    for code in industries:
        gap("use_column", code, sum(use.get(r, code) for r in products) - use.get("T005", code))
        gap(
            "industry_output",
            code,
            use.get("T018", code) - use.get("T005", code) - use.get("VABAS", code),
        )
        gap(
            "value_added",
            code,
            use.get("V001", code)
            + use.get("T00OTOP", code)
            - use.get("T00OSUB", code)
            + use.get("V003", code)
            - use.get("VABAS", code),
        )
    for code in supply_products:
        parts = sum(
            supply.get(code, c)
            for name, codes in SUPPLY.items()
            if name != "total_supply"
            for c in codes
        )
        gap("supply_parts", code, supply.get(code, "T016") - parts)
        gap("use_supply", code, supply.get(code, "T016") - use.get(code, "T019"))
        gap(
            "make_row",
            code,
            sum(supply.get(code, c) for c in supply_industries) - supply.get(code, "T007"),
        )
    for code in supply_industries:
        gap(
            "make_column",
            code,
            sum(supply.get(r, code) for r in supply_products) - supply.get("T017", code),
        )
        gap("make_use_output", code, supply.get("T017", code) - use.get("T018", code))
    final_sum = sum(use.get(code, final) for code in products for final in finals)
    import_sum = sum(supply.get(code, c) for code in supply_products for c in SUPPLY["imports"])
    value_added = sum(use.get("VAPRO", code) for code in industries)
    if abs(final_sum - import_sum - value_added) * 10000 > value_added:
        raise ReferenceBuildError("accounts_identity: gdp")
    controls = {
        "T018": sum(use.get("T018", code) for code in industries),
        "T005": sum(use.get("T005", code) for code in industries),
        "VABAS": sum(use.get("VABAS", code) for code in industries),
        "T019": sum(use.get(code, "T019") for code in products),
    }
    totals = {(c.block, c.row_key, c.column_key): c.value for c in cells}
    exact = {
        "gross_output": (
            sum(totals[("industry", i, "gross_output")] for i in INDUSTRIES),
            controls["T018"],
        ),
        "value_added_basic": (
            sum(totals[("industry", i, "value_added_basic")] for i in INDUSTRIES),
            controls["VABAS"],
        ),
        "households": (
            sum(totals[("use", p, "households")] for p in PRODUCTS),
            sum(use.get(code, "F010") for code in products),
        ),
        "total_supply": (
            sum(totals[("supply", p, "total_supply")] for p in PRODUCTS),
            sum(supply.get(code, "T016") for code in supply_products),
        ),
    }
    for name, (folded, source) in exact.items():
        if folded != source * 1000:
            raise ReferenceBuildError(f"accounts_fold_total: {name}")
    return {
        "checks": gaps,
        "source_controls": controls,
        "gdp": {
            "final_uses_usd_millions": final_sum,
            "imports_usd_millions": import_sum,
            "value_added_by_product_usd_millions": value_added,
            "gap_usd_millions": final_sum - import_sum - value_added,
        },
    }


def check_owner_2017(summary: BeaSheet, use_detail: BeaSheet) -> dict[str, int]:
    """The 2017 summary's housing column and row must equal the detail's two, within 2 million."""
    pairs = {"T005": "T005", "V001": "V00100", "T00OTOP": "T00OTOP", "V003": "V00300"}
    gaps: dict[str, int] = {}
    for name, detail_row in pairs.items():
        detail = sum(use_detail.get(detail_row, c) for c in ("531HSO", "531HST"))
        gaps[name] = abs(summary.get(name, HOUSING) - detail)
    detail_households = sum(use_detail.get(r, "F01000") for r in ("531HSO", "531HST"))
    gaps["F010"] = abs(summary.get(HOUSING, "F010") - detail_households)
    for name, value in gaps.items():
        if value > 2:
            raise ReferenceBuildError(f"accounts_identity: owner_2017/{name}")
    return gaps


def build(
    *,
    source_root: Path,
    artifact_out: Path = ARTIFACT_OUT,
    metadata_out: Path = METADATA_OUT,
) -> dict[str, Any]:
    inputs = (v2.ARTIFACT_OUT, v2.METADATA_OUT, v2.MAPPING_V2_PATH, ACCOUNTS_MAPPING, SOURCES)
    ensure_output_paths((artifact_out, metadata_out), inputs)
    files = verify_accounts_sources(source_root)
    functions = v2.load_mapping_v2()
    mapping = load_accounts_mapping(ACCOUNTS_MAPPING, functions)
    use = read_sheet(files["use_summary"], "2024", code_row=5, first_row=7)
    supply = read_sheet(files["supply_summary"], "2024", code_row=5, first_row=7)
    use_2017 = read_sheet(files["use_summary"], "2017", code_row=5, first_row=7)
    use_detail = read_sheet(files["use_detail"], "2017", code_row=5, first_row=6)
    supply_detail = read_sheet(files["supply_detail"], "2017", code_row=5, first_row=6)
    check_summary_coverage(mapping, use)
    owner_occupied_shares(use_detail, supply_detail)
    owner_gaps = check_owner_2017(use_2017, use_detail)
    nation = v2.read_basis_v2()
    shares = split_shares(nation, mapping)
    folded = fold(use, supply, mapping, shares)
    cells = (*folded, *jobs_cells(nation, functions), *split_cells(nation, mapping))
    verified = check(folded, use, supply)
    counts = {block: sum(c.block == block for c in cells) for block in BLOCK_ORDER}
    by_key = {(c.block, c.row_key, c.column_key): c.value for c in cells}
    owner_use_sum = sum(by_key[("use", p, OWNER)] for p in PRODUCTS)
    owner_gap = owner_use_sum - by_key[("industry", OWNER, "intermediate_inputs")]
    owner_make = sum(by_key[("make", OWNER, p)] for p in PRODUCTS)
    owner_make_less_output = owner_make - by_key[("industry", OWNER, "gross_output")]
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows((c.block, c.row_key, c.column_key, c.unit, str(c.value)) for c in cells)
    encoded = buffer.getvalue().encode("ascii")
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    with (
        artifact_out.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed,
    ):
        compressed.write(encoded)
    manifest = json.loads(SOURCES.read_bytes())
    metadata = {
        "contract": "NationalTradeAccounts2024V1",
        "issue": "PER-371",
        "year": 2024,
        "artifact": {
            "path": provenance_path(artifact_out),
            "format": "csv.gz",
            "sha256": sha256(artifact_out),
            "bytes": artifact_out.stat().st_size,
            "decoded_bytes": len(encoded),
            "rows": len(cells),
            "columns": list(COLUMNS),
            "ordering": "blocks in the order of block_order, each dense in the order of its row and column lists",
            "block_order": list(BLOCK_ORDER),
            "block_rows": counts,
            "rows_of_blocks": {
                "use": list(PRODUCTS),
                "supply": list(PRODUCTS),
                "make": list(INDUSTRIES),
                "industry": list(INDUSTRIES),
                "jobs": list(TRADES),
                "split": list(mapping.splits),
            },
            "columns_of_blocks": {
                "use": [*INDUSTRIES, *FINAL_USES],
                "supply": list(SUPPLY),
                "make": list(PRODUCTS),
                "industry": list(INDUSTRY),
                "jobs": list(JOBS),
                "split": {code: list(parts) for code, parts in mapping.splits.items()},
            },
            "writer": {"gzip_level": 9, "mtime": 0, "line_end": "\\n", "encoding": "ascii"},
        },
        "regeneration": (
            "UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python "
            "tools/make_national_trade_accounts.py --source-root /media/user/data/babylon-data"
        ),
        "writer_versions": {"openpyxl": openpyxl.__version__},
        "sources": {
            "bea_workbooks": [
                {k: entry[k] for k in ("id", "path", "bytes", "sha256")}
                for entry in manifest["sources"]
            ],
            "bea_sources_manifest": {
                "path": provenance_path(SOURCES),
                "sha256": sha256(SOURCES),
            },
            "accounts_mapping": {
                "path": provenance_path(ACCOUNTS_MAPPING),
                "sha256": sha256(ACCOUNTS_MAPPING),
            },
            "function_mapping": {
                "path": provenance_path(v2.MAPPING_V2_PATH),
                "sha256": sha256(v2.MAPPING_V2_PATH),
            },
            "leaf_basis": pinned_input(v2.ARTIFACT_OUT, v2.METADATA_OUT),
        },
        "coverage": {
            "block_rows": counts,
            "rows_in_all": len(cells),
            "jobs_in_all": sum(by_key[("jobs", trade, "jobs")] for trade in TRADES),
        },
        "checks": verified["checks"],
        "check_bound_usd_millions": GAP_BOUND_MILLIONS,
        "source_controls": verified["source_controls"],
        "gdp": verified["gdp"],
        "housing": {
            "owner_intermediate_gap_usd_thousands": owner_gap,
            "owner_make_less_gross_output_usd_thousands": owner_make_less_output,
            "owner_2017_summary_vs_detail_gaps_usd_millions": owner_gaps,
        },
        "semantics": {
            "units": "use, supply, make and industry cells are whole USD thousands (the source's millions times 1,000, then shared); jobs cells are jobs or whole USD; split cells are jobs. Values keep the source's sign.",
            "price_basis": "Product rows are at purchasers' prices: trade and transport margins and product taxes sit in the goods rows (the margin columns are positive for goods and negative for the distribution and transport trades' own products). Industry figures are at basic prices. Imports are the positive supply columns MCIF plus MADJ.",
            "blocks": "use: product rows by industry and final-use columns. supply: product rows by supply column. make: what each industry makes of each product. industry: output, inputs and value added by industry. jobs: national published QCEW jobs and payroll by trade. split: the jobs that share each split industry.",
            "splits": "A split industry's cell is shared by national published jobs of its NAICS leaves, over ownerships 1, 2, 3 and 5, by largest remainder on the absolute value. A product row is split first, then each part by the column split.",
            "housing": "Owner-occupied housing is cut from BEA industry and product HS with the 2017 detail shares of the mapping contract (rent that home owners are counted as paying themselves). The owner's intermediate inputs are HS's total split by its share; the HS column's cells are each split by the same share, so their sum differs from it by rounding (housing.owner_intermediate_gap_usd_thousands). The owner makes only its own product; the rest of HS stays with construction and housing. The owner's row of make is its commodity output, which is not its gross output: housing.owner_make_less_gross_output_usd_thousands is the difference, construction and housing carries the opposite difference, and the pair adds up to the source.",
            "government": "General government and government enterprises are public provisioning. Federal (F06, F07) and state and local (F10) final uses stay apart by level.",
            "residual_rows": "Used (scrap_used) and Other (noncomparable) are product rows only.",
            "inventory": "Change in private inventories (F030) is a final use, signed as the source gives it.",
            "judgments": [
                "GFE, mostly the postal service, is distribution and transport.",
                "GSLE and the general governments are public provisioning.",
                "Public schools and hospitals are counted twice in kind: their jobs stay in household services and their output is counted under government. Stage 5 settles it.",
                "2,080 hours a year for all trades.",
            ],
            "limits": "No money or hour is allocated to households, sites or recipes by this table. The native reader is not built yet.",
        },
        "native_readers": [],
        "runtime_consumers": [],
    }
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--artifact-out", type=Path, default=ARTIFACT_OUT)
    parser.add_argument("--metadata-out", type=Path, default=METADATA_OUT)
    args = parser.parse_args()
    metadata = build(
        source_root=args.source_root,
        artifact_out=args.artifact_out,
        metadata_out=args.metadata_out,
    )
    print(
        json.dumps(
            {
                "artifact": metadata["artifact"]["sha256"],
                "rows": metadata["artifact"]["rows"],
                "checks": metadata["checks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
