"""Tests for rent differential calculator (Feature 038, US4).

Feature: 038-unified-class-system
TDD Phase: RED then GREEN

Tests cover:
- T032: RentDifferentialResult model validation
- T033: compute_differential tests (positive sign, suppressed, SETTLER self=0)
- T034: compute_county_aggregate tests (employment-weighted, all-suppressed, Wayne>=Oakland)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.tensor import NoDataSentinel
from babylon.models.enums import CommunityType
from tests.constants import ClassSystemDefaults

CS = ClassSystemDefaults()


class TestRentDifferentialResult:
    """T032: RentDifferentialResult model validation."""

    @pytest.mark.unit
    def test_valid_result(self) -> None:
        """Valid RentDifferentialResult creates without error."""
        from babylon.economics.melt.rent_differential import RentDifferentialResult

        result = RentDifferentialResult(
            fips="26163",
            nation=CommunityType.NEW_AFRIKAN,
            year=2022,
            differential=5000.0,
            naics_count=3,
            suppressed_count=1,
        )
        assert result.fips == "26163"
        assert result.differential == 5000.0
        assert result.naics_count == 3
        assert result.suppressed_count == 1

    @pytest.mark.unit
    def test_frozen_immutability(self) -> None:
        """RentDifferentialResult must be frozen."""
        from babylon.economics.melt.rent_differential import RentDifferentialResult

        result = RentDifferentialResult(
            fips="26163",
            nation=CommunityType.NEW_AFRIKAN,
            year=2022,
            differential=5000.0,
            naics_count=3,
            suppressed_count=0,
        )
        with pytest.raises(ValidationError):
            result.differential = 0.0  # type: ignore[misc]

    @pytest.mark.unit
    def test_fips_pattern(self) -> None:
        """FIPS must be a 5-digit string."""
        from babylon.economics.melt.rent_differential import RentDifferentialResult

        result = RentDifferentialResult(
            fips="26163",
            nation=CommunityType.NEW_AFRIKAN,
            year=2022,
            differential=5000.0,
            naics_count=1,
            suppressed_count=0,
        )
        assert len(result.fips) == 5

    @pytest.mark.unit
    def test_naics_plus_suppressed_positive(self) -> None:
        """naics_count + suppressed_count must be > 0."""
        from babylon.economics.melt.rent_differential import RentDifferentialResult

        with pytest.raises(ValidationError):
            RentDifferentialResult(
                fips="26163",
                nation=CommunityType.NEW_AFRIKAN,
                year=2022,
                differential=0.0,
                naics_count=0,
                suppressed_count=0,
            )


class TestComputeDifferential:
    """T033: compute_differential tests."""

    @pytest.mark.unit
    def test_positive_differential(self) -> None:
        """BC-016: Settler earnings > nation earnings -> positive result."""
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        result = calc.compute_differential(CS.WAYNE_FIPS, CommunityType.NEW_AFRIKAN, "31-33", 2022)
        assert not isinstance(result, NoDataSentinel)
        assert result > 0.0

    @pytest.mark.unit
    def test_suppressed_returns_sentinel(self) -> None:
        """BC-015: Suppressed ACS data returns NoDataSentinel."""
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        # Use a NAICS code that doesn't exist in mock data
        result = calc.compute_differential(CS.WAYNE_FIPS, CommunityType.NEW_AFRIKAN, "99", 2022)
        assert isinstance(result, NoDataSentinel)

    @pytest.mark.unit
    def test_settler_self_differential_zero(self) -> None:
        """BC-019: SETTLER vs SETTLER = 0.0 (no differential)."""
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        result = calc.compute_differential(CS.WAYNE_FIPS, CommunityType.SETTLER, "31-33", 2022)
        assert not isinstance(result, NoDataSentinel)
        assert result == 0.0

    @pytest.mark.unit
    def test_unknown_fips_returns_sentinel(self) -> None:
        """Unknown FIPS code returns NoDataSentinel."""
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        result = calc.compute_differential("99999", CommunityType.NEW_AFRIKAN, "31-33", 2022)
        assert isinstance(result, NoDataSentinel)


class TestComputeCountyAggregate:
    """T034: compute_county_aggregate tests."""

    @pytest.mark.unit
    def test_employment_weighted(self) -> None:
        """BC-017: Employment-weighted average across NAICS codes."""
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        result = calc.compute_county_aggregate(CS.WAYNE_FIPS, CommunityType.NEW_AFRIKAN, 2022)
        assert not isinstance(result, NoDataSentinel)
        assert result > 0.0

    @pytest.mark.unit
    def test_all_suppressed_returns_sentinel(self) -> None:
        """BC-018: All NAICS suppressed returns NoDataSentinel."""
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        # Use unknown FIPS where no NAICS data exists
        result = calc.compute_county_aggregate("99999", CommunityType.NEW_AFRIKAN, 2022)
        assert isinstance(result, NoDataSentinel)

    @pytest.mark.unit
    def test_wayne_ge_oakland(self) -> None:
        """BC-020: Wayne County differential >= Oakland County differential.

        Internal colony thesis: wage gap is wider where extractive
        relationship is most direct (urban core vs suburbs).
        """
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        wayne = calc.compute_county_aggregate(CS.WAYNE_FIPS, CommunityType.NEW_AFRIKAN, 2022)
        oakland = calc.compute_county_aggregate(CS.OAKLAND_FIPS, CommunityType.NEW_AFRIKAN, 2022)
        assert not isinstance(wayne, NoDataSentinel)
        assert not isinstance(oakland, NoDataSentinel)
        assert wayne >= oakland

    @pytest.mark.unit
    def test_settler_aggregate_zero(self) -> None:
        """SETTLER county aggregate is always 0.0."""
        from babylon.economics.melt.rent_differential import (
            DefaultRentDifferentialCalculator,
        )

        calc = DefaultRentDifferentialCalculator()
        result = calc.compute_county_aggregate(CS.WAYNE_FIPS, CommunityType.SETTLER, 2022)
        assert not isinstance(result, NoDataSentinel)
        assert result == 0.0
