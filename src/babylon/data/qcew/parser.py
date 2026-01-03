"""CSV parser for BLS QCEW data files.

Handles the BLS QCEW annual CSV format with 44 columns covering
employment, wages, location quotients, and year-over-year changes.

Also supports raw single-file CSV parsing for bulk ingestion and
Excel parsing for labor hours data.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd  # type: ignore[import-untyped]


@dataclass
class QcewRecord:
    """Parsed QCEW record with typed fields."""

    # Geographic
    area_fips: str
    area_title: str
    agglvl_code: int

    # Industry
    industry_code: str
    industry_title: str

    # Ownership
    own_code: str
    own_title: str

    # Time
    year: int

    # Core metrics
    establishments: int | None
    employment: int | None
    total_wages: float | None
    avg_weekly_wage: int | None
    avg_annual_pay: int | None

    # Location quotients
    lq_employment: float | None
    lq_avg_annual_pay: float | None

    # Year-over-year
    oty_employment_chg: int | None
    oty_employment_pct: float | None

    # Metadata
    disclosure_code: str


def safe_int(value: str) -> int | None:
    """Convert string to int, returning None for empty/invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def safe_float(value: str) -> float | None:
    """Convert string to float, returning None for empty/invalid values."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def determine_area_type(agglvl_code: int, area_fips: str) -> str:
    """Determine area type from aggregation level code.

    BLS agglvl_code meanings (subset):
        10-18: National level
        20-28: Statewide (using state FIPS)
        30-38: MSA/CSA level
        40-48: Metropolitan/micropolitan division
        50-58: CSA/County equivalents
        70-78: County level

    Args:
        agglvl_code: BLS aggregation level code
        area_fips: FIPS code for area

    Returns:
        Area type string: "national", "state", "msa", "county"
    """
    if agglvl_code < 20:
        return "national"
    elif agglvl_code < 40:
        # 20-29 = state, 30-39 = MSA/CSA
        if area_fips.startswith("CS"):
            return "csa"
        elif len(area_fips) == 5 and area_fips.endswith("000"):
            return "state"
        else:
            return "msa"
    elif agglvl_code < 70:
        return "msa"
    else:
        return "county"


def determine_naics_level(industry_code: str) -> int:
    """Determine NAICS hierarchy level from industry code.

    Args:
        industry_code: NAICS or aggregation code

    Returns:
        Level: 0=total, 2-6=NAICS depth, 99=supersector/domain
    """
    code = industry_code.strip()

    # Total all industries
    if code == "10":
        return 0

    # Domain codes (101=goods, 102=service)
    if code in ("101", "102"):
        return 98

    # Supersector codes (1011-1029)
    if len(code) == 4 and code.startswith("10"):
        return 99

    # NAICS sector (2-digit, but may include ranges like "31-33")
    if "-" in code:
        return 2

    # Standard NAICS hierarchy based on code length
    code_len = len(code)
    level_map = {2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
    return level_map.get(code_len, 99)  # Unknown/other


def extract_state_fips(area_fips: str) -> str | None:
    """Extract 2-digit state FIPS from area FIPS code.

    Args:
        area_fips: Full FIPS code (e.g., "01001" for Autauga County, AL)

    Returns:
        2-digit state FIPS or None for non-state areas (CSAs, national)
    """
    if area_fips.startswith("CS") or area_fips.startswith("US"):
        return None
    if len(area_fips) >= 2:
        return area_fips[:2]
    return None


def parse_qcew_csv(filepath: Path) -> Iterator[QcewRecord]:
    """Parse a single QCEW CSV file and yield records.

    Args:
        filepath: Path to CSV file

    Yields:
        QcewRecord for each data row
    """
    with filepath.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                record = QcewRecord(
                    # Geographic
                    area_fips=row["area_fips"].strip(),
                    area_title=row["area_title"].strip(),
                    agglvl_code=int(row["agglvl_code"]),
                    # Industry
                    industry_code=row["industry_code"].strip(),
                    industry_title=row["industry_title"].strip(),
                    # Ownership
                    own_code=row["own_code"].strip(),
                    own_title=row["own_title"].strip(),
                    # Time
                    year=int(row["year"]),
                    # Core metrics
                    establishments=safe_int(row["annual_avg_estabs_count"]),
                    employment=safe_int(row["annual_avg_emplvl"]),
                    total_wages=safe_float(row["total_annual_wages"]),
                    avg_weekly_wage=safe_int(row["annual_avg_wkly_wage"]),
                    avg_annual_pay=safe_int(row["avg_annual_pay"]),
                    # Location quotients
                    lq_employment=safe_float(row["lq_annual_avg_emplvl"]),
                    lq_avg_annual_pay=safe_float(row["lq_avg_annual_pay"]),
                    # Year-over-year
                    oty_employment_chg=safe_int(row["oty_annual_avg_emplvl_chg"]),
                    oty_employment_pct=safe_float(row["oty_annual_avg_emplvl_pct_chg"]),
                    # Metadata
                    disclosure_code=row.get("disclosure_code", "").strip(),
                )
                yield record
            except (KeyError, ValueError) as e:
                # Skip malformed rows but log issue
                print(f"Warning: Skipping row in {filepath.name}: {e}")
                continue


def parse_all_area_files(data_dir: Path) -> Iterator[QcewRecord]:
    """Parse all CSV files in the by_area directory.

    Args:
        data_dir: Path to 2024.annual.by_area directory

    Yields:
        QcewRecord for each data row across all files
    """
    csv_files = sorted(data_dir.glob("*.csv"))

    for filepath in csv_files:
        yield from parse_qcew_csv(filepath)


@dataclass
class QcewRawRecord:
    """Raw QCEW record - all original columns preserved for bulk ingestion.

    Used with parse_raw_csv_chunked() for the 494MB single-file CSV.
    """

    # Geographic
    area_fips: str
    agglvl_code: int
    size_code: int

    # Classification
    own_code: str
    industry_code: str

    # Time
    year: int
    qtr: str

    # Core metrics
    annual_avg_estabs: int | None
    annual_avg_emplvl: int | None
    total_annual_wages: float | None
    taxable_annual_wages: float | None
    annual_contributions: float | None
    annual_avg_wkly_wage: int | None
    avg_annual_pay: int | None

    # Location quotients
    lq_disclosure_code: str
    lq_annual_avg_estabs: float | None
    lq_annual_avg_emplvl: float | None
    lq_total_annual_wages: float | None
    lq_taxable_annual_wages: float | None
    lq_annual_contributions: float | None
    lq_annual_avg_wkly_wage: float | None
    lq_avg_annual_pay: float | None

    # Year-over-year
    oty_disclosure_code: str
    oty_annual_avg_estabs_chg: int | None
    oty_annual_avg_estabs_pct_chg: float | None
    oty_annual_avg_emplvl_chg: int | None
    oty_annual_avg_emplvl_pct_chg: float | None
    oty_total_annual_wages_chg: float | None
    oty_total_annual_wages_pct_chg: float | None
    oty_taxable_annual_wages_chg: float | None
    oty_taxable_annual_wages_pct_chg: float | None
    oty_annual_contributions_chg: float | None
    oty_annual_contributions_pct_chg: float | None
    oty_annual_avg_wkly_wage_chg: int | None
    oty_annual_avg_wkly_wage_pct_chg: float | None
    oty_avg_annual_pay_chg: int | None
    oty_avg_annual_pay_pct_chg: float | None

    # Metadata
    disclosure_code: str


@dataclass
class LaborHoursRecord:
    """Record from BLS labor hours Excel files.

    Used with parse_labor_hours_excel() for quarterly granularity data.
    """

    # Geographic
    area_code: str
    state: str | None
    county: str | None
    area_type: str | None
    state_name: str | None
    area_name: str | None

    # Classification
    own_code: str
    naics: str
    ownership_label: str | None
    industry_label: str | None

    # Time
    year: int
    qtr: str  # "A", "1", "2", "3", "4"

    # Core metrics
    status_code: str | None
    establishments: int | None
    employment: int | None
    total_wages: float | None
    avg_weekly_wage: int | None
    avg_annual_pay: int | None

    # Location quotients
    employment_lq: float | None
    wage_lq: float | None


def parse_raw_csv_chunked(
    filepath: Path,
    chunk_size: int = 100_000,
) -> Iterator[pd.DataFrame]:
    """Parse raw QCEW CSV in chunks using pandas for memory efficiency.

    Args:
        filepath: Path to 2022.annual.singlefile.csv
        chunk_size: Rows per chunk (default 100k for ~494MB file)

    Yields:
        pandas DataFrames, one chunk at a time

    Note:
        Requires pandas. Import is deferred to avoid startup cost.
    """
    import pandas as pd

    # Column name mapping: raw CSV uses different names than schema
    dtype_spec = {
        "area_fips": str,
        "own_code": str,
        "industry_code": str,
        "agglvl_code": "Int64",
        "size_code": "Int64",
        "year": "Int64",
        "qtr": str,
        "disclosure_code": str,
        "annual_avg_estabs": "Int64",
        "annual_avg_emplvl": "Int64",
        "total_annual_wages": float,
        "taxable_annual_wages": float,
        "annual_contributions": float,
        "annual_avg_wkly_wage": "Int64",
        "avg_annual_pay": "Int64",
        "lq_disclosure_code": str,
        "lq_annual_avg_estabs": float,
        "lq_annual_avg_emplvl": float,
        "lq_total_annual_wages": float,
        "lq_taxable_annual_wages": float,
        "lq_annual_contributions": float,
        "lq_annual_avg_wkly_wage": float,
        "lq_avg_annual_pay": float,
        "oty_disclosure_code": str,
        "oty_annual_avg_estabs_chg": "Int64",
        "oty_annual_avg_estabs_pct_chg": float,
        "oty_annual_avg_emplvl_chg": "Int64",
        "oty_annual_avg_emplvl_pct_chg": float,
        "oty_total_annual_wages_chg": float,
        "oty_total_annual_wages_pct_chg": float,
        "oty_taxable_annual_wages_chg": float,
        "oty_taxable_annual_wages_pct_chg": float,
        "oty_annual_contributions_chg": float,
        "oty_annual_contributions_pct_chg": float,
        "oty_annual_avg_wkly_wage_chg": "Int64",
        "oty_annual_avg_wkly_wage_pct_chg": float,
        "oty_avg_annual_pay_chg": "Int64",
        "oty_avg_annual_pay_pct_chg": float,
    }

    yield from pd.read_csv(
        filepath,
        chunksize=chunk_size,
        dtype=dtype_spec,
        na_values=["", " "],
        keep_default_na=True,
    )


def parse_labor_hours_excel(
    filepath: Path,
) -> Iterator[LaborHoursRecord]:
    """Parse a BLS labor hours Excel file and yield records.

    Args:
        filepath: Path to allhlcn22*.xlsx file

    Yields:
        LaborHoursRecord for each data row

    Note:
        Requires openpyxl. Import is deferred to avoid startup cost.
    """
    import openpyxl  # type: ignore[import-untyped]

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active

    # Skip header row
    rows = ws.iter_rows(min_row=2, values_only=True)

    for row in rows:
        # Handle empty rows
        if row[0] is None:
            continue

        try:
            record = LaborHoursRecord(
                # Geographic (columns 0-9)
                area_code=str(row[0]) if row[0] else "",
                state=str(row[1]) if row[1] else None,
                county=str(row[2]) if row[2] else None,
                area_type=str(row[7]) if row[7] else None,
                state_name=str(row[8]) if row[8] else None,
                area_name=str(row[9]) if row[9] else None,
                # Classification (columns 3-5, 10-11)
                own_code=str(row[3]) if row[3] else "0",
                naics=str(row[4]) if row[4] else "10",
                ownership_label=str(row[10]) if row[10] else None,
                industry_label=str(row[11]) if row[11] else None,
                # Time (columns 5-6)
                year=int(row[5]) if row[5] else 2022,
                qtr=str(row[6]) if row[6] else "A",
                # Core metrics (columns 12-17)
                status_code=str(row[12]) if row[12] else None,
                establishments=int(row[13]) if row[13] else None,
                employment=int(row[14]) if row[14] else None,
                total_wages=float(row[15]) if row[15] else None,
                avg_weekly_wage=int(row[16]) if row[16] else None,
                avg_annual_pay=int(row[17]) if row[17] else None,
                # Location quotients (columns 18-19)
                employment_lq=float(row[18]) if row[18] else None,
                wage_lq=float(row[19]) if row[19] else None,
            )
            yield record
        except (ValueError, IndexError) as e:
            # Skip malformed rows
            print(f"Warning: Skipping row in {filepath.name}: {e}")
            continue

    wb.close()


def parse_all_labor_hours_files(
    data_dir: Path,
) -> Iterator[LaborHoursRecord]:
    """Parse all Excel files in the mass_labor_hours directory.

    Args:
        data_dir: Path to data/mass_labor_hours/

    Yields:
        LaborHoursRecord for each data row across all files
    """
    xlsx_files = sorted(data_dir.glob("allhlcn*.xlsx"))

    for filepath in xlsx_files:
        yield from parse_labor_hours_excel(filepath)


__all__ = [
    "QcewRecord",
    "QcewRawRecord",
    "LaborHoursRecord",
    "parse_qcew_csv",
    "parse_all_area_files",
    "parse_raw_csv_chunked",
    "parse_labor_hours_excel",
    "parse_all_labor_hours_files",
    "determine_area_type",
    "determine_naics_level",
    "extract_state_fips",
    "safe_int",
    "safe_float",
]
