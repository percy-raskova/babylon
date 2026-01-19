"""Census data ingestion module.

Provides SQLite database for ACS Census research data analysis.
Separate from main babylon.db to keep research data isolated from game state.

Modules:
    database: Census SQLite engine and session management
    schema: SQLAlchemy ORM models for census tables
    api_client: Census Bureau API client
    loader_3nf: Direct 3NF loader (recommended)

Usage:
    # Load directly to 3NF (recommended)
    from babylon.data.census import CensusLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(census_years=[2021])
    loader = CensusLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} facts")

    # Query the database
    from babylon.data.census import get_census_db, CensusCounty
    db = next(get_census_db())
    counties = db.query(CensusCounty).all()
"""

from babylon.data.census.api_client import (
    CensusAPIClient,
    CountyData,
    VariableMetadata,
    fetch_county_table,
)
from babylon.data.census.database import (
    CENSUS_DB_PATH,
    CensusBase,
    census_engine,
    get_census_db,
    init_census_db,
)
from babylon.data.census.loader_3nf import (
    ALL_TABLES,
    MARXIAN_TABLES,
    ORIGINAL_TABLES,
    CensusLoader,
)
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
from babylon.data.exceptions import CensusAPIError

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
