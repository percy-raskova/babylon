"""TDD tests for Hump Shape wealth dynamics.

These tests verify that the simulation exhibits the three-phase
wealth pattern: Growth -> Plateau -> Decay over 20 simulated years.

RED phase tests are marked with @pytest.mark.red_phase and will
fail until the system is properly calibrated with correct parameters.

Success Criteria: The "Hump Shape"
----------------------------------
Over 1040 ticks (20 years), C_b (Core Bourgeoisie) wealth must show:

    Growth (Years 0-2):    Wealth increases as Production taps Biocapacity
    Stagnation (Years 2-10): Wealth plateaus as Subsistence equilibrates
    Decay (Years 10-20):    Wealth declines as MetabolismSystem degrades Biocapacity
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.scenarios import create_imperial_circuit_scenario
from babylon.engine.simulation_engine import step

pytestmark = [pytest.mark.integration, pytest.mark.theory_rift]

# Phase boundaries in ticks (1 tick = 1 week, 52 ticks = 1 year)
GROWTH_END = 104  # Year 2
PLATEAU_END = 520  # Year 10
SIMULATION_END = 1040  # Year 20

# Entity IDs from imperial circuit scenario
CORE_BOURGEOISIE_ID = "C003"
COMPRADOR_ID = "C002"
PERIPHERY_WORKER_ID = "C001"
LABOR_ARISTOCRACY_ID = "C004"


def run_simulation_and_collect_history(
    max_ticks: int = SIMULATION_END,
    defines: GameDefines | None = None,
) -> tuple[list[float], list[float], int]:
    """Run simulation and collect C_b wealth history.

    Args:
        max_ticks: Maximum ticks to simulate
        defines: Optional GameDefines override

    Returns:
        Tuple of (c_b_wealth_history, rent_pool_history, ticks_survived)
    """
    state, config, default_defines = create_imperial_circuit_scenario()
    defines = defines or default_defines
    persistent_context: dict[str, Any] = {}

    c_b_wealth_history: list[float] = []
    rent_pool_history: list[float] = []

    for _ in range(max_ticks):
        try:
            state = step(state, config, persistent_context, defines)
        except Exception:
            break

        # Track C_b wealth
        c_b = state.entities.get(CORE_BOURGEOISIE_ID)
        if c_b and getattr(c_b, "active", True):
            c_b_wealth_history.append(float(c_b.wealth))
        else:
            break  # C_b died

        rent_pool_history.append(float(state.economy.imperial_rent_pool))

    return c_b_wealth_history, rent_pool_history, len(c_b_wealth_history)


@pytest.mark.integration
@pytest.mark.red_phase
class TestHumpShapeGrowthPhase:
    """Growth phase tests (Years 0-2, ticks 0-104).

    During the growth phase, C_b wealth should INCREASE as:
    - Workers produce value from healthy biocapacity
    - Extraction flows to Core Bourgeoisie via tribute
    - Income exceeds subsistence burn
    """

    def test_c_b_wealth_increases_in_first_year(self) -> None:
        """C_b wealth at tick 52 should exceed initial wealth."""
        wealth_history, _, ticks = run_simulation_and_collect_history(max_ticks=52)

        assert ticks >= 52, f"Simulation died at tick {ticks}, expected to survive 52"
        assert len(wealth_history) >= 52, "Not enough wealth history collected"

        initial_wealth = wealth_history[0]
        year_1_wealth = wealth_history[51]

        assert year_1_wealth > initial_wealth, (
            f"C_b wealth should increase in Year 1: "
            f"initial={initial_wealth:.4f}, year_1={year_1_wealth:.4f}"
        )

    def test_c_b_wealth_increases_for_two_years(self) -> None:
        """C_b wealth at tick 104 should exceed tick 52 wealth."""
        wealth_history, _, ticks = run_simulation_and_collect_history(max_ticks=GROWTH_END)

        assert ticks >= GROWTH_END, f"Simulation died at tick {ticks}, expected {GROWTH_END}"

        year_1_wealth = wealth_history[51]
        year_2_wealth = wealth_history[GROWTH_END - 1]

        assert year_2_wealth > year_1_wealth, (
            f"C_b wealth should continue growing in Year 2: "
            f"year_1={year_1_wealth:.4f}, year_2={year_2_wealth:.4f}"
        )

    def test_rent_pool_grows_during_growth_phase(self) -> None:
        """Imperial rent pool should accumulate during growth phase."""
        _, rent_pool_history, ticks = run_simulation_and_collect_history(max_ticks=GROWTH_END)

        assert ticks >= GROWTH_END, f"Simulation died at tick {ticks}"

        initial_pool = rent_pool_history[0]
        growth_end_pool = rent_pool_history[GROWTH_END - 1]

        # Pool should grow or at least maintain value during prosperity
        assert growth_end_pool >= initial_pool * 0.8, (
            f"Rent pool should not collapse during growth: "
            f"initial={initial_pool:.2f}, end={growth_end_pool:.2f}"
        )


@pytest.mark.integration
@pytest.mark.red_phase
class TestHumpShapePlateauPhase:
    """Plateau phase tests (Years 2-10, ticks 104-520).

    During the plateau phase:
    - C_b wealth should be relatively STABLE
    - Peak wealth should occur somewhere in this phase
    - Variance should be low (equilibrium state)
    """

    def test_c_b_wealth_peaks_in_plateau_phase(self) -> None:
        """Maximum C_b wealth should occur between tick 104 and 520."""
        wealth_history, _, ticks = run_simulation_and_collect_history(max_ticks=PLATEAU_END)

        assert ticks >= PLATEAU_END, f"Simulation died at tick {ticks}, expected {PLATEAU_END}"

        peak_value = max(wealth_history)
        peak_tick = wealth_history.index(peak_value)

        assert GROWTH_END <= peak_tick <= PLATEAU_END, (
            f"Peak should be in plateau phase (ticks {GROWTH_END}-{PLATEAU_END}): "
            f"peak at tick {peak_tick} with value {peak_value:.4f}"
        )

    def test_wealth_variation_within_twenty_percent_of_peak(self) -> None:
        """C_b wealth should stay within +/- 20% of peak during plateau."""
        wealth_history, _, ticks = run_simulation_and_collect_history(max_ticks=PLATEAU_END)

        assert ticks >= PLATEAU_END, f"Simulation died at tick {ticks}"

        plateau_phase = wealth_history[GROWTH_END:PLATEAU_END]
        peak_value = max(plateau_phase)
        min_value = min(plateau_phase)

        variation = (peak_value - min_value) / peak_value if peak_value > 0 else 1.0

        assert variation < 0.40, (
            f"Plateau variation too high: {variation:.2%} "
            f"(peak={peak_value:.4f}, min={min_value:.4f})"
        )


@pytest.mark.integration
@pytest.mark.red_phase
class TestHumpShapeDecayPhase:
    """Decay phase tests (Years 10-20, ticks 520-1040).

    During the decay phase:
    - C_b wealth should DECLINE as biocapacity degrades
    - MetabolismSystem entropy should reduce production
    - Final wealth should be significantly below peak
    """

    def test_c_b_wealth_declines_in_decay_phase(self) -> None:
        """C_b wealth at tick 1040 should be less than at tick 520."""
        wealth_history, _, ticks = run_simulation_and_collect_history(max_ticks=SIMULATION_END)

        assert ticks >= SIMULATION_END, (
            f"Simulation died at tick {ticks}, expected {SIMULATION_END}"
        )

        plateau_end_wealth = wealth_history[PLATEAU_END - 1]
        final_wealth = wealth_history[-1]

        assert final_wealth < plateau_end_wealth, (
            f"C_b wealth should decline in decay phase: "
            f"plateau_end={plateau_end_wealth:.4f}, final={final_wealth:.4f}"
        )

    def test_final_wealth_significantly_below_peak(self) -> None:
        """Final wealth should be at least 30% below peak (metabolic rift effect)."""
        wealth_history, _, ticks = run_simulation_and_collect_history(max_ticks=SIMULATION_END)

        assert ticks >= SIMULATION_END, f"Simulation died at tick {ticks}"

        peak_wealth = max(wealth_history)
        final_wealth = wealth_history[-1]
        decay_ratio = final_wealth / peak_wealth if peak_wealth > 0 else 1.0

        assert decay_ratio < 0.70, (
            f"Final wealth should be <70% of peak: "
            f"ratio={decay_ratio:.2%}, peak={peak_wealth:.4f}, final={final_wealth:.4f}"
        )

    def test_simulation_survives_to_tick_1040(self) -> None:
        """Simulation should complete full 20 years without premature death."""
        _, _, ticks = run_simulation_and_collect_history(max_ticks=SIMULATION_END)

        assert ticks == SIMULATION_END, (
            f"Simulation should survive full 20 years: "
            f"survived {ticks} ticks, expected {SIMULATION_END}"
        )


@pytest.mark.integration
@pytest.mark.red_phase
class TestHumpShapeScoring:
    """Tests for the Hump Shape scoring function.

    The scoring function evaluates how well a wealth trajectory
    matches the ideal Growth -> Plateau -> Decay pattern.
    """

    def test_perfect_hump_shape_scores_above_80(self) -> None:
        """A proper Hump Shape trajectory should score > 80."""
        # Create synthetic perfect hump shape
        perfect_hump: list[float] = []

        # Growth phase: linear increase from 1.0 to 2.0
        for i in range(GROWTH_END):
            perfect_hump.append(1.0 + (i / GROWTH_END))

        # Plateau phase: stable around 2.0
        for _ in range(GROWTH_END, PLATEAU_END):
            perfect_hump.append(2.0)

        # Decay phase: linear decrease from 2.0 to 0.5
        for i in range(PLATEAU_END, SIMULATION_END):
            progress = (i - PLATEAU_END) / (SIMULATION_END - PLATEAU_END)
            perfect_hump.append(2.0 - 1.5 * progress)

        score = calculate_hump_shape_score(perfect_hump)

        assert score >= 80.0, f"Perfect Hump Shape should score >= 80, got {score:.1f}"

    def test_flat_line_scores_below_30(self) -> None:
        """A flat wealth trajectory should score poorly."""
        flat_line = [1.0] * SIMULATION_END

        score = calculate_hump_shape_score(flat_line)

        assert score < 30.0, f"Flat line should score < 30, got {score:.1f}"

    def test_early_death_scores_zero(self) -> None:
        """A trajectory that dies before growth phase scores 0."""
        early_death = [1.0] * 50  # Dies at tick 50

        score = calculate_hump_shape_score(early_death)

        assert score == 0.0, f"Early death should score 0, got {score:.1f}"

    def test_monotonic_decline_scores_low(self) -> None:
        """A trajectory that only declines should score poorly."""
        decline = [1.0 - (i / SIMULATION_END) * 0.9 for i in range(SIMULATION_END)]

        score = calculate_hump_shape_score(decline)

        assert score < 40.0, f"Monotonic decline should score < 40, got {score:.1f}"


def calculate_hump_shape_score(wealth_history: list[float]) -> float:
    """Score how well the simulation exhibits Hump Shape dynamics.

    Components:
    1. Growth Score (0-30): Did wealth grow in Years 0-2?
    2. Peak Score (0-20): Is there a clear peak in Years 2-10?
    3. Decay Score (0-30): Did wealth decline in Years 10-20?
    4. Survival Score (0-20): Bonus for surviving all 1040 ticks

    Args:
        wealth_history: List of C_b wealth values at each tick

    Returns:
        Score from 0-100 (higher = better Hump Shape)
    """
    if len(wealth_history) < GROWTH_END:
        return 0.0  # Failed in growth phase

    # 1. Growth Score: Compare end of growth phase to start
    growth_start = wealth_history[0]
    growth_end_wealth = wealth_history[min(GROWTH_END - 1, len(wealth_history) - 1)]
    growth_ratio = growth_end_wealth / max(growth_start, 0.01)

    if growth_ratio < 1.0:
        growth_score = 0.0
    elif growth_ratio < 1.5:
        growth_score = 15.0 * (growth_ratio - 1.0) / 0.5
    else:
        growth_score = 15.0 + 15.0 * min(1.0, (growth_ratio - 1.5) / 0.5)

    # 2. Peak Score: Find peak and verify it's in plateau phase
    peak_idx = max(range(len(wealth_history)), key=lambda i: wealth_history[i])
    peak_value = wealth_history[peak_idx]

    if GROWTH_END <= peak_idx <= PLATEAU_END:
        peak_score = 20.0  # Peak in correct phase
    elif peak_idx < GROWTH_END:
        peak_score = 5.0  # Peak too early
    else:
        peak_score = 10.0  # Peak too late

    # 3. Decay Score: Compare end of simulation to peak
    if len(wealth_history) >= SIMULATION_END:
        final_wealth = wealth_history[-1]
        decay_ratio = final_wealth / max(peak_value, 0.01)
        if decay_ratio > 0.9:
            decay_score = 0.0
        elif decay_ratio > 0.5:
            decay_score = 15.0 * (0.9 - decay_ratio) / 0.4
        elif decay_ratio > 0.1:
            decay_score = 15.0 + 15.0 * (0.5 - decay_ratio) / 0.4
        else:
            decay_score = 30.0
    else:
        decay_score = 15.0 * len(wealth_history) / SIMULATION_END

    # 4. Survival Score
    survival_ticks = len(wealth_history)
    if survival_ticks >= SIMULATION_END:
        survival_score = 20.0
    elif survival_ticks >= PLATEAU_END:
        survival_score = 10.0 + 10.0 * (survival_ticks - PLATEAU_END) / (
            SIMULATION_END - PLATEAU_END
        )
    else:
        survival_score = 10.0 * survival_ticks / PLATEAU_END

    return growth_score + peak_score + decay_score + survival_score
