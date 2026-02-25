"""Tests for WorkingDayState model (Feature 021, US3)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.working_day.types import WorkingDayState


class TestWorkingDayState:
    """Tests for WorkingDayState frozen Pydantic model."""

    def test_basic_construction(self) -> None:
        """State constructs with valid inputs."""
        state = WorkingDayState(
            fips_code="26163",
            naics_sector="31",
            year=2019,
            avg_weekly_hours=42.5,
            labor_intensity_index=1.15,
        )
        assert state.avg_weekly_hours == 42.5
        assert state.labor_intensity_index == 1.15

    def test_frozen_immutability(self) -> None:
        """State is frozen (immutable)."""
        state = WorkingDayState(
            fips_code="26163",
            naics_sector="31",
            year=2019,
            avg_weekly_hours=42.5,
            labor_intensity_index=1.15,
        )
        with pytest.raises(ValidationError):
            state.avg_weekly_hours = 50.0  # type: ignore[misc]

    def test_hours_zero_valid(self) -> None:
        """Zero hours is valid (sector shutdown)."""
        state = WorkingDayState(
            fips_code="26163",
            naics_sector="31",
            year=2019,
            avg_weekly_hours=0.0,
            labor_intensity_index=1.0,
        )
        assert state.avg_weekly_hours == 0.0

    def test_hours_exceeding_168_rejected(self) -> None:
        """Hours above 168 (24*7) are rejected."""
        with pytest.raises(ValidationError):
            WorkingDayState(
                fips_code="26163",
                naics_sector="31",
                year=2019,
                avg_weekly_hours=169.0,
                labor_intensity_index=1.0,
            )

    def test_intensity_must_be_positive(self) -> None:
        """Labor intensity must be > 0."""
        with pytest.raises(ValidationError):
            WorkingDayState(
                fips_code="26163",
                naics_sector="31",
                year=2019,
                avg_weekly_hours=40.0,
                labor_intensity_index=0.0,
            )

    def test_naics_sector_length(self) -> None:
        """NAICS sector must be exactly 2 characters."""
        with pytest.raises(ValidationError):
            WorkingDayState(
                fips_code="26163",
                naics_sector="3",  # Too short
                year=2019,
                avg_weekly_hours=40.0,
                labor_intensity_index=1.0,
            )

    def test_negative_hours_rejected(self) -> None:
        """Negative hours are rejected."""
        with pytest.raises(ValidationError):
            WorkingDayState(
                fips_code="26163",
                naics_sector="31",
                year=2019,
                avg_weekly_hours=-1.0,
                labor_intensity_index=1.0,
            )
