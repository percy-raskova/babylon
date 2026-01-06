"""FCC Broadband Coverage loader.

Loads FCC BDC (Broadband Data Collection) broadband coverage data from
downloaded CSV files into the Babylon 3NF schema.

The loader reads pre-downloaded national summary CSVs and populates the
FactBroadbandCoverage table with county-level coverage metrics at multiple
speed tiers.

Source: https://broadbandmap.fcc.gov/data-download/nationwide-data
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from babylon.data.fcc.parser import parse_fcc_summary_csv
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimCounty,
    DimDataSource,
    FactBroadbandCoverage,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default download directory relative to project root
DEFAULT_DOWNLOAD_DIR = Path("data/fcc/downloads")


class FCCBroadbandLoader(DataLoader):
    """Loader for FCC Broadband Data Collection coverage data.

    Reads downloaded FCC BDC national summary CSVs and loads county-level
    broadband coverage metrics into FactBroadbandCoverage.

    The loader expects pre-downloaded CSV files in the download directory
    with structure: {download_dir}/{as_of_date}/national/*.csv

    Example:
        from babylon.data.fcc import FCCBroadbandLoader

        loader = FCCBroadbandLoader()
        stats = loader.load(session, as_of_date="2025-06-30")
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        download_dir: Path | None = None,
    ) -> None:
        """Initialize FCC broadband loader.

        Args:
            config: Optional loader configuration.
            download_dir: Directory containing downloaded FCC data.
                Defaults to data/fcc/downloads.
        """
        super().__init__(config)
        self._download_dir = download_dir or DEFAULT_DOWNLOAD_DIR
        self._fips_to_county: dict[str, int] = {}
        self._source_id: int | None = None

    def get_dimension_tables(self) -> list[type[Any]]:
        """Return dimension tables this loader populates."""
        return [DimDataSource]

    def get_fact_tables(self) -> list[type[Any]]:
        """Return fact tables this loader populates."""
        return [FactBroadbandCoverage]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load FCC broadband coverage data into 3NF schema.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing FCC data before loading.
            verbose: If True, print progress information.
            as_of_date: FCC data date to load (e.g., "2025-06-30").
                If not provided, uses most recent available.

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="fcc_broadband")

        as_of_date = kwargs.get("as_of_date")
        date_dir: Path | None
        if isinstance(as_of_date, str):
            date_dir = self._download_dir / as_of_date
        else:
            # Find most recent date directory
            date_dir = self._find_latest_date_dir()

        if date_dir is None:
            stats.errors.append(f"No download data found in {self._download_dir}")
            return stats

        if verbose:
            print(f"Loading FCC Broadband Coverage from {date_dir}")

        # Find national CSV (fixed broadband)
        national_dir = date_dir / "national"
        csv_files = list(national_dir.glob("*fixed_broadband_summary_by_geography*.csv"))

        if not csv_files:
            stats.errors.append(f"No national CSV files found in {national_dir}")
            return stats

        csv_path = csv_files[0]
        if verbose:
            print(f"  CSV: {csv_path.name}")

        try:
            if reset:
                if verbose:
                    print("  Clearing existing FCC broadband data...")
                self._clear_fcc_data(session)
                session.flush()

            self._load_county_lookup(session)
            if verbose:
                print(f"  Loaded {len(self._fips_to_county):,} county mappings")

            self._load_data_source(session, as_of_date=date_dir.name)
            stats.dimensions_loaded["dim_data_source"] = 1
            session.flush()

            fact_count, skipped = self._load_coverage_facts(session, csv_path, verbose)
            stats.facts_loaded["fact_broadband_coverage"] = fact_count
            stats.files_processed = 1
            stats.record_ingest("fcc:fact_broadband_coverage", fact_count)

            if skipped > 0 and verbose:
                print(f"  Skipped {skipped} counties not in database")

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.record_api_error(e, context="fcc:load")
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _find_latest_date_dir(self) -> Path | None:
        """Find most recent date directory in downloads."""
        if not self._download_dir.exists():
            return None

        date_dirs = [d for d in self._download_dir.iterdir() if d.is_dir() and d.name[0].isdigit()]

        if not date_dirs:
            return None

        # Sort by name (ISO date format sorts chronologically)
        date_dirs.sort(key=lambda d: d.name, reverse=True)
        return date_dirs[0]

    def _clear_fcc_data(self, session: Session) -> None:
        """Clear FCC broadband coverage data."""
        # Find FCC source(s)
        sources = (
            session.query(DimDataSource).filter(DimDataSource.source_code.like("FCC_BDC_%")).all()
        )
        source_ids = [s.source_id for s in sources]

        if source_ids:
            session.query(FactBroadbandCoverage).filter(
                FactBroadbandCoverage.source_id.in_(source_ids)
            ).delete(synchronize_session=False)

    def _load_county_lookup(self, session: Session) -> None:
        """Build FIPS -> county_id lookup."""
        counties = session.query(DimCounty).all()
        self._fips_to_county = {c.fips: c.county_id for c in counties}

    def _load_data_source(self, session: Session, as_of_date: str) -> None:
        """Load/ensure data source dimension for FCC BDC."""
        source_code = f"FCC_BDC_{as_of_date.replace('-', '')}"

        # Extract year from as_of_date (e.g., "2025-06-30" -> 2025)
        try:
            year = int(as_of_date.split("-")[0])
        except (ValueError, IndexError):
            year = 2024

        self._source_id = self._get_or_create_data_source(
            session,
            source_code=source_code,
            source_name=f"FCC Broadband Data Collection ({as_of_date})",
            source_url="https://broadbandmap.fcc.gov/data-download/nationwide-data",
            source_agency="FCC",
            source_year=year,
        )

    def _load_coverage_facts(
        self,
        session: Session,
        csv_path: Path,
        verbose: bool,
    ) -> tuple[int, int]:
        """Load county broadband coverage facts from CSV.

        Args:
            session: Database session.
            csv_path: Path to national summary CSV.
            verbose: Print progress.

        Returns:
            Tuple of (loaded_count, skipped_count).
        """
        if self._source_id is None:
            msg = "Data source not loaded"
            raise RuntimeError(msg)

        loaded = 0
        skipped = 0

        # Parse CSV with default filters (Total, County, Residential, Any Technology)
        for record in parse_fcc_summary_csv(csv_path):
            county_id = self._fips_to_county.get(record.county_fips)
            if county_id is None:
                skipped += 1
                continue

            # Convert decimal (0.0-1.0) to percentage (0.00-100.00)
            # Numeric(5,2) allows values up to 999.99, so 100.00 fits
            pct_25_3 = self._to_percentage(record.pct_25_3)
            pct_100_20 = self._to_percentage(record.pct_100_20)
            pct_1000_100 = self._to_percentage(record.pct_1000_100)

            fact = FactBroadbandCoverage(
                county_id=county_id,
                source_id=self._source_id,
                pct_25_3=pct_25_3,
                pct_100_20=pct_100_20,
                pct_1000_100=pct_1000_100,
                provider_count=None,  # Not available in summary CSV
            )
            session.add(fact)
            loaded += 1

            # Batch flush for performance
            if loaded % 500 == 0:
                session.flush()
                if verbose:
                    print(f"  Loaded {loaded:,} counties...", end="\r")

        session.flush()

        if verbose:
            print(f"  Loaded {loaded:,} county coverage records")

        return loaded, skipped

    @staticmethod
    def _to_percentage(decimal_value: Decimal) -> Decimal:
        """Convert decimal (0.0-1.0) to percentage (0.00-100.00).

        Args:
            decimal_value: Decimal value between 0 and 1.

        Returns:
            Percentage as Decimal, rounded to 2 decimal places.
        """
        # Multiply by 100 and round to 2 decimal places
        return (decimal_value * 100).quantize(Decimal("0.01"))


__all__ = ["FCCBroadbandLoader"]
