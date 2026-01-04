"""Census data ingestion module.

Provides SQLite database for ACS Census research data analysis.
Separate from main babylon.db to keep research data isolated from game state.

Modules:
    database: Census SQLite engine and session management
    schema: SQLAlchemy ORM models for census tables
    parser: CSV parsing utilities for ACS data files (legacy)
    loader: Batch ingestion logic for census CSV data (legacy)
    api_client: Census Bureau API client
    api_loader: API-based ingestion for county-level data

Usage:
    # Load from Census API (recommended)
    from babylon.data.census import load_census_from_api

    stats = load_census_from_api(year=2022, reset=True)

    # Legacy: Load from CSV files
    from babylon.data.census import load_census_data
    from pathlib import Path

    census_dir = Path("data/census")
    stats = load_census_data(census_dir, reset=True)

    # Query the database
    from babylon.data.census import get_census_db, CensusCounty
    db = next(get_census_db())
    counties = db.query(CensusCounty).all()
"""

from babylon.data.census.api_client import (
    CensusAPIClient,
    CensusAPIError,
    CountyData,
    VariableMetadata,
    fetch_county_table,
)
from babylon.data.census.api_loader import (
    ALL_TABLES,
    MARXIAN_TABLES,
    ORIGINAL_TABLES,
    load_census_from_api,
)
from babylon.data.census.database import (
    CENSUS_DB_PATH,
    CensusBase,
    census_engine,
    get_census_db,
    init_census_db,
)
from babylon.data.census.loader import load_census_data
from babylon.data.census.loader_3nf import CensusLoader
from babylon.data.census.schema import (
    CensusColumnMetadata,
    CensusCommute,
    CensusCounty,
    CensusDataSource,
    CensusEducation,
    CensusEmploymentStatus,
    CensusGini,
    CensusHoursWorked,
    CensusHousingTenure,
    CensusIncomeDistribution,
    CensusInvestmentIncome,
    CensusMedianIncome,
    CensusMedianRent,
    CensusMetroArea,
    CensusOccupation,
    CensusPoverty,
    CensusRentBurden,
    CensusSelfEmployment,
    CensusWageIncome,
    CensusWorkerClass,
)

__all__ = [
    # Database
    "CENSUS_DB_PATH",
    "CensusBase",
    "census_engine",
    "get_census_db",
    "init_census_db",
    # API Client
    "CensusAPIClient",
    "CensusAPIError",
    "CountyData",
    "VariableMetadata",
    "fetch_county_table",
    # Loaders
    "CensusLoader",  # 3NF direct loader (recommended)
    "load_census_from_api",  # Legacy API loader (writes to research.sqlite)
    "load_census_data",  # Legacy CSV loader
    # Table constants
    "ALL_TABLES",
    "ORIGINAL_TABLES",
    "MARXIAN_TABLES",
    # Dimension tables
    "CensusCounty",
    "CensusMetroArea",  # Backwards compatibility alias
    "CensusDataSource",
    # Original fact tables (8)
    "CensusMedianIncome",
    "CensusIncomeDistribution",
    "CensusEmploymentStatus",
    "CensusWorkerClass",
    "CensusHousingTenure",
    "CensusMedianRent",
    "CensusRentBurden",
    "CensusOccupation",
    # Marxian analysis fact tables (8 new)
    "CensusHoursWorked",
    "CensusPoverty",
    "CensusEducation",
    "CensusGini",
    "CensusCommute",
    "CensusWageIncome",
    "CensusSelfEmployment",
    "CensusInvestmentIncome",
    # Metadata
    "CensusColumnMetadata",
]
