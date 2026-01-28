"""Database configuration and session management.

Provides SQLAlchemy engine and session configuration for the application.
Uses SQLite for local persistence - simple, embedded, no server required.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from babylon.config.base import BaseConfig as Config


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Initialize SQLite database engine
engine: Engine = create_engine(Config.DATABASE_URL)

# Configure session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    """Get a database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
