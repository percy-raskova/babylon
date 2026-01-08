"""QCEW data loader for direct 3NF schema population.

Loads BLS Quarterly Census of Employment and Wages data using a hybrid approach:
- API for recent years (2021+): Fetches directly from BLS QCEW Open Data API
- Files for historical years (2013-2020): Reads from local CSV downloads

Supports three geographic levels:
- County (agglvl_code 70-78) → FactQcewAnnual
- State (agglvl_code 20-28) → FactQcewStateAnnual
- Metro/Micro/CSA (agglvl_code 30-58) → FactQcewMetroAnnual

Example:
    from babylon.data.qcew import QcewLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(qcew_years=list(range(2013, 2026)))
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session)  # Hybrid: API for 2021+, files for 2013-2020
        print(f"Loaded {stats.facts_loaded} QCEW observations")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import delete
from tqdm import tqdm

from babylon.data.api_loader_base import ApiLoaderBase
from babylon.data.exceptions import QcewAPIError
from babylon.data.loader_base import LoadStats
from babylon.data.normalize.classifications import classify_class_composition
from babylon.data.normalize.schema import (
    DimCounty,
    DimDataSource,
    DimIndustry,
    DimMetroArea,
    DimOwnership,
    DimState,
    DimTime,
    FactQcewAnnual,
    FactQcewMetroAnnual,
    FactQcewStateAnnual,
)
from babylon.data.qcew.api_client import (
    QcewAPIClient,
    QcewAreaRecord,
    get_state_area_code,
)
from babylon.data.qcew.parser import (
    QcewRecord,
    determine_naics_level,
    extract_state_fips,
    parse_qcew_csv,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# --- Constants: BLS QCEW Aggregation Level Ranges ---
# https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm

# County-level aggregation (agglvl_code 70-78)
AGGLVL_COUNTY_MIN = 70
AGGLVL_COUNTY_MAX = 78

# State-level aggregation (agglvl_code 20-28)
AGGLVL_STATE_MIN = 20
AGGLVL_STATE_MAX = 28

# MSA aggregation (agglvl_code 30-38)
AGGLVL_MSA_MIN = 30
AGGLVL_MSA_MAX = 38

# Micropolitan aggregation (agglvl_code 40-48)
AGGLVL_MICRO_MIN = 40
AGGLVL_MICRO_MAX = 48

# CSA aggregation (agglvl_code 50-58)
AGGLVL_CSA_MIN = 50
AGGLVL_CSA_MAX = 58

# Combined metro area range for routing
AGGLVL_METRO_MIN = 30
AGGLVL_METRO_MAX = 58

# Year cutoff for hybrid loading: API provides rolling 5 years
API_CUTOFF_YEAR = 2021

# Default data path for QCEW CSV files
DEFAULT_QCEW_PATH = Path("data/qcew")

# Batch size for database flushes
BATCH_FLUSH_SIZE = 10000


@dataclass
class GeoCounts:
    """Counters for records by geographic level."""

    county: int = 0
    state: int = 0
    metro: int = 0

    @property
    def total(self) -> int:
        """Total records across all geographic levels."""
        return self.county + self.state + self.metro


class QcewLoader(ApiLoaderBase):
    """Loader for BLS QCEW data into 3NF schema.

    Uses hybrid loading strategy:
    - API for years >= API_CUTOFF_YEAR (2021+)
    - Files for years < API_CUTOFF_YEAR (2013-2020)

    Supports three geographic levels:
    - County (agglvl_code 70-78) → FactQcewAnnual
    - State (agglvl_code 20-28) → FactQcewStateAnnual
    - Metro/Micro/CSA (agglvl_code 30-58) → FactQcewMetroAnnual

    The loader populates:
    - DimIndustry: NAICS industries with class composition
    - DimOwnership: Ownership types (private/government)
    - DimTime: Temporal dimension (shared with other loaders)
    - FactQcewAnnual: County-level employment/wage observations
    - FactQcewStateAnnual: State-level aggregates
    - FactQcewMetroAnnual: MSA/Micropolitan/CSA aggregates
    """

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimDataSource, DimIndustry, DimOwnership, DimTime]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactQcewAnnual, FactQcewStateAnnual, FactQcewMetroAnnual]

    def _make_client(self) -> QcewAPIClient:
        """Create a QCEW API client."""
        return QcewAPIClient()

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load QCEW data into 3NF schema using hybrid approach.

        Args:
            session: SQLAlchemy session for normalized database.
            reset: If True, clear existing QCEW data before loading.
            verbose: If True, log progress messages to console AND logger.
            **kwargs: Additional options including:
                force_api: If True, use API for all years (may fail for old years).
                force_files: If True, use files for all years.
                data_path: Path to QCEW CSV directory for file-based loading.

        Returns:
            LoadStats with counts of loaded records by geographic level.
        """
        force_api = bool(kwargs.get("force_api", False))
        force_files = bool(kwargs.get("force_files", False))
        data_path = kwargs.get("data_path")

        # Partition years into API vs file-based
        api_years, file_years = self._partition_years(force_api, force_files)

        if verbose:
            self._log_year_partition(api_years, file_years)

        stats = LoadStats(source="qcew_hybrid")

        if reset:
            self._clear_qcew_tables(session, verbose)

        # Load data source dimension
        self._load_data_source(session, verbose)

        # Load from API for recent years
        if api_years:
            api_stats = self._load_from_api(session, api_years, verbose)
            self._merge_stats(stats, api_stats)

        # Load from files for historical years
        if file_years:
            file_stats = self._load_from_files(session, file_years, verbose, data_path)
            self._merge_stats(stats, file_stats)

        return stats

    def _partition_years(self, force_api: bool, force_files: bool) -> tuple[list[int], list[int]]:
        """Partition configured years into API vs file-based lists."""
        api_years: list[int] = []
        file_years: list[int] = []

        for year in self.config.qcew_years:
            if force_files:
                file_years.append(year)
            elif force_api or year >= API_CUTOFF_YEAR:
                api_years.append(year)
            else:
                file_years.append(year)

        return api_years, file_years

    def _log_year_partition(self, api_years: list[int], file_years: list[int]) -> None:
        """Log the year partition for visibility."""
        if api_years:
            msg = f"API years: {min(api_years)}-{max(api_years)}"
            logger.info(msg)
            print(msg)
        if file_years:
            msg = f"File years: {min(file_years)}-{max(file_years)}"
            logger.info(msg)
            print(msg)

    def _merge_stats(self, target: LoadStats, source: LoadStats) -> None:
        """Merge source stats into target."""
        for k, v in source.dimensions_loaded.items():
            target.dimensions_loaded[k] = target.dimensions_loaded.get(k, 0) + v
        for k, v in source.facts_loaded.items():
            target.facts_loaded[k] = target.facts_loaded.get(k, 0) + v
        target.api_calls += source.api_calls
        target.files_processed += source.files_processed
        target.errors.extend(source.errors)

    def _load_from_api(
        self,
        session: Session,
        years: list[int],
        verbose: bool,
    ) -> LoadStats:
        """Load QCEW data from BLS API for specified years."""
        stats = LoadStats(source="qcew_api")

        states = session.query(DimState).all()
        if not states:
            msg = "No states in DimState - run CensusLoader first"
            stats.errors.append(msg)
            logger.error(msg)
            print(f"ERROR: {msg}")
            return stats

        # Build lookup caches
        lookups = self._build_all_lookups(session)
        counts = GeoCounts()

        if verbose:
            msg = f"API: Fetching {len(years)} years, {len(states)} states"
            logger.info(msg)
            print(msg)

        with self._client_scope(self._make_client()) as client:
            for year in years:
                if verbose:
                    msg = f"Processing {year} via API..."
                    logger.info(msg)
                    print(msg)

                self._process_api_year(
                    session, client, year, states, lookups, counts, stats, verbose
                )

        session.commit()
        self._finalize_stats(stats, lookups, counts, verbose, "API")
        return stats

    def _process_api_year(
        self,
        session: Session,
        client: QcewAPIClient,
        year: int,
        states: list[DimState],
        lookups: dict[str, dict[str, int]],
        counts: GeoCounts,
        stats: LoadStats,
        verbose: bool,
    ) -> None:
        """Process a single year of API data."""
        state_iter = tqdm(states, desc=f"States {year}", disable=not verbose)

        for state in state_iter:
            area_code = get_state_area_code(state.state_fips)
            stats.api_calls += 1

            try:
                for record in client.get_area_annual_data(year, area_code):
                    self._process_api_record(session, record, year, state, lookups, counts)
                    self._maybe_flush(session, counts, verbose)

            except QcewAPIError as e:
                self._handle_api_error(e, area_code, year, stats)

    def _process_api_record(
        self,
        session: Session,
        record: QcewAreaRecord,
        year: int,
        state: DimState,
        lookups: dict[str, dict[str, int]],
        counts: GeoCounts,
    ) -> None:
        """Process a single API record and route to appropriate fact table."""
        agglvl = record.agglvl_code

        # Resolve shared dimensions
        industry_id = self._get_or_create_industry(
            session,
            record.industry_code,
            f"Industry {record.industry_code}",
            lookups["industry"],
        )
        ownership_id = self._get_or_create_ownership(
            session,
            record.own_code,
            f"Ownership {record.own_code}",
            lookups["ownership"],
        )
        time_id = self._get_or_create_time(session, year)

        # Route to appropriate fact table
        if AGGLVL_COUNTY_MIN <= agglvl <= AGGLVL_COUNTY_MAX:
            self._create_county_fact_api(
                session, record, state, lookups, industry_id, ownership_id, time_id
            )
            counts.county += 1
        elif AGGLVL_STATE_MIN <= agglvl <= AGGLVL_STATE_MAX:
            self._create_state_fact_api(
                session, record, lookups, industry_id, ownership_id, time_id, agglvl
            )
            counts.state += 1
        elif AGGLVL_METRO_MIN <= agglvl <= AGGLVL_METRO_MAX:
            self._create_metro_fact_api(
                session, record, lookups, industry_id, ownership_id, time_id, agglvl
            )
            counts.metro += 1

    def _create_county_fact_api(
        self,
        session: Session,
        record: QcewAreaRecord,
        state: DimState,
        lookups: dict[str, dict[str, int]],
        industry_id: int,
        ownership_id: int,
        time_id: int,
    ) -> None:
        """Create county-level fact from API record."""
        county_id = lookups["county"].get(record.area_fips)
        if county_id is None:
            county_id = self._get_or_create_county(
                session,
                record.area_fips,
                f"County {record.area_fips}",
                lookups["state"].get(state.state_fips, state.state_id),
                lookups["county"],
            )
        fact = FactQcewAnnual(
            county_id=county_id,
            industry_id=industry_id,
            ownership_id=ownership_id,
            time_id=time_id,
            establishments=record.annual_avg_estabs,
            employment=record.annual_avg_emplvl,
            total_wages_usd=record.total_annual_wages,
            avg_weekly_wage_usd=record.annual_avg_wkly_wage,
            avg_annual_pay_usd=record.avg_annual_pay,
            lq_employment=record.lq_annual_avg_emplvl,
            lq_annual_pay=record.lq_avg_annual_pay,
            disclosure_code=record.disclosure_code or None,
        )
        session.add(fact)

    def _create_state_fact_api(
        self,
        session: Session,
        record: QcewAreaRecord,
        lookups: dict[str, dict[str, int]],
        industry_id: int,
        ownership_id: int,
        time_id: int,
        agglvl: int,
    ) -> None:
        """Create state-level fact from API record."""
        state_id = lookups["state"].get(record.area_fips[:2])
        if state_id:
            fact = FactQcewStateAnnual(
                state_id=state_id,
                industry_id=industry_id,
                ownership_id=ownership_id,
                time_id=time_id,
                establishments=record.annual_avg_estabs,
                employment=record.annual_avg_emplvl,
                total_wages_usd=record.total_annual_wages,
                avg_weekly_wage_usd=record.annual_avg_wkly_wage,
                avg_annual_pay_usd=record.avg_annual_pay,
                lq_employment=record.lq_annual_avg_emplvl,
                lq_annual_pay=record.lq_avg_annual_pay,
                disclosure_code=record.disclosure_code or None,
                agglvl_code=agglvl,
            )
            session.add(fact)

    def _create_metro_fact_api(
        self,
        session: Session,
        record: QcewAreaRecord,
        lookups: dict[str, dict[str, int]],
        industry_id: int,
        ownership_id: int,
        time_id: int,
        agglvl: int,
    ) -> None:
        """Create metro-level fact from API record."""
        metro_id = lookups["metro"].get(record.area_fips)
        if metro_id:
            area_type = self._determine_metro_type(agglvl)
            fact = FactQcewMetroAnnual(
                metro_area_id=metro_id,
                industry_id=industry_id,
                ownership_id=ownership_id,
                time_id=time_id,
                establishments=record.annual_avg_estabs,
                employment=record.annual_avg_emplvl,
                total_wages_usd=record.total_annual_wages,
                avg_weekly_wage_usd=record.annual_avg_wkly_wage,
                avg_annual_pay_usd=record.avg_annual_pay,
                lq_employment=record.lq_annual_avg_emplvl,
                lq_annual_pay=record.lq_avg_annual_pay,
                disclosure_code=record.disclosure_code or None,
                agglvl_code=agglvl,
                area_type=area_type,
            )
            session.add(fact)

    def _handle_api_error(
        self,
        error: QcewAPIError,
        area_code: str,
        year: int,
        stats: LoadStats,
    ) -> None:
        """Handle API errors with appropriate logging."""
        if error.status_code == 404:
            logger.debug(f"No data for {area_code} in {year}")
        else:
            msg = f"API error for {area_code}/{year}: {error.message}"
            stats.record_api_error(
                error,
                context=f"qcew:{area_code}:{year}",
                details={
                    "loader": "qcew",
                    "area_code": area_code,
                    "year": year,
                    "endpoint": error.url,
                },
            )
            stats.errors.append(msg)
            logger.warning(msg)
            print(f"WARNING: {msg}")

    def _determine_metro_type(self, agglvl_code: int) -> str:
        """Determine metro area type from aggregation level code."""
        if AGGLVL_MSA_MIN <= agglvl_code <= AGGLVL_MSA_MAX:
            return "msa"
        elif AGGLVL_MICRO_MIN <= agglvl_code <= AGGLVL_MICRO_MAX:
            return "micropolitan"
        elif AGGLVL_CSA_MIN <= agglvl_code <= AGGLVL_CSA_MAX:
            return "csa"
        return "unknown"

    def _build_all_lookups(self, session: Session) -> dict[str, dict[str, int]]:
        """Build all geographic lookup caches."""
        return {
            "state": self._build_state_lookup(session),
            "county": self._build_county_lookup(session),
            "metro": self._build_metro_lookup(session),
            "industry": {},
            "ownership": {},
        }

    def _build_metro_lookup(self, session: Session) -> dict[str, int]:
        """Build metro area FIPS/CBSA to metro_area_id lookup."""
        metros = session.query(DimMetroArea).all()
        lookup: dict[str, int] = {}
        for m in metros:
            if m.cbsa_code:
                lookup[m.cbsa_code] = m.metro_area_id
            if m.geo_id:
                lookup[m.geo_id] = m.metro_area_id
        return lookup

    def _maybe_flush(self, session: Session, counts: GeoCounts, verbose: bool) -> None:
        """Flush session if batch threshold reached."""
        if counts.total % BATCH_FLUSH_SIZE == 0:
            session.flush()
            if verbose:
                print(f"  Loaded {counts.total:,} observations...")

    def _finalize_stats(
        self,
        stats: LoadStats,
        lookups: dict[str, dict[str, int]],
        counts: GeoCounts,
        verbose: bool,
        source_type: str,
    ) -> None:
        """Finalize statistics after loading."""
        stats.dimensions_loaded["industries"] = len(lookups["industry"])
        stats.dimensions_loaded["ownerships"] = len(lookups["ownership"])
        stats.facts_loaded["qcew_county"] = counts.county
        stats.facts_loaded["qcew_state"] = counts.state
        stats.facts_loaded["qcew_metro"] = counts.metro
        stats.record_ingest(f"qcew_{source_type.lower()}:county", counts.county)
        stats.record_ingest(f"qcew_{source_type.lower()}:state", counts.state)
        stats.record_ingest(f"qcew_{source_type.lower()}:metro", counts.metro)

        if verbose:
            msg = (
                f"{source_type} loading complete: {counts.county:,} county, "
                f"{counts.state:,} state, {counts.metro:,} metro records"
            )
            logger.info(msg)
            print(msg)

    def _load_from_files(
        self,
        session: Session,
        years: list[int],
        verbose: bool,
        data_path: object,
    ) -> LoadStats:
        """Load QCEW data from local CSV files for historical years."""
        stats = LoadStats(source="qcew_files")
        csv_dir = Path(data_path) if isinstance(data_path, (str, Path)) else DEFAULT_QCEW_PATH

        if not csv_dir.exists():
            msg = f"QCEW data directory not found: {csv_dir}"
            stats.errors.append(msg)
            logger.error(msg)
            print(f"ERROR: {msg}")
            return stats

        csv_files = list(csv_dir.glob("*.csv"))
        stats.files_processed = len(csv_files)

        if not csv_files:
            msg = f"No CSV files found in {csv_dir}"
            stats.errors.append(msg)
            logger.error(msg)
            print(f"ERROR: {msg}")
            return stats

        if verbose:
            msg = f"Files: Processing {len(csv_files)} CSV files for years {years}"
            logger.info(msg)
            print(msg)

        lookups = self._build_all_lookups(session)
        counts = GeoCounts()
        years_to_load = set(years)

        file_iter = tqdm(csv_files, desc="CSV files", disable=not verbose)
        for csv_file in file_iter:
            self._process_csv_file(session, csv_file, years_to_load, lookups, counts, verbose)

        session.commit()
        self._finalize_stats(stats, lookups, counts, verbose, "File")
        return stats

    def _process_csv_file(
        self,
        session: Session,
        csv_file: Path,
        years_to_load: set[int],
        lookups: dict[str, dict[str, int]],
        counts: GeoCounts,
        verbose: bool,
    ) -> None:
        """Process a single CSV file."""
        logger.debug(f"Processing {csv_file.name}...")

        for record in parse_qcew_csv(csv_file):
            if record.year not in years_to_load:
                continue
            self._process_file_record(session, record, lookups, counts)
            self._maybe_flush(session, counts, verbose)

    def _process_file_record(
        self,
        session: Session,
        record: QcewRecord,
        lookups: dict[str, dict[str, int]],
        counts: GeoCounts,
    ) -> None:
        """Process a single file record and route to appropriate fact table."""
        agglvl = getattr(record, "agglvl_code", AGGLVL_COUNTY_MAX)

        # Resolve shared dimensions
        industry_id = self._get_or_create_industry(
            session,
            record.industry_code,
            record.industry_title,
            lookups["industry"],
        )
        ownership_id = self._get_or_create_ownership(
            session,
            record.own_code,
            record.own_title,
            lookups["ownership"],
        )
        time_id = self._get_or_create_time(session, record.year)

        # Route to appropriate fact table
        if AGGLVL_COUNTY_MIN <= agglvl <= AGGLVL_COUNTY_MAX:
            if self._create_county_fact_file(
                session, record, lookups, industry_id, ownership_id, time_id
            ):
                counts.county += 1
        elif AGGLVL_STATE_MIN <= agglvl <= AGGLVL_STATE_MAX:
            self._create_state_fact_file(
                session, record, lookups, industry_id, ownership_id, time_id, agglvl
            )
            counts.state += 1
        elif AGGLVL_METRO_MIN <= agglvl <= AGGLVL_METRO_MAX:
            self._create_metro_fact_file(
                session, record, lookups, industry_id, ownership_id, time_id, agglvl
            )
            counts.metro += 1

    def _create_county_fact_file(
        self,
        session: Session,
        record: QcewRecord,
        lookups: dict[str, dict[str, int]],
        industry_id: int,
        ownership_id: int,
        time_id: int,
    ) -> bool:
        """Create county-level fact from file record. Returns True if created."""
        county_id = lookups["county"].get(record.area_fips)
        if county_id is None:
            state_fips = extract_state_fips(record.area_fips)
            if state_fips and state_fips in lookups["state"]:
                county_id = self._get_or_create_county(
                    session,
                    record.area_fips,
                    record.area_title,
                    lookups["state"][state_fips],
                    lookups["county"],
                )
            else:
                return False

        fact = FactQcewAnnual(
            county_id=county_id,
            industry_id=industry_id,
            ownership_id=ownership_id,
            time_id=time_id,
            establishments=record.establishments,
            employment=record.employment,
            total_wages_usd=record.total_wages,
            avg_weekly_wage_usd=record.avg_weekly_wage,
            avg_annual_pay_usd=record.avg_annual_pay,
            lq_employment=record.lq_employment,
            lq_annual_pay=record.lq_avg_annual_pay,
            disclosure_code=record.disclosure_code or None,
        )
        session.add(fact)
        return True

    def _create_state_fact_file(
        self,
        session: Session,
        record: QcewRecord,
        lookups: dict[str, dict[str, int]],
        industry_id: int,
        ownership_id: int,
        time_id: int,
        agglvl: int,
    ) -> None:
        """Create state-level fact from file record."""
        state_fips = record.area_fips[:2]
        state_id = lookups["state"].get(state_fips)
        if state_id:
            fact = FactQcewStateAnnual(
                state_id=state_id,
                industry_id=industry_id,
                ownership_id=ownership_id,
                time_id=time_id,
                establishments=record.establishments,
                employment=record.employment,
                total_wages_usd=record.total_wages,
                avg_weekly_wage_usd=record.avg_weekly_wage,
                avg_annual_pay_usd=record.avg_annual_pay,
                lq_employment=record.lq_employment,
                lq_annual_pay=record.lq_avg_annual_pay,
                disclosure_code=record.disclosure_code or None,
                agglvl_code=agglvl,
            )
            session.add(fact)

    def _create_metro_fact_file(
        self,
        session: Session,
        record: QcewRecord,
        lookups: dict[str, dict[str, int]],
        industry_id: int,
        ownership_id: int,
        time_id: int,
        agglvl: int,
    ) -> None:
        """Create metro-level fact from file record."""
        metro_id = lookups["metro"].get(record.area_fips)
        if metro_id:
            area_type = self._determine_metro_type(agglvl)
            fact = FactQcewMetroAnnual(
                metro_area_id=metro_id,
                industry_id=industry_id,
                ownership_id=ownership_id,
                time_id=time_id,
                establishments=record.establishments,
                employment=record.employment,
                total_wages_usd=record.total_wages,
                avg_weekly_wage_usd=record.avg_weekly_wage,
                avg_annual_pay_usd=record.avg_annual_pay,
                lq_employment=record.lq_employment,
                lq_annual_pay=record.lq_avg_annual_pay,
                disclosure_code=record.disclosure_code or None,
                agglvl_code=agglvl,
                area_type=area_type,
            )
            session.add(fact)

    # -- Helper methods (preserved from original loader) --

    def _clear_qcew_tables(self, session: Session, verbose: bool) -> None:
        """Clear QCEW-specific tables (not shared dimensions)."""
        if verbose:
            logger.info("Clearing existing QCEW data...")

        session.execute(delete(FactQcewAnnual))
        session.execute(delete(FactQcewStateAnnual))
        session.execute(delete(FactQcewMetroAnnual))
        session.flush()

    def _load_data_source(self, session: Session, verbose: bool) -> int:
        """Load or get QCEW data source dimension."""
        source_id = self._get_or_create_data_source(
            session,
            source_code="QCEW",
            source_name="BLS Quarterly Census of Employment and Wages",
            source_url="https://www.bls.gov/qcew/",
            description=(
                "Comprehensive establishment-level data on employment and wages "
                "by industry and county. Essential for labor aristocracy analysis "
                "and geographic class composition mapping."
            ),
        )
        if verbose:
            logger.info("  Loaded QCEW data source")
        return source_id

    def _build_state_lookup(self, session: Session) -> dict[str, int]:
        """Build state FIPS to state_id lookup."""
        states = session.query(DimState).all()
        return {s.state_fips: s.state_id for s in states}

    def _build_county_lookup(self, session: Session) -> dict[str, int]:
        """Build county FIPS to county_id lookup."""
        counties = session.query(DimCounty).all()
        return {c.fips: c.county_id for c in counties}

    def _get_or_create_county(
        self,
        session: Session,
        fips: str,
        area_title: str,
        state_id: int,
        county_lookup: dict[str, int],
    ) -> int:
        """Get or create county dimension."""
        if fips in county_lookup:
            return county_lookup[fips]

        county_fips = fips[2:5] if len(fips) >= 5 else fips

        county = DimCounty(
            fips=fips,
            state_id=state_id,
            county_fips=county_fips,
            county_name=area_title,
        )
        session.add(county)
        session.flush()
        county_lookup[fips] = county.county_id
        return county.county_id

    def _get_or_create_industry(
        self,
        session: Session,
        naics_code: str,
        industry_title: str,
        industry_lookup: dict[str, int],
    ) -> int:
        """Get or create industry dimension."""
        if naics_code in industry_lookup:
            return industry_lookup[naics_code]

        existing = session.query(DimIndustry).filter(DimIndustry.naics_code == naics_code).first()
        if existing:
            if not existing.has_qcew_data:
                existing.has_qcew_data = True
            industry_lookup[naics_code] = existing.industry_id
            return existing.industry_id

        naics_level = determine_naics_level(naics_code)
        sector_code = naics_code[:2] if len(naics_code) >= 2 else None
        parent_code = naics_code[:-1] if len(naics_code) > 2 else None
        class_comp = classify_class_composition(naics_code, industry_title)

        industry = DimIndustry(
            naics_code=naics_code,
            industry_title=industry_title,
            naics_level=naics_level,
            parent_naics_code=parent_code,
            sector_code=sector_code,
            class_composition=class_comp,
            has_qcew_data=True,
            has_productivity_data=False,
            has_fred_data=False,
        )
        session.add(industry)
        session.flush()
        industry_lookup[naics_code] = industry.industry_id
        return industry.industry_id

    def _get_or_create_ownership(
        self,
        session: Session,
        own_code: str,
        own_title: str,
        ownership_lookup: dict[str, int],
    ) -> int:
        """Get or create ownership dimension."""
        if own_code in ownership_lookup:
            return ownership_lookup[own_code]

        existing = session.query(DimOwnership).filter(DimOwnership.own_code == own_code).first()
        if existing:
            ownership_lookup[own_code] = existing.ownership_id
            return existing.ownership_id

        is_government = own_code in ("1", "2", "3", "4")
        is_private = own_code == "5"

        ownership = DimOwnership(
            own_code=own_code,
            own_title=own_title,
            is_government=is_government,
            is_private=is_private,
        )
        session.add(ownership)
        session.flush()
        ownership_lookup[own_code] = ownership.ownership_id
        return ownership.ownership_id
