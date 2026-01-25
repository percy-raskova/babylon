"""Unit tests for Territory H3 integration."""

import pytest
from pydantic import ValidationError

from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType


def test_territory_with_h3_index():
    """Test that a Territory can be created with a valid H3 index."""
    # Valid H3 index (resolution 4)
    valid_h3 = "842a107ffffffff"

    territory = Territory(
        id="T001", name="Test Sector", sector_type=SectorType.INDUSTRIAL, h3_index=valid_h3
    )

    assert territory.h3_index == valid_h3


def test_territory_h3_validation():
    """Test that invalid H3 indices are rejected."""
    # Invalid H3 index (too short)
    invalid_h3 = "842a107"

    with pytest.raises(ValidationError) as excinfo:
        Territory(
            id="T002", name="Bad Sector", sector_type=SectorType.INDUSTRIAL, h3_index=invalid_h3
        )

    # Check that the error relates to the pattern
    assert "String should match pattern" in str(excinfo.value)


def test_territory_h3_optional():
    """Test that h3_index is optional."""
    territory = Territory(id="T003", name="Abstract Sector", sector_type=SectorType.RESIDENTIAL)

    assert territory.h3_index is None
