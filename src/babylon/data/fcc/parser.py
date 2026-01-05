"""FCC BDC CSV parser for broadband coverage data.

Parses downloaded FCC Broadband Data Collection summary CSVs into typed records
for ingestion into the Babylon database.

The parser filters to county-level, residential, "Any Technology" records
to provide aggregate broadband coverage metrics.
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TextIO


@dataclass(frozen=True)
class FCCBroadbandRecord:
    """Parsed FCC broadband coverage record for a county.

    Attributes:
        county_fips: 5-digit county FIPS code (e.g., "06001").
        county_name: County name (e.g., "Alameda County").
        state_name: State abbreviation from full description (e.g., "CA").
        total_units: Total broadband serviceable locations in county.
        pct_25_3: Percent of locations with 25/3 Mbps service (0.0-1.0).
        pct_100_20: Percent of locations with 100/20 Mbps service (0.0-1.0).
        pct_1000_100: Percent of locations with 1000/100 Mbps service (0.0-1.0).
    """

    county_fips: str
    county_name: str
    state_name: str
    total_units: int
    pct_25_3: Decimal
    pct_100_20: Decimal
    pct_1000_100: Decimal


def parse_fcc_summary_csv(
    filepath: Path,
    *,
    area_data_type: str = "Total",
    geography_type: str = "County",
    biz_res: str = "R",
    technology: str = "Any Technology",
) -> Iterator[FCCBroadbandRecord]:
    """Parse FCC BDC summary CSV into broadband coverage records.

    Filters CSV rows to specified area type, geography type, business/residential
    flag, and technology type, then yields parsed records.

    Args:
        filepath: Path to FCC summary CSV file.
        area_data_type: Area type filter ("Total", "Urban", "Rural", "Nontribal").
            Defaults to "Total" for aggregate county coverage.
        geography_type: Geography type to filter on. Defaults to "County".
        biz_res: Business ("B") or Residential ("R") filter. Defaults to "R".
        technology: Technology type to filter on. Defaults to "Any Technology".

    Yields:
        FCCBroadbandRecord for each matching row.

    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        KeyError: If required columns are missing from CSV.

    Example:
        >>> from pathlib import Path
        >>> csv_path = Path("data/fcc/downloads/2025-06-30/national/summary.csv")
        >>> for record in parse_fcc_summary_csv(csv_path):
        ...     print(f"{record.county_fips}: {record.pct_25_3:.1%}")
    """
    with filepath.open(encoding="utf-8") as f:
        yield from _parse_fcc_csv_stream(
            f,
            area_data_type=area_data_type,
            geography_type=geography_type,
            biz_res=biz_res,
            technology=technology,
        )


def _parse_fcc_csv_stream(
    stream: TextIO,
    *,
    area_data_type: str,
    geography_type: str,
    biz_res: str,
    technology: str,
) -> Iterator[FCCBroadbandRecord]:
    """Parse FCC CSV from a text stream.

    Internal implementation for testability with StringIO.
    """
    reader = csv.DictReader(stream)

    # Validate required columns
    required_columns = {
        "area_data_type",
        "geography_type",
        "geography_id",
        "geography_desc",
        "geography_desc_full",
        "total_units",
        "biz_res",
        "technology",
        "speed_25_3",
        "speed_100_20",
        "speed_1000_100",
    }

    if reader.fieldnames is None:
        return

    missing = required_columns - set(reader.fieldnames)
    if missing:
        msg = f"Missing required columns: {sorted(missing)}"
        raise KeyError(msg)

    for row in reader:
        # Apply filters
        if row["area_data_type"] != area_data_type:
            continue
        if row["geography_type"] != geography_type:
            continue
        if row["biz_res"] != biz_res:
            continue
        if row["technology"] != technology:
            continue

        # Parse state name from full description (e.g., "Alameda County, CA" -> "CA")
        state_name = _extract_state_from_desc(row["geography_desc_full"])

        yield FCCBroadbandRecord(
            county_fips=row["geography_id"],
            county_name=row["geography_desc"],
            state_name=state_name,
            total_units=int(row["total_units"]),
            pct_25_3=Decimal(row["speed_25_3"]),
            pct_100_20=Decimal(row["speed_100_20"]),
            pct_1000_100=Decimal(row["speed_1000_100"]),
        )


def _extract_state_from_desc(desc_full: str) -> str:
    """Extract state abbreviation from full geography description.

    Args:
        desc_full: Full description like "Alameda County, CA".

    Returns:
        State abbreviation (e.g., "CA") or empty string if not parseable.
    """
    if ", " in desc_full:
        return desc_full.rsplit(", ", 1)[-1]
    return ""


def count_counties_by_state(filepath: Path) -> dict[str, int]:
    """Count number of counties per state in FCC summary CSV.

    Useful for validation and debugging.

    Args:
        filepath: Path to FCC summary CSV file.

    Returns:
        Dict mapping state abbreviations to county counts.
    """
    counts: dict[str, int] = {}
    for record in parse_fcc_summary_csv(filepath):
        state = record.state_name
        counts[state] = counts.get(state, 0) + 1
    return counts
