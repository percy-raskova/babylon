"""Shared constants for formula calculations.

These constants are loaded from :class:`~babylon.config.defines.GameDefines`.
``GameDefines.load_default()`` reads ``src/babylon/data/defines.yaml`` if
present (optional override) and otherwise returns the dataclass defaults
compiled into ``GameDefines``. The repository ships without the YAML, so
the dataclass defaults are the canonical source today; the YAML is a
calibration override callers may add.
"""

from typing import Final

from babylon.config.defines import GameDefines

# Load defaults: reads src/babylon/data/defines.yaml if present, otherwise
# falls back to the dataclass defaults compiled into GameDefines.
_DEFINES: Final[GameDefines] = GameDefines.load_default()

# Kahneman-Tversky loss aversion coefficient
# Losses are perceived as 2.25x more impactful than equivalent gains
# Source: GameDefines.behavioral.loss_aversion_lambda
LOSS_AVERSION_COEFFICIENT: Final[float] = _DEFINES.behavioral.loss_aversion_lambda

# Small constant to prevent division by zero
# Source: GameDefines.precision.epsilon
EPSILON: Final[float] = _DEFINES.precision.epsilon

# Standard annual full-time work hours (40 h/week x 52 weeks)
# Canonical single source for the ``2080`` constant previously redefined
# ad hoc across the economics modules (throughput, dynamics, gamma, melt,
# leontief_rent). Source: GameDefines.timescale.hours_per_year
HOURS_PER_YEAR: Final[int] = _DEFINES.timescale.hours_per_year

# Weeks per simulation year (weekly tick calendar).
# Canonical single source for the ``52`` constant.
# Source: GameDefines.timescale.weeks_per_year
WEEKS_PER_YEAR: Final[int] = _DEFINES.timescale.weeks_per_year
