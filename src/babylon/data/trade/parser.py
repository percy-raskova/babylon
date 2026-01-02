"""Excel parsing utilities for UN trade data files.

Handles the specific format of the country.xlsx trade data:
- Columns: year, CTY_CODE, CTYNAME
- Monthly imports: IJAN through IDEC
- Annual imports: IYR
- Monthly exports: EJAN through EDEC
- Annual exports: EYR
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

# Month column mappings
IMPORT_MONTHS = [
    "IJAN",
    "IFEB",
    "IMAR",
    "IAPR",
    "IMAY",
    "IJUN",
    "IJUL",
    "IAUG",
    "ISEP",
    "IOCT",
    "INOV",
    "IDEC",
]
EXPORT_MONTHS = [
    "EJAN",
    "EFEB",
    "EMAR",
    "EAPR",
    "EMAY",
    "EJUN",
    "EJUL",
    "EAUG",
    "ESEP",
    "EOCT",
    "ENOV",
    "EDEC",
]

# Regional aggregates that should be flagged
REGIONAL_NAMES = {
    "Africa",
    "Asia",
    "Australia and Oceania",
    "Central America",
    "Europe",
    "European Union",
    "Middle East",
    "North America",
    "South America",
    "South/Central America",
    "OPEC",
    "Pacific Rim",
    "Euro Area",
    "Newly Industrialized Countries",
    "Advanced Technology Products",
}


@dataclass
class TradeCountryData:
    """Parsed country/region data."""

    cty_code: str
    name: str
    is_region: bool = False


@dataclass
class TradeRowData:
    """Parsed row of trade data."""

    cty_code: str
    year: int
    monthly_imports: list[float | None] = field(default_factory=list)  # 12 values
    monthly_exports: list[float | None] = field(default_factory=list)  # 12 values
    annual_imports: float | None = None
    annual_exports: float | None = None


@dataclass
class TradeDataFrame:
    """Parsed trade data with metadata."""

    countries: list[TradeCountryData]
    rows: list[TradeRowData]
    year_range: tuple[int, int]


def safe_float(value: Any) -> float | None:
    """Convert value to float, returning None for invalid values.

    Args:
        value: Value to convert

    Returns:
        Float value or None
    """
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> int | None:
    """Convert value to int, returning None for invalid values.

    Args:
        value: Value to convert

    Returns:
        Integer value or None
    """
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_trade_excel(xlsx_path: Path) -> TradeDataFrame:
    """Parse UN trade data Excel file.

    Args:
        xlsx_path: Path to country.xlsx file

    Returns:
        TradeDataFrame with parsed countries and trade rows
    """
    # Read Excel file
    df = pd.read_excel(xlsx_path, sheet_name="country")

    # Extract unique countries
    country_df = df[["CTY_CODE", "CTYNAME"]].drop_duplicates()
    countries: list[TradeCountryData] = []

    for _, row in country_df.iterrows():
        cty_code = str(row["CTY_CODE"]).strip()
        name = str(row["CTYNAME"]).strip()
        is_region = name in REGIONAL_NAMES

        countries.append(
            TradeCountryData(
                cty_code=cty_code,
                name=name,
                is_region=is_region,
            )
        )

    # Parse trade rows
    rows: list[TradeRowData] = []
    min_year = 9999
    max_year = 0

    for _, row in df.iterrows():
        year = safe_int(row["year"])
        if year is None:
            continue

        min_year = min(min_year, year)
        max_year = max(max_year, year)

        cty_code = str(row["CTY_CODE"]).strip()

        # Parse monthly values
        monthly_imports = [safe_float(row.get(col)) for col in IMPORT_MONTHS]
        monthly_exports = [safe_float(row.get(col)) for col in EXPORT_MONTHS]

        # Parse annual totals
        annual_imports = safe_float(row.get("IYR"))
        annual_exports = safe_float(row.get("EYR"))

        rows.append(
            TradeRowData(
                cty_code=cty_code,
                year=year,
                monthly_imports=monthly_imports,
                monthly_exports=monthly_exports,
                annual_imports=annual_imports,
                annual_exports=annual_exports,
            )
        )

    return TradeDataFrame(
        countries=countries,
        rows=rows,
        year_range=(min_year, max_year),
    )
