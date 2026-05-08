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
