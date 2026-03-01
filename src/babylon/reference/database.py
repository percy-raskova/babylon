"""Reference database configuration (immutable federal statistical data).

The reference database contains normalized 3NF federal statistical data
for initializing simulation state. This data is treated as immutable
after initial load - loaders write once, simulation reads only.

Architecture (ADR030 - Unified SQLite Runtime):
    - ETL/Loading: SQLite (reliable UPSERT, idempotent operations)
    - Reference Data: SQLite (census, QCEW, geography)
    - Simulation State: SQLite (tick-keyed temporal tables per ADR031)

Located at data/sqlite/marxist-data-3NF.sqlite by default. Override with
BABYLON_NORMALIZED_DB_PATH to target an alternate build database.

SQLite was chosen for the entire stack because:
- Reliable on_conflict_do_update (UPSERT) support via SQLAlchemy
- Mature, battle-tested SQLAlchemy dialect
- Predictable constraint enforcement within transactions
- Idempotent loader operations without duplicate key violations
- Single file deployment (no additional database servers)
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Normalized database path - 3NF structure for analytical queries
# From src/babylon/reference/database.py -> repo root is 4 parents up
_REPO_ROOT = Path(__file__).parent.parent.parent.parent

# Legacy source database path (for reference during migration)
SOURCE_DB_PATH = _REPO_ROOT / "data" / "sqlite" / "research.sqlite"
SOURCE_DATABASE_URL = f"sqlite:///{SOURCE_DB_PATH}"


def _resolve_db_path(env_var: str, default_path: Path) -> Path:
    env_value = os.getenv(env_var)
    if not env_value:
        return default_path

    env_path = Path(env_value).expanduser()
    if not env_path.is_absolute():
        env_path = _REPO_ROOT / env_path

    return env_path


NORMALIZED_DB_PATH = _resolve_db_path(
    "BABYLON_NORMALIZED_DB_PATH",
    _REPO_ROOT / "data" / "sqlite" / "marxist-data-3NF.sqlite",
)
NORMALIZED_DATABASE_URL = f"sqlite:///{NORMALIZED_DB_PATH}"


class NormalizedBase(DeclarativeBase):
    """Base class for all normalized 3NF SQLAlchemy models."""

    pass


def get_normalized_engine(echo: bool = False) -> Engine:
    """Create normalized SQLite database engine with FK enforcement.

    SQLite requires explicit PRAGMA foreign_keys=ON to enforce foreign keys.
    This is set via an event listener on every connection.

    Args:
        echo: If True, log SQL statements

    Returns:
        Engine: SQLAlchemy engine for the normalized 3NF SQLite database.
    """
    NORMALIZED_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(NORMALIZED_DATABASE_URL, echo=echo)

    # Enable FK constraints for SQLite (must be set on every connection)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(
        dbapi_conn: object,  # sqlite3.Connection at runtime
        _connection_record: object,
    ) -> None:
        import sqlite3

        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_source_engine() -> Engine:
    """Create source database engine (research.sqlite).

    Returns:
        Engine: SQLAlchemy engine for research.sqlite
    """
    return create_engine(SOURCE_DATABASE_URL)


# Initialize engines lazily
_normalized_engine: Engine | None = None
_source_engine: Engine | None = None


def normalized_engine() -> Engine:
    """Get or create the normalized database engine."""
    global _normalized_engine
    if _normalized_engine is None:
        _normalized_engine = get_normalized_engine()
    return _normalized_engine


def source_engine() -> Engine:
    """Get or create the source database engine."""
    global _source_engine
    if _source_engine is None:
        _source_engine = get_source_engine()
    return _source_engine


# Session factories (created lazily)
_NormalizedSessionLocal: sessionmaker[Session] | None = None


def get_normalized_session_factory() -> sessionmaker[Session]:
    """Get or create the normalized session factory."""
    global _NormalizedSessionLocal
    if _NormalizedSessionLocal is None:
        _NormalizedSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=normalized_engine()
        )
    return _NormalizedSessionLocal


def get_normalized_db() -> Iterator[Session]:
    """Get a normalized database session (generator for dependency injection).

    Yields:
        Session: SQLAlchemy database session
    """
    session_factory = get_normalized_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_normalized_session() -> Iterator[Session]:
    """Get a normalized database session as a context manager.

    This provides write access to the reference database and should
    only be used by loaders during initial data population.

    Usage::

        with get_normalized_session() as session:
            session.add(obj)
            session.commit()

    Yields:
        Session: SQLAlchemy database session with write access.
    """
    session_factory = get_normalized_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_reference_session() -> Iterator[Session]:
    """Get a read-only reference database session.

    This is the preferred API for simulation code to access reference data.
    The session is read-only by convention - no commit is performed.

    Usage::

        from babylon.reference.database import get_reference_session
        from babylon.reference.schema import DimCounty

        with get_reference_session() as session:
            counties = session.query(DimCounty).all()

    Yields:
        Session: SQLAlchemy database session (read-only by convention).
    """
    session_factory = get_normalized_session_factory()
    session = session_factory()
    try:
        yield session
        # No commit - read-only by convention
    finally:
        session.close()


def init_normalized_db() -> None:
    """Create all normalized database tables."""
    from babylon.reference import schema  # noqa: F401

    NormalizedBase.metadata.create_all(bind=normalized_engine())
