"""Tests for rent/types.py honesty markers.

Feature: 024-capital-volume-iii
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.rent.types import RentCategory

pytestmark = pytest.mark.unit


class TestRentCategoryDormantMarker:
    """Honesty sweep (U2, Row N): RentCategory has zero behavioral
    consumers — RentExtraction carries the three categories as discrete
    named fields, never keyed by this enum. Documented as dormant rather
    than silently rotting."""

    def test_docstring_declares_dormant(self) -> None:
        doc = RentCategory.__doc__ or ""
        assert "DORMANT" in doc

    def test_enum_values_unchanged(self) -> None:
        assert RentCategory.AGRICULTURAL == "agricultural"
        assert RentCategory.RESOURCE == "resource"
        assert RentCategory.URBAN == "urban"
