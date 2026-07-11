"""Alpha-smoothing for coefficient history in the tick dynamics pipeline.

Feature: 017-simulation-tick-dynamics

Exponential moving average (EMA) smoothing for gamma coefficients.
Update rule: value[t] = value[t-1] + alpha * (raw[t] - value[t-1])
First tick: value[0] = raw[0] (no smoothing applied).

See Also:
    :mod:`babylon.domain.economics.tick.types`: SmoothedCoefficients
    :mod:`babylon.domain.economics.tick.system`: Pipeline integration
"""

from __future__ import annotations


class CoefficientSmoother:
    """Alpha-smooth raw coefficient values over ticks.

    Args:
        alpha: Smoothing parameter in (0, 1]. Larger alpha means faster
            convergence to raw values. Default 0.3.

    Raises:
        ValueError: If alpha is not in (0, 1].

    Example:
        >>> smoother = CoefficientSmoother(alpha=0.3)
        >>> smoother.smooth(raw=0.72, previous=0.68, is_initialized=True)
        0.692
    """

    def __init__(self, alpha: float = 0.3) -> None:
        if alpha <= 0 or alpha > 1:
            msg = f"alpha must be in (0, 1], got {alpha}"
            raise ValueError(msg)
        self.alpha = alpha

    def smooth(
        self,
        raw: float,
        previous: float,
        is_initialized: bool,
    ) -> float:
        """Apply alpha-smoothing to a coefficient value.

        Args:
            raw: Current raw computed value.
            previous: Previous smoothed value.
            is_initialized: False on first tick (raw passthrough).

        Returns:
            Smoothed coefficient value.
        """
        if not is_initialized:
            return raw
        return previous + self.alpha * (raw - previous)


__all__ = ["CoefficientSmoother"]
