"""Research database configuration and session management.

Provides a unified SQLite database for all empirical research data:
- Census ACS data (census_* tables)
- Trade/imperial rent data (trade_* tables)

Located at data/sqlite/research.sqlite, isolated from main game database.
"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Research database path - unified empirical data, separate from main babylon.db
RESEARCH_DB_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "data" / "sqlite" / "research.sqlite"
)
RESEARCH_DATABASE_URL = f"sqlite:///{RESEARCH_DB_PATH}"

# Backwards compatibility aliases
CENSUS_DB_PATH = RESEARCH_DB_PATH
CENSUS_DATABASE_URL = RESEARCH_DATABASE_URL


class CensusBase(DeclarativeBase):
    """Base class for all census SQLAlchemy models."""

    pass


def get_census_engine() -> Engine:
    """Create research database engine.

    Returns:
        Engine: SQLAlchemy engine for research.sqlite
    """
    # Ensure parent directory exists
    RESEARCH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(RESEARCH_DATABASE_URL)


# Initialize census database engine
census_engine: Engine = get_census_engine()

# Configure session factory
CensusSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=census_engine)


def get_census_db() -> Iterator[Session]:
    """Get a census database session.

    Yields:
        Session: SQLAlchemy database session for census data
    """
    db = CensusSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_census_db() -> None:
    """Create all census database tables."""
    # Import schema to register all models with CensusBase.metadata
    from babylon.data.census import schema  # noqa: F401

    CensusBase.metadata.create_all(bind=census_engine)
