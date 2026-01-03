"""Normalized 3NF research database configuration.

Provides a properly normalized database for Marxian economic analysis,
populated via ETL from research.sqlite.

Located at data/sqlite/marxist-data-3NF.sqlite.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Normalized database path - 3NF structure for analytical queries
NORMALIZED_DB_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "data"
    / "sqlite"
    / "marxist-data-3NF.sqlite"
)
NORMALIZED_DATABASE_URL = f"sqlite:///{NORMALIZED_DB_PATH}"

# Source database (for ETL)
SOURCE_DB_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "data" / "sqlite" / "research.sqlite"
)
SOURCE_DATABASE_URL = f"sqlite:///{SOURCE_DB_PATH}"


class NormalizedBase(DeclarativeBase):
    """Base class for all normalized 3NF SQLAlchemy models."""

    pass


def get_normalized_engine(echo: bool = False) -> Engine:
    """Create normalized database engine with FK enforcement.

    Args:
        echo: If True, log SQL statements

    Returns:
        Engine: SQLAlchemy engine for marxist-data-3NF.sqlite
    """
    NORMALIZED_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(NORMALIZED_DATABASE_URL, echo=echo)

    # Enable foreign key enforcement for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
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
    """Get a normalized database session.

    Yields:
        Session: SQLAlchemy database session
    """
    session_factory = get_normalized_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_normalized_db() -> None:
    """Create all normalized database tables."""
    from babylon.data.normalize import schema  # noqa: F401

    NormalizedBase.metadata.create_all(bind=normalized_engine())
