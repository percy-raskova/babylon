"""Database configuration and session management.

Provides SQLAlchemy engine and session configuration for the application.
Uses SQLite for local persistence - simple, embedded, no server required.
"""

from typing import Any, Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from babylon.config.base import BaseConfig as Config

# Initialize SQLite database engine
engine: Engine = create_engine(Config.DATABASE_URL)

# Configure session factory
SessionLocal: Any = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()


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
