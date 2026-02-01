"""Shared constants for formula calculations.

These constants are loaded from GameDefines (YAML-first architecture).
The canonical source is src/babylon/data/defines.yaml.
"""

from typing import Final

from babylon.config.defines import GameDefines

# Load defaults from YAML
_DEFINES: Final[GameDefines] = GameDefines.load_default()

# Kahneman-Tversky loss aversion coefficient
# Losses are perceived as 2.25x more impactful than equivalent gains
# Source: GameDefines.behavioral.loss_aversion_lambda
LOSS_AVERSION_COEFFICIENT: Final[float] = _DEFINES.behavioral.loss_aversion_lambda

# Small constant to prevent division by zero
# Source: GameDefines.precision.epsilon
EPSILON: Final[float] = _DEFINES.precision.epsilon
