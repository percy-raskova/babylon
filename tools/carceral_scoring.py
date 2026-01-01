#!/usr/bin/env python3
"""Carceral Equilibrium scoring for parameter optimization.

Scores simulations based on phase transition timing and terminal outcome,
aligned with the 70-year trajectory in ai-docs/carceral-equilibrium.md.

The Carceral Equilibrium trajectory describes the inevitable progression
of late-stage imperialism through seven phases:

1. Imperial Extraction (Years 0-20)
2. Peripheral Revolt (Years 15-25)
3. Superwage Crisis (Years 20-30)
4. Carceral Turn (Years 25-40)
5. Control Ratio Crisis (Years 35-50)
6. Genocide Phase (Years 45-65)
7. Stable Necropolis (Years 60-70+)

This module provides scoring functions that reward simulations exhibiting
phase transitions within these theoretically expected windows.

See Also:
    ai-docs/carceral-equilibrium.md: Full theory specification
    ai-docs/theory.md: MLM-TW foundation
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.models.enums import EventType

# =============================================================================
# CONSTANTS
# =============================================================================

TICKS_PER_YEAR: Final[int] = 52
"""Simulation ticks per year (1 tick = 1 week)."""


# =============================================================================
# PHASE WINDOW DEFINITIONS
# =============================================================================


@dataclass(frozen=True)
class PhaseWindow:
    """Expected timing window for a Carceral Equilibrium phase transition.

    Attributes:
        name: Human-readable phase name (matches milestone dict keys)
        event_type: The EventType that signals this phase transition
        earliest_year: Beginning of acceptable window (full credit)
        latest_year: End of acceptable window (full credit)
        weight: Scoring weight (0-1), all weights should sum to 1.0
    """

    name: str
    event_type: EventType
    earliest_year: int
    latest_year: int
    weight: float


# Phase windows based on ai-docs/carceral-equilibrium.md
# Windows are slightly wider than the theoretical ranges to allow for
# parameter variation while still rewarding correct sequencing.
PHASE_WINDOWS: Final[tuple[PhaseWindow, ...]] = (
    PhaseWindow(
        name="superwage_crisis",
        event_type=EventType.SUPERWAGE_CRISIS,
        earliest_year=20,
        latest_year=40,
        weight=0.25,
    ),
    PhaseWindow(
        name="class_decomposition",
        event_type=EventType.CLASS_DECOMPOSITION,
        earliest_year=25,
        latest_year=50,
        weight=0.25,
    ),
    PhaseWindow(
        name="control_ratio_crisis",
        event_type=EventType.CONTROL_RATIO_CRISIS,
        earliest_year=35,
        latest_year=60,
        weight=0.25,
    ),
    PhaseWindow(
        name="terminal_decision",
        event_type=EventType.TERMINAL_DECISION,
        earliest_year=45,
        latest_year=100,
        weight=0.25,
    ),
)


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================


def calculate_timing_score(
    tick: int,
    window: PhaseWindow,
    max_years: float,
) -> float:
    """Calculate timing score for a single phase transition.

    Args:
        tick: The simulation tick when the phase occurred
        window: The PhaseWindow defining expected timing
        max_years: Maximum simulation length in years

    Returns:
        Score from 0.0 to 1.0:
        - 1.0 if phase occurred within expected window
        - Linear decay if early (from 0 at tick 0 to 1.0 at earliest_year)
        - Linear decay if late (from 1.0 at latest_year to 0 at max_years)
    """
    year = tick / TICKS_PER_YEAR

    if window.earliest_year <= year <= window.latest_year:
        # Within expected window: full credit
        return 1.0
    elif year < window.earliest_year:
        # Early: linear decay from 0 at year 0 to 1.0 at earliest_year
        if window.earliest_year == 0:
            return 1.0
        return max(0.0, year / window.earliest_year)
    else:
        # Late: linear decay from 1.0 at latest_year to 0 at max_years
        remaining = max_years - window.latest_year
        if remaining <= 0:
            return 0.0
        return max(0.0, 1.0 - (year - window.latest_year) / remaining)


def calculate_carceral_equilibrium_score(
    phase_milestones: dict[str, int | None],
    terminal_outcome: str | None,
    max_ticks: int,
) -> float:
    """Score a simulation run based on Carceral Equilibrium phase timing.

    This is the main objective function for parameter optimization. It rewards
    simulations that exhibit the theoretically correct phase transition sequence
    within expected timing windows.

    Args:
        phase_milestones: Dict mapping phase name -> tick when occurred.
            Keys should match PhaseWindow.name values.
            None indicates the phase never occurred.
        terminal_outcome: The outcome of TERMINAL_DECISION event:
            - "revolution": Workers organized, overthrew system
            - "genocide": Atomized surplus population eliminated
            - None: Terminal decision never reached
        max_ticks: Total simulation length in ticks

    Returns:
        Score from 0.0 (no phases occurred) to 100.0 (perfect trajectory).

    Scoring Formula:
        - Each phase contributes up to (weight * 100) points
        - Full points if phase occurs within expected window
        - Partial points if early/late (linear decay)
        - Zero points if phase never occurs
        - 10% bonus for revolutionary outcome
        - 10% penalty for genocide outcome

    Example:
        >>> milestones = {
        ...     "superwage_crisis": 1300,      # Year 25 (in window)
        ...     "class_decomposition": 1820,   # Year 35 (in window)
        ...     "control_ratio_crisis": 2340,  # Year 45 (in window)
        ...     "terminal_decision": 2860,     # Year 55 (in window)
        ... }
        >>> score = calculate_carceral_equilibrium_score(
        ...     milestones, "revolution", max_ticks=5200
        ... )
        >>> score  # Near 100 due to perfect timing + revolution bonus
    """
    score = 0.0
    max_years = max_ticks / TICKS_PER_YEAR

    for window in PHASE_WINDOWS:
        tick = phase_milestones.get(window.name)
        if tick is None:
            # Phase never occurred: 0 points for this phase
            continue

        timing_score = calculate_timing_score(tick, window, max_years)
        score += timing_score * window.weight * 100

    # Terminal outcome modifiers
    if terminal_outcome == "revolution":
        score *= 1.1  # 10% bonus for revolutionary outcome
    elif terminal_outcome == "genocide":
        score *= 0.9  # 10% penalty for genocide (still valid trajectory)

    return min(100.0, score)


def format_phase_report(
    phase_milestones: dict[str, int | None],
    terminal_outcome: str | None,
    max_ticks: int,
) -> str:
    """Format a human-readable report of phase timing and scoring.

    Args:
        phase_milestones: Dict mapping phase name -> tick
        terminal_outcome: "revolution", "genocide", or None
        max_ticks: Total simulation length

    Returns:
        Multi-line string report suitable for console output
    """
    lines = ["=" * 60, "CARCERAL EQUILIBRIUM PHASE REPORT", "=" * 60, ""]
    max_years = max_ticks / TICKS_PER_YEAR

    for window in PHASE_WINDOWS:
        tick = phase_milestones.get(window.name)
        if tick is None:
            status = "NOT REACHED"
            year_str = "---"
            timing_str = "0.00"
        else:
            year = tick / TICKS_PER_YEAR
            year_str = f"{year:.1f}"
            timing_score = calculate_timing_score(tick, window, max_years)
            timing_str = f"{timing_score:.2f}"
            if window.earliest_year <= year <= window.latest_year:
                status = "IN WINDOW"
            elif year < window.earliest_year:
                status = "EARLY"
            else:
                status = "LATE"

        lines.append(f"{window.name.upper()}")
        lines.append(f"  Expected: Years {window.earliest_year}-{window.latest_year}")
        lines.append(f"  Actual:   Year {year_str} ({status})")
        lines.append(f"  Score:    {timing_str} (weight: {window.weight:.2f})")
        lines.append("")

    # Overall score
    score = calculate_carceral_equilibrium_score(phase_milestones, terminal_outcome, max_ticks)
    lines.append("-" * 60)
    lines.append(f"Terminal Outcome: {terminal_outcome or 'NOT REACHED'}")
    lines.append(f"TOTAL SCORE: {score:.2f} / 100.00")
    lines.append("=" * 60)

    return "\n".join(lines)


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "TICKS_PER_YEAR",
    "PhaseWindow",
    "PHASE_WINDOWS",
    "calculate_timing_score",
    "calculate_carceral_equilibrium_score",
    "format_phase_report",
]
