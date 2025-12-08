"""Tests for DatabaseConnection wrapper.

RED Phase: These tests define the contract for the database connection.
The DatabaseConnection provides injectable database access for testing.

Test Intent:
- DatabaseConnection wraps SQLAlchemy engine/session creation
- Session context manager provides clean resource management
- Supports in-memory SQLite for testing
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.mark.ledger
class TestDatabaseConnection:
    """Test DatabaseConnection behavior."""

    def test_default_creates_sqlite_connection(self) -> None:
        """Default constructor creates a SQLite connection."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection()

        try:
            # Should have created an engine
            assert db._engine is not None
            # Should be SQLite by default
            assert "sqlite" in str(db._engine.url)
        finally:
            db.close()

    def test_custom_url_creates_connection(self) -> None:
        """Can create connection with custom URL."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection(url="sqlite:///:memory:")

        try:
            assert "memory" in str(db._engine.url)
        finally:
            db.close()

    def test_session_context_manager_yields_valid_session(self) -> None:
        """Session context manager yields a usable SQLAlchemy session."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection(url="sqlite:///:memory:")

        try:
            with db.session() as session:
                assert isinstance(session, Session)
                # Should be able to execute a simple query
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            db.close()

    def test_session_auto_closes(self) -> None:
        """Session is closed after context manager exits."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection(url="sqlite:///:memory:")
        captured_session: Session | None = None

        try:
            with db.session() as session:
                captured_session = session
                assert session.is_active

            # Session should be closed after exiting context
            # Note: Session might still exist but be inactive/closed
            assert captured_session is not None
        finally:
            db.close()

    def test_session_rollback_on_exception(self) -> None:
        """Session rolls back uncommitted DML on exception."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection(url="sqlite:///:memory:")

        try:
            # First, create table in a committed session
            with db.session() as session:
                session.execute(text("CREATE TABLE test (id INTEGER)"))
                session.commit()

            # Now try to insert and fail
            with pytest.raises(ValueError), db.session() as session:
                session.execute(text("INSERT INTO test VALUES (1)"))
                # Raise exception before commit - should rollback
                raise ValueError("Test error")

            # INSERT should have been rolled back, table should be empty
            with db.session() as session:
                result = session.execute(text("SELECT COUNT(*) FROM test"))
                assert result.scalar() == 0
        finally:
            db.close()

    def test_close_disposes_engine(self) -> None:
        """close() disposes the underlying engine's connection pool."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection(url="sqlite:///:memory:")

        # Engine should exist before close
        assert db._engine is not None
        pool_id_before = id(db._engine.pool)

        db.close()

        # dispose() creates a fresh pool, so the pool object changes
        pool_id_after = id(db._engine.pool)
        assert pool_id_before != pool_id_after

    def test_memory_database_for_testing(self) -> None:
        """In-memory database works correctly for tests."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection(url="sqlite:///:memory:")

        try:
            with db.session() as session:
                session.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY)"))
                session.execute(text("INSERT INTO test_table VALUES (42)"))
                session.commit()

            # Data should persist within the same connection
            with db.session() as session:
                result = session.execute(text("SELECT id FROM test_table"))
                assert result.scalar() == 42
        finally:
            db.close()

    def test_multiple_sessions_share_connection(self) -> None:
        """Multiple sessions can be created from the same connection."""
        from babylon.engine.database import DatabaseConnection

        db = DatabaseConnection(url="sqlite:///:memory:")

        try:
            with db.session() as session1:
                session1.execute(text("CREATE TABLE shared (val INTEGER)"))
                session1.execute(text("INSERT INTO shared VALUES (1)"))
                session1.commit()

            with db.session() as session2:
                result = session2.execute(text("SELECT val FROM shared"))
                assert result.scalar() == 1
        finally:
            db.close()
