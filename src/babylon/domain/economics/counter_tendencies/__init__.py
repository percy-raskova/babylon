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
    COUNTER_TENDENCY_WEIGHTS,
    CounterTendencyStrength,
)

__all__: list[str] = [
    # Constants
    "COUNTER_TENDENCY_WEIGHTS",
    # Types
    "CounterTendencyStrength",
    # Protocols
    "CounterTendencyCalculator",
    # Implementations
    "DefaultCounterTendencyCalculator",
]
