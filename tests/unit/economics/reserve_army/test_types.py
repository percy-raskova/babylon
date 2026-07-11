"""Tests for ReserveArmyState and ReserveArmyDynamics models (Feature 021, US1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.economics.reserve_army.types import ReserveArmyDynamics, ReserveArmyState


class TestReserveArmyState:
    """Tests for ReserveArmyState frozen Pydantic model."""

    def test_basic_construction(self) -> None:
        """State constructs with valid inputs."""
        state = ReserveArmyState(
            fips_code="26163",
            year=2010,
            floating_reserve=5000,
            latent_reserve=3000,
            stagnant_reserve=2000,
            pauperized=1000,
            labor_force=100000,
        )
        assert state.fips_code == "26163"
        assert state.floating_reserve == 5000

    def test_total_reserve_excludes_pauperized(self) -> None:
        """Total reserve is floating + latent + stagnant (no pauperized per Marx)."""
        state = ReserveArmyState(
            fips_code="26163",
            year=2010,
            floating_reserve=5000,
            latent_reserve=3000,
            stagnant_reserve=2000,
            pauperized=1000,
            labor_force=100000,
        )
        assert state.total_reserve == 10000  # 5000 + 3000 + 2000

    def test_reserve_ratio_computation(self) -> None:
        """Reserve ratio is total_reserve / labor_force."""
        state = ReserveArmyState(
            fips_code="26163",
            year=2010,
            floating_reserve=5000,
            latent_reserve=3000,
            stagnant_reserve=2000,
            pauperized=1000,
            labor_force=100000,
        )
        assert state.reserve_ratio == pytest.approx(0.10)

    def test_reserve_ratio_clamped_at_one(self) -> None:
        """Reserve ratio cannot exceed 1.0."""
        state = ReserveArmyState(
            fips_code="26163",
            year=2010,
            floating_reserve=60000,
            latent_reserve=30000,
            stagnant_reserve=20000,
            pauperized=0,
            labor_force=100000,
        )
        # total_reserve = 110000, ratio = 1.1, clamped to 1.0
        assert state.reserve_ratio == 1.0

    def test_zero_reserves(self) -> None:
        """All zero reserves produce zero ratio."""
        state = ReserveArmyState(
            fips_code="26163",
            year=2010,
            floating_reserve=0,
            latent_reserve=0,
            stagnant_reserve=0,
            pauperized=0,
            labor_force=100000,
        )
        assert state.total_reserve == 0
        assert state.reserve_ratio == 0.0

    def test_frozen_immutability(self) -> None:
        """State is frozen (immutable)."""
        state = ReserveArmyState(
            fips_code="26163",
            year=2010,
            floating_reserve=5000,
            latent_reserve=3000,
            stagnant_reserve=2000,
            pauperized=1000,
            labor_force=100000,
        )
        with pytest.raises(ValidationError):
            state.floating_reserve = 9999  # type: ignore[misc]

    def test_labor_force_must_be_positive(self) -> None:
        """Labor force must be > 0."""
        with pytest.raises(ValidationError):
            ReserveArmyState(
                fips_code="26163",
                year=2010,
                floating_reserve=0,
                latent_reserve=0,
                stagnant_reserve=0,
                pauperized=0,
                labor_force=0,
            )

    def test_negative_reserve_rejected(self) -> None:
        """Negative reserve values are rejected."""
        with pytest.raises(ValidationError):
            ReserveArmyState(
                fips_code="26163",
                year=2010,
                floating_reserve=-1,
                latent_reserve=0,
                stagnant_reserve=0,
                pauperized=0,
                labor_force=100000,
            )

    def test_fips_length_validation(self) -> None:
        """FIPS code must be exactly 5 characters."""
        with pytest.raises(ValidationError):
            ReserveArmyState(
                fips_code="2616",  # Too short
                year=2010,
                floating_reserve=0,
                latent_reserve=0,
                stagnant_reserve=0,
                pauperized=0,
                labor_force=100000,
            )


class TestReserveArmyDynamics:
    """Tests for ReserveArmyDynamics frozen Pydantic model."""

    def test_basic_construction(self) -> None:
        """Dynamics constructs with valid inputs."""
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=5,
            mechanization_displacement=500,
            firm_failures=200,
            expansion_absorption=300,
            emigration=100,
        )
        assert dynamics.mechanization_displacement == 500

    def test_net_inflow_positive(self) -> None:
        """Net inflow is positive when inflows exceed outflows."""
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=5,
            mechanization_displacement=500,
            firm_failures=200,
            expansion_absorption=100,
            emigration=50,
        )
        assert dynamics.net_inflow == 550  # (500+200) - (100+50)

    def test_net_inflow_negative(self) -> None:
        """Net inflow is negative when outflows exceed inflows (absorption)."""
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=5,
            mechanization_displacement=100,
            firm_failures=50,
            expansion_absorption=300,
            emigration=100,
        )
        assert dynamics.net_inflow == -250  # (100+50) - (300+100)

    def test_net_inflow_zero(self) -> None:
        """Net inflow is zero when inflows equal outflows."""
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=5,
            mechanization_displacement=200,
            firm_failures=100,
            expansion_absorption=200,
            emigration=100,
        )
        assert dynamics.net_inflow == 0

    def test_frozen_immutability(self) -> None:
        """Dynamics is frozen (immutable)."""
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=5,
            mechanization_displacement=500,
            firm_failures=200,
            expansion_absorption=300,
            emigration=100,
        )
        with pytest.raises(ValidationError):
            dynamics.tick = 10  # type: ignore[misc]
