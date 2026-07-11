"""Precarity indicator derivation for the tick dynamics pipeline.

Feature: 017-simulation-tick-dynamics

Derives U-6, PTER, and NILF precarity indicators from unemployment rate
and a precaritization rate (typically mapped from lumpenproletariat share).

See Also:
    :mod:`babylon.domain.economics.tick.system`: Pipeline orchestration
    :mod:`babylon.domain.economics.tick.types`: CountyEconomicState
"""

from __future__ import annotations


class PrecarityDeriver:
    """Derive precarity indicators from unemployment and precaritization.

    The handoff rule: lumpenproletariat_share in the class distribution maps
    to a precaritization_rate, encoding the relationship between class
    decomposition and labor market precarity indicators.

    Args:
        pter_fraction: Fraction of precaritization allocated to PTER.
            Default 0.4.
        nilf_fraction: Fraction of precaritization allocated to NILF.
            Default 0.6.

    Example:
        >>> deriver = PrecarityDeriver()
        >>> u6, pter, nilf = deriver.derive(0.05, 0.10)
        >>> round(u6, 2)
        0.15
    """

    def __init__(
        self,
        pter_fraction: float = 0.4,
        nilf_fraction: float = 0.6,
    ) -> None:
        self.pter_fraction = pter_fraction
        self.nilf_fraction = nilf_fraction

    def derive(
        self,
        unemployment_rate: float,
        precaritization_rate: float,
    ) -> tuple[float, float, float]:
        """Derive U-6, PTER, and NILF from inputs.

        Args:
            unemployment_rate: County U-3 unemployment rate.
            precaritization_rate: Rate of labor force precaritization
                (typically lumpenproletariat share).

        Returns:
            Tuple of (u6_rate, pter_rate, nilf_rate), each clamped to [0, 1].
        """
        u6 = min(max(unemployment_rate + precaritization_rate, 0.0), 1.0)
        pter = min(max(precaritization_rate * self.pter_fraction, 0.0), 1.0)
        nilf = min(max(precaritization_rate * self.nilf_fraction, 0.0), 1.0)
        return (u6, pter, nilf)


__all__ = ["PrecarityDeriver"]
