"""Integration test fixtures for Django web tests.

These tests require a running PostgreSQL instance.
Set POSTGRES_HOST, POSTGRES_DB, etc. environment variables.

Skip marker: @pytest.mark.requires_postgres
"""

from __future__ import annotations

import os
import uuid

import pytest

# Skip the entire module if PostgreSQL is unavailable
requires_postgres = pytest.mark.requires_postgres


def postgres_available() -> bool:
    """Check if PostgreSQL connection details are configured."""
    return os.environ.get("POSTGRES_HOST", "") != ""


@pytest.fixture
def unique_session_id() -> uuid.UUID:
    """Generate a unique UUID for each test to avoid conflicts."""
    return uuid.uuid4()
