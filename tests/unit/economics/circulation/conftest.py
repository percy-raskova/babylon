"""Shared test fixtures for Capital Volume II circulation tests.

Feature: 023-capital-volume-ii

Provides DomainFactory helpers and pytest fixtures for creating
test instances of circulation types with sensible defaults.
"""

from __future__ import annotations

import pytest

from babylon.economics.tensor import DepartmentRow
from babylon.models.types import Currency, LaborHours

# =============================================================================
# DOMAIN FACTORY DEFAULTS
# =============================================================================


@pytest.fixture
def sample_dept_i() -> DepartmentRow:
    """Department I (Means of Production) — standard test values."""
    return DepartmentRow(
        c=LaborHours(200.0),
        v=LaborHours(100.0),
        s=LaborHours(100.0),
    )


@pytest.fixture
def sample_dept_iia() -> DepartmentRow:
    """Department IIa (Necessary Consumption) — standard test values."""
    return DepartmentRow(
        c=LaborHours(150.0),
        v=LaborHours(75.0),
        s=LaborHours(75.0),
    )


@pytest.fixture
def sample_dept_iib() -> DepartmentRow:
    """Department IIb (Luxury Consumption) — standard test values."""
    return DepartmentRow(
        c=LaborHours(50.0),
        v=LaborHours(25.0),
        s=LaborHours(25.0),
    )


@pytest.fixture
def sample_dept_iii() -> DepartmentRow:
    """Department III (Social Reproduction) — standard test values."""
    return DepartmentRow(
        c=LaborHours(80.0),
        v=LaborHours(60.0),
        s=LaborHours(60.0),
    )


# =============================================================================
# CONSTANTS FOR TEST SCENARIOS
# =============================================================================

WAYNE_COUNTY_FIPS = "26163"
TEST_YEAR = 2022
DEFAULT_TOTAL_CAPITAL = Currency(100.0)
