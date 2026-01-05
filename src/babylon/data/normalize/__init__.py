"""Normalized 3NF research database module.

Provides a properly normalized database for Marxian economic analysis,
populated directly by DataLoader implementations.

Database location: data/sqlite/marxist-data-3NF.sqlite

Usage:
    from babylon.data import DataLoader, LoaderConfig
    from babylon.data.normalize import get_normalized_db
    from babylon.data.census import CensusLoader

    config = LoaderConfig(census_year=2022)
    loader = CensusLoader(config)

    with get_normalized_db() as session:
        stats = loader.load(session, reset=True)
        print(stats)

Or via CLI:
    mise run data:load
    mise run data:census -- --year 2022
"""

from __future__ import annotations

# Re-export classification functions
from babylon.data.normalize.classifications import (
    classify_class_composition,
    classify_labor_type,
    classify_marxian_class,
    classify_ownership,
    classify_rent_burden,
    classify_world_system_tier,
)
from babylon.data.normalize.database import (
    NORMALIZED_DATABASE_URL,
    NORMALIZED_DB_PATH,
    NormalizedBase,
    get_normalized_db,
    get_normalized_engine,
    init_normalized_db,
    normalized_engine,
)
from babylon.data.normalize.views import VIEWS, create_views, drop_views

__all__ = [
    # Database
    "NORMALIZED_DATABASE_URL",
    "NORMALIZED_DB_PATH",
    "NormalizedBase",
    "get_normalized_db",
    "get_normalized_engine",
    "init_normalized_db",
    "normalized_engine",
    # Views
    "VIEWS",
    "create_views",
    "drop_views",
    # Classifications
    "classify_class_composition",
    "classify_labor_type",
    "classify_marxian_class",
    "classify_ownership",
    "classify_rent_burden",
    "classify_world_system_tier",
]
