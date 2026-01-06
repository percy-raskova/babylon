"""FRED (Federal Reserve Economic Data) ingestion module.

Provides direct 3NF ingestion of macroeconomic time series data from the
Federal Reserve Bank of St. Louis FRED API. Supports:

- **National indicators**: CPI, wages, unemployment, debt, Gini, M2, PPP
- **State-level unemployment**: 51 states via LAUST series
- **Productivity**: Labor productivity and output per hour (via FRED API)
- **DFA wealth distribution**: Quarterly wealth by percentile class

Modules:
    api_client: Rate-limited FRED API client
    parser: Response parsing utilities
    loader_3nf: Direct 3NF loader (recommended)

Usage:
    from babylon.data.fred import FredLoader
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    config = LoaderConfig(fred_start_year=1990, fred_end_year=2024)
    loader = FredLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"Loaded {stats.facts_loaded} facts")

API Documentation:
    https://fred.stlouisfed.org/docs/api/fred/
"""

from babylon.data.exceptions import FredAPIError
from babylon.data.fred.api_client import (
    DFA_ASSET_CATEGORIES,
    DFA_WEALTH_CLASSES,
    DFA_WEALTH_LEVEL_SERIES,
    DFA_WEALTH_SHARE_SERIES,
    INDUSTRY_UNEMPLOYMENT_SERIES,
    NATIONAL_SERIES,
    US_STATES,
    FredAPIClient,
    Observation,
    SeriesData,
    SeriesMetadata,
)
from babylon.data.fred.loader_3nf import (
    ALL_NATIONAL_SERIES,
    PRODUCTIVITY_SERIES,
    FredLoader,
)
from babylon.data.fred.parser import (
    IndustryUnemploymentRecord,
    NationalRecord,
    StateUnemploymentRecord,
    WealthLevelRecord,
    WealthShareRecord,
    get_dfa_level_series_list,
    get_dfa_share_series_list,
    get_industry_series_list,
    get_national_series_list,
    get_state_fips_list,
    parse_industry_unemployment,
    parse_national_series,
    parse_state_unemployment,
    parse_wealth_level,
    parse_wealth_share,
)
from babylon.data.fred.schema import (
    FredAssetCategory,
    FredIndustry,
    FredIndustryUnemployment,
    FredNational,
    FredSeries,
    FredState,
    FredStateUnemployment,
    FredWealthClass,
    FredWealthLevel,
    FredWealthShare,
)

__all__ = [
    # API Client
    "FredAPIClient",
    "FredAPIError",
    "SeriesMetadata",
    "SeriesData",
    "Observation",
    "NATIONAL_SERIES",
    "US_STATES",
    "INDUSTRY_UNEMPLOYMENT_SERIES",
    # DFA Wealth Distribution Constants
    "DFA_WEALTH_CLASSES",
    "DFA_ASSET_CATEGORIES",
    "DFA_WEALTH_LEVEL_SERIES",
    "DFA_WEALTH_SHARE_SERIES",
    # Loaders
    "FredLoader",  # 3NF direct loader (recommended)
    "ALL_NATIONAL_SERIES",  # National + Productivity series
    "PRODUCTIVITY_SERIES",  # Productivity series only
    # Parser
    "NationalRecord",
    "StateUnemploymentRecord",
    "IndustryUnemploymentRecord",
    "WealthLevelRecord",
    "WealthShareRecord",
    "parse_national_series",
    "parse_state_unemployment",
    "parse_industry_unemployment",
    "parse_wealth_level",
    "parse_wealth_share",
    "get_national_series_list",
    "get_state_fips_list",
    "get_industry_series_list",
    "get_dfa_level_series_list",
    "get_dfa_share_series_list",
    # Schema
    "FredSeries",
    "FredState",
    "FredIndustry",
    "FredNational",
    "FredStateUnemployment",
    "FredIndustryUnemployment",
    # DFA Wealth Distribution Schema
    "FredWealthClass",
    "FredAssetCategory",
    "FredWealthLevel",
    "FredWealthShare",
]
