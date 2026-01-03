"""USGS Mineral Commodity Summaries CSV parser.

Parses commodity and aggregate data from USGS MCS CSV files into structured
records for database loading.

CSV structures:

Per-commodity files (mcs2025-*_salient.csv):
    Header: DataSource, Commodity, Year, metric1, metric2, ...
    Data: MCS2025, Lithium, 2020, value1, value2, ...

Aggregate files:
    MCS2025_T1_Mineral_Industry_Trends.csv: Industry employment and production
    MCS2025_T3_State_Value_Rank.csv: State-level production rankings

Special value handling:
    "W" = Withheld (proprietary data protection)
    "NA", "N/A", "" = Not Available
    ">50", ">25" = Greater than threshold (for NIR_pct)
    "<1" = Less than threshold
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CommodityRecord:
    """Parsed commodity observation."""

    commodity_code: str
    commodity_name: str
    metric_code: str
    metric_name: str
    year: int
    value: float | None
    value_text: str | None


@dataclass
class TrendRecord:
    """Parsed mineral industry trend."""

    year: int
    values: dict[str, float | None] = field(default_factory=dict)


@dataclass
class StateRecord:
    """Parsed state mineral production."""

    state_name: str
    year: int
    value_millions: float | None
    rank: int | None
    percent_total: float | None
    principal_commodities: str | None


@dataclass
class ImportSourceRecord:
    """Parsed import source country."""

    country: str
    commodity_count: int
    map_class: str | None


def parse_value(raw: str | None) -> tuple[float | None, str | None]:
    """Parse raw value, handling USGS special cases.

    USGS uses:
        - "W" = Withheld to avoid disclosing proprietary data
        - "NA", "N/A", "" = Not available
        - ">50", ">25" = Greater than threshold (for NIR_pct)
        - "<1" = Less than threshold
        - Numeric = Direct value (may include commas)

    Args:
        raw: Raw string value from CSV

    Returns:
        Tuple of (numeric_value, original_text_if_special)

    Examples:
        >>> parse_value("28.5")
        (28.5, None)
        >>> parse_value("W")
        (None, 'W')
        >>> parse_value(">50")
        (50.0, '>50')
        >>> parse_value("1,234")
        (1234.0, None)
    """
    if raw is None:
        return None, None

    raw_str = str(raw).strip()

    # Empty or NA variants
    if not raw_str or raw_str.upper() in ("NA", "N/A", "--", "-"):
        return None, raw_str if raw_str else None

    # Withheld
    if raw_str.upper() == "W":
        return None, "W"

    # Greater than (e.g., ">50")
    if raw_str.startswith(">"):
        try:
            return float(raw_str[1:].replace(",", "")), raw_str
        except ValueError:
            return None, raw_str

    # Less than (e.g., "<1")
    if raw_str.startswith("<"):
        try:
            return float(raw_str[1:].replace(",", "")), raw_str
        except ValueError:
            return None, raw_str

    # E notation for "Net Exporter" in NIR column
    if raw_str.upper() == "E":
        return None, "E"

    # Regular numeric value
    try:
        # Remove commas and any trailing text (e.g., "2024_estimated")
        clean = re.sub(r"[,_a-zA-Z]+", "", raw_str)
        if clean:
            return float(clean), None
    except ValueError:
        pass

    return None, raw_str


def extract_commodity_code(filename: str) -> str:
    """Extract commodity code from filename.

    Args:
        filename: CSV filename (e.g., "mcs2025-lithium_salient.csv")

    Returns:
        Commodity code (e.g., "lithium")

    Examples:
        >>> extract_commodity_code("mcs2025-lithium_salient.csv")
        'lithium'
        >>> extract_commodity_code("mcs2025-reare_salient.csv")
        'reare'
    """
    match = re.search(r"mcs2025-(\w+)_salient\.csv", filename, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    # Fallback
    return Path(filename).stem.replace("mcs2025-", "").replace("_salient", "").lower()


def normalize_metric_code(column_name: str) -> str:
    """Normalize column name to metric code.

    Args:
        column_name: Raw column name from CSV header

    Returns:
        Normalized metric code

    Examples:
        >>> normalize_metric_code("USprod_Primary_kt")
        'USprod_Primary_kt'
        >>> normalize_metric_code("NIR_pct")
        'NIR_pct'
    """
    # Remove leading/trailing whitespace
    return column_name.strip()


def get_metric_category(metric_code: str) -> str:
    """Determine metric category from code.

    Args:
        metric_code: Metric code (e.g., "USprod_t", "NIR_pct")

    Returns:
        Category string

    Examples:
        >>> get_metric_category("USprod_t")
        'production'
        >>> get_metric_category("NIR_pct")
        'strategic'
    """
    code_upper = metric_code.upper()

    if "USPROD" in code_upper or "MINE_PROD" in code_upper or "PROD" in code_upper:
        return "production"
    if "IMPORT" in code_upper:
        return "trade"
    if "EXPORT" in code_upper:
        return "trade"
    if "CONSUMP" in code_upper or "SUPPLY" in code_upper:
        return "consumption"
    if "PRICE" in code_upper or "AVG" in code_upper:
        return "price"
    if "NIR" in code_upper or "STOCK" in code_upper:
        return "strategic"
    if "EMPLOY" in code_upper:
        return "employment"

    return "other"


def parse_commodity_csv(file_path: Path) -> list[CommodityRecord]:
    """Parse individual commodity CSV file.

    CSV structure:
        Header: DataSource, Commodity, Year, metric1, metric2, ...
        Data: MCS2025, Lithium, 2020, value1, value2, ...

    Handles duplicate column names by taking the first occurrence only.

    Args:
        file_path: Path to commodity CSV file

    Returns:
        List of CommodityRecord for each (metric, year) combination
    """
    if not file_path.exists():
        return []

    commodity_code = extract_commodity_code(file_path.name)
    records: list[CommodityRecord] = []

    with file_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            return []

        # Get metric columns (skip DataSource, Commodity, Year)
        # Deduplicate column names - take first occurrence only
        seen_cols: set[str] = set()
        metric_columns: list[str] = []
        for col in reader.fieldnames:
            if col not in ("DataSource", "Commodity", "Year") and col not in seen_cols:
                metric_columns.append(col)
                seen_cols.add(col)

        for row in reader:
            # Get commodity name from row (more accurate than filename)
            commodity_name = row.get("Commodity", commodity_code.title())

            # Parse year
            year_str = row.get("Year", "")
            try:
                # Handle "2024_estimated" format
                year = int(re.sub(r"[^0-9]", "", year_str)[:4])
            except (ValueError, IndexError):
                continue

            # Parse each metric column
            for metric_col in metric_columns:
                raw_value = row.get(metric_col)
                value, value_text = parse_value(raw_value)

                # Skip if no data
                if value is None and value_text is None:
                    continue

                metric_code = normalize_metric_code(metric_col)

                records.append(
                    CommodityRecord(
                        commodity_code=commodity_code,
                        commodity_name=commodity_name,
                        metric_code=metric_code,
                        metric_name=metric_col,  # Use original column name
                        year=year,
                        value=value,
                        value_text=value_text,
                    )
                )

    return records


def parse_trends_csv(file_path: Path) -> list[TrendRecord]:
    """Parse MCS2025_T1_Mineral_Industry_Trends.csv.

    Args:
        file_path: Path to trends CSV file

    Returns:
        List of TrendRecord (one per year)
    """
    if not file_path.exists():
        return []

    records: list[TrendRecord] = []

    with file_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Parse year
            year_str = row.get("Year", "")
            try:
                year = int(re.sub(r"[^0-9]", "", year_str)[:4])
            except (ValueError, IndexError):
                continue

            values: dict[str, float | None] = {}
            for key, raw in row.items():
                if key in ("Source", "Year"):
                    continue
                value, _ = parse_value(raw)
                values[key] = value

            records.append(TrendRecord(year=year, values=values))

    return records


def parse_state_csv(file_path: Path) -> list[StateRecord]:
    """Parse MCS2025_T3_State_Value_Rank.csv.

    Args:
        file_path: Path to state CSV file

    Returns:
        List of StateRecord
    """
    if not file_path.exists():
        return []

    records: list[StateRecord] = []

    with file_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            state_name = row.get("State", "").strip()
            if not state_name:
                continue

            # Parse year from Year column
            year_str = row.get("Year", "")
            try:
                year = int(re.sub(r"[^0-9]", "", year_str)[:4])
            except (ValueError, IndexError):
                year = 2024  # Default to latest

            # Parse value
            value_raw = row.get("Value _millions_prelim_2024") or row.get(
                "Value_millions_prelim_2024"
            )
            value_millions, _ = parse_value(value_raw)

            # Parse rank
            rank_raw = row.get("State_Rank_prelim_2024")
            rank_val, _ = parse_value(rank_raw)
            rank = int(rank_val) if rank_val is not None else None

            # Parse percent
            pct_raw = row.get("State_percent_total_prelim")
            percent_total, _ = parse_value(pct_raw)

            # Principal commodities
            principal = row.get("Principal_commodities", "")

            records.append(
                StateRecord(
                    state_name=state_name,
                    year=year,
                    value_millions=value_millions,
                    rank=rank,
                    percent_total=percent_total,
                    principal_commodities=principal if principal else None,
                )
            )

    return records


def parse_import_sources_csv(file_path: Path) -> list[ImportSourceRecord]:
    """Parse major import sources CSV.

    CSV structure:
        Source,Country,Commodity_Count,Map_Class
        MCS2024,Australia,6,4 to 6
        ...

    Args:
        file_path: Path to MCS2025_Fig3_Major_Import_Sources.csv

    Returns:
        List of ImportSourceRecord objects.
    """
    records: list[ImportSourceRecord] = []

    with file_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            country = row.get("Country", "").strip()
            if not country:
                continue

            try:
                commodity_count = int(row.get("Commodity_Count", "0"))
            except ValueError:
                commodity_count = 0

            map_class = row.get("Map_Class", "").strip() or None

            records.append(
                ImportSourceRecord(
                    country=country,
                    commodity_count=commodity_count,
                    map_class=map_class,
                )
            )

    return records


def discover_commodity_files(materials_dir: Path) -> list[Path]:
    """Discover all commodity salient CSV files.

    Prefers commodities/ subdirectory over minerals/ to avoid duplicates.
    Only adds files from minerals/ if they don't exist in commodities/.

    Args:
        materials_dir: Path to data/raw_mats/ directory

    Returns:
        List of paths to commodity CSV files (deduplicated by filename)
    """
    if not materials_dir.exists():
        return []

    # Track seen filenames to deduplicate
    seen_names: set[str] = set()
    files: list[Path] = []

    # Check commodities/ subdirectory first (preferred source)
    commodities_dir = materials_dir / "commodities"
    if commodities_dir.exists():
        for f in sorted(commodities_dir.glob("mcs2025-*_salient.csv")):
            if f.name not in seen_names:
                files.append(f)
                seen_names.add(f.name)

    # Check minerals/ subdirectory only for files not in commodities/
    minerals_dir = materials_dir / "minerals"
    if minerals_dir.exists():
        for f in sorted(minerals_dir.glob("mcs2025-*_salient.csv")):
            if f.name not in seen_names:
                files.append(f)
                seen_names.add(f.name)

    return sorted(files)


def discover_aggregate_files(materials_dir: Path) -> dict[str, Path | None]:
    """Discover aggregate data files.

    Args:
        materials_dir: Path to data/raw_mats/ directory

    Returns:
        Dict with keys: trends, states, import_sources
    """
    result: dict[str, Path | None] = {
        "trends": None,
        "states": None,
        "import_sources": None,
    }

    if not materials_dir.exists():
        return result

    # Check both root and minerals/ subdirectory
    search_dirs = [materials_dir, materials_dir / "minerals"]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Trends file
        trends = search_dir / "MCS2025_T1_Mineral_Industry_Trends.csv"
        if trends.exists() and result["trends"] is None:
            result["trends"] = trends

        # State file
        states = search_dir / "MCS2025_T3_State_Value_Rank.csv"
        if states.exists() and result["states"] is None:
            result["states"] = states

        # Import sources (if exists)
        imports = search_dir / "MCS2025_Fig3_Major_Import_Sources.csv"
        if imports.exists() and result["import_sources"] is None:
            result["import_sources"] = imports

    return result
