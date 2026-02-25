"""Tests for DispossessionEvent and TerritoryDispossessionState (Feature 021, US2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.dispossession.types import (
    DispossessionEvent,
    TerritoryDispossessionState,
)
from babylon.models.enums import DispossessionType, SocialRole


class TestDispossessionEvent:
    """Tests for DispossessionEvent frozen Pydantic model."""

    def test_basic_construction(self) -> None:
        """Event constructs with valid inputs."""
        event = DispossessionEvent(
            fips_code="26163",
            tick=5,
            dispossession_type=DispossessionType.FORECLOSURE,
            event_count=150,
            total_value_transferred=5_000_000.0,
            affected_class=SocialRole.LABOR_ARISTOCRACY,
            receiving_category="institutional_investor",
        )
        assert event.dispossession_type == DispossessionType.FORECLOSURE
        assert event.event_count == 150

    def test_all_dispossession_types(self) -> None:
        """All 8 dispossession types are valid."""
        for dtype in DispossessionType:
            event = DispossessionEvent(
                fips_code="26163",
                tick=0,
                dispossession_type=dtype,
                event_count=1,
                total_value_transferred=100.0,
                affected_class=SocialRole.LABOR_ARISTOCRACY,
                receiving_category="state",
            )
            assert event.dispossession_type == dtype

    def test_frozen_immutability(self) -> None:
        """Event is frozen (immutable)."""
        event = DispossessionEvent(
            fips_code="26163",
            tick=5,
            dispossession_type=DispossessionType.EVICTION,
            event_count=50,
            total_value_transferred=100_000.0,
            affected_class=SocialRole.INTERNAL_PROLETARIAT,
            receiving_category="landlord",
        )
        with pytest.raises(ValidationError):
            event.event_count = 999  # type: ignore[misc]

    def test_negative_value_rejected(self) -> None:
        """Negative value transferred is rejected."""
        with pytest.raises(ValidationError):
            DispossessionEvent(
                fips_code="26163",
                tick=5,
                dispossession_type=DispossessionType.FORECLOSURE,
                event_count=1,
                total_value_transferred=-100.0,
                affected_class=SocialRole.LABOR_ARISTOCRACY,
                receiving_category="bank",
            )

    def test_negative_count_rejected(self) -> None:
        """Negative event count is rejected."""
        with pytest.raises(ValidationError):
            DispossessionEvent(
                fips_code="26163",
                tick=5,
                dispossession_type=DispossessionType.FORECLOSURE,
                event_count=-1,
                total_value_transferred=100.0,
                affected_class=SocialRole.LABOR_ARISTOCRACY,
                receiving_category="bank",
            )

    def test_zero_event_count_valid(self) -> None:
        """Zero event count is valid (no events this tick)."""
        event = DispossessionEvent(
            fips_code="26163",
            tick=5,
            dispossession_type=DispossessionType.FORECLOSURE,
            event_count=0,
            total_value_transferred=0.0,
            affected_class=SocialRole.LABOR_ARISTOCRACY,
            receiving_category="none",
        )
        assert event.event_count == 0


class TestTerritoryDispossessionState:
    """Tests for TerritoryDispossessionState frozen Pydantic model."""

    def test_basic_construction(self) -> None:
        """State constructs with valid inputs."""
        state = TerritoryDispossessionState(
            fips_code="26163",
            year=2010,
            foreclosure_rate=0.05,
            eviction_rate=0.03,
            displacement_rate=0.02,
            concentrated_ownership=0.15,
            absentee_landlord_share=0.20,
        )
        assert state.foreclosure_rate == 0.05

    def test_all_zero_rates(self) -> None:
        """All zero rates is valid (no dispossession activity)."""
        state = TerritoryDispossessionState(
            fips_code="26163",
            year=2010,
            foreclosure_rate=0.0,
            eviction_rate=0.0,
            displacement_rate=0.0,
            concentrated_ownership=0.0,
            absentee_landlord_share=0.0,
        )
        assert state.foreclosure_rate == 0.0

    def test_rate_exceeding_one_rejected(self) -> None:
        """Rates above 1.0 are rejected."""
        with pytest.raises(ValidationError):
            TerritoryDispossessionState(
                fips_code="26163",
                year=2010,
                foreclosure_rate=1.5,
                eviction_rate=0.0,
                displacement_rate=0.0,
                concentrated_ownership=0.0,
                absentee_landlord_share=0.0,
            )

    def test_frozen_immutability(self) -> None:
        """State is frozen (immutable)."""
        state = TerritoryDispossessionState(
            fips_code="26163",
            year=2010,
            foreclosure_rate=0.05,
            eviction_rate=0.03,
            displacement_rate=0.02,
            concentrated_ownership=0.15,
            absentee_landlord_share=0.20,
        )
        with pytest.raises(ValidationError):
            state.foreclosure_rate = 0.99  # type: ignore[misc]
