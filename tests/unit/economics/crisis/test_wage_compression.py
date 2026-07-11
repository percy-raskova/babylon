"""Tests for wage compression during deep crisis.

Feature: 018-crisis-devaluation-mechanics
Tasks: T056-T062

Tests wage compression and accumulation halt during deep crisis:
- US5 AS1: Deep crisis reduces wages by 2% per period
- US5 AS2: Accumulation halts when wages fall below subsistence floor
- US5 AS3: Crisis trap - stable equilibrium without external shock
- Cumulative wage compression tracking in CrisisState
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.types import (
    CountyEconomicState,
    CrisisPhase,
    CrisisState,
)


def _make_county(
    fips: str = "26163",
    year: int = 2015,
    median_wage: float = 25.0,
    phase: CrisisPhase = CrisisPhase.DEEP,
    crisis_duration: int = 6,
    cumulative_wage_compression: float = 0.0,
) -> CountyEconomicState:
    """Build a county state for wage compression tests.

    Args:
        fips: County FIPS code.
        year: Year for the county state.
        median_wage: Hourly median wage.
        phase: Crisis phase.
        crisis_duration: Crisis duration in periods.
        cumulative_wage_compression: Previously applied compression.
    """
    from babylon.domain.economics.dynamics.types import ClassDistribution

    dist = ClassDistribution(
        fips=fips,
        year=year,
        bourgeoisie_share=0.01,
        petit_bourgeoisie_share=0.09,
        labor_aristocracy_share=0.35,
        proletariat_share=0.40,
        lumpenproletariat_share=0.15,
    )
    crisis_state = CrisisState(
        phase=phase,
        consecutive_below=6,
        consecutive_recovery=0,
        crisis_start_period=3,
        crisis_duration=crisis_duration,
        peak_severity=0.03,
        cumulative_wage_compression=cumulative_wage_compression,
    )
    return CountyEconomicState(
        fips=fips,
        year=year,
        capital_stock=1_000_000_000.0,
        throughput_position=0.90,
        supply_chain_depth=2.1,
        unemployment_rate=0.08,
        u6_rate=0.12,
        pter_rate=0.04,
        nilf_rate=0.06,
        median_wage=median_wage,
        employment=350000.0,
        phi_hour=3.50,
        crisis_state=crisis_state,
        class_distribution=dist,
    )


# =============================================================================
# T056: US5 AS1 - Deep crisis reduces wages by 2% per period
# =============================================================================


@pytest.mark.unit
class TestWageCompression:
    """US5 AS1: Deep crisis reduces wages proportionally per period."""

    def test_deep_crisis_compresses_wage(self) -> None:
        """One DEEP period reduces median_wage by wage_compression_rate."""
        from babylon.domain.economics.crisis.wage_compression import apply_wage_compression

        county = _make_county(median_wage=25.0, phase=CrisisPhase.DEEP)
        rate = 0.02  # 2% per period

        result = apply_wage_compression(county, rate)

        assert result.median_wage == pytest.approx(25.0 * (1 - 0.02))
        assert result.crisis_state.cumulative_wage_compression == pytest.approx(0.02)

    def test_multiple_periods_compound(self) -> None:
        """Wage compression compounds over multiple DEEP periods."""
        from babylon.domain.economics.crisis.wage_compression import apply_wage_compression

        county = _make_county(
            median_wage=25.0,
            phase=CrisisPhase.DEEP,
            cumulative_wage_compression=0.0,
        )
        rate = 0.02

        # Apply 4 quarterly periods (one annual step)
        current = county
        for _ in range(4):
            current = apply_wage_compression(current, rate)

        # 25.0 * (1 - 0.02)^4 = 25.0 * 0.92236816
        expected_wage = 25.0 * (1 - 0.02) ** 4
        assert current.median_wage == pytest.approx(expected_wage, rel=1e-6)

        # Cumulative compression: 1 - (1 - 0.02)^4
        expected_cumulative = 1.0 - (1 - 0.02) ** 4
        assert current.crisis_state.cumulative_wage_compression == pytest.approx(
            expected_cumulative, rel=1e-6
        )

    def test_non_deep_phase_no_compression(self) -> None:
        """ONSET, EARLY, and RECOVERY do not apply wage compression."""
        from babylon.domain.economics.crisis.wage_compression import apply_wage_compression

        for phase in [CrisisPhase.ONSET, CrisisPhase.EARLY, CrisisPhase.RECOVERY]:
            county = _make_county(median_wage=25.0, phase=phase)
            result = apply_wage_compression(county, 0.02)
            assert result.median_wage == pytest.approx(25.0)
            assert result.crisis_state.cumulative_wage_compression == 0.0

    def test_normal_phase_no_compression(self) -> None:
        """NORMAL phase is passthrough."""
        from babylon.domain.economics.crisis.wage_compression import apply_wage_compression

        county = _make_county(median_wage=25.0, phase=CrisisPhase.NORMAL)
        # Override crisis_state to NORMAL
        county = county.model_copy(update={"crisis_state": CrisisState.normal()})
        result = apply_wage_compression(county, 0.02)
        assert result.median_wage == pytest.approx(25.0)


# =============================================================================
# T057: US5 AS2 - Accumulation halts when wages below subsistence floor
# =============================================================================


@pytest.mark.unit
class TestAccumulationHalt:
    """US5 AS2: Wages below subsistence floor halt upward mobility."""

    def test_wages_below_floor_flags_accumulation_halt(self) -> None:
        """When compressed wage < floor_ratio * subsistence, accumulation should halt."""
        from babylon.domain.economics.crisis.wage_compression import (
            should_halt_accumulation,
        )

        # subsistence = 12.0 $/hr, floor_ratio = 0.8 -> floor = 9.6
        assert should_halt_accumulation(wage=9.0, subsistence=12.0, floor_ratio=0.8)

    def test_wages_above_floor_allows_accumulation(self) -> None:
        """Wages above the floor allow normal accumulation."""
        from babylon.domain.economics.crisis.wage_compression import (
            should_halt_accumulation,
        )

        assert not should_halt_accumulation(wage=15.0, subsistence=12.0, floor_ratio=0.8)

    def test_wages_at_floor_boundary(self) -> None:
        """Wages exactly at the floor do not halt accumulation."""
        from babylon.domain.economics.crisis.wage_compression import (
            should_halt_accumulation,
        )

        floor = 12.0 * 0.8  # 9.6
        assert not should_halt_accumulation(wage=floor, subsistence=12.0, floor_ratio=0.8)

    def test_sustained_compression_eventually_halts(self) -> None:
        """Enough DEEP periods compress wages below the floor."""
        from babylon.domain.economics.crisis.wage_compression import (
            apply_wage_compression,
            should_halt_accumulation,
        )

        # Start at 12.0 (subsistence level), floor_ratio=0.8 -> floor=9.6
        county = _make_county(median_wage=12.0, phase=CrisisPhase.DEEP)
        rate = 0.02
        subsistence = 12.0
        floor_ratio = 0.8

        # How many periods to drop below 9.6?
        # 12.0 * (1-0.02)^n < 9.6 -> n > ln(0.8)/ln(0.98) ~= 11.04
        current = county
        for _ in range(12):
            current = apply_wage_compression(current, rate)

        assert should_halt_accumulation(current.median_wage, subsistence, floor_ratio)


# =============================================================================
# T058: US5 AS3 - Crisis trap: stable equilibrium
# =============================================================================


@pytest.mark.unit
class TestCrisisTrap:
    """US5 AS3: Crisis trap - crisis persists as stable equilibrium."""

    def test_compressed_wages_sustain_crisis(self) -> None:
        """Once wages are compressed, crisis conditions self-sustain.

        The crisis trap: deep crisis -> wage compression -> accumulation halt ->
        no recovery of class composition -> conditions remain below threshold.
        """
        from babylon.domain.economics.crisis.wage_compression import (
            apply_wage_compression,
            should_halt_accumulation,
        )

        county = _make_county(median_wage=15.0, phase=CrisisPhase.DEEP)
        rate = 0.02
        subsistence = 12.0
        floor_ratio = 0.8

        # Run 20 DEEP periods (5 annual steps)
        current = county
        wages_over_time: list[float] = [current.median_wage]

        for _ in range(20):
            current = apply_wage_compression(current, rate)
            wages_over_time.append(current.median_wage)

        # Wages should monotonically decrease
        for i in range(1, len(wages_over_time)):
            assert wages_over_time[i] < wages_over_time[i - 1]

        # After 20 periods: 15.0 * (1-0.02)^20 = 15.0 * 0.6676... = ~10.01
        # Floor = 9.6. At 20 periods, not yet halted (10.01 > 9.6).
        expected_wage = 15.0 * (1 - 0.02) ** 20
        assert not should_halt_accumulation(current.median_wage, subsistence, floor_ratio)
        assert current.median_wage == pytest.approx(expected_wage, rel=1e-6)

        # Cumulative compression tracks correctly
        expected_compression = 1.0 - (1 - 0.02) ** 20
        assert current.crisis_state.cumulative_wage_compression == pytest.approx(
            expected_compression, rel=1e-6
        )

    def test_crisis_trap_accumulation_rate_near_zero(self) -> None:
        """SC-006: Deep crisis produces accumulation rate near zero.

        After sufficient compression, accumulation should effectively halt.
        """
        from babylon.domain.economics.crisis.wage_compression import (
            apply_wage_compression,
            should_halt_accumulation,
        )

        # Start at $15/hr, subsistence at $12/hr, floor at $9.6/hr
        county = _make_county(median_wage=15.0, phase=CrisisPhase.DEEP)
        rate = 0.02
        subsistence = 12.0
        floor_ratio = 0.8

        # 15 * 0.98^n < 9.6 -> n > ln(9.6/15)/ln(0.98) ~= 22.2
        current = county
        for _ in range(25):
            current = apply_wage_compression(current, rate)

        assert should_halt_accumulation(current.median_wage, subsistence, floor_ratio)


# =============================================================================
# T059: Cumulative wage compression tracking
# =============================================================================


@pytest.mark.unit
class TestCumulativeWageCompressionTracking:
    """CrisisState.cumulative_wage_compression tracking invariants."""

    def test_starts_at_zero(self) -> None:
        """Normal crisis state has zero cumulative compression."""
        normal = CrisisState.normal()
        assert normal.cumulative_wage_compression == 0.0

    def test_only_increases_during_deep(self) -> None:
        """Compression only accumulates during DEEP phase."""
        from babylon.domain.economics.crisis.wage_compression import apply_wage_compression

        county = _make_county(median_wage=25.0, phase=CrisisPhase.DEEP)
        result = apply_wage_compression(county, 0.02)
        assert result.crisis_state.cumulative_wage_compression > 0.0

    def test_preserved_during_non_deep(self) -> None:
        """Previously accumulated compression is preserved (not reset) in non-DEEP."""
        from babylon.domain.economics.crisis.wage_compression import apply_wage_compression

        # County with existing compression but now in RECOVERY
        county = _make_county(
            median_wage=20.0,
            phase=CrisisPhase.RECOVERY,
            cumulative_wage_compression=0.10,
        )
        result = apply_wage_compression(county, 0.02)

        # Should preserve existing compression, not increase it
        assert result.crisis_state.cumulative_wage_compression == 0.10

    def test_cumulative_bounded_by_one(self) -> None:
        """Cumulative wage compression never exceeds 1.0."""
        from babylon.domain.economics.crisis.wage_compression import apply_wage_compression

        # Start with 95% compression already applied
        county = _make_county(
            median_wage=1.0,
            phase=CrisisPhase.DEEP,
            cumulative_wage_compression=0.95,
        )
        result = apply_wage_compression(county, 0.10)

        assert result.crisis_state.cumulative_wage_compression <= 1.0
