"""CSV parsing utilities for ACS Census data files.

Handles the specific format of Census Bureau CSV exports:
- Row 1: Column codes (GEO_ID, NAME, B19001_001E, ...)
- Row 2: Human-readable labels (Geography, Geographic Area Name, ...)
- Row 3+: Actual data values

Also handles special values that indicate missing/suppressed data.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

# Special Census values that should be treated as NULL
CENSUS_NULL_VALUES = {"N", "-", "(X)", "**", "***", "null", ""}

# Data variants we support
MAIN_VARIANT = "ACSDT5Y2021"
AIAN_VARIANT = "ACSDT5YAIAN2021"
SUPPORTED_VARIANTS = {MAIN_VARIANT, AIAN_VARIANT}


@dataclass
class ColumnMapping:
    """Mapping from Census column codes to human-readable labels."""

    table_code: str
    code_to_label: dict[str, str] = field(default_factory=dict)


@dataclass
class CensusDataFrame:
    """Parsed Census data with metadata."""

    table_code: str
    variant: str
    data: pd.DataFrame
    column_labels: dict[str, str]


def extract_cbsa_code(geo_id: str) -> str | None:
    """Extract CBSA code from Census GEO_ID.

    Args:
        geo_id: Full Census geography ID (e.g., "310M600US10180")

    Returns:
        5-digit CBSA code (e.g., "10180") or None if not extractable
    """
    # Pattern: 310M600US followed by 5-digit CBSA code
    match = re.search(r"310M\d{3}US(\d{5})", geo_id)
    if match:
        return match.group(1)
    return None


def parse_metadata_csv(metadata_path: Path) -> ColumnMapping:
    """Parse Census Column-Metadata.csv file.

    Args:
        metadata_path: Path to *-Column-Metadata.csv file

    Returns:
        ColumnMapping with code-to-label dictionary
    """
    # Extract table code from filename (e.g., "B19001" from "ACSDT5Y2021.B19001-Column-Metadata.csv")
    filename = metadata_path.name
    table_match = re.search(r"\.([BC]\d{5})-Column-Metadata\.csv$", filename)
    if not table_match:
        raise ValueError(f"Cannot extract table code from filename: {filename}")

    table_code = table_match.group(1)

    # Read metadata CSV
    df = pd.read_csv(metadata_path)
    code_to_label = dict(zip(df["Column Name"], df["Label"], strict=False))

    return ColumnMapping(table_code=table_code, code_to_label=code_to_label)


def parse_data_csv(data_path: Path, skip_moe: bool = True) -> CensusDataFrame:
    """Parse Census Data.csv file.

    Args:
        data_path: Path to *-Data.csv file
        skip_moe: If True, skip Margin of Error columns (default: True)

    Returns:
        CensusDataFrame with parsed data and metadata
    """
    # Extract table code and variant from filename
    filename = data_path.name
    # Pattern: VARIANT.TABLE-Data.csv
    match = re.search(r"^(ACSDT5Y\w*2021)\.([BC]\d{5})-Data\.csv$", filename)
    if not match:
        raise ValueError(f"Cannot parse filename: {filename}")

    variant = match.group(1)
    table_code = match.group(2)

    # Read CSV with two header rows
    # Row 1: Column codes, Row 2: Labels
    df_codes = pd.read_csv(data_path, nrows=0, encoding="utf-8-sig")  # Just headers
    df_labels = pd.read_csv(data_path, skiprows=1, nrows=1, header=None, encoding="utf-8-sig")

    # Create label mapping from row 2
    column_labels = dict(zip(df_codes.columns, df_labels.iloc[0], strict=False))

    # Read actual data (skip first 2 rows which are headers)
    df = pd.read_csv(data_path, skiprows=2, header=None, encoding="utf-8-sig")
    df.columns = df_codes.columns

    # Filter to only estimate columns (skip MOE if requested)
    if skip_moe:
        # Keep GEO_ID, NAME, and columns ending in E (estimates)
        # Also keep POPGROUP columns for AIAN variant
        keep_cols = ["GEO_ID", "NAME"]
        if "POPGROUP" in df.columns:
            keep_cols.extend(["POPGROUP", "POPGROUP_LABEL"])

        estimate_cols = [c for c in df.columns if c.endswith("E") and c not in keep_cols]
        df = df[keep_cols + estimate_cols]

        # Filter column_labels too
        column_labels = {k: v for k, v in column_labels.items() if k in df.columns}

    # Handle special Census NULL values
    for col in df.columns:
        if df[col].dtype == object:  # String columns
            df[col] = df[col].replace(CENSUS_NULL_VALUES, None)

    return CensusDataFrame(
        table_code=table_code,
        variant=variant,
        data=df,
        column_labels=column_labels,
    )


def discover_census_files(census_dir: Path) -> dict[str, dict[str, Path]]:
    """Discover all Census data files in directory.

    Args:
        census_dir: Path to data/census/ directory

    Returns:
        Nested dict: {table_code: {variant: data_path}}
    """
    files: dict[str, dict[str, Path]] = {}

    for table_dir in census_dir.iterdir():
        if not table_dir.is_dir():
            continue

        table_code = table_dir.name
        files[table_code] = {}

        for data_file in table_dir.glob("*-Data.csv"):
            # Extract variant from filename
            match = re.search(r"^(ACSDT5Y\w*2021)", data_file.name)
            if match and match.group(1) in SUPPORTED_VARIANTS:
                variant = match.group(1)
                files[table_code][variant] = data_file

    return files


def get_estimate_columns(df: pd.DataFrame, table_code: str) -> list[str]:
    """Get list of estimate column codes (excluding GEO_ID, NAME, etc).

    Args:
        df: DataFrame with Census data
        table_code: Census table code (e.g., "B19001")

    Returns:
        List of column codes like ["B19001_001E", "B19001_002E", ...]
    """
    return [c for c in df.columns if c.startswith(table_code) and c.endswith("E")]


def parse_column_label(label: str) -> tuple[str, str | None]:
    """Parse Census column label to extract hierarchy.

    Labels have format like:
    - "Estimate!!Total:"
    - "Estimate!!Total:!!Less than $10,000"
    - "Estimate!!Male:!!Management, business, science, and arts occupations:"

    Args:
        label: Raw Census label string

    Returns:
        Tuple of (clean_label, category) where category is top-level grouping
    """
    if not label or not isinstance(label, str):
        return ("", None)

    # Remove "Estimate!!" prefix
    clean = label.replace("Estimate!!", "").replace("Margin of Error!!", "")

    # Split by "!!" to get hierarchy
    parts = clean.split("!!")

    # First non-empty part after removing "Total:" is the category
    category = None
    for part in parts:
        part = part.strip().rstrip(":")
        if part and part.lower() not in ("total", ""):
            category = part
            break

    # Full label is the last meaningful part
    full_label = parts[-1].strip().rstrip(":") if parts else ""

    return (full_label, category)


def safe_int(value: Any) -> int | None:
    """Convert value to int, returning None for invalid values.

    Args:
        value: Value to convert

    Returns:
        Integer value or None
    """
    if pd.isna(value) or value in CENSUS_NULL_VALUES:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_float(value: Any) -> float | None:
    """Convert value to float, returning None for invalid values.

    Args:
        value: Value to convert

    Returns:
        Float value or None
    """
    if pd.isna(value) or value in CENSUS_NULL_VALUES:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
