"""Reserve Army wage pressure calculator (Feature 021, FR-002).

Implements the bounded sigmoid mapping from reserve_ratio to wage pressure.
Higher reserve ratios produce stronger downward pressure on wages.
"""

from __future__ import annotations

import math

from babylon.config.defines import ReserveArmyDefines


class DefaultWagePressureCalculator:
    """Computes wage pressure from reserve army ratio using bounded sigmoid.

    The sigmoid function maps reserve_ratio to a wage pressure coefficient
    in [0, ceiling]. The midpoint r0 and steepness k are configurable
    via ReserveArmyDefines.

    Formula:
        raw = 1 / (1 + exp(-k * (reserve_ratio - r0)))
        wage_pressure = ceiling * raw

    Args:
        defines: Configuration with sigmoid_k, sigmoid_r0, wage_pressure_ceiling.
    """

    def __init__(self, defines: ReserveArmyDefines | None = None) -> None:
        self._defines = defines if defines is not None else ReserveArmyDefines()

    def compute_wage_pressure(self, reserve_ratio: float) -> float:
        """Compute wage pressure coefficient from reserve ratio.

        Args:
            reserve_ratio: Fraction of labor force in reserve army, in [0, 1].

        Returns:
            Wage pressure coefficient in [0, ceiling].
        """
        if reserve_ratio <= 0.0:
            return 0.0

        k = self._defines.sigmoid_k
        r0 = self._defines.sigmoid_r0
        ceiling = self._defines.wage_pressure_ceiling

        # Bounded sigmoid: shift so that pressure is ~0 when ratio is near 0
        exponent = -k * (reserve_ratio - r0)
        # Clamp exponent to prevent overflow
        exponent = max(min(exponent, 500.0), -500.0)
        raw = 1.0 / (1.0 + math.exp(exponent))

        # Normalize: subtract sigmoid(0 - r0) so pressure starts near 0
        baseline_exponent = -k * (0.0 - r0)
        baseline_exponent = max(min(baseline_exponent, 500.0), -500.0)
        baseline = 1.0 / (1.0 + math.exp(baseline_exponent))

        # Normalize to [0, ceiling]
        max_raw = 1.0 - baseline
        if max_raw <= 0.0:
            return 0.0

        normalized = (raw - baseline) / max_raw
        return ceiling * max(0.0, min(normalized, 1.0))
