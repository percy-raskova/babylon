import os
import random
import shutil
import tempfile
import time
from collections.abc import Generator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from babylon.config.testing import TestingConfig
from babylon.data.database import Base
from babylon.metrics.collector import MetricsCollector

# Import all models to ensure they're registered with SQLAlchemy


@pytest.fixture(autouse=True)
def _isolate_random_state() -> Generator[None, None, None]:
    """Isolate random state between tests to prevent pollution.

    Tests calling random.seed() (e.g., George Floyd Dynamic tests)
    won't affect subsequent tests. Each test starts with the random
    state it inherited, and that state is restored after the test.
    """
    saved_state = random.getstate()
    try:
        yield
    finally:
        random.setstate(saved_state)


@pytest.fixture(scope="session")
def test_dir():
    """Create a temporary directory for all tests."""
    temp_dir = tempfile.mkdtemp()
    os.chmod(temp_dir, 0o755)
    yield temp_dir
    time.sleep(0.1)  # Allow OS to release handles
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_db():
    """Create a test database."""
    # Create test engine with SQLite in-memory database
    engine = create_engine(TestingConfig.DATABASE_URL)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Override the SessionLocal in the database module
    import babylon.data.database

    babylon.data.database.SessionLocal = TestingSessionLocal

    return engine


@pytest.fixture(scope="function")
def metrics_collector(_test_db: Engine) -> MetricsCollector:
    """Create a fresh metrics collector for each test."""
    return MetricsCollector()
