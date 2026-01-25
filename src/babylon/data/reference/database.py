"""Reference database configuration (immutable federal statistical data).

The reference database contains normalized 3NF federal statistical data
for initializing simulation state. This data is treated as immutable
after initial load - loaders write once, simulation reads only.

Located at data/duckdb/marxist-data-3NF.duckdb by default. Override with
BABYLON_NORMALIZED_DB_PATH to target an alternate build database.

DuckDB was chosen over SQLite for:
- Better analytical query performance (columnar storage)
- Native Parquet and CSV support for data import/export
- Future DuckPGQ graph query support (Topology layer unification)
- Concurrent read access without locking
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Normalized database path - 3NF structure for analytical queries
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


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
    _REPO_ROOT / "data" / "duckdb" / "marxist-data-3NF.duckdb",
)
NORMALIZED_DATABASE_URL = f"duckdb:///{NORMALIZED_DB_PATH}"

# Legacy source database path (for reference during migration)
SOURCE_DB_PATH = _REPO_ROOT / "data" / "sqlite" / "research.sqlite"
SOURCE_DATABASE_URL = f"sqlite:///{SOURCE_DB_PATH}"


class NormalizedBase(DeclarativeBase):
    """Base class for all normalized 3NF SQLAlchemy models."""

    pass


def get_normalized_engine(echo: bool = False) -> Engine:
    """Create normalized DuckDB database engine.

    DuckDB enforces foreign keys by default and supports concurrent reads.

    Args:
        echo: If True, log SQL statements

    Returns:
        Engine: SQLAlchemy engine for the normalized 3NF DuckDB database.
    """
    NORMALIZED_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(NORMALIZED_DATABASE_URL, echo=echo)
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

    Usage:
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

    Usage:
        from babylon.data.reference import get_reference_session, DimCounty

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
    from babylon.data.reference import schema  # noqa: F401

    NormalizedBase.metadata.create_all(bind=normalized_engine())
