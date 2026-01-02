"""CSV parser for BLS QCEW data files.

Handles the BLS QCEW annual CSV format with 44 columns covering
employment, wages, location quotients, and year-over-year changes.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


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


__all__ = [
    "QcewRecord",
    "parse_qcew_csv",
    "parse_all_area_files",
    "determine_area_type",
    "determine_naics_level",
    "extract_state_fips",
    "safe_int",
    "safe_float",
]
