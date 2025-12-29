"""Shared constants for formula calculations.

These constants are used across multiple formula modules.
"""

from typing import Final

# Kahneman-Tversky loss aversion coefficient
# Losses are perceived as 2.25x more impactful than equivalent gains
LOSS_AVERSION_COEFFICIENT: Final[float] = 2.25

# Small constant to prevent division by zero
EPSILON: Final[float] = 1e-6
