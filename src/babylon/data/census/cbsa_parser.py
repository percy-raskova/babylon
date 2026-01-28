"""Parser for Census Bureau CBSA delineation files.

Downloads and parses the official CBSA-to-county mapping from Census Bureau,
enabling metropolitan statistical area aggregation of county-level data.

Source: https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html

The CBSA (Core Based Statistical Area) delineation file maps counties to:
- Metropolitan Statistical Areas (MSA): 50K+ urban core population
- Micropolitan Statistical Areas: 10K-50K urban core population
- Combined Statistical Areas (CSA): Adjacent CBSAs with commuting ties
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Default path for CBSA delineation Excel file
CBSA_EXCEL_PATH = Path("data/census/cbsa_delineation_2023.xlsx")

# Git LFS pointer signature
_LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def _is_lfs_pointer(filepath: Path) -> bool:
    """Check if a file is a Git LFS pointer instead of actual content.

    Git LFS pointers are small text files that reference the actual
    binary content stored in Git LFS. They have a specific format:

        version https://git-lfs.github.com/spec/v1
        oid sha256:abc123...
        size 12345

    Args:
        filepath: Path to the file to check.

    Returns:
        True if the file appears to be a Git LFS pointer, False otherwise.
    """
    if not filepath.exists():
        return False

    # Read first 128 bytes to check for LFS pointer signature
    try:
        with open(filepath, "rb") as f:
            header = f.read(128)
        return header.startswith(_LFS_POINTER_PREFIX)
    except OSError:
        return False


# Expected column names in the delineation file
CBSA_CODE_COL = "CBSA Code"
CBSA_TITLE_COL = "CBSA Title"
METRO_MICRO_COL = "Metropolitan/Micropolitan Statistical Area"
CSA_CODE_COL = "CSA Code"
CSA_TITLE_COL = "CSA Title"
COUNTY_NAME_COL = "County/County Equivalent"
STATE_NAME_COL = "State Name"
STATE_FIPS_COL = "FIPS State Code"
COUNTY_FIPS_COL = "FIPS County Code"
CENTRAL_OUTLYING_COL = "Central/Outlying County"


@dataclass
class CBSARecord:
    """A single CBSA-to-county mapping record.

    Represents one row from the CBSA delineation file, mapping a county
    to its containing CBSA (and optionally CSA).

    Attributes:
        cbsa_code: 5-digit CBSA code.
        cbsa_title: Full name of the CBSA (e.g., "New York-Newark-Jersey City, NY-NJ-PA").
        area_type: "msa" or "micropolitan".
        csa_code: Optional 3-digit CSA code if county is part of a CSA.
        csa_title: Optional CSA name.
        county_fips: 5-digit combined state+county FIPS code.
        county_name: County name (e.g., "Los Angeles County").
        state_fips: 2-digit state FIPS code.
        state_name: State name (e.g., "California").
        is_central_county: True if county contains the urban core, False if outlying.
    """

    cbsa_code: str
    cbsa_title: str
    area_type: str  # "msa" or "micropolitan"
    csa_code: str | None
    csa_title: str | None
    county_fips: str  # 5-digit state+county FIPS
    county_name: str
    state_fips: str
    state_name: str
    is_central_county: bool


def parse_cbsa_delineation(filepath: Path | None = None) -> list[CBSARecord]:
    """Parse CBSA delineation Excel file.

    Args:
        filepath: Path to Excel file. Defaults to CBSA_EXCEL_PATH.

    Returns:
        List of CBSARecord objects mapping counties to CBSAs.

    Raises:
        FileNotFoundError: If the delineation file doesn't exist.
        ValueError: If required columns are missing from the file.
    """
    if filepath is None:
        filepath = CBSA_EXCEL_PATH

    if not filepath.exists():
        raise FileNotFoundError(
            f"CBSA delineation file not found at {filepath}. "
            "Download from: https://www.census.gov/geographies/reference-files/"
            "time-series/demo/metro-micro/delineation-files.html"
        )

    # Read Excel with header on row 3 (0-indexed row 2)
    df = pd.read_excel(filepath, sheet_name=0, header=2, dtype=str)

    # Validate required columns
    required_cols = [
        CBSA_CODE_COL,
        CBSA_TITLE_COL,
        METRO_MICRO_COL,
        STATE_FIPS_COL,
        COUNTY_FIPS_COL,
    ]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    records: list[CBSARecord] = []

    for _, row in df.iterrows():
        # Skip rows without CBSA code
        cbsa_code = str(row.get(CBSA_CODE_COL, "")).strip()
        if not cbsa_code or cbsa_code == "nan":
            continue

        # Determine area type from "Metropolitan/Micropolitan Statistical Area" column
        metro_micro = str(row.get(METRO_MICRO_COL, "")).strip()
        if "Metropolitan" in metro_micro and "Micropolitan" not in metro_micro:
            area_type = "msa"
        elif "Micropolitan" in metro_micro:
            area_type = "micropolitan"
        else:
            # Skip unknown types
            logger.debug(f"Skipping unknown area type: {metro_micro}")
            continue

        # Build 5-digit county FIPS
        state_fips = str(row.get(STATE_FIPS_COL, "")).strip().zfill(2)
        county_fips_3 = str(row.get(COUNTY_FIPS_COL, "")).strip().zfill(3)

        # Handle nan values
        if state_fips == "nan" or county_fips_3 == "nan":
            continue

        county_fips = f"{state_fips}{county_fips_3}"

        # Handle optional CSA fields
        csa_code_raw = str(row.get(CSA_CODE_COL, "")).strip()
        csa_code: str | None = None if not csa_code_raw or csa_code_raw == "nan" else csa_code_raw

        csa_title_raw = str(row.get(CSA_TITLE_COL, "")).strip()
        csa_title: str | None = (
            None if not csa_title_raw or csa_title_raw == "nan" else csa_title_raw
        )

        # Central/Outlying determination
        central_outlying = str(row.get(CENTRAL_OUTLYING_COL, "")).strip()
        is_central = central_outlying.lower() == "central"

        record = CBSARecord(
            cbsa_code=cbsa_code,
            cbsa_title=str(row.get(CBSA_TITLE_COL, "")).strip(),
            area_type=area_type,
            csa_code=csa_code,
            csa_title=csa_title,
            county_fips=county_fips,
            county_name=str(row.get(COUNTY_NAME_COL, "")).strip(),
            state_fips=state_fips,
            state_name=str(row.get(STATE_NAME_COL, "")).strip(),
            is_central_county=is_central,
        )
        records.append(record)

    logger.info(f"Parsed {len(records)} CBSA-to-county mappings from {filepath}")
    return records


def get_unique_cbsas(records: list[CBSARecord]) -> list[dict[str, str]]:
    """Extract unique CBSA records for DimMetroArea population.

    Args:
        records: List of CBSARecord objects from parse_cbsa_delineation().

    Returns:
        List of dicts with cbsa_code, metro_name, and area_type for unique CBSAs.
    """
    seen: set[str] = set()
    cbsas: list[dict[str, str]] = []

    for r in records:
        if r.cbsa_code not in seen:
            seen.add(r.cbsa_code)
            cbsas.append(
                {
                    "cbsa_code": r.cbsa_code,
                    "metro_name": r.cbsa_title,
                    "area_type": r.area_type,
                }
            )

    return cbsas


def get_unique_csas(records: list[CBSARecord]) -> list[dict[str, str]]:
    """Extract unique CSA records for DimMetroArea population.

    CSAs (Combined Statistical Areas) are aggregations of adjacent CBSAs.
    They use the same DimMetroArea table with area_type='csa'.

    Args:
        records: List of CBSARecord objects from parse_cbsa_delineation().

    Returns:
        List of dicts with cbsa_code (actually CSA code), metro_name, and area_type.
    """
    seen: set[str] = set()
    csas: list[dict[str, str]] = []

    for r in records:
        if r.csa_code and r.csa_code not in seen:
            seen.add(r.csa_code)
            csas.append(
                {
                    "cbsa_code": r.csa_code,  # Use cbsa_code column for CSA codes
                    "metro_name": r.csa_title or f"CSA {r.csa_code}",
                    "area_type": "csa",
                }
            )

    return csas


def get_county_metro_mappings(
    records: list[CBSARecord],
) -> list[dict[str, str | bool]]:
    """Extract county-to-metro mappings for BridgeCountyMetro population.

    Args:
        records: List of CBSARecord objects.

    Returns:
        List of dicts with county_fips, cbsa_code, and is_principal_city.
    """
    mappings: list[dict[str, str | bool]] = []

    for r in records:
        # Primary CBSA mapping
        mappings.append(
            {
                "county_fips": r.county_fips,
                "cbsa_code": r.cbsa_code,
                "is_principal_city": r.is_central_county,
            }
        )

        # Also add CSA mapping if present
        if r.csa_code:
            mappings.append(
                {
                    "county_fips": r.county_fips,
                    "cbsa_code": r.csa_code,  # CSA code
                    "is_principal_city": False,  # CSAs don't have principal cities
                }
            )

    return mappings


__all__ = [
    "CBSA_EXCEL_PATH",
    "CBSARecord",
    "parse_cbsa_delineation",
    "get_unique_cbsas",
    "get_unique_csas",
    "get_county_metro_mappings",
]
