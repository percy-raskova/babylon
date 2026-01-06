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


__all__ = [
    "DataLoader",
    "LoaderConfig",
    "LoadStats",
]
