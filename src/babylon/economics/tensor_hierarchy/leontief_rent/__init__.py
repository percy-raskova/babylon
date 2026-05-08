"""Leontief imperial-rent pipeline data sources (Spec 057).

Provides the per-industry periphery wage coefficients, final-demand vector,
and per-county industry-rent allocator that feed into
:func:`babylon.economics.tick.system.imperial_rent.compute`.

See ``specs/057-leontief-rent-integration/`` for the design.
"""

from __future__ import annotations

from babylon.economics.tensor_hierarchy.leontief_rent.final_demand import (
    DefaultFinalDemandSource,
)
from babylon.economics.tensor_hierarchy.leontief_rent.periphery_labor_coefficients import (
    DefaultPeripheryLaborCoefficientsSource,
    PeripheryLaborCoefficientsSource,
    PeripheryWageMetadata,
)

__all__: list[str] = [
    "DefaultFinalDemandSource",
    "DefaultPeripheryLaborCoefficientsSource",
    "PeripheryLaborCoefficientsSource",
    "PeripheryWageMetadata",
]
