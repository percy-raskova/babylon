"""BLS Industry Productivity data ingestion module.

Provides SQLite tables for labor productivity metrics by NAICS industry,
joinable with QCEW wage data for Marxian value analysis.

Modules:
    schema: SQLAlchemy ORM models for productivity tables
    parser: Excel parsing utilities for BLS files
    loader: Batch ingestion logic

Usage:
    from babylon.data.productivity import load_productivity_data
    from pathlib import Path

    stats = load_productivity_data(Path("data/productivity"), year=2022, reset=True)
    print(f"Loaded {stats.industries_loaded} industries, {stats.records_loaded} records")

    # Query the database
    from babylon.data.census import get_census_db
    from babylon.data.productivity import ProductivityIndustry, ProductivityAnnual

    db = next(get_census_db())
    industries = db.query(ProductivityIndustry).all()

    # Join with QCEW for rate of exploitation analysis
    # productivity.naics_code -> qcew_industries.industry_code
"""

from babylon.data.productivity.loader import (
    LoadStats,
    load_multi_year_productivity,
    load_productivity_data,
)
from babylon.data.productivity.parser import (
    HOURS_EMPLOYMENT_FILE,
    LABOR_PRODUCTIVITY_FILE,
    IndustryRecord,
    ParsedProductivityData,
    ProductivityRecord,
    discover_available_years,
    parse_productivity_data,
)
from babylon.data.productivity.schema import (
    ProductivityAnnual,
    ProductivityIndustry,
)

__all__ = [
    # Loader
    "LoadStats",
    "load_productivity_data",
    "load_multi_year_productivity",
    # Parser
    "HOURS_EMPLOYMENT_FILE",
    "LABOR_PRODUCTIVITY_FILE",
    "IndustryRecord",
    "ParsedProductivityData",
    "ProductivityRecord",
    "discover_available_years",
    "parse_productivity_data",
    # Schema
    "ProductivityAnnual",
    "ProductivityIndustry",
]
