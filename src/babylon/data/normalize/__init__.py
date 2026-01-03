"""Normalized 3NF research database module.

Provides a properly normalized database for Marxian economic analysis,
populated via ETL from the denormalized research.sqlite.

Database location: data/sqlite/marxist-data-3NF.sqlite

Usage:
    from babylon.data.normalize import run_etl
    stats = run_etl(reset=True)
    print(stats)

Or via CLI:
    poetry run python -m babylon.data.normalize --reset
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
from babylon.data.normalize.etl import ETLStats, run_etl
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
    # ETL
    "ETLStats",
    "run_etl",
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
