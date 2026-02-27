"""LODES Origin-Destination commuter flow loader for 3NF schema population.

Loads LEHD LODES OD (Origin-Destination) data aggregated to county-to-county flows.
This enables commuter-adjusted throughput analysis for Feature 014.

Data Source:
    https://lehd.ces.census.gov/data/lodes/LODES8/
    Files: {state}_od_main_JT00_{year}.csv.gz

LODES OD Fields Used:
    - w_geocode: Work block GEOID (15 digits)
    - h_geocode: Home block GEOID (15 digits)
    - S000: Total jobs
    - SA01: Jobs for workers age 29 or younger
    - SA02: Jobs for workers age 30 to 54
    - SA03: Jobs for workers age 55 or older
    - SE01: Jobs with earnings $1250/month or less
    - SE02: Jobs with earnings $1251/month to $3333/month
    - SE03: Jobs with earnings greater than $3333/month

Processing Strategy:
    1. Load block crosswalk (BridgeLodesBlock) into memory lookup
    2. Stream OD file, mapping blocks to counties
    3. Aggregate in memory (county_pair → job counts) per state file
    4. Batch write aggregated rows to FactLodesCommuterFlow
    5. Checkpoint per state-year for resume capability
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl
from sqlalchemy import delete

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.reference.schema import (
    DimCounty,
    DimTime,
    FactLodesCommuterFlow,
)
from babylon.data.utils import BatchWriter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from babylon.data.preflight import PreflightCheck

logger = logging.getLogger(__name__)

DEFAULT_LODES_OD_PATH = Path("data/lodes/od")

# US state FIPS codes (50 states + DC)
US_STATE_FIPS = [
    "01",
    "02",
    "04",
    "05",
    "06",
    "08",
    "09",
    "10",
    "11",
    "12",
    "13",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "38",
    "39",
    "40",
    "41",
    "42",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "50",
    "51",
    "53",
    "54",
    "55",
    "56",
]

# State FIPS to abbreviation mapping
STATE_FIPS_TO_ABBREV = {
    "01": "al",
    "02": "ak",
    "04": "az",
    "05": "ar",
    "06": "ca",
    "08": "co",
    "09": "ct",
    "10": "de",
    "11": "dc",
    "12": "fl",
    "13": "ga",
    "15": "hi",
    "16": "id",
    "17": "il",
    "18": "in",
    "19": "ia",
    "20": "ks",
    "21": "ky",
    "22": "la",
    "23": "me",
    "24": "md",
    "25": "ma",
    "26": "mi",
    "27": "mn",
    "28": "ms",
    "29": "mo",
    "30": "mt",
    "31": "ne",
    "32": "nv",
    "33": "nh",
    "34": "nj",
    "35": "nm",
    "36": "ny",
    "37": "nc",
    "38": "nd",
    "39": "oh",
    "40": "ok",
    "41": "or",
    "42": "pa",
    "44": "ri",
    "45": "sc",
    "46": "sd",
    "47": "tn",
    "48": "tx",
    "49": "ut",
    "50": "vt",
    "51": "va",
    "53": "wa",
    "54": "wv",
    "55": "wi",
    "56": "wy",
}


def _get_od_filename(state_abbrev: str, year: int) -> str:
    """Get the expected OD filename for a state and year."""
    return f"{state_abbrev}_od_main_JT00_{year}.csv.gz"


def _find_od_file(data_dir: Path, state_fips: str, year: int) -> Path | None:
    """Find OD file for a state and year.

    Searches in data_dir and data_dir/{state_abbrev}/.
    """
    state_abbrev = STATE_FIPS_TO_ABBREV.get(state_fips)
    if not state_abbrev:
        return None

    filename = _get_od_filename(state_abbrev, year)

    # Check data_dir directly
    direct_path = data_dir / filename
    if direct_path.exists():
        return direct_path

    # Check state subdirectory
    state_path = data_dir / state_abbrev / filename
    if state_path.exists():
        return state_path

    return None


class LODESODLoader(DataLoader):
    """Loader for LODES Origin-Destination commuter flow data.

    Aggregates block-level OD flows to county-to-county flows.
    """

    def get_dimension_tables(self) -> list[type]:
        """No dimensions loaded - uses existing DimCounty and DimTime."""
        return []

    def get_fact_tables(self) -> list[type]:
        return [FactLodesCommuterFlow]

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,  # noqa: ARG002
    ) -> list[PreflightCheck]:
        """Check if LODES OD files exist.

        Args:
            data_dir: Base data directory (e.g., Path("data/")).
            online: If True, validate network endpoints (unused for LODES).

        Returns:
            List of PreflightCheck results.
        """
        from babylon.data.preflight import PreflightCheck

        checks: list[PreflightCheck] = []
        od_dir = data_dir / "lodes" / "od"

        if not od_dir.exists():
            checks.append(
                PreflightCheck(
                    check_id="lodes:od_dir",
                    status="fail",
                    message=f"Missing LODES OD directory: {od_dir}",
                    hint="Download OD files from https://lehd.ces.census.gov/data/lodes/LODES8/",
                )
            )
        else:
            # Check for at least one OD file
            od_files = list(od_dir.glob("*_od_main_JT00_*.csv.gz"))
            if not od_files:
                # Also check state subdirectories
                od_files = list(od_dir.glob("*/*_od_main_JT00_*.csv.gz"))

            if not od_files:
                checks.append(
                    PreflightCheck(
                        check_id="lodes:od_files",
                        status="warn",
                        message=f"No LODES OD files found in {od_dir}",
                        hint="Download from https://lehd.ces.census.gov/data/lodes/LODES8/",
                    )
                )
            else:
                checks.append(
                    PreflightCheck(
                        check_id="lodes:od_files",
                        status="ok",
                        message=f"Found {len(od_files)} LODES OD file(s)",
                    )
                )

        return checks

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load LODES OD data aggregated to county-to-county flows.

        Args:
            session: SQLAlchemy session
            reset: If True, clear existing data before loading
            verbose: If True, log progress
            **kwargs:
                data_dir: Path to LODES OD data directory
                years: List of years to load (default: [2020, 2021, 2022])
                states: List of state FIPS codes (default: all 51)

        Returns:
            LoadStats with row counts and any errors
        """
        stats = LoadStats(source="lodes_od")

        # Get parameters
        data_dir_param = kwargs.get("data_dir", DEFAULT_LODES_OD_PATH)
        data_dir = Path(str(data_dir_param))
        years = kwargs.get("years", [2020, 2021, 2022])
        if not isinstance(years, list):
            years = [2020, 2021, 2022]

        states = kwargs.get("states", self.config.state_fips_list or US_STATE_FIPS)
        if not isinstance(states, list):
            states = US_STATE_FIPS

        if reset:
            self._clear_existing_data(session, verbose)
            self._clear_checkpoints(session, "lodes_od")
            session.flush()

        # Build lookups
        lookups = self._initialize_lookups(session)

        result = self._load_all_files(session, data_dir, years, states, lookups, verbose)

        session.commit()

        stats.files_processed = result["files_processed"]
        stats.facts_loaded["lodes_commuter_flow"] = result["total_loaded"]
        stats.record_ingest("lodes_od:flows", result["total_loaded"])

        return stats

    def _count_available_files(
        self,
        data_dir: Path,
        years: list[Any],
        states: list[Any],
        lookups: dict[str, Any],
    ) -> int:
        """Count OD files available for processing."""
        total = 0
        for year in years:
            if lookups["time"].get(year) is None:
                continue
            for state_fips in states:
                if _find_od_file(data_dir, state_fips, year) is not None:
                    total += 1
        return total

    def _load_all_files(
        self,
        session: Session,
        data_dir: Path,
        years: list[Any],
        states: list[Any],
        lookups: dict[str, Any],
        verbose: bool,
    ) -> dict[str, int]:
        """Process all OD files with progress tracking.

        Returns:
            Dict with total_loaded, files_processed, files_skipped counts.
        """
        total_files = self._count_available_files(data_dir, years, states, lookups)
        total_loaded = 0
        files_processed = 0
        files_skipped = 0
        file_counter = 0
        t_start = time.monotonic()

        if verbose:
            print(f"\nLODES OD Import: {total_files} files to process")
            print(f"{'=' * 60}")

        for year in years:
            time_id = lookups["time"].get(year)
            if time_id is None:
                if verbose:
                    logger.warning("Year %d not found in DimTime, skipping", year)
                continue

            for state_fips in states:
                od_path = _find_od_file(data_dir, state_fips, year)
                if od_path is None:
                    continue

                file_counter += 1
                result = self._load_single_file(
                    session,
                    od_path,
                    time_id,
                    state_fips,
                    year,
                    lookups,
                    verbose,
                    file_counter,
                    total_files,
                    t_start,
                )

                if result == -1:
                    files_skipped += 1
                elif result > 0:
                    total_loaded += result
                    files_processed += 1

        elapsed_total = time.monotonic() - t_start
        if verbose:
            print(f"{'=' * 60}")
            print(
                f"LODES OD complete: {total_loaded} county-pair flows "
                f"from {files_processed} files in {elapsed_total:.1f}s"
            )
            if files_skipped > 0:
                print(f"  ({files_skipped} files skipped via checkpoint)")

        return {
            "total_loaded": total_loaded,
            "files_processed": files_processed,
            "files_skipped": files_skipped,
        }

    def _load_single_file(
        self,
        session: Session,
        od_path: Path,
        time_id: int,
        state_fips: str,
        year: int,
        lookups: dict[str, Any],
        verbose: bool,
        file_counter: int,
        total_files: int,
        t_start: float,
    ) -> int:
        """Load a single OD file with checkpoint check and progress printing.

        Returns:
            Number of county-pairs loaded, or -1 if skipped via checkpoint.
        """
        file_hash = self._get_file_hash(od_path)
        if self._is_completed(session, "lodes_od", year, file_hash, state_fips, "T"):
            if verbose:
                print(f"  [{file_counter}/{total_files}] {state_fips} {year}: skipped (checkpoint)")
            return -1

        t_file = time.monotonic()
        state_abbrev = STATE_FIPS_TO_ABBREV.get(state_fips, state_fips)

        loaded = self._process_od_file(session, od_path, time_id, lookups, verbose)

        if loaded > 0:
            self._mark_completed(session, "lodes_od", year, file_hash, state_fips, "T", loaded)

        elapsed_file = time.monotonic() - t_file
        elapsed_total = time.monotonic() - t_start
        remaining_files = total_files - file_counter
        avg_per_file = elapsed_total / file_counter
        eta = avg_per_file * remaining_files

        if verbose:
            print(
                f"  [{file_counter}/{total_files}] "
                f"{state_abbrev.upper()} {year}: "
                f"{loaded} county-pairs "
                f"({elapsed_file:.1f}s, "
                f"~{eta:.0f}s remaining)"
            )

        return loaded

    def _clear_existing_data(self, session: Session, verbose: bool) -> None:
        """Clear existing LODES commuter flow data."""
        if verbose:
            logger.info("Clearing existing LODES commuter flow data...")
        session.execute(delete(FactLodesCommuterFlow))
        session.flush()

    def _initialize_lookups(self, session: Session) -> dict[str, Any]:
        """Initialize lookup dictionaries from dimension tables."""
        # County FIPS -> county_id
        county_lookup = {c.fips: c.county_id for c in session.query(DimCounty).all()}

        # Year -> time_id (annual only)
        time_lookup = {
            t.year: t.time_id
            for t in session.query(DimTime).filter(DimTime.is_annual.is_(True)).all()
        }

        # Block crosswalk lookup: block_geoid -> county_id
        # This is used when block-level precision is needed
        # For performance, we use direct FIPS extraction from block GEOID
        # (first 5 digits = county FIPS) rather than loading full crosswalk

        return {
            "county": county_lookup,
            "time": time_lookup,
        }

    def _process_od_file(
        self,
        session: Session,
        od_path: Path,
        time_id: int,
        lookups: dict[str, Any],
        verbose: bool,
    ) -> int:
        """Process a single OD file and aggregate to county-pair flows.

        Uses Polars for vectorized CSV parsing and aggregation:
            1. Read gzipped CSV with Polars (Rust-native gzip decompression)
            2. Extract county FIPS via vectorized str.slice(0, 5)
            3. Group by county pair and sum job counts (Rust groupby)
            4. Iterate aggregated rows (~500-5000) and batch write

        Memory: ~200-500 MB per file (columnar in-memory), bounded per file.
        """
        county_lookup = lookups["county"]
        job_columns = ["S000", "SA01", "SA02", "SA03", "SE01", "SE02", "SE03"]

        # Read only needed columns from gzipped CSV via Polars (Rust engine)
        df = pl.read_csv(
            od_path,
            columns=["w_geocode", "h_geocode", *job_columns],
            schema_overrides={"w_geocode": pl.Utf8, "h_geocode": pl.Utf8},
            null_values=[""],
        )

        # Vectorized FIPS extraction: first 5 chars of 15-digit block GEOID
        df = df.with_columns(
            pl.col("h_geocode").str.slice(0, 5).alias("home_fips"),
            pl.col("w_geocode").str.slice(0, 5).alias("work_fips"),
        )

        # Aggregate to county-pair level (Rust groupby + sum)
        agg_df = df.group_by(["home_fips", "work_fips"]).agg([pl.col(c).sum() for c in job_columns])

        # Filter out zero-flow pairs
        agg_df = agg_df.filter(pl.col("S000") > 0)

        # Map FIPS to county IDs and batch write
        writer = BatchWriter(session, self.config.batch_size)
        batch: list[dict[str, Any]] = []
        pairs_written = 0

        for row in agg_df.iter_rows(named=True):
            home_county_id = county_lookup.get(row["home_fips"])
            work_county_id = county_lookup.get(row["work_fips"])

            if home_county_id is None or work_county_id is None:
                continue

            batch.append(
                {
                    "home_county_id": home_county_id,
                    "work_county_id": work_county_id,
                    "time_id": time_id,
                    "total_jobs": row["S000"],
                    "jobs_age_29_under": row["SA01"] or None,
                    "jobs_age_30_54": row["SA02"] or None,
                    "jobs_age_55_plus": row["SA03"] or None,
                    "jobs_earn_low": row["SE01"] or None,
                    "jobs_earn_mid": row["SE02"] or None,
                    "jobs_earn_high": row["SE03"] or None,
                }
            )
            pairs_written += 1

            if len(batch) >= self.config.batch_size:
                writer.write(FactLodesCommuterFlow, batch)
                batch.clear()

        if batch:
            writer.write(FactLodesCommuterFlow, batch)

        if verbose:
            logger.debug(
                "Aggregated %d input rows to %d county pairs (%d written)",
                len(df),
                len(agg_df),
                pairs_written,
            )

        return pairs_written

    def _get_file_hash(self, path: Path) -> str:
        """Create a short hash of file path for checkpoint key."""
        return hashlib.md5(str(path).encode()).hexdigest()[:16]
