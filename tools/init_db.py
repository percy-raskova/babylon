#!/usr/bin/env python3
"""Initialize SQLite database with schema.

Creates all tables defined in babylon.data.schema.

Usage:
    poetry run python tools/init_db.py
"""

from pathlib import Path


def init_db() -> None:
    """Create all database tables."""
    # Import here to avoid circular imports and allow schema to be loaded
    # Import schema to register all models with Base.metadata
    from babylon.data import schema  # noqa: F401
    from babylon.data.database import Base, engine

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Report success
    db_path = str(engine.url).replace("sqlite:///", "")
    print(f"Database initialized: {db_path}")
    print(f"Tables created: {list(Base.metadata.tables.keys())}")


def main() -> None:
    """Entry point."""
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    init_db()


if __name__ == "__main__":
    main()
