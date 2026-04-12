"""Metabolic aggregate derivations (Spec 040 Discipline 2).

These derivations compute ecological/metabolic aggregates from WorldState
primitives. They were previously ``@computed_field`` properties on
WorldState; now they are standalone functions marked ``@derived``.

The WorldState ``@computed_field`` properties remain for backward
compatibility but delegate to these functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.derivations.decorator import derived
from babylon.derivations.registry import DerivedRegistry
from babylon.models.types import Currency

if TYPE_CHECKING:
    from babylon.models.world_state import WorldState

# Module-level registry for metabolic derivations
metabolic_registry = DerivedRegistry()


@derived(name="total_biocapacity", registry=metabolic_registry)
def compute_total_biocapacity(state: WorldState) -> Currency:
    """Global sum of territory biocapacity.

    Args:
        state: Current world state snapshot.

    Returns:
        Sum of biocapacity across all territories.
    """
    return Currency(sum(t.biocapacity for t in state.territories.values()))


@derived(name="total_consumption", registry=metabolic_registry)
def compute_total_consumption(state: WorldState) -> Currency:
    """Global sum of entity consumption needs.

    Args:
        state: Current world state snapshot.

    Returns:
        Sum of consumption_needs across all entities.
    """
    return Currency(sum(e.consumption_needs for e in state.entities.values()))


@derived(name="overshoot_ratio", registry=metabolic_registry)
def compute_overshoot_ratio(state: WorldState) -> float:
    """Global ecological overshoot ratio.

    Args:
        state: Current world state snapshot.

    Returns:
        Ratio of total consumption to total biocapacity.
        Returns 999.0 if biocapacity is zero or negative.
    """
    total_bio = compute_total_biocapacity(state)
    if total_bio <= 0:
        return 999.0
    return float(compute_total_consumption(state) / total_bio)
