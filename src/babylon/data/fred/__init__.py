"""FRED (Federal Reserve Economic Data) ingestion module.

Provides SQLite tables for macroeconomic time series data from the
Federal Reserve Bank of St. Louis FRED API. Supports:

- **National indicators**: CPI, wages, unemployment, debt, Gini, M2, PPP
- **State-level unemployment**: 51 states via LAUST series
- **Industry-level unemployment**: 8 major sectors via LNU04 series
- **DFA wealth distribution**: Quarterly wealth by percentile class (Top 1%,
  90-99%, 50-90%, Bottom 50%) from the Federal Reserve's Distributional
  Financial Accounts

All tables are stored in the unified research.sqlite database alongside
Census, QCEW, Trade, and Productivity data for integrated Marxian analysis.

Modules:
    schema: SQLAlchemy ORM models for FRED tables
    api_client: Rate-limited FRED API client
    parser: Response parsing utilities
    loader: Batch ingestion logic

Usage:
    from babylon.data.fred import load_fred_data, LoadStats

    # Load all FRED data for 2022 (national + state + industry + wealth)
    stats = load_fred_data(year=2022, reset=True)
    print(f"Loaded {stats.national_records} national records")
    print(f"Loaded {stats.state_records} state unemployment records")
    print(f"Loaded {stats.industry_records} industry unemployment records")
    print(f"Loaded {stats.wealth_level_records} wealth level records")
    print(f"Loaded {stats.wealth_share_records} wealth share records")

    # Query the database
    from babylon.data.census import get_census_db
    from babylon.data.fred import FredNational, FredSeries

    db = next(get_census_db())
    cpi = db.query(FredNational).join(FredSeries).filter(
        FredSeries.series_id == "CPIAUCSL"
    ).all()

    # Join with QCEW for wage analysis
    # fred_industries.naics_sector -> qcew_industries.industry_code

    # Query wealth by Babylon class
    from babylon.data.fred import FredWealthLevel, FredWealthClass
    labor_aristocracy = db.query(FredWealthLevel).join(FredWealthClass).filter(
        FredWealthClass.babylon_class == "labor_aristocracy"
    ).all()

Series Catalog:
    National Series (8):
        CPIAUCSL - Consumer Price Index (real wage calculation)
        AHETPI - Average Hourly Earnings (nominal wage input)
        UNRATE - Unemployment Rate (reserve army proxy)
        GFDEBTN - Federal Debt (fiscal trilemma)
        GINIALLRF - Gini Index (class tension initialization)
        M2SL - M2 Money Supply (fictitious capital proxy)
        PPPTTLUSD - PPP Conversion Factor (unequal exchange)
        RGDPCHUSA625NUPN - PPP GDP/Capita (imperial bribe / superwages)

    State Unemployment (51):
        LAUST{FIPS}0000000003A - e.g., LAUST120000000000003A (Florida)

    Industry Unemployment (8):
        LNU04032231 - Construction
        LNU04032232 - Manufacturing
        LNU04032236 - Transportation & Utilities
        LNU04032237 - Information
        LNU04032238 - Financial Activities
        LNU04032239 - Professional & Business Services
        LNU04032240 - Education & Health Services
        LNU04032241 - Leisure & Hospitality

    DFA Wealth Distribution (20 series):
        Levels ($ Millions):
            WFRBLT01000 - Top 1% Total Assets
            WFRBLN09027 - 90-99% Total Assets
            WFRBLN40054 - 50-90% Total Assets (Labor Aristocracy)
            WFRBLB50081 - Bottom 50% Total Assets
            (+ Real Estate and Net Worth variants for each class)

        Shares (%):
            WFRBST01134 - Top 1% Share of Net Worth
            WFRBSN09161 - 90-99% Share of Net Worth
            WFRBSN40188 - 50-90% Share of Net Worth
            WFRBSB50215 - Bottom 50% Share of Net Worth
            (+ Asset Share variants for each class)

API Documentation:
    https://fred.stlouisfed.org/docs/api/fred/
    https://www.federalreserve.gov/releases/z1/dataviz/dfa/
"""

from babylon.data.fred.api_client import (
    DFA_ASSET_CATEGORIES,
    DFA_WEALTH_CLASSES,
    DFA_WEALTH_LEVEL_SERIES,
    DFA_WEALTH_SHARE_SERIES,
    INDUSTRY_UNEMPLOYMENT_SERIES,
    NATIONAL_SERIES,
    US_STATES,
    FredAPIClient,
    FredAPIError,
    Observation,
    SeriesData,
    SeriesMetadata,
)
from babylon.data.fred.loader import (
    LoadStats,
    init_fred_tables,
    load_fred_data,
    reset_fred_tables,
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
    "LoadStats",  # Legacy loader stats
    "load_fred_data",  # Legacy API loader (writes to research.sqlite)
    "init_fred_tables",
    "reset_fred_tables",
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
