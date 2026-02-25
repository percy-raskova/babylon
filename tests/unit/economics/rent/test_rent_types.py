"""Tests for RentExtraction frozen model.

Feature: 024-capital-volume-iii (US4, FR-007)
TDD Red Phase: Tests define expected behavior for ground rent decomposition.

RentExtraction: Decomposes ground rent into three categories (agricultural,
resource, urban) and provides computed total_rent and rent_share_of_surplus.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.rent.types import RentExtraction

# =============================================================================
# Frozen Model Invariants
# =============================================================================


@pytest.mark.unit
class TestRentExtractionFrozen:
    """RentExtraction model is frozen (immutable)."""

    def test_frozen(self) -> None:
        """Cannot mutate fields after construction."""
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=50_000_000.0,
            resource_rent=10_000_000.0,
            urban_rent=2_400_000_000.0,
        )
        with pytest.raises(ValidationError):
            rent.agricultural_rent = 0.0  # type: ignore[misc]


# =============================================================================
# Field Validation
# =============================================================================


@pytest.mark.unit
class TestRentExtractionValidation:
    """RentExtraction field constraints."""

    def test_fips_code_length_5(self) -> None:
        """fips_code must be exactly 5 characters."""
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=1.0,
            resource_rent=1.0,
            urban_rent=1.0,
        )
        assert rent.fips_code == "26163"

    def test_fips_code_too_short_rejected(self) -> None:
        """fips_code shorter than 5 characters is rejected."""
        with pytest.raises(ValidationError):
            RentExtraction(
                fips_code="2616",
                year=2020,
                agricultural_rent=1.0,
                resource_rent=1.0,
                urban_rent=1.0,
            )

    def test_fips_code_too_long_rejected(self) -> None:
        """fips_code longer than 5 characters is rejected."""
        with pytest.raises(ValidationError):
            RentExtraction(
                fips_code="261630",
                year=2020,
                agricultural_rent=1.0,
                resource_rent=1.0,
                urban_rent=1.0,
            )

    def test_negative_agricultural_rent_rejected(self) -> None:
        """Negative agricultural_rent is rejected."""
        with pytest.raises(ValidationError):
            RentExtraction(
                fips_code="26163",
                year=2020,
                agricultural_rent=-1.0,
                resource_rent=0.0,
                urban_rent=0.0,
            )

    def test_negative_resource_rent_rejected(self) -> None:
        """Negative resource_rent is rejected."""
        with pytest.raises(ValidationError):
            RentExtraction(
                fips_code="26163",
                year=2020,
                agricultural_rent=0.0,
                resource_rent=-1.0,
                urban_rent=0.0,
            )

    def test_negative_urban_rent_rejected(self) -> None:
        """Negative urban_rent is rejected."""
        with pytest.raises(ValidationError):
            RentExtraction(
                fips_code="26163",
                year=2020,
                agricultural_rent=0.0,
                resource_rent=0.0,
                urban_rent=-1.0,
            )

    def test_zero_values_accepted(self) -> None:
        """All zero rent values are valid."""
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=0.0,
            resource_rent=0.0,
            urban_rent=0.0,
        )
        assert rent.total_rent == pytest.approx(0.0)


# =============================================================================
# Computed Fields
# =============================================================================


@pytest.mark.unit
class TestRentExtractionComputed:
    """RentExtraction computed fields."""

    def test_total_rent_sums_three_categories(self) -> None:
        """total_rent = agricultural + resource + urban."""
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=50_000_000.0,
            resource_rent=10_000_000.0,
            urban_rent=2_400_000_000.0,
        )
        expected = 50_000_000.0 + 10_000_000.0 + 2_400_000_000.0
        assert rent.total_rent == pytest.approx(expected)

    def test_rent_share_of_surplus_normal(self) -> None:
        """rent_share_of_surplus = total_rent / total_surplus."""
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=50_000_000.0,
            resource_rent=10_000_000.0,
            urban_rent=2_400_000_000.0,
        )
        total_surplus = 10_000_000_000.0
        expected = rent.total_rent / total_surplus
        assert rent.rent_share_of_surplus(total_surplus) == pytest.approx(expected)

    def test_rent_share_of_surplus_zero_surplus(self) -> None:
        """Returns 0.0 when total_surplus is zero."""
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=50_000_000.0,
            resource_rent=10_000_000.0,
            urban_rent=2_400_000_000.0,
        )
        assert rent.rent_share_of_surplus(0.0) == pytest.approx(0.0)

    def test_rent_share_of_surplus_negative_surplus(self) -> None:
        """Returns 0.0 when total_surplus is negative."""
        rent = RentExtraction(
            fips_code="26163",
            year=2020,
            agricultural_rent=50_000_000.0,
            resource_rent=10_000_000.0,
            urban_rent=2_400_000_000.0,
        )
        assert rent.rent_share_of_surplus(-100.0) == pytest.approx(0.0)
