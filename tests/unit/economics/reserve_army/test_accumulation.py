"""Tests for DefaultAccumulationLoopCalculator (Capital Vol I U3).

Feature: 021-capital-volume-i / vol1-value-production U3

Ch. 25 (The General Law of Capitalist Accumulation): a rising organic
composition of capital displaces workers via mechanization; firm failures
(bankruptcy) add a second, independent inflow. The two flows accumulate
into a persistent reserve-army stock per territory; the stock's share of
the labor force (stock / (stock + employment)) is reserve_ratio.
"""

from __future__ import annotations

import math

import pytest

from babylon.config.defines.economy_labor import ReserveArmyDefines
from babylon.domain.economics.reserve_army.accumulation import (
    DefaultAccumulationLoopCalculator,
)
from babylon.domain.economics.reserve_army.types import ReserveArmyDynamics


class TestComputeDynamics:
    """Tests for DefaultAccumulationLoopCalculator.compute_dynamics."""

    def test_no_data_returns_none(self) -> None:
        """No OCC delta and no bankruptcy rate -> honest absence, not zero flow."""
        calc = DefaultAccumulationLoopCalculator()
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=None,
            occ_prior=None,
            bankruptcy_rate=None,
            employment=100_000.0,
        )
        assert result is None

    def test_zero_employment_returns_none(self) -> None:
        """No labor base to displace from -> None regardless of OCC/bankruptcy."""
        calc = DefaultAccumulationLoopCalculator()
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=2.5,
            occ_prior=2.0,
            bankruptcy_rate=0.02,
            employment=0.0,
        )
        assert result is None

    def test_rising_occ_produces_mechanization_displacement(self) -> None:
        """Rising organic composition displaces a fraction of employment."""
        defines = ReserveArmyDefines(mechanization_displacement_rate=0.05)
        calc = DefaultAccumulationLoopCalculator(defines)
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=2.5,
            occ_prior=2.0,
            bankruptcy_rate=None,
            employment=100_000.0,
        )
        assert result is not None
        assert isinstance(result, ReserveArmyDynamics)
        # delta_occ=0.5 * employment=100_000 * rate=0.05 = 2500
        assert result.mechanization_displacement == 2500
        assert result.firm_failures == 0
        assert result.fips_code == "26163"
        assert result.tick == 52

    def test_falling_occ_produces_no_mechanization_displacement(self) -> None:
        """A FALLING organic composition is not a displacement event (Ch. 25 is
        about RISING composition only) — with no bankruptcy data either, the
        whole flow is an honest empty domain."""
        calc = DefaultAccumulationLoopCalculator()
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=2.0,
            occ_prior=2.5,
            bankruptcy_rate=None,
            employment=100_000.0,
        )
        assert result is None

    def test_bankruptcy_produces_firm_failures(self) -> None:
        """A positive bankruptcy rate produces a firm_failures inflow."""
        defines = ReserveArmyDefines(firm_failure_conversion_rate=0.5)
        calc = DefaultAccumulationLoopCalculator(defines)
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=None,
            occ_prior=None,
            bankruptcy_rate=0.02,
            employment=100_000.0,
        )
        assert result is not None
        # bankruptcy_rate=0.02 * employment=100_000 * rate=0.5 = 1000
        assert result.firm_failures == 1000
        assert result.mechanization_displacement == 0

    def test_infinite_occ_ignored(self) -> None:
        """A v=0 tensor's organic_composition is float('inf') — never treated
        as a real delta (Constitution III.11: never fabricate from a
        mathematically-undefined input)."""
        calc = DefaultAccumulationLoopCalculator()
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=float("inf"),
            occ_prior=2.0,
            bankruptcy_rate=None,
            employment=100_000.0,
        )
        assert result is None

    def test_missing_prior_occ_falls_back_to_bankruptcy_only(self) -> None:
        """No prior-year tensor (e.g. campaign's first simulated year) means no
        delta is computable — but bankruptcy-driven firm failures still land."""
        calc = DefaultAccumulationLoopCalculator()
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=2.0,
            occ_prior=None,
            bankruptcy_rate=0.01,
            employment=100_000.0,
        )
        assert result is not None
        assert result.mechanization_displacement == 0
        assert result.firm_failures == 500  # 0.01 * 100_000 * 0.5

    def test_both_flows_combine(self) -> None:
        """Mechanization + firm failures both contribute in the same tick."""
        calc = DefaultAccumulationLoopCalculator()
        result = calc.compute_dynamics(
            fips_code="26163",
            tick=52,
            occ_current=2.5,
            occ_prior=2.0,
            bankruptcy_rate=0.02,
            employment=100_000.0,
        )
        assert result is not None
        assert result.mechanization_displacement == 2500
        assert result.firm_failures == 1000


class TestComputeReserveRatio:
    """Tests for DefaultAccumulationLoopCalculator.compute_reserve_ratio."""

    def test_first_tick_stock_from_zero(self) -> None:
        """Stock starts at 0.0 — a real initial condition, not a fabrication."""
        calc = DefaultAccumulationLoopCalculator()
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=52,
            mechanization_displacement=1000,
            firm_failures=0,
            expansion_absorption=0,
            emigration=0,
        )
        new_stock, ratio = calc.compute_reserve_ratio(
            prior_stock=0.0, dynamics=dynamics, employment=99_000.0
        )
        assert new_stock == pytest.approx(1000.0)
        assert ratio == pytest.approx(1000.0 / 100_000.0)

    def test_stock_accumulates_across_ticks(self) -> None:
        """A carried prior stock accumulates the new tick's net inflow."""
        calc = DefaultAccumulationLoopCalculator()
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=104,
            mechanization_displacement=500,
            firm_failures=0,
            expansion_absorption=0,
            emigration=0,
        )
        new_stock, _ratio = calc.compute_reserve_ratio(
            prior_stock=1000.0, dynamics=dynamics, employment=100_000.0
        )
        assert new_stock == pytest.approx(1500.0)

    def test_stock_floored_at_zero(self) -> None:
        """Net outflow (absorption) cannot drive the stock negative."""
        calc = DefaultAccumulationLoopCalculator()
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=104,
            mechanization_displacement=0,
            firm_failures=0,
            expansion_absorption=500,
            emigration=0,
        )
        new_stock, ratio = calc.compute_reserve_ratio(
            prior_stock=100.0, dynamics=dynamics, employment=100_000.0
        )
        assert new_stock == 0.0
        assert ratio == 0.0

    def test_zero_employment_and_zero_stock_ratio_is_zero(self) -> None:
        """No labor force and no stock -> honestly zero, not a division error."""
        calc = DefaultAccumulationLoopCalculator()
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=104,
            mechanization_displacement=0,
            firm_failures=0,
            expansion_absorption=0,
            emigration=0,
        )
        new_stock, ratio = calc.compute_reserve_ratio(
            prior_stock=0.0, dynamics=dynamics, employment=0.0
        )
        assert new_stock == 0.0
        assert ratio == 0.0

    def test_ratio_never_exceeds_one(self) -> None:
        """Reserve ratio is a fraction of the labor force — never > 1.0."""
        calc = DefaultAccumulationLoopCalculator()
        dynamics = ReserveArmyDynamics(
            fips_code="26163",
            tick=104,
            mechanization_displacement=10_000,
            firm_failures=0,
            expansion_absorption=0,
            emigration=0,
        )
        new_stock, ratio = calc.compute_reserve_ratio(
            prior_stock=0.0, dynamics=dynamics, employment=0.0
        )
        assert new_stock == pytest.approx(10_000.0)
        assert ratio <= 1.0
        assert math.isclose(ratio, 1.0)
