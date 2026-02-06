"""Tests for DefaultTickInitializer.

Feature: 017-simulation-tick-dynamics
Task: T025
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.economics.tick.conftest import (
    WAYNE_FIPS,
    MockBasketVisibilityCalculator,
    MockCapitalStockCalculator,
    MockClassTransitionEngine,
    MockGammaIIICalculator,
    MockImperialRentCalculator,
    MockMELTCalculator,
    MockThroughputCalculator,
)

from babylon.economics.tick.initializer import DefaultTickInitializer
from babylon.economics.tick.types import SimulationTickState
from babylon.engine.services import ServiceContainer


def _make_services(**kwargs: Any) -> ServiceContainer:
    """Create ServiceContainer with mock calculators."""
    defaults = {
        "melt_calculator": MockMELTCalculator(),
        "basket_calculator": MockBasketVisibilityCalculator(),
        "gamma_calculator": MockGammaIIICalculator(),
        "capital_calculator": MockCapitalStockCalculator(),
        "throughput_calculator": MockThroughputCalculator(),
        "transition_engine": MockClassTransitionEngine(),
        "imperial_rent_calculator": MockImperialRentCalculator(),
    }
    defaults.update(kwargs)
    return ServiceContainer.create(**defaults)


class TestDefaultTickInitializer:
    """Tests for DefaultTickInitializer census seeding."""

    def test_initialize_creates_valid_state(self) -> None:
        """Verify initializer creates valid SimulationTickState."""
        initializer = DefaultTickInitializer()
        services = _make_services()
        state = initializer.initialize(
            year=2015,
            county_fips=[WAYNE_FIPS],
            services=services,
        )
        assert isinstance(state, SimulationTickState)
        assert state.year == 2015
        assert WAYNE_FIPS in state.county_states

    def test_initialize_seeds_national_params(self) -> None:
        """Verify national params are seeded from calculators."""
        initializer = DefaultTickInitializer()
        services = _make_services(melt_calculator=MockMELTCalculator(tau=65.0))
        state = initializer.initialize(
            year=2015,
            county_fips=[WAYNE_FIPS],
            services=services,
        )
        assert state.national_params.tau == 65.0

    def test_initialize_seeds_county_state(self) -> None:
        """Verify county state is seeded from calculators."""
        initializer = DefaultTickInitializer()
        services = _make_services(capital_calculator=MockCapitalStockCalculator(k_value=2e9))
        state = initializer.initialize(
            year=2015,
            county_fips=[WAYNE_FIPS],
            services=services,
        )
        assert state.county_states[WAYNE_FIPS].capital_stock == 2e9

    def test_initialize_multiple_counties(self) -> None:
        """Verify initialization works with multiple counties."""
        initializer = DefaultTickInitializer()
        services = _make_services()
        state = initializer.initialize(
            year=2015,
            county_fips=[WAYNE_FIPS, "06037"],  # Wayne + LA County
            services=services,
        )
        assert len(state.county_states) == 2
        assert WAYNE_FIPS in state.county_states
        assert "06037" in state.county_states

    def test_initialize_coefficients_not_initialized(self) -> None:
        """Verify coefficients start as not initialized (FR-027)."""
        initializer = DefaultTickInitializer()
        services = _make_services()
        state = initializer.initialize(
            year=2015,
            county_fips=[WAYNE_FIPS],
            services=services,
        )
        assert state.coefficients.is_initialized is False

    def test_county_set_immutability(self) -> None:
        """Verify county set is fixed after initialization (FR-026).

        Frozen Pydantic model prevents reassigning the county_states attribute.
        """
        initializer = DefaultTickInitializer()
        services = _make_services()
        state = initializer.initialize(
            year=2015,
            county_fips=[WAYNE_FIPS],
            services=services,
        )
        # Frozen model: cannot reassign county_states attribute
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            state.county_states = {}  # type: ignore[misc]

    def test_class_distribution_sums_to_one(self) -> None:
        """Verify initial class distributions sum to one."""
        initializer = DefaultTickInitializer()
        services = _make_services()
        state = initializer.initialize(
            year=2015,
            county_fips=[WAYNE_FIPS],
            services=services,
        )
        dist = state.county_states[WAYNE_FIPS].class_distribution
        total = (
            dist.bourgeoisie_share
            + dist.petit_bourgeoisie_share
            + dist.labor_aristocracy_share
            + dist.proletariat_share
            + dist.lumpenproletariat_share
        )
        assert abs(total - 1.0) < 0.001
