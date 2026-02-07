"""Wage compression during deep crisis periods.

Feature: 018-crisis-devaluation-mechanics (FR-016 through FR-018)

Applies compounding wage compression during DEEP crisis phases and
detects accumulation halt conditions (crisis trap).

Formula (FR-016):
    wage_new = wage_current * (1 - wage_compression_rate)
    cumulative = 1 - (1 - rate)^k  where k = number of DEEP periods

See Also:
    :mod:`babylon.economics.tick.types`: CrisisState, CountyEconomicState
    :mod:`babylon.config.defines`: CrisisDefines (wage_compression_rate)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.economics.tick.types import CrisisPhase

if TYPE_CHECKING:
    from babylon.economics.tick.types import CountyEconomicState


def apply_wage_compression(
    county: CountyEconomicState,
    wage_compression_rate: float,
) -> CountyEconomicState:
    """Apply one period of wage compression if in DEEP crisis.

    Only DEEP crisis phases trigger compression. Other phases pass through
    unchanged, preserving any previously accumulated compression.

    Args:
        county: Current county economic state.
        wage_compression_rate: Per-period compression fraction (e.g. 0.02).

    Returns:
        Updated CountyEconomicState with compressed wage and updated
        CrisisState.cumulative_wage_compression.
    """
    if county.crisis_state.phase != CrisisPhase.DEEP:
        return county

    new_wage = county.median_wage * (1.0 - wage_compression_rate)

    # Update cumulative compression: 1 - (1-existing)*(1-rate)
    prev_cumulative = county.crisis_state.cumulative_wage_compression
    new_cumulative = 1.0 - (1.0 - prev_cumulative) * (1.0 - wage_compression_rate)
    new_cumulative = min(new_cumulative, 1.0)  # Clamp to [0, 1]

    new_crisis_state = county.crisis_state.model_copy(
        update={"cumulative_wage_compression": new_cumulative}
    )

    return county.model_copy(
        update={
            "median_wage": new_wage,
            "crisis_state": new_crisis_state,
        }
    )


def should_halt_accumulation(
    wage: float,
    subsistence: float,
    floor_ratio: float,
) -> bool:
    """Check if wages have fallen below the accumulation halt floor.

    When compressed wages drop below floor_ratio * subsistence, upward
    class transitions (accumulation) should be clamped to zero (FR-017).

    Args:
        wage: Current (compressed) hourly wage.
        subsistence: Subsistence cost per hour (v_reproduction).
        floor_ratio: Floor as fraction of subsistence (default 0.8).

    Returns:
        True if accumulation should halt (wage strictly below floor).
    """
    floor = subsistence * floor_ratio
    return wage < floor


__all__ = ["apply_wage_compression", "should_halt_accumulation"]
