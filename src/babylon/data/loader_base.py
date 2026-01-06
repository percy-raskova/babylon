"""Base classes for unified data loading infrastructure.

Provides a common DataLoader ABC that enforces consistency, parameterization,
idempotency, and proper structure across all data sources. All loaders write
directly to the normalized 3NF schema in marxist-data-3NF.sqlite.

Usage:
    from babylon.data.loader_base import DataLoader, LoadStats

    class CensusLoader(DataLoader):
        def load(self, session: Session, reset: bool = True, **kwargs) -> LoadStats:
            ...
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.orm import Session


@dataclass
class LoaderConfig:
    """Configuration for data loaders.

    Parameterizes temporal coverage, geographic scope, and operational settings
    across all data loaders. This enables future database expansion without code
    changes by adjusting year ranges, geographic filters, or batch sizes.

    Temporal Parameters (per data source):
        census_years: List of ACS 5-year estimate vintages (default: 2009-2023).
            Each year represents a 5-year period (e.g., 2022 = 2018-2022 estimates).
        fred_start_year: Start year for FRED time series data.
        fred_end_year: End year for FRED time series data.
        energy_start_year: Start year for EIA energy data.
        energy_end_year: End year for EIA energy data.
        trade_years: List of years to load trade data for.
        qcew_years: List of years to load QCEW data for.
        materials_years: List of years to load materials data for.

    Geographic Scope:
        state_fips_list: List of 2-digit state FIPS codes to load (None = all 52).
        include_territories: Include US territories beyond PR (VI, GU, AS, MP).

    Operational:
        batch_size: Rows per bulk insert operation.
        request_delay_seconds: Rate limiting delay between API calls.
        max_retries: Max retry attempts for failed API requests.
        verbose: Enable progress output during loading.

    Example:
        # Default config - all data, full ranges
        config = LoaderConfig()

        # Custom config - single state, reduced year range
        config = LoaderConfig(
            census_years=[2021, 2022],  # Load only 2021 and 2022
            fred_start_year=2000,
            fred_end_year=2023,
            state_fips_list=["06"],  # California only
        )
    """

    # Temporal - Census (list of years for multi-year loading)
    census_years: list[int] = field(
        default_factory=lambda: list(range(2009, 2024))  # 2009-2023 inclusive (15 years)
    )

    # Temporal - FRED (time series range)
    fred_start_year: int = 1990
    fred_end_year: int = 2024

    # Temporal - Energy (EIA annual data)
    energy_start_year: int = 1990
    energy_end_year: int = 2024

    # Temporal - File-based sources (years to look for)
    trade_years: list[int] = field(default_factory=lambda: list(range(2010, 2025)))
    qcew_years: list[int] = field(default_factory=lambda: list(range(2015, 2024)))
    materials_years: list[int] = field(default_factory=lambda: list(range(2015, 2024)))

    # Geographic scope
    state_fips_list: list[str] | None = None  # None = all 52 (50 + DC + PR)
    include_territories: bool = False  # VI, GU, AS, MP

    # Operational
    batch_size: int = 10_000
    request_delay_seconds: float = 0.5
    max_retries: int = 3
    verbose: bool = True


@dataclass
class LoadStats:
    """Statistics returned by all loaders.

    Provides consistent tracking of load operations across all data sources,
    including dimension/fact table row counts, errors, and source metadata.

    Attributes:
        source: Identifier for the data source (e.g., "census", "fred").
        dimensions_loaded: Map of dimension table names to row counts.
        facts_loaded: Map of fact table names to row counts.
        errors: List of error messages encountered during load.
        api_calls: Number of API calls made (for API-based loaders).
        files_processed: Number of files processed (for file-based loaders).
    """

    source: str
    dimensions_loaded: dict[str, int] = field(default_factory=dict)
    facts_loaded: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    api_calls: int = 0
    files_processed: int = 0

    @property
    def total_dimensions(self) -> int:
        """Total rows loaded across all dimension tables."""
        return sum(self.dimensions_loaded.values())

    @property
    def total_facts(self) -> int:
        """Total rows loaded across all fact tables."""
        return sum(self.facts_loaded.values())

    @property
    def total_rows(self) -> int:
        """Total rows loaded across all tables."""
        return self.total_dimensions + self.total_facts

    @property
    def has_errors(self) -> bool:
        """Whether any errors were encountered."""
        return len(self.errors) > 0

    def __str__(self) -> str:
        """Human-readable summary of load statistics."""
        lines = [
            f"LoadStats({self.source})",
            f"  Dimensions: {self.total_dimensions:,} rows across {len(self.dimensions_loaded)} tables",
            f"  Facts: {self.total_facts:,} rows across {len(self.facts_loaded)} tables",
        ]
        if self.api_calls > 0:
            lines.append(f"  API calls: {self.api_calls}")
        if self.files_processed > 0:
            lines.append(f"  Files processed: {self.files_processed}")
        if self.has_errors:
            lines.append(f"  Errors: {len(self.errors)}")
        return "\n".join(lines)


class DataLoader(ABC):
    """Abstract base class for all data loaders.

    Enforces a consistent contract across all data source loaders:
    - load(): Main entry point for loading data into 3NF schema
    - get_dimension_tables(): Returns list of dimension table models
    - get_fact_tables(): Returns list of fact table models

    All loaders accept a LoaderConfig for parameterized temporal coverage,
    geographic scope, and operational settings. If no config is provided,
    sensible defaults are used.

    Idempotency Strategy:
        All loaders use DELETE + INSERT within a transaction for idempotency.
        This is appropriate for a "load-once, read-many" scenario where we
        want clean slate loading without complex UPSERT logic.

    Common Infrastructure:
        - _get_or_create_time(): Time dimension lookup with caching
        - _time_cache: Instance-level cache for time dimension lookups

    Attributes:
        config: LoaderConfig instance controlling loader behavior.

    Example:
        class CensusLoader(DataLoader):
            def load(self, session: Session, reset: bool = True, **kwargs) -> LoadStats:
                stats = LoadStats(source="census")
                years = self.config.census_years  # Use config parameter
                with session.begin():
                    if reset:
                        self.clear_tables(session)
                    for year in years:
                        # ... load data for specified year ...
                        pass
                return stats

        # Use with custom config
        config = LoaderConfig(census_years=[2021], state_fips_list=["06"])
        loader = CensusLoader(config)
        stats = loader.load(session)
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize loader with optional configuration.

        Args:
            config: LoaderConfig instance. If None, uses default config values.
        """
        self.config = config if config is not None else LoaderConfig()
        # Time dimension cache: (year, month, quarter) -> time_id
        self._time_cache: dict[tuple[int, int | None, int | None], int] = {}

    @abstractmethod
    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load data into 3NF schema.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing data before loading (default: True).
            verbose: If True, print progress information (default: True).
            **kwargs: Additional loader-specific parameters.

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        ...

    @abstractmethod
    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates.

        Returns:
            List of SQLAlchemy model classes for dimension tables.
        """
        ...

    @abstractmethod
    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates.

        Returns:
            List of SQLAlchemy model classes for fact tables.
        """
        ...

    def clear_tables(self, session: Session) -> None:
        """Clear all tables this loader populates.

        Clears fact tables first (to respect FK constraints), then dimensions.
        Uses DELETE within the current transaction context.

        Args:
            session: SQLAlchemy session for the normalized database.
        """
        # Delete facts first (they reference dimensions)
        for table in self.get_fact_tables():
            session.query(table).delete()

        # Then delete dimensions
        for table in self.get_dimension_tables():
            session.query(table).delete()

    def _get_or_create_time(
        self,
        session: Session,
        year: int,
        month: int | None = None,
        quarter: int | None = None,
    ) -> int:
        """Get or create a time dimension record with caching.

        Provides a unified interface for time dimension management across all
        loaders. Supports annual, monthly, and quarterly granularity with
        instance-level caching to minimize database lookups.

        Args:
            session: SQLAlchemy session for the normalized database.
            year: 4-digit calendar year.
            month: 1-12 month for monthly data, None for annual/quarterly.
            quarter: 1-4 quarter for quarterly data, None for annual/monthly.

        Returns:
            time_id for the matching DimTime record.

        Note:
            - If month is None and quarter is None: annual granularity
            - If month is provided: monthly granularity (quarter auto-calculated)
            - If quarter is provided and month is None: quarterly granularity
        """
        # Import here to avoid circular dependency
        from babylon.data.normalize.schema import DimTime

        cache_key = (year, month, quarter)
        if cache_key in self._time_cache:
            return self._time_cache[cache_key]

        # Determine if annual (no month and no quarter specified)
        is_annual = month is None and quarter is None

        # Build query to find existing record
        query = session.query(DimTime).filter(DimTime.year == year)

        if month is not None:
            query = query.filter(DimTime.month == month)
        else:
            query = query.filter(DimTime.month.is_(None))

        if quarter is not None:
            query = query.filter(DimTime.quarter == quarter)
        else:
            query = query.filter(DimTime.quarter.is_(None))

        existing = query.first()
        if existing:
            self._time_cache[cache_key] = existing.time_id
            return existing.time_id

        # Create new time record
        # Auto-calculate quarter from month if month is provided
        calculated_quarter = quarter
        if month is not None and quarter is None:
            calculated_quarter = (month - 1) // 3 + 1

        time_record = DimTime(
            year=year,
            month=month,
            quarter=calculated_quarter,
            is_annual=is_annual,
        )
        session.add(time_record)
        session.flush()

        self._time_cache[cache_key] = time_record.time_id
        return time_record.time_id

    def _get_or_create_data_source(
        self,
        session: Session,
        source_code: str,
        source_name: str,
        source_url: str | None = None,
        description: str | None = None,
        source_agency: str | None = None,
        source_year: int | None = None,
        coverage_start_year: int | None = None,
        coverage_end_year: int | None = None,
    ) -> int:
        """Get or create a data source dimension record.

        Provides a unified interface for data source dimension management across
        all loaders. Checks for existing source by source_code before creating.

        Args:
            session: SQLAlchemy session for the normalized database.
            source_code: Unique identifier for the data source (e.g., "EIA", "CENSUS").
            source_name: Human-readable name for the data source.
            source_url: URL for the data source (optional).
            description: Description of the data source (optional).
            source_agency: Government agency that provides the data (optional).
            source_year: Year of the data release (optional).
            coverage_start_year: First year of data coverage (optional).
            coverage_end_year: Last year of data coverage (optional).

        Returns:
            source_id for the matching or newly created DimDataSource record.
        """
        # Import here to avoid circular dependency
        from babylon.data.normalize.schema import DimDataSource

        # Check for existing source
        existing = (
            session.query(DimDataSource).filter(DimDataSource.source_code == source_code).first()
        )
        if existing:
            return existing.source_id

        # Create new source record
        source = DimDataSource(
            source_code=source_code,
            source_name=source_name,
            source_url=source_url,
            description=description,
            source_agency=source_agency,
            source_year=source_year,
            coverage_start_year=coverage_start_year,
            coverage_end_year=coverage_end_year,
        )
        session.add(source)
        session.flush()

        return source.source_id

    def _build_county_lookup(self, session: Session) -> dict[str, int]:
        """Build a FIPS code to county_id lookup dictionary.

        Used by spatial loaders (HIFLD, MIRTA) that aggregate facility data
        to the county level. The returned dictionary maps 5-digit FIPS codes
        to database county_id values.

        Args:
            session: SQLAlchemy session for the normalized database.

        Returns:
            Dictionary mapping 5-digit FIPS codes (str) to county_id (int).

        Example:
            fips_to_county = self._build_county_lookup(session)
            county_id = fips_to_county.get("06001")  # Alameda County, CA
        """
        # Import here to avoid circular dependency
        from babylon.data.normalize.schema import DimCounty

        counties = session.query(DimCounty).all()
        return {c.fips: c.county_id for c in counties}


__all__ = [
    "DataLoader",
    "LoaderConfig",
    "LoadStats",
]
