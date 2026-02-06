"""Tests for wealth accumulation calculator.

Feature: 016-class-dynamics-engine
Task: T014
"""

from __future__ import annotations

import pytest

from babylon.economics.dynamics.accumulation import DefaultAccumulationCalculator
from babylon.economics.dynamics.savings_schedule import DefaultSavingsRateSchedule
from babylon.economics.melt.types import ClassPosition


class TestDefaultAccumulationCalculator:
    """Tests for DefaultAccumulationCalculator per US1 acceptance scenarios."""

    def test_scenario1_standard_accumulation(self) -> None:
        """S1: $60k wage, 15% effective savings -> ~$1,350 accumulation.

        Given a worker with annual wage income of $60,000 and savings rate
        of 15% (test parameter), the annual wealth gain is approximately
        $1,500 (surplus times savings rate).

        Note: Using default schedule rates (LA=12% + phi_adjustment).
        """
        schedule = DefaultSavingsRateSchedule()
        calc = DefaultAccumulationCalculator(schedule)
        result = calc.compute(
            wage=60000.0,
            phi_hour=3.50,
            class_position=ClassPosition.LABOR_ARISTOCRACY,
        )
        assert result.annual_accumulation > 0.0
        assert result.wage == pytest.approx(60000.0)
        # LA base rate 0.12, phi_adjustment ~0.12 -> effective ~0.17
        # consumption = 60000 * (1 - 0.17) = ~49800
        # accumulation = (60000 - 49800) * 0.17 = ~1734
        assert result.annual_accumulation > 1000.0
        assert result.savings_rate > 0.12  # higher than base due to phi

    def test_scenario2_near_subsistence(self) -> None:
        """S2: Near-subsistence wage -> near-zero accumulation.

        Given a worker with wage income near-subsistence, the annual
        wealth gain is near zero regardless of imperial rent benefit.
        """
        schedule = DefaultSavingsRateSchedule()
        calc = DefaultAccumulationCalculator(schedule)
        result = calc.compute(
            wage=15000.0,  # near minimum wage
            phi_hour=1.0,
            class_position=ClassPosition.PROLETARIAT,
        )
        # Proletariat base rate = 0.03, small phi adjustment
        # Very low savings rate means near-zero accumulation
        assert result.annual_accumulation >= 0.0
        assert result.annual_accumulation < 500.0  # small amount

    def test_scenario3_phi_comparison(self) -> None:
        """S3: Worker with phi subsidy accumulates faster than without.

        Given a worker with imperial rent subsidy, when comparing to
        an identical worker without subsidy, the subsidized worker
        accumulates faster.
        """
        schedule = DefaultSavingsRateSchedule()
        calc = DefaultAccumulationCalculator(schedule)

        with_phi = calc.compute(
            wage=50000.0,
            phi_hour=5.0,
            class_position=ClassPosition.PROLETARIAT,
        )
        without_phi = calc.compute(
            wage=50000.0,
            phi_hour=0.0,
            class_position=ClassPosition.PROLETARIAT,
        )
        assert with_phi.annual_accumulation > without_phi.annual_accumulation
        assert with_phi.phi_adjustment > 0.0
        assert without_phi.phi_adjustment == pytest.approx(0.0)

    def test_scenario4_zero_wage_guard(self) -> None:
        """S4: Zero wage produces zero accumulation (no crash).

        Given a worker with zero wage, the system handles gracefully
        with zero accumulation and zero phi_adjustment.
        """
        schedule = DefaultSavingsRateSchedule()
        calc = DefaultAccumulationCalculator(schedule)
        result = calc.compute(
            wage=0.0,
            phi_hour=3.50,
            class_position=ClassPosition.LUMPENPROLETARIAT,
        )
        assert result.annual_accumulation == pytest.approx(0.0)
        assert result.phi_adjustment == pytest.approx(0.0)
        assert result.consumption == pytest.approx(0.0)
        assert result.years_to_threshold is None

    def test_years_to_threshold_positive_accumulation(self) -> None:
        """Positive accumulation calculates years to wealth threshold."""
        schedule = DefaultSavingsRateSchedule()
        calc = DefaultAccumulationCalculator(schedule, wealth_threshold=142000.0)
        result = calc.compute(
            wage=60000.0,
            phi_hour=3.50,
            class_position=ClassPosition.LABOR_ARISTOCRACY,
        )
        assert result.years_to_threshold is not None
        assert result.years_to_threshold > 0.0

    def test_years_to_threshold_zero_accumulation(self) -> None:
        """Zero accumulation returns None for years_to_threshold."""
        schedule = DefaultSavingsRateSchedule()
        calc = DefaultAccumulationCalculator(schedule)
        result = calc.compute(
            wage=0.0,
            phi_hour=0.0,
            class_position=ClassPosition.LUMPENPROLETARIAT,
        )
        assert result.years_to_threshold is None

    def test_lumpenproletariat_zero_savings(self) -> None:
        """Lumpenproletariat has 0% savings rate -> zero accumulation."""
        schedule = DefaultSavingsRateSchedule()
        calc = DefaultAccumulationCalculator(schedule)
        result = calc.compute(
            wage=20000.0,
            phi_hour=0.0,
            class_position=ClassPosition.LUMPENPROLETARIAT,
        )
        assert result.savings_rate == pytest.approx(0.0)
        assert result.annual_accumulation == pytest.approx(0.0)

    def test_protocol_compliance(self) -> None:
        """DefaultAccumulationCalculator satisfies AccumulationCalculator protocol."""
        from babylon.economics.dynamics.data_sources import AccumulationCalculator

        schedule = DefaultSavingsRateSchedule()
        calc: AccumulationCalculator = DefaultAccumulationCalculator(schedule)
        result = calc.compute(
            wage=50000.0,
            phi_hour=0.0,
            class_position=ClassPosition.PROLETARIAT,
        )
        assert result.annual_accumulation >= 0.0
