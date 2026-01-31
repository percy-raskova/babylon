"""Pytest fixtures for God Mode Dashboard unit tests.

This module provides fixtures for testing dashboard components
including MockSimulation and Qt widget helpers.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from babylon.ui.dashboard.testing import MockSimulation

if TYPE_CHECKING:
    from babylon.models.snapshots import TerritoryState


@pytest.fixture
def mock_simulation() -> MockSimulation:
    """Create a fresh MockSimulation for each test.

    Returns:
        Empty MockSimulation with no territories.
    """
    return MockSimulation()


@pytest.fixture
def mock_simulation_detroit() -> MockSimulation:
    """Create a MockSimulation pre-populated with Detroit territories.

    Returns:
        MockSimulation with Wayne, Oakland, and Macomb counties.
    """
    return MockSimulation.with_detroit_territories()


@pytest.fixture
def wayne_county_territory(mock_simulation_detroit: MockSimulation) -> TerritoryState:
    """Get Wayne County territory from Detroit mock.

    Args:
        mock_simulation_detroit: Detroit mock simulation fixture.

    Returns:
        Wayne County TerritoryState (FIPS 26163).
    """
    territory = mock_simulation_detroit.get_territory_state("26163")
    assert territory is not None
    return territory


@pytest.fixture
def oakland_county_territory(mock_simulation_detroit: MockSimulation) -> TerritoryState:
    """Get Oakland County territory from Detroit mock.

    Args:
        mock_simulation_detroit: Detroit mock simulation fixture.

    Returns:
        Oakland County TerritoryState (FIPS 26125).
    """
    territory = mock_simulation_detroit.get_territory_state("26125")
    assert territory is not None
    return territory


@pytest.fixture
def sample_h3_index() -> str:
    """Provide a valid H3 index for testing.

    Returns:
        Valid 15-character H3 hex string at resolution 5.
        This is a real Detroit H3 index (Wayne County, Downtown Detroit).
    """
    return "852ab2c7fffffff"


@pytest.fixture
def invalid_h3_index() -> str:
    """Provide an invalid H3 index for error testing.

    Returns:
        Invalid H3 string (wrong length).
    """
    return "invalid"


@pytest.fixture
def unclaimed_h3_index() -> str:
    """Provide a valid but unclaimed H3 index for testing.

    Returns:
        Valid H3 string that is not claimed by any territory.
    """
    return "852a1000fffffff"
