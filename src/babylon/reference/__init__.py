"""Reference database module (immutable federal statistical data).

The reference database contains normalized 3NF federal statistical data
for initializing simulation state. This data is immutable after initial
load - loaders write once, simulation reads only.

Database location: data/sqlite/marxist-data-3NF.sqlite
    (override via BABYLON_NORMALIZED_DB_PATH)

Usage::

    from babylon.reference.database import get_reference_session
    from babylon.reference.schema import DimCounty

    with get_reference_session() as session:
        counties = session.query(DimCounty).all()
"""

from babylon.reference.database import (
    NORMALIZED_DATABASE_URL,
    NORMALIZED_DB_PATH,
    NormalizedBase,
    get_normalized_db,
    get_normalized_engine,
    get_normalized_session,
    get_normalized_session_factory,
    get_reference_session,
    init_normalized_db,
    normalized_engine,
)

__all__ = [
    "get_reference_session",
    "get_normalized_session",
    "get_normalized_session_factory",
    "NORMALIZED_DATABASE_URL",
    "NORMALIZED_DB_PATH",
    "NormalizedBase",
    "get_normalized_db",
    "get_normalized_engine",
    "init_normalized_db",
    "normalized_engine",
]
