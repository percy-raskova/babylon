"""TRPF counter-tendencies module (Capital Volume III).

Tracks six counter-tendencies to the falling rate of profit and computes
net tendency strength indicator.

See Also:
    :mod:`babylon.domain.economics.crisis`: TRPF crisis mechanics (Feature 018)
    :mod:`babylon.domain.economics.distribution`: Surplus value distribution
"""

from babylon.domain.economics.counter_tendencies.calculator import (
    CounterTendencyCalculator,
    DefaultCounterTendencyCalculator,
)
from babylon.domain.economics.counter_tendencies.types import (
    CounterTendencyStrength,
    counter_tendency_weights,
    imperial_rent_reference_scale,
)

__all__: list[str] = [
    # Coefficient accessors (GameDefines-backed since the 2026-07-18
    # honesty sweep; these are functions, not constants)
    "counter_tendency_weights",
    "imperial_rent_reference_scale",
    # Types
    "CounterTendencyStrength",
    # Protocols
    "CounterTendencyCalculator",
    # Implementations
    "DefaultCounterTendencyCalculator",
]
