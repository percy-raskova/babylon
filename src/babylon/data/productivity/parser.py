"""Excel parsing utilities for BLS Industry Productivity data.

Handles the MachineReadable sheet format from BLS productivity Excel files:
- Sector, NAICS, Industry, Digit, Basis, Measure, Units, Year, Value

Pivots long-format data into wide format per industry-year for database ingestion.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

# Files in data/productivity/
HOURS_EMPLOYMENT_FILE = "hours-employment-detailed-industries.xlsx"
LABOR_PRODUCTIVITY_FILE = "labor-productivity-detailed-industries.xlsx"

# Sheet name for machine-readable data
MACHINE_READABLE_SHEET = "MachineReadable"

# Measures to extract from hours/employment file
HOURS_MEASURES = {
    ("Hours worked", "Index (2017=100)"): "hours_worked_index",
    ("Hours worked", "Millions of hours"): "hours_worked_millions",
    ("Employment", "Thousands of jobs"): "employment_thousands",
}

# Measures to extract from labor productivity file
PRODUCTIVITY_MEASURES = {
    ("Labor productivity", "Index (2017=100)"): "labor_productivity_index",
    ("Labor productivity", "% Change from previous year"): "labor_productivity_pct_chg",
    ("Hourly compensation", "Index (2017=100)"): "hourly_compensation_index",
    ("Unit labor costs", "Index (2017=100)"): "unit_labor_costs_index",
    ("Real sectoral output", "Index (2017=100)"): "real_output_index",
    ("Sectoral output", "Index (2017=100)"): "sectoral_output_index",
    ("Labor compensation", "Millions of current dollars"): "labor_compensation_millions",
    ("Sectoral output", "Millions of current dollars"): "sectoral_output_millions",
}


@dataclass
class IndustryRecord:
    """Parsed industry dimension record."""

    naics_code: str
    industry_title: str
    sector: str | None
    digit_level: str


@dataclass
class ProductivityRecord:
    """Parsed productivity fact record for a single industry-year."""

    naics_code: str
    year: int
    # Core productivity
    labor_productivity_index: float | None = None
    labor_productivity_pct_chg: float | None = None
    # Hours and employment
    hours_worked_index: float | None = None
    hours_worked_millions: float | None = None
    employment_thousands: float | None = None
    # Compensation
    hourly_compensation_index: float | None = None
    unit_labor_costs_index: float | None = None
    # Output
    real_output_index: float | None = None
    sectoral_output_index: float | None = None
    # Absolute values (millions)
    labor_compensation_millions: float | None = None
    sectoral_output_millions: float | None = None


@dataclass
class ParsedProductivityData:
    """Container for parsed productivity data."""

    industries: list[IndustryRecord] = field(default_factory=list)
    records: list[ProductivityRecord] = field(default_factory=list)


def parse_value(value: Any) -> float | None:
    """Parse a cell value to float, handling N.A. and other special values."""
    if pd.isna(value):
        return None
    if isinstance(value, str):
        if value.strip().upper() in ("N.A.", "NA", "-", "", "N/A"):
            return None
        try:
            return float(value)
        except ValueError:
            return None
    if isinstance(value, int | float):
        import math

        f = float(value)
        return None if math.isnan(f) else f
    return None


def _safe_get(row: Any, key: str) -> float | None:
    """Safely get a float value from a row, converting NaN to None."""
    val = row.get(key)
    if val is None or pd.isna(val):
        return None
    import math

    if isinstance(val, float) and math.isnan(val):
        return None
    return float(val)


def load_hours_employment(filepath: Path, year: int | None = None) -> pd.DataFrame:
    """Load hours and employment data from Excel.

    Args:
        filepath: Path to hours-employment-detailed-industries.xlsx
        year: Optional year to filter (default: all years)

    Returns:
        DataFrame with columns: NAICS, Industry, Sector, Digit, Year, + measure columns
    """
    df = pd.read_excel(filepath, sheet_name=MACHINE_READABLE_SHEET)

    if year is not None:
        df = df[df["Year"] == year]

    # Pivot measures into columns
    result_rows = []
    for (naics, industry, sector, digit, yr), group in df.groupby(
        ["NAICS", "Industry", "Sector", "Digit", "Year"]
    ):
        row: dict[str, Any] = {
            "NAICS": str(naics),
            "Industry": industry,
            "Sector": sector,
            "Digit": digit,
            "Year": int(yr),
        }

        for _, record in group.iterrows():
            measure = record["Measure"]
            units = record["Units"]
            key = (measure, units)
            if key in HOURS_MEASURES:
                col_name = HOURS_MEASURES[key]
                row[col_name] = parse_value(record["Value"])

        result_rows.append(row)

    return pd.DataFrame(result_rows)


def load_labor_productivity(filepath: Path, year: int | None = None) -> pd.DataFrame:
    """Load labor productivity data from Excel.

    Args:
        filepath: Path to labor-productivity-detailed-industries.xlsx
        year: Optional year to filter (default: all years)

    Returns:
        DataFrame with columns: NAICS, Industry, Sector, Digit, Year, + measure columns
    """
    df = pd.read_excel(filepath, sheet_name=MACHINE_READABLE_SHEET)

    if year is not None:
        df = df[df["Year"] == year]

    # Pivot measures into columns
    result_rows = []
    for (naics, industry, sector, digit, yr), group in df.groupby(
        ["NAICS", "Industry", "Sector", "Digit", "Year"]
    ):
        row: dict[str, Any] = {
            "NAICS": str(naics),
            "Industry": industry,
            "Sector": sector,
            "Digit": digit,
            "Year": int(yr),
        }

        for _, record in group.iterrows():
            measure = record["Measure"]
            units = record["Units"]
            key = (measure, units)
            if key in PRODUCTIVITY_MEASURES:
                col_name = PRODUCTIVITY_MEASURES[key]
                row[col_name] = parse_value(record["Value"])

        result_rows.append(row)

    return pd.DataFrame(result_rows)


def parse_productivity_data(
    productivity_dir: Path,
    year: int = 2022,
) -> ParsedProductivityData:
    """Parse both productivity Excel files and merge into unified records.

    Args:
        productivity_dir: Path to data/productivity/ directory
        year: Year to extract (default: 2022)

    Returns:
        ParsedProductivityData with industries and records
    """
    hours_path = productivity_dir / HOURS_EMPLOYMENT_FILE
    prod_path = productivity_dir / LABOR_PRODUCTIVITY_FILE

    if not hours_path.exists():
        raise FileNotFoundError(f"Hours file not found: {hours_path}")
    if not prod_path.exists():
        raise FileNotFoundError(f"Productivity file not found: {prod_path}")

    # Load both files
    hours_df = load_hours_employment(hours_path, year)
    prod_df = load_labor_productivity(prod_path, year)

    # Merge only on NAICS + Year to avoid mismatches in Industry/Sector/Digit text
    merged = pd.merge(
        hours_df,
        prod_df,
        on=["NAICS", "Year"],
        how="outer",
        suffixes=("_hours", "_prod"),
    )

    # Extract unique industries (prefer hours file, fallback to prod file)
    industries: dict[str, IndustryRecord] = {}
    for _, row in merged.iterrows():
        naics = str(row["NAICS"])
        if naics not in industries:
            # Prefer hours data, fallback to prod data for industry info
            industry = row.get("Industry_hours") or row.get("Industry_prod") or ""
            sector = row.get("Sector_hours") or row.get("Sector_prod")
            digit = row.get("Digit_hours") or row.get("Digit_prod") or ""
            industries[naics] = IndustryRecord(
                naics_code=naics,
                industry_title=industry,
                sector=sector if pd.notna(sector) else None,
                digit_level=str(digit),
            )

    # Create productivity records
    records: list[ProductivityRecord] = []
    for _, row in merged.iterrows():
        record = ProductivityRecord(
            naics_code=str(row["NAICS"]),
            year=int(row["Year"]),
            # Hours/employment
            hours_worked_index=_safe_get(row, "hours_worked_index"),
            hours_worked_millions=_safe_get(row, "hours_worked_millions"),
            employment_thousands=_safe_get(row, "employment_thousands"),
            # Productivity
            labor_productivity_index=_safe_get(row, "labor_productivity_index"),
            labor_productivity_pct_chg=_safe_get(row, "labor_productivity_pct_chg"),
            # Compensation
            hourly_compensation_index=_safe_get(row, "hourly_compensation_index"),
            unit_labor_costs_index=_safe_get(row, "unit_labor_costs_index"),
            # Output
            real_output_index=_safe_get(row, "real_output_index"),
            sectoral_output_index=_safe_get(row, "sectoral_output_index"),
            labor_compensation_millions=_safe_get(row, "labor_compensation_millions"),
            sectoral_output_millions=_safe_get(row, "sectoral_output_millions"),
        )
        records.append(record)

    return ParsedProductivityData(
        industries=list(industries.values()),
        records=records,
    )


def discover_available_years(productivity_dir: Path) -> list[int]:
    """Discover available years in productivity data.

    Args:
        productivity_dir: Path to data/productivity/ directory

    Returns:
        Sorted list of available years
    """
    hours_path = productivity_dir / HOURS_EMPLOYMENT_FILE
    df = pd.read_excel(hours_path, sheet_name=MACHINE_READABLE_SHEET, usecols=["Year"])
    return sorted(df["Year"].unique().tolist())
