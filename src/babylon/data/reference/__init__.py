"""Reference database module (immutable federal statistical data).

The reference database contains normalized 3NF federal statistical data
for initializing simulation state. This data is immutable after initial
load - loaders write once, simulation reads only.

Database location: data/sqlite/marxist-data-3NF.sqlite (override via BABYLON_NORMALIZED_DB_PATH)

Usage:
    # Read-only access (default for simulation)
    from babylon.data.reference import get_reference_session

    with get_reference_session() as session:
        counties = session.query(DimCounty).all()

    # Write access (for loaders only)
    from babylon.data.reference import get_normalized_session

    with get_normalized_session() as session:
        session.add(new_record)
        session.commit()

Or via CLI:
    mise run data:load
    mise run data:census -- --year 2021
"""

from __future__ import annotations

# Re-export classification functions
from babylon.data.reference.classifications import (
    classify_class_composition,
    classify_labor_type,
    classify_marxian_class,
    classify_ownership,
    classify_rent_burden,
    classify_world_system_tier,
)
from babylon.data.reference.database import (
    NORMALIZED_DATABASE_URL,
    NORMALIZED_DB_PATH,
    NormalizedBase,
    get_normalized_db,
    get_normalized_engine,
    get_normalized_session,
    get_reference_session,
    init_normalized_db,
    normalized_engine,
)
from babylon.data.reference.views import VIEWS, create_views, drop_views

__all__ = [
    # Database - Public API
    "get_reference_session",  # Read-only access (preferred for simulation)
    "get_normalized_session",  # Write access (for loaders)
    # Database - Low-level
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
