# =============================================================================
# MUTMUT COMPATIBILITY PATCH - MUST BE AT VERY TOP BEFORE ANY IMPORTS
# =============================================================================
# mutmut.__main__.py line 978 calls set_start_method('fork') at module import time.
# This conflicts with pytest-asyncio's pre-set multiprocessing context.
# Solution: Make set_start_method idempotent (ignore "already set" errors).
# See: https://github.com/pytorch/pytorch/issues/3492
# ruff: noqa: E402 (imports must come after the multiprocessing patch)
import contextlib
import multiprocessing as _mp

_original_set_start_method = _mp.set_start_method


def _idempotent_set_start_method(method: str | None, force: bool = False) -> None:
    """Wrapper that ignores 'context already set' errors."""
    with contextlib.suppress(RuntimeError):
        _original_set_start_method(method, force=force)


_mp.set_start_method = _idempotent_set_start_method
# =============================================================================
# END MUTMUT PATCH
# =============================================================================

import os
import random
import shutil
import tempfile
import time
from collections.abc import Generator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

# NOTE: babylon imports are done lazily inside fixtures to support mutmut.
# mutmut only copies mutated files to mutants/src/, not the full package.
# Module-level babylon imports would fail during mutation testing.

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from babylon.metrics.collector import MetricsCollector


@pytest.fixture(autouse=True)
def _isolate_random_state() -> Generator[None, None, None]:
    """Isolate random state between tests to prevent pollution.

    Each test starts with a deterministic random seed (42) to ensure
    reproducibility regardless of test ordering. This prevents test
    flakiness from stochastic systems like StruggleSystem's spark check.

    Tests that need specific random behavior can call random.seed()
    themselves; the state will be restored after the test completes.
    """
    saved_state = random.getstate()
    # Seed with deterministic value for reproducibility across test orderings
    random.seed(42)
    try:
        yield
    finally:
        random.setstate(saved_state)


@pytest.fixture(scope="session")
def test_dir() -> Generator[str, None, None]:
    """Create a temporary directory for all tests."""
    temp_dir = tempfile.mkdtemp()
    os.chmod(temp_dir, 0o755)
    yield temp_dir
    time.sleep(0.1)  # Allow OS to release handles
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_db() -> "Engine":
    """Create a test database.

    Imports are done lazily to support mutation testing with mutmut.
    """
    # Lazy imports for mutmut compatibility
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from babylon.config.testing import TestingConfig
    from babylon.data.database import Base

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
def metrics_collector(test_db: "Engine") -> "MetricsCollector":
    """Create a fresh metrics collector for each test.

    Imports are done lazily to support mutation testing with mutmut.
    """
    from babylon.metrics.collector import MetricsCollector

    return MetricsCollector()


# =============================================================================
# MOCK FIXTURES
# =============================================================================
# These fixtures provide standardized mocks following the spec= pattern
# for type safety. See tests/README.md for mock pattern guidelines.
# =============================================================================


@pytest.fixture
def mock_llm_provider() -> MagicMock:
    """Mock LLM provider for narrative tests.

    Uses spec=LLMProvider to ensure mock follows the Protocol interface.
    Any access to undefined attributes/methods will raise AttributeError.

    Returns:
        MagicMock with LLMProvider interface, pre-configured generate().

    Example:
        def test_narrative_uses_llm(mock_llm_provider):
            mock_llm_provider.generate.return_value = "Custom response"
            director = NarrativeDirector(llm=mock_llm_provider)
            assert "Custom" in director.narrate(state)
    """
    # Lazy import for mutmut compatibility
    from babylon.ai.llm_provider import LLMProvider

    mock = MagicMock(spec=LLMProvider)
    mock.name = "MockLLM"
    mock.generate.return_value = "Mock narrative response"
    return mock


@pytest.fixture
def mock_chroma_client() -> MagicMock:
    """Mock ChromaDB client for RAG tests.

    Note: Uses plain MagicMock without spec= because ChromaDB is an external
    library and we don't want strict interface validation for external deps.

    Returns:
        MagicMock with query/add methods configured for typical usage.

    Example:
        def test_vector_store_query(mock_chroma_client):
            mock_chroma_client.query.return_value = {"ids": [["id1"]]}
            store = VectorStore(chroma_client=mock_chroma_client)
            results = store.query_similar(embedding)
    """
    mock = MagicMock()
    mock.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "embeddings": None,
        "metadatas": [[]],
        "distances": [[]],
    }
    mock.add.return_value = None
    mock.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    return mock


@pytest.fixture
def mock_chroma_collection() -> MagicMock:
    """Mock ChromaDB collection for VectorStore tests.

    Pre-configured to return empty results to prevent None subscript errors.

    Returns:
        MagicMock with query/add methods configured.
    """
    mock = MagicMock()
    mock.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "embeddings": None,
        "metadatas": [[]],
        "distances": [[]],
    }
    mock.add.return_value = None
    mock.count.return_value = 0
    return mock


@pytest.fixture
def mock_simulation() -> MagicMock:
    """Mock Simulation for engine tests.

    Uses spec=Simulation to ensure mock follows the Simulation interface.

    Returns:
        MagicMock with Simulation interface.
    """
    # Lazy import for mutmut compatibility
    from babylon.engine.simulation import Simulation

    mock = MagicMock(spec=Simulation)
    mock.tick = 0
    mock.is_running = False
    return mock
