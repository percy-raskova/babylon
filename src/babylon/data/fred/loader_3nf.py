"""FRED data loader for direct 3NF schema population.

Loads FRED (Federal Reserve Economic Data) directly from the FRED API into the
normalized 3NF schema (marxist-data-3NF.sqlite), bypassing intermediate research.sqlite.

This loader:
- Uses LoaderConfig for parameterized temporal (fred_start_year, fred_end_year) settings
- Uses existing FredAPIClient for API calls
- Applies Babylon class mappings inline during load
- Uses DELETE+INSERT pattern for idempotency
- Writes to 5 fact tables and supporting dimensions

Usage:
    from babylon.data.fred.loader_3nf import FredLoader
    from babylon.data import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session_factory

    config = LoaderConfig(fred_start_year=1990, fred_end_year=2024)
    loader = FredLoader(config)

    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
        print(stats)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from tqdm import tqdm

from babylon.data.api_loader_base import ApiLoaderBase
from babylon.data.exceptions import FredAPIError
from babylon.data.fred.api_client import (
    DFA_ASSET_CATEGORIES,
    DFA_WEALTH_CLASSES,
    DFA_WEALTH_LEVEL_SERIES,
    DFA_WEALTH_SHARE_SERIES,
    INDUSTRY_UNEMPLOYMENT_SERIES,
    NATIONAL_SERIES,
    FredAPIClient,
)
from babylon.data.loader_base import LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimAssetCategory,
    DimDataSource,
    DimFredSeries,
    DimIndustry,
    DimState,
    DimTime,
    DimWealthClass,
    FactFredIndustryUnemployment,
    FactFredNational,
    FactFredStateUnemployment,
    FactFredWealthLevels,
    FactFredWealthShares,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Productivity series to add to national data (available via FRED)
# Note: PRS85006033 and PRS85006103 do not exist in FRED; replaced with valid alternatives
PRODUCTIVITY_SERIES = {
    "OPHNFB": "Nonfarm Business Sector: Real Output Per Hour of All Persons",
    "HOANBS": "Nonfarm Business Sector: Hours Worked for All Workers",
}

# All national series including productivity
ALL_NATIONAL_SERIES = {**NATIONAL_SERIES, **PRODUCTIVITY_SERIES}

# Default state FIPS codes (50 states + DC)
DEFAULT_STATE_FIPS = [
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


class FredLoader(ApiLoaderBase):
    """Loader for FRED data into 3NF schema.

    Fetches macroeconomic time series from FRED API and loads directly
    into the normalized 3NF schema with Babylon class mappings applied inline.

    Attributes:
        config: LoaderConfig controlling year range and operations.

    Example:
        config = LoaderConfig(fred_start_year=2000, fred_end_year=2024)
        loader = FredLoader(config)
        stats = loader.load(session, reset=True)
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize FRED loader with configuration."""
        super().__init__(config)
        self._client: FredAPIClient | None = None
        self._series_to_id: dict[str, int] = {}
        self._class_to_id: dict[str, int] = {}
        self._category_to_id: dict[str, int] = {}
        self._state_fips_to_id: dict[str, int] = {}
        self._industry_naics_to_id: dict[str, int] = {}
        # Note: _time_cache is initialized by base class DataLoader.__init__()
        self._source_id: int | None = None

    def _make_client(self) -> FredAPIClient:
        """Create a FRED API client."""
        return FredAPIClient()

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [
            DimDataSource,
            DimFredSeries,
            DimWealthClass,
            DimAssetCategory,
            DimTime,
            # Note: DimState and DimIndustry are shared dimensions
            # that may be loaded by other loaders (Census, QCEW)
        ]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [
            FactFredNational,
            FactFredWealthLevels,
            FactFredWealthShares,
            FactFredIndustryUnemployment,
            FactFredStateUnemployment,
        ]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load FRED data into 3NF schema.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing FRED data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        stats = LoadStats(source="fred")
        start_year = self.config.fred_start_year
        end_year = self.config.fred_end_year
        state_fips_list = self.config.state_fips_list or DEFAULT_STATE_FIPS

        if verbose:
            print(f"Loading FRED data for {start_year}-{end_year}")
            print(f"States: {len(state_fips_list)}")

        try:
            with self._client_scope(self._make_client()):
                # Clear existing FRED data if reset
                if reset:
                    if verbose:
                        print("Clearing existing FRED data...")
                    self._clear_fred_tables(session)
                    session.flush()

                # Load dimensions
                self._load_data_source(session, start_year, end_year)
                stats.dimensions_loaded["dim_data_source"] = 1

                series_count = self._load_series_dimension(session, verbose)
                stats.dimensions_loaded["dim_fred_series"] = series_count

                class_count = self._load_wealth_class_dimension(session, verbose)
                stats.dimensions_loaded["dim_wealth_class"] = class_count

                category_count = self._load_asset_category_dimension(session, verbose)
                stats.dimensions_loaded["dim_asset_category"] = category_count

                # Build state and industry lookups (may already exist from other loaders)
                self._build_state_lookup(session, state_fips_list)
                self._build_industry_lookup(session)

                session.flush()

                # Load fact tables
                national_count = self._load_fact_national(session, start_year, end_year, verbose)
                stats.facts_loaded["fact_fred_national"] = national_count
                stats.record_ingest(
                    f"fred:{start_year}-{end_year}:fact_fred_national",
                    national_count,
                )
                stats.api_calls += len(ALL_NATIONAL_SERIES)

                state_count = self._load_fact_state_unemployment(
                    session, state_fips_list, start_year, end_year, verbose
                )
                stats.facts_loaded["fact_fred_state_unemployment"] = state_count
                stats.record_ingest(
                    f"fred:{start_year}-{end_year}:fact_fred_state_unemployment",
                    state_count,
                )
                stats.api_calls += len(state_fips_list)

                industry_count = self._load_fact_industry_unemployment(
                    session, start_year, end_year, verbose
                )
                stats.facts_loaded["fact_fred_industry_unemployment"] = industry_count
                stats.record_ingest(
                    f"fred:{start_year}-{end_year}:fact_fred_industry_unemployment",
                    industry_count,
                )
                stats.api_calls += len(INDUSTRY_UNEMPLOYMENT_SERIES)

                wealth_level_count = self._load_fact_wealth_levels(
                    session, start_year, end_year, verbose
                )
                stats.facts_loaded["fact_fred_wealth_levels"] = wealth_level_count
                stats.record_ingest(
                    f"fred:{start_year}-{end_year}:fact_fred_wealth_levels",
                    wealth_level_count,
                )
                stats.api_calls += len(DFA_WEALTH_LEVEL_SERIES)

                wealth_share_count = self._load_fact_wealth_shares(
                    session, start_year, end_year, verbose
                )
                stats.facts_loaded["fact_fred_wealth_shares"] = wealth_share_count
                stats.record_ingest(
                    f"fred:{start_year}-{end_year}:fact_fred_wealth_shares",
                    wealth_share_count,
                )
                stats.api_calls += len(DFA_WEALTH_SHARE_SERIES)

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.record_api_error(e, context="fred:load")
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _clear_fred_tables(self, session: Session) -> None:
        """Clear FRED-specific tables (not shared dimensions)."""
        # Clear fact tables first
        session.query(FactFredNational).delete()
        session.query(FactFredWealthLevels).delete()
        session.query(FactFredWealthShares).delete()
        session.query(FactFredIndustryUnemployment).delete()
        session.query(FactFredStateUnemployment).delete()

        # Clear FRED-specific dimensions
        session.query(DimFredSeries).delete()
        session.query(DimWealthClass).delete()
        session.query(DimAssetCategory).delete()

        # Note: Do NOT clear DimState, DimIndustry, DimTime - shared dimensions

    # =========================================================================
    # DIMENSION LOADERS
    # =========================================================================

    def _load_data_source(self, session: Session, start_year: int, end_year: int) -> None:
        """Load data source dimension."""
        source_code = f"FRED_API_{start_year}_{end_year}"
        self._source_id = self._get_or_create_data_source(
            session,
            source_code=source_code,
            source_name=f"Federal Reserve Economic Data (FRED) {start_year}-{end_year}",
            source_year=end_year,
            source_agency="Federal Reserve Bank of St. Louis",
            coverage_start_year=start_year,
            coverage_end_year=end_year,
        )

    def _load_series_dimension(self, session: Session, verbose: bool) -> int:
        """Load FRED series dimension from API metadata."""
        assert self._client is not None

        count = 0
        all_series = list(ALL_NATIONAL_SERIES.keys())

        # Add DFA series
        for series_id in DFA_WEALTH_LEVEL_SERIES.values():
            if series_id not in all_series:
                all_series.append(series_id)
        for series_id in DFA_WEALTH_SHARE_SERIES.values():
            if series_id not in all_series:
                all_series.append(series_id)

        series_iter = tqdm(all_series, desc="Series", disable=not verbose)

        for series_code in series_iter:
            try:
                metadata = self._client.get_series_info(series_code)
                series = DimFredSeries(
                    series_code=series_code,
                    title=metadata.title,
                    units=metadata.units,
                    frequency=metadata.frequency,
                    seasonal_adjustment=metadata.seasonal_adjustment,
                    source=metadata.source,
                )
                session.add(series)
                session.flush()
                self._series_to_id[series_code] = series.series_id
                count += 1

            except FredAPIError as e:
                logger.warning(f"Failed to fetch series info for {series_code}: {e}")
                continue

        return count

    def _load_wealth_class_dimension(self, session: Session, _verbose: bool) -> int:
        """Load wealth class dimension with Babylon mappings."""
        count = 0

        for code, metadata in DFA_WEALTH_CLASSES.items():
            wealth_class = DimWealthClass(
                percentile_code=code,
                percentile_label=str(metadata["label"]),
                babylon_class=str(metadata["babylon_class"]),
            )
            session.add(wealth_class)
            session.flush()
            self._class_to_id[code] = wealth_class.wealth_class_id
            count += 1

        return count

    def _load_asset_category_dimension(self, session: Session, _verbose: bool) -> int:
        """Load asset category dimension with Marxian interpretations."""
        count = 0

        for code, metadata in DFA_ASSET_CATEGORIES.items():
            category = DimAssetCategory(
                category_code=code,
                category_label=metadata["label"],
                marxian_interpretation=metadata["interpretation"],
            )
            session.add(category)
            session.flush()
            self._category_to_id[code] = category.category_id
            count += 1

        return count

    def _build_state_lookup(self, session: Session, state_fips_list: list[str]) -> None:
        """Build state FIPS to ID lookup from existing DimState records."""
        states = session.query(DimState).filter(DimState.state_fips.in_(state_fips_list)).all()

        for state in states:
            self._state_fips_to_id[state.state_fips] = state.state_id

        # Log warning if states are missing
        missing = set(state_fips_list) - set(self._state_fips_to_id.keys())
        if missing:
            logger.warning(f"Missing states in dim_state (run CensusLoader first?): {missing}")

    def _build_industry_lookup(self, session: Session) -> None:
        """Build industry NAICS to ID lookup from existing DimIndustry records."""
        # Map LNU codes to NAICS sectors
        lnu_to_naics = {code: sector for code, (_, sector) in INDUSTRY_UNEMPLOYMENT_SERIES.items()}

        # Get industries matching these NAICS codes
        naics_codes = list(set(lnu_to_naics.values()))
        industries = (
            session.query(DimIndustry).filter(DimIndustry.naics_code.in_(naics_codes)).all()
        )

        for industry in industries:
            self._industry_naics_to_id[industry.naics_code] = industry.industry_id

    # =========================================================================
    # FACT TABLE LOADERS
    # Note: _get_or_create_time() is inherited from DataLoader base class
    # =========================================================================

    def _load_fact_national(
        self,
        session: Session,
        start_year: int,
        end_year: int,
        verbose: bool,
    ) -> int:
        """Load national economic series facts."""
        assert self._client is not None

        observation_start = f"{start_year}-01-01"
        observation_end = f"{end_year}-12-31"
        count = 0

        series_iter = tqdm(ALL_NATIONAL_SERIES.items(), desc="National", disable=not verbose)

        for series_code, _title in series_iter:
            series_id = self._series_to_id.get(series_code)
            if not series_id:
                continue

            try:
                data = self._client.get_series_observations(
                    series_code,
                    observation_start=observation_start,
                    observation_end=observation_end,
                )

                for obs in data.observations:
                    if obs.value is None:
                        continue

                    # Parse date
                    year, month = _parse_date(obs.date)
                    if year is None:
                        continue

                    time_id = self._get_or_create_time(session, year, month)

                    fact = FactFredNational(
                        series_id=series_id,
                        time_id=time_id,
                        value=Decimal(str(obs.value)),
                    )
                    session.add(fact)
                    count += 1

            except FredAPIError as e:
                logger.warning(f"Failed to fetch national series {series_code}: {e}")
                continue

        session.flush()
        return count

    def _load_fact_state_unemployment(
        self,
        session: Session,
        state_fips_list: list[str],
        start_year: int,
        end_year: int,
        verbose: bool,
    ) -> int:
        """Load state unemployment facts."""
        assert self._client is not None

        observation_start = f"{start_year}-01-01"
        observation_end = f"{end_year}-12-31"
        count = 0

        state_iter = tqdm(state_fips_list, desc="State Unemp", disable=not verbose)

        for fips_code in state_iter:
            state_id = self._state_fips_to_id.get(fips_code)
            if not state_id:
                continue

            try:
                data = self._client.get_state_unemployment(
                    fips_code,
                    observation_start=observation_start,
                    observation_end=observation_end,
                )

                for obs in data.observations:
                    if obs.value is None:
                        continue

                    year, month = _parse_date(obs.date)
                    if year is None:
                        continue

                    time_id = self._get_or_create_time(session, year, month)

                    fact = FactFredStateUnemployment(
                        state_id=state_id,
                        time_id=time_id,
                        unemployment_rate=Decimal(str(obs.value)),
                    )
                    session.add(fact)
                    count += 1

            except FredAPIError as e:
                logger.warning(f"Failed to fetch state unemployment for {fips_code}: {e}")
                continue

        session.flush()
        return count

    def _load_fact_industry_unemployment(
        self,
        session: Session,
        start_year: int,
        end_year: int,
        verbose: bool,
    ) -> int:
        """Load industry unemployment facts."""
        assert self._client is not None

        observation_start = f"{start_year}-01-01"
        observation_end = f"{end_year}-12-31"
        count = 0

        industry_iter = tqdm(
            INDUSTRY_UNEMPLOYMENT_SERIES.items(),
            desc="Industry Unemp",
            disable=not verbose,
        )

        for lnu_code, (_, naics_sector) in industry_iter:
            industry_id = self._industry_naics_to_id.get(naics_sector)
            if not industry_id:
                logger.warning(f"Industry {naics_sector} not found in dim_industry")
                continue

            try:
                data = self._client.get_series_observations(
                    lnu_code,
                    observation_start=observation_start,
                    observation_end=observation_end,
                )

                for obs in data.observations:
                    if obs.value is None:
                        continue

                    year, month = _parse_date(obs.date)
                    if year is None:
                        continue

                    time_id = self._get_or_create_time(session, year, month)

                    fact = FactFredIndustryUnemployment(
                        industry_id=industry_id,
                        time_id=time_id,
                        unemployment_rate=Decimal(str(obs.value)),
                    )
                    session.add(fact)
                    count += 1

            except FredAPIError as e:
                logger.warning(f"Failed to fetch industry unemployment {lnu_code}: {e}")
                continue

        session.flush()
        return count

    def _load_fact_wealth_levels(
        self,
        session: Session,
        start_year: int,
        end_year: int,
        verbose: bool,
    ) -> int:
        """Load DFA wealth level facts."""
        assert self._client is not None

        observation_start = f"{start_year}-01-01"
        observation_end = f"{end_year}-12-31"
        count = 0

        series_iter = tqdm(
            DFA_WEALTH_LEVEL_SERIES.items(),
            desc="Wealth Levels",
            disable=not verbose,
        )

        for (percentile_code, asset_category), series_code in series_iter:
            series_id = self._series_to_id.get(series_code)
            wealth_class_id = self._class_to_id.get(percentile_code)
            category_id = self._category_to_id.get(asset_category)

            if not all([series_id, wealth_class_id, category_id]):
                continue

            try:
                data = self._client.get_series_observations(
                    series_code,
                    observation_start=observation_start,
                    observation_end=observation_end,
                )

                for obs in data.observations:
                    if obs.value is None:
                        continue

                    year, month = _parse_date(obs.date)
                    if year is None:
                        continue

                    # Quarterly data - compute quarter from month
                    quarter = ((month - 1) // 3 + 1) if month else None
                    time_id = self._get_or_create_time(session, year, month=None, quarter=quarter)

                    fact = FactFredWealthLevels(
                        series_id=series_id,
                        wealth_class_id=wealth_class_id,
                        category_id=category_id,
                        time_id=time_id,
                        value_millions=Decimal(str(obs.value)),
                    )
                    session.add(fact)
                    count += 1

            except FredAPIError as e:
                logger.warning(f"Failed to fetch wealth levels {series_code}: {e}")
                continue

        session.flush()
        return count

    def _load_fact_wealth_shares(
        self,
        session: Session,
        start_year: int,
        end_year: int,
        verbose: bool,
    ) -> int:
        """Load DFA wealth share facts."""
        assert self._client is not None

        observation_start = f"{start_year}-01-01"
        observation_end = f"{end_year}-12-31"
        count = 0

        series_iter = tqdm(
            DFA_WEALTH_SHARE_SERIES.items(),
            desc="Wealth Shares",
            disable=not verbose,
        )

        for (percentile_code, asset_category), series_code in series_iter:
            series_id = self._series_to_id.get(series_code)
            wealth_class_id = self._class_to_id.get(percentile_code)
            category_id = self._category_to_id.get(asset_category)

            if not all([series_id, wealth_class_id, category_id]):
                continue

            try:
                data = self._client.get_series_observations(
                    series_code,
                    observation_start=observation_start,
                    observation_end=observation_end,
                )

                for obs in data.observations:
                    if obs.value is None:
                        continue

                    year, month = _parse_date(obs.date)
                    if year is None:
                        continue

                    # Quarterly data - compute quarter from month
                    quarter = ((month - 1) // 3 + 1) if month else None
                    time_id = self._get_or_create_time(session, year, month=None, quarter=quarter)

                    fact = FactFredWealthShares(
                        series_id=series_id,
                        wealth_class_id=wealth_class_id,
                        category_id=category_id,
                        time_id=time_id,
                        share_percent=Decimal(str(obs.value)),
                    )
                    session.add(fact)
                    count += 1

            except FredAPIError as e:
                logger.warning(f"Failed to fetch wealth shares {series_code}: {e}")
                continue

        session.flush()
        return count


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _parse_date(date_str: str) -> tuple[int | None, int | None]:
    """Parse YYYY-MM-DD date string to (year, month)."""
    if not date_str:
        return None, None

    parts = date_str.split("-")
    if len(parts) < 2:
        return None, None

    try:
        year = int(parts[0])
        month = int(parts[1])
        return year, month
    except ValueError:
        return None, None


__all__ = [
    "FredLoader",
    "ALL_NATIONAL_SERIES",
    "PRODUCTIVITY_SERIES",
]
