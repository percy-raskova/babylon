"""Tests for HousingValueDecomposition frozen model.

Feature: 024-capital-volume-iii (US4, FR-008, FR-009)
TDD Red Phase: Tests define expected behavior for housing value decomposition.

HousingValueDecomposition: Decomposes housing market price into construction
value, capitalized ground rent, and speculative premium.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.rent.types import HousingValueDecomposition

# =============================================================================
# Frozen Model Invariants
# =============================================================================


@pytest.mark.unit
class TestHousingValueDecompositionFrozen:
    """HousingValueDecomposition model is frozen (immutable)."""

    def test_frozen(self) -> None:
        """Cannot mutate fields after construction."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=30_000.0,
            ground_rent_capitalized=15_000.0,
            speculative_premium=7_000.0,
        )
        with pytest.raises(ValidationError):
            housing.construction_value = 0.0  # type: ignore[misc]


# =============================================================================
# Field Validation
# =============================================================================


@pytest.mark.unit
class TestHousingValueDecompositionValidation:
    """HousingValueDecomposition field constraints."""

    def test_fips_code_length_5(self) -> None:
        """fips_code must be exactly 5 characters."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=30_000.0,
            ground_rent_capitalized=15_000.0,
            speculative_premium=7_000.0,
        )
        assert housing.fips_code == "26163"

    def test_fips_code_too_short_rejected(self) -> None:
        """fips_code shorter than 5 characters is rejected."""
        with pytest.raises(ValidationError):
            HousingValueDecomposition(
                fips_code="2616",
                year=2020,
                construction_value=30_000.0,
                ground_rent_capitalized=15_000.0,
                speculative_premium=7_000.0,
            )

    def test_negative_construction_value_rejected(self) -> None:
        """Negative construction_value is rejected."""
        with pytest.raises(ValidationError):
            HousingValueDecomposition(
                fips_code="26163",
                year=2020,
                construction_value=-1.0,
                ground_rent_capitalized=15_000.0,
                speculative_premium=7_000.0,
            )

    def test_negative_ground_rent_capitalized_rejected(self) -> None:
        """Negative ground_rent_capitalized is rejected."""
        with pytest.raises(ValidationError):
            HousingValueDecomposition(
                fips_code="26163",
                year=2020,
                construction_value=30_000.0,
                ground_rent_capitalized=-1.0,
                speculative_premium=7_000.0,
            )

    def test_negative_speculative_premium_rejected(self) -> None:
        """Negative speculative_premium is rejected."""
        with pytest.raises(ValidationError):
            HousingValueDecomposition(
                fips_code="26163",
                year=2020,
                construction_value=30_000.0,
                ground_rent_capitalized=15_000.0,
                speculative_premium=-1.0,
            )

    def test_zero_values_accepted(self) -> None:
        """All zero values are valid."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=0.0,
            ground_rent_capitalized=0.0,
            speculative_premium=0.0,
        )
        assert housing.market_price == pytest.approx(0.0)


# =============================================================================
# Computed Fields
# =============================================================================


@pytest.mark.unit
class TestHousingValueDecompositionComputed:
    """HousingValueDecomposition computed fields."""

    def test_market_price_sums_components(self) -> None:
        """market_price = construction + rent_cap + speculation."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=30_000.0,
            ground_rent_capitalized=15_000.0,
            speculative_premium=7_000.0,
        )
        assert housing.market_price == pytest.approx(52_000.0)

    def test_fictitious_fraction_normal(self) -> None:
        """fictitious_fraction = (rent_cap + speculation) / market_price."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=30_000.0,
            ground_rent_capitalized=15_000.0,
            speculative_premium=7_000.0,
        )
        expected = (15_000.0 + 7_000.0) / 52_000.0
        assert housing.fictitious_fraction == pytest.approx(expected)

    def test_fictitious_fraction_zero_market_price(self) -> None:
        """Returns 0.0 when market_price is 0 (all components zero)."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=0.0,
            ground_rent_capitalized=0.0,
            speculative_premium=0.0,
        )
        assert housing.fictitious_fraction == pytest.approx(0.0)

    def test_fictitious_fraction_pure_construction(self) -> None:
        """Fictitious fraction is 0.0 when no rent or speculation."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=100_000.0,
            ground_rent_capitalized=0.0,
            speculative_premium=0.0,
        )
        assert housing.fictitious_fraction == pytest.approx(0.0)

    def test_fictitious_fraction_all_speculative(self) -> None:
        """Fictitious fraction approaches 1.0 when construction value is tiny."""
        housing = HousingValueDecomposition(
            fips_code="26163",
            year=2020,
            construction_value=1.0,
            ground_rent_capitalized=500_000.0,
            speculative_premium=499_999.0,
        )
        expected = (500_000.0 + 499_999.0) / (1.0 + 500_000.0 + 499_999.0)
        assert housing.fictitious_fraction == pytest.approx(expected)
        assert housing.fictitious_fraction > 0.99
