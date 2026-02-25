"""Inventory tracking and realization crisis detection.

Feature: 023-capital-volume-ii
User Story: US5 - Inventory & Realization (FR-015, FR-016, FR-017)

Functions:
    - compute_realization_metrics: Construct a RealizationCrisis assessment
    - detect_realization_crisis: Trend-based crisis detection from time series

The realization problem is central to Marx's analysis: commodities produced
must be sold (realized) to complete the circuit M-C-P-C'-M'. When effective
demand fails to absorb production, the C'-M' phase stalls and crisis ensues.

See Also:
    :class:`babylon.economics.circulation.types.RealizationCrisis`: Data model
    :class:`babylon.economics.circulation.types.InventoryState`: Inventory tracking
"""

from __future__ import annotations

from babylon.economics.circulation.types import (
    InventoryState,
    RealizationCrisis,
)
from babylon.models.types import Currency


def compute_realization_metrics(
    value_produced: Currency,
    value_realized: Currency,
    fips_code: str,
    year: int,
) -> RealizationCrisis:
    """Compute realization gap, rate, and severity.

    Constructs a :class:`RealizationCrisis` model whose computed fields
    derive realization_gap, realization_rate, and crisis_severity from
    the produced/realized values.

    Args:
        value_produced: Total value of commodities produced (C').
        value_realized: Total value actually sold/realized (M').
        fips_code: 5-digit county FIPS code.
        year: Calendar year.

    Returns:
        RealizationCrisis with computed gap, rate, and severity.
    """
    return RealizationCrisis(
        fips_code=fips_code,
        year=year,
        commodity_value_produced=value_produced,
        commodity_value_realized=value_realized,
    )


def detect_realization_crisis(
    inventory_trend: list[InventoryState],
    production_trend: list[Currency],
) -> bool:
    """Detect realization crisis from inventory and production trends.

    A realization crisis is indicated when finished goods inventory is
    rising while production is flat or falling. This signals that the
    market cannot absorb what is being produced.

    Compares the first and last elements of each trend series.

    Args:
        inventory_trend: Time-ordered list of InventoryState snapshots.
        production_trend: Time-ordered list of production values (Currency).

    Returns:
        True if finished goods are rising AND production is flat or falling.
        False if either list has fewer than 2 elements.
    """
    min_data_points = 2
    if len(inventory_trend) < min_data_points or len(production_trend) < min_data_points:
        return False

    first_inventory = inventory_trend[0].finished_goods
    last_inventory = inventory_trend[-1].finished_goods
    inventory_rising = last_inventory > first_inventory

    first_production = production_trend[0]
    last_production = production_trend[-1]
    production_flat_or_falling = last_production <= first_production

    return inventory_rising and production_flat_or_falling


__all__ = [
    "compute_realization_metrics",
    "detect_realization_crisis",
]
