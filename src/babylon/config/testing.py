"""Testing configuration for Babylon/Babylon.

Provides isolated configuration for unit and integration tests.
Test environments are ephemeral - created and destroyed with each session.
"""

from pathlib import Path
from typing import Final


class TestingConfig:
    """Configuration for test environments.

    Uses in-memory SQLite and temporary directories to ensure
    test isolation and reproducibility.
    """

    # === Database ===
    DATABASE_URL: Final[str] = "sqlite:///:memory:"
    DB_POOL_SIZE: Final[int] = 1
    DB_MAX_OVERFLOW: Final[int] = 0

    # === Logging ===
    LOG_LEVEL: Final[str] = "DEBUG"
    LOG_DIR: Final[Path] = Path("/tmp/babylon_test_logs")

    # === Metrics ===
    METRICS_ENABLED: Final[bool] = True

    # === ChromaDB ===
    CHROMADB_PERSIST_DIR: Final[str] = "/tmp/babylon_test_chroma"

    # === Flags ===
    TESTING: Final[bool] = True
    DEBUG: Final[bool] = True
