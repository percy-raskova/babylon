"""Injectable database connection for the simulation engine.

This module provides a DatabaseConnection class that wraps SQLAlchemy
engine and session creation, enabling dependency injection for testing.

Unlike the module-level singletons in babylon.data.database, this class
allows creating isolated database connections for each test or component.

Sprint 3: Central Committee (Dependency Injection)
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConnection:
    """Injectable database connection wrapper.

    Wraps SQLAlchemy engine and sessionmaker to provide clean
    resource management and testability.

    Example:
        >>> db = DatabaseConnection(url="sqlite:///:memory:")
        >>> with db.session() as session:
        ...     result = session.execute(text("SELECT 1"))
        ...     print(result.scalar())
        1
        >>> db.close()
    """

    def __init__(self, url: str = "sqlite:///babylon.db") -> None:
        """Initialize database connection.

        Args:
            url: SQLAlchemy database URL. Defaults to local SQLite file.
                 Use "sqlite:///:memory:" for in-memory testing.
        """
        self._engine: Engine = create_engine(url)
        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Get a database session within a context manager.

        The session is automatically closed when the context exits.
        On exception, the session is rolled back.

        Yields:
            SQLAlchemy Session object

        Example:
            >>> with db.session() as session:
            ...     session.execute(text("INSERT INTO ..."))
            ...     session.commit()
        """
        session = self._session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Dispose of the database engine and release resources.

        After calling close(), the connection cannot be used.
        Attempting to create new sessions will fail.
        """
        self._engine.dispose()
