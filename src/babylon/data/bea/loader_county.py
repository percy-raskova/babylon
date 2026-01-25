"""BEA county GDP data loader for 3NF schema.

Loads BEA CAGDP2 (County GDP by Industry) from bulk CSV downloads into the
normalized 3NF schema (marxist-data-3NF.duckdb). This loader populates:
- fact_bea_county_gdp: Annual GDP by industry for each county

The CAGDP2 table uses approximately 20 industries at the county level, which
is coarser than the ~70 industries at the national level. The BridgeNAICSBEA
table handles mapping between these levels.

Usage:
    from babylon.data.bea import BEACountyGDPLoader
    from babylon.data.normalize.database import get_normalized_session_factory

    loader = BEACountyGDPLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from __future__ import annotations

import csv
import logging
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimBEAIndustry,
    DimCounty,
    FactBEACountyGDP,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default data directory relative to project root
DEFAULT_DATA_DIR = Path("data")

# BEA suppressed data marker
SUPPRESSED_VALUE = "(D)"

# NAICS code to BEA line code mapping for county-level data
# The CAGDP2 table uses these industry classifications
NAICS_TO_LINE_CODE: dict[str, int] = {
    "...": 1,  # All industry total (line 1)
    "11": 3,  # Agriculture, forestry, fishing, hunting
    "21": 6,  # Mining
    "22": 10,  # Utilities
    "23": 11,  # Construction
    "31-33": 12,  # Manufacturing
    "42": 34,  # Wholesale trade
    "44-45": 35,  # Retail trade
    "48-49": 36,  # Transportation and warehousing
    "51": 45,  # Information
    "52": 50,  # Finance and insurance
    "53": 56,  # Real estate
    "54": 60,  # Professional services
    "55": 64,  # Management of companies
    "56": 65,  # Administrative services
    "61": 69,  # Educational services
    "62": 70,  # Health care
    "71": 76,  # Arts, entertainment, recreation
    "72": 79,  # Accommodation and food services
    "81": 82,  # Other services
    "92": 83,  # Government and government enterprises
}


def parse_gdp_value(value_str: str) -> Decimal | None:
    """Parse GDP value from string, handling suppression and converting to millions.

    Args:
        value_str: Value string from CSV (in thousands of dollars).

    Returns:
        Value in millions of dollars, or None if suppressed/invalid.
    """
    value_str = value_str.strip()

    if not value_str or value_str == SUPPRESSED_VALUE:
        return None

    try:
        # Remove commas if present
        value_str = value_str.replace(",", "")
        # Convert from thousands to millions
        value_thousands = Decimal(value_str)
        return value_thousands / 1000
    except (InvalidOperation, ValueError):
        return None


def extract_county_fips(geofips: str) -> str | None:
    """Extract 5-digit county FIPS from GeoFIPS field.

    Args:
        geofips: GeoFIPS value from CSV (may have quotes/spaces).

    Returns:
        5-digit county FIPS code, or None if not a county.
    """
    # Clean the FIPS code
    fips = geofips.strip().strip('"').strip()

    # Skip non-county entries (national, state, metro)
    if len(fips) != 5:
        return None

    # Must be all numeric (metro areas have letters like M0001)
    if not fips.isdigit():
        return None

    # Skip special codes (00000 = national, XX000 = state)
    if fips == "00000":
        return None
    if fips.endswith("000"):
        return None

    return fips


class BEACountyGDPLoader(DataLoader):
    """Loader for BEA county GDP data into 3NF schema.

    Parses CAGDP2 CSV files from BEA regional data downloads and loads
    GDP by industry for each county into the normalized schema.

    Attributes:
        config: LoaderConfig controlling operational settings.
        data_dir: Path to data directory containing bea/regional/.

    Example:
        loader = BEACountyGDPLoader()
        stats = loader.load(session, reset=True)
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """Initialize BEA county GDP loader.

        Args:
            config: LoaderConfig for operational settings.
            data_dir: Path to data directory. Defaults to "data" in project root.
        """
        super().__init__(config)
        self.data_dir = data_dir if data_dir is not None else DEFAULT_DATA_DIR
        self._county_cache: dict[str, int] = {}  # fips -> county_id
        self._industry_cache: dict[str, int] = {}  # naics_code -> bea_industry_id

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return []  # No dimensions, fact only

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactBEACountyGDP]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load BEA county GDP data into 3NF schema.

        Parses the CAGDP2 CSV file and loads GDP values for each
        county-industry-year combination.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing county GDP data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded facts.
        """
        stats = LoadStats(source="bea_county_gdp")

        if verbose:
            print("Loading BEA county GDP data...")

        try:
            # Build lookup caches
            self._build_county_cache(session)
            self._build_industry_cache(session)

            if not self._county_cache:
                stats.errors.append("DimCounty is empty - run CensusLoader first")
                return stats

            if not self._industry_cache:
                stats.errors.append("DimBEAIndustry is empty - run BEANationalLoader first")
                return stats

            # Clear existing data if reset
            if reset:
                if verbose:
                    print("Clearing existing county GDP data...")
                session.query(FactBEACountyGDP).delete()
                session.commit()

            # Find and extract CSV from zip
            csv_path = self._get_csv_path(verbose)
            if csv_path is None:
                stats.errors.append("CAGDP2.zip not found in data/bea/regional/")
                return stats

            # Load facts from CSV
            fact_count = self._load_from_csv(session, csv_path, verbose)
            stats.facts_loaded["fact_bea_county_gdp"] = fact_count
            stats.files_processed = 1

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _get_csv_path(self, verbose: bool) -> Path | None:
        """Get path to CAGDP2 CSV, extracting from zip if needed.

        Returns:
            Path to CSV file, or None if not found.
        """
        zip_path = self.data_dir / "bea" / "regional" / "CAGDP2.zip"
        if not zip_path.exists():
            return None

        # Extract to same directory
        extract_dir = zip_path.parent
        csv_name = "CAGDP2__ALL_AREAS_2001_2023.csv"
        csv_path = extract_dir / csv_name

        if not csv_path.exists():
            if verbose:
                print(f"Extracting {csv_name} from {zip_path.name}...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract(csv_name, extract_dir)

        return csv_path

    def _build_county_cache(self, session: Session) -> None:
        """Build FIPS -> county_id lookup cache."""
        counties = session.query(DimCounty.county_id, DimCounty.county_fips).all()
        self._county_cache = {fips: county_id for county_id, fips in counties}

    def _build_industry_cache(self, session: Session) -> None:
        """Build NAICS code -> bea_industry_id lookup cache.

        Uses line_number as the canonical key since CAGDP2 line codes
        correspond to specific industries.
        """
        industries = session.query(
            DimBEAIndustry.bea_industry_id,
            DimBEAIndustry.bea_code,
            DimBEAIndustry.line_number,
        ).all()

        # Map both by code and by line_number
        for bea_id, code, line_number in industries:
            self._industry_cache[code] = bea_id
            if line_number:
                self._industry_cache[f"line:{line_number}"] = bea_id

    def _get_industry_id(self, naics_code: str) -> int | None:
        """Get BEA industry ID for a NAICS code.

        Args:
            naics_code: NAICS code from IndustryClassification column.

        Returns:
            bea_industry_id or None if not found.
        """
        # First try direct code lookup
        if naics_code in self._industry_cache:
            return self._industry_cache[naics_code]

        # Try line number mapping
        line_code = NAICS_TO_LINE_CODE.get(naics_code)
        if line_code:
            line_key = f"line:{line_code}"
            if line_key in self._industry_cache:
                return self._industry_cache[line_key]

        return None

    def _load_from_csv(
        self,
        session: Session,
        csv_path: Path,
        verbose: bool,
    ) -> int:
        """Load facts from CAGDP2 CSV file.

        Args:
            session: SQLAlchemy session.
            csv_path: Path to extracted CSV file.
            verbose: Enable progress output.

        Returns:
            Number of fact rows loaded.
        """
        count = 0
        skipped_counties = 0
        skipped_industries = 0

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Get year columns (all columns from 2001 to 2023)
            year_columns = [col for col in reader.fieldnames or [] if col.isdigit()]

            # Count lines for progress bar
            f.seek(0)
            total_lines = sum(1 for _ in f) - 1  # Subtract header
            f.seek(0)
            next(reader)  # Skip header since we're at start

            reader = csv.DictReader(f)
            row_iter = tqdm(reader, total=total_lines, desc="County GDP", disable=not verbose)

            for row in row_iter:
                # Extract county FIPS
                fips = extract_county_fips(row["GeoFIPS"])
                if fips is None:
                    continue

                # Get county_id
                county_id = self._county_cache.get(fips)
                if county_id is None:
                    skipped_counties += 1
                    continue

                # Get industry classification
                naics_code = row["IndustryClassification"].strip()
                industry_id = self._get_industry_id(naics_code)
                if industry_id is None:
                    skipped_industries += 1
                    continue

                # Process each year column
                for year_str in year_columns:
                    year = int(year_str)
                    value = parse_gdp_value(row[year_str])

                    if value is None:
                        continue

                    time_id = self._get_or_create_time(session, year)

                    fact = FactBEACountyGDP(
                        county_id=county_id,
                        bea_industry_id=industry_id,
                        time_id=time_id,
                        gdp_millions=value,
                    )
                    session.add(fact)
                    count += 1

                    if count % 10000 == 0:
                        session.flush()

        session.flush()

        if verbose:
            if skipped_counties > 0:
                print(f"  Skipped {skipped_counties} rows - county not in DimCounty")
            if skipped_industries > 0:
                print(f"  Skipped {skipped_industries} rows - industry not mapped")

        return count


__all__ = [
    "BEACountyGDPLoader",
    "extract_county_fips",
    "parse_gdp_value",
]
