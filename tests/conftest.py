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

import logging
import os
import random
import shutil
import tempfile
import time
from collections.abc import Generator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from hypothesis import HealthCheck, settings

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

# Register a Hypothesis profile for mutmut runs.
# mutmut executes tests from a different executor context, which triggers
# Hypothesis's differing_executors health check (false positive).
settings.register_profile(
    "mutmut",
    suppress_health_check=[HealthCheck.differing_executors],
)

# Spec 053: register `default` and `slow` profiles here (project-wide) so
# `HYPOTHESIS_PROFILE=slow pytest …` resolves before the per-package
# conftest in tests/property/conftest.py runs. Registration must precede
# `load_profile` below.
settings.register_profile(
    "default",
    max_examples=100,
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "slow",
    max_examples=500,
    derandomize=False,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# Activate the requested profile (mutmut/slow/default/etc).
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))

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


@pytest.fixture(autouse=True)
def enable_logging_propagation() -> Generator[None, None, None]:
    """Ensure caplog catches babylon logs despite Django settings disabling propagation."""
    logger = logging.getLogger("babylon")
    old_propagate = logger.propagate
    logger.propagate = True
    yield
    logger.propagate = old_propagate


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
    """Create a test database with reference schema.

    Imports are done lazily to support mutation testing with mutmut.
    """
    from sqlalchemy import create_engine

    from babylon.reference.database import NormalizedBase

    engine = create_engine("sqlite:///:memory:")
    NormalizedBase.metadata.create_all(bind=engine)

    return engine


@pytest.fixture(scope="function")
def metrics_collector() -> "MetricsCollector":
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


# =============================================================================
# PYTEST-QT FIXTURES (Feature 007: God Mode Dashboard)
# =============================================================================


@pytest.fixture(scope="session")
def qapp_args() -> list[str]:
    """Arguments passed to QApplication for pytest-qt.

    Returns:
        List of command-line arguments for QApplication initialization.
    """
    return ["--platform", "offscreen"]


@pytest.fixture
def qtbot_headless(qapp_args: list[str], qtbot):  # type: ignore[no-untyped-def]
    """Qt test helper configured for headless operation.

    This wraps the standard pytest-qt qtbot fixture with headless configuration.
    Use this for testing Qt widgets without a display.

    Args:
        qapp_args: QApplication arguments (injected).
        qtbot: Standard pytest-qt bot fixture (injected).

    Returns:
        The qtbot fixture, configured for headless operation.
    """
    return qtbot


# =============================================================================
# DJANGO DB SETUP — exclude externally-managed postgres alias
# =============================================================================
# tests/integration/web/conftest.py registers an ephemeral testcontainers
# Postgres as the "postgres" Django alias and runs its own migration/DDL
# pipeline against it. pytest-django's stock ``django_db_setup`` (used by
# every test outside ``tests/integration/web/``) would otherwise also try
# to create a test database for the postgres alias and fail because
# testcontainers already created it. Filtering "postgres" out here lets
# the integration override own its lifecycle while leaving the default
# SQLite setup untouched for unit tests.


@pytest.fixture(scope="session")
def django_db_setup(  # type: ignore[no-untyped-def]
    request: pytest.FixtureRequest,
    django_test_environment: None,  # noqa: ARG001
    django_db_blocker,
    django_db_use_migrations: bool,
    django_db_keepdb: bool,
    django_db_createdb: bool,
    django_db_modify_db_settings: None,  # noqa: ARG001
) -> Generator[None, None, None]:
    """Replicate pytest-django's default ``django_db_setup`` but skip the
    externally-managed ``"postgres"`` alias.

    Identical to ``pytest_django.fixtures.django_db_setup`` except
    ``"postgres"`` is removed from the alias set passed to
    ``setup_databases``. The integration ``conftest.py`` under
    ``tests/integration/web/`` overrides this fixture for tests in that
    directory and handles postgres setup itself.
    """
    from django.test.utils import setup_databases, teardown_databases
    from pytest_django.fixtures import _disable_migrations, _get_databases_for_setup

    setup_databases_args: dict[str, object] = {}

    if not django_db_use_migrations:
        _disable_migrations()

    if django_db_keepdb and not django_db_createdb:
        setup_databases_args["keepdb"] = True

    aliases, serialized_aliases = _get_databases_for_setup(request.session.items)

    aliases = {a for a in aliases if a != "postgres"}
    serialized_aliases = {a for a in serialized_aliases if a != "postgres"}

    with django_db_blocker.unblock():
        db_cfg = setup_databases(
            verbosity=request.config.option.verbose,
            interactive=False,
            aliases=aliases,
            serialized_aliases=serialized_aliases,
            **setup_databases_args,
        )

    yield

    if not django_db_keepdb:
        with django_db_blocker.unblock():
            try:
                teardown_databases(db_cfg, verbosity=request.config.option.verbose)
            except Exception as exc:  # noqa: BLE001
                request.node.warn(
                    pytest.PytestWarning(f"Error when trying to teardown test databases: {exc!r}")
                )


# =============================================================================
# POSTGRES FIXTURES (Feature 037: PostgreSQL Runtime Database)
# =============================================================================


@pytest.fixture(scope="session")
def pg_dsn() -> str:
    """PostgreSQL DSN for integration tests.

    Reads from BABYLON_TEST_PG_DSN env var or defaults to localhost.
    """
    return os.environ.get(
        "BABYLON_TEST_PG_DSN",
        "dbname=babylon_test host=localhost",
    )


@pytest.fixture(scope="session")
def pg_pool(pg_dsn: str) -> Generator["ConnectionPool", None, None]:
    """Session-scoped connection pool for Postgres integration tests.

    Skips all tests requiring Postgres if the database is unavailable.
    """
    from psycopg import OperationalError
    from psycopg_pool import ConnectionPool

    try:
        pool = ConnectionPool(conninfo=pg_dsn, min_size=1, max_size=4, open=True)
        # Verify the connection is actually usable
        with pool.connection() as conn:
            conn.execute("SELECT 1")
    except (OperationalError, OSError):
        pytest.skip("PostgreSQL not available (set BABYLON_TEST_PG_DSN)")
        return  # unreachable, but satisfies type checker

    yield pool
    pool.close()
