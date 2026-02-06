"""Crisis amplification for class dynamics transition rates.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

Implements FR-009: Multiplicative amplifier on transition rates during crisis.
Downward rates (dispossession, precaritization) multiplied by crisis_amplifier,
upward rates (accumulation, stabilization) multiplied by recovery_dampener.

Default factors calibrated from peak-to-stable-year rate ratios
(research.md §5): crisis_amplifier=2.5, recovery_dampener=0.3.

See Also:
    :mod:`babylon.economics.dynamics.data_sources`: CrisisAmplifier protocol
    ``specs/016-class-dynamics-engine/research.md``: Section 5
"""

from __future__ import annotations

from babylon.economics.dynamics.types import TransitionRates

# Default amplification factors (research.md §5)
_DEFAULT_CRISIS_AMPLIFIER: float = 2.5
_DEFAULT_RECOVERY_DAMPENER: float = 0.3


class DefaultCrisisAmplifier:
    """Default crisis amplification implementation.

    During crisis (``crisis=True``), downward transition rates are multiplied
    by ``crisis_amplifier`` and upward rates by ``recovery_dampener``.
    Non-crisis periods are passthrough.

    All amplified rates are clamped to [0, 1].

    Args:
        crisis_amplifier: Multiplier for downward rates. Default 2.5.
        recovery_dampener: Multiplier for upward rates. Default 0.3.

    Example:
        >>> amp = DefaultCrisisAmplifier()
        >>> amplified = amp.amplify(rates, crisis=True)
        >>> amplified.dispossession  # 2.5x base rate
    """

    def __init__(
        self,
        crisis_amplifier: float = _DEFAULT_CRISIS_AMPLIFIER,
        recovery_dampener: float = _DEFAULT_RECOVERY_DAMPENER,
    ) -> None:
        """Initialize with amplification factors.

        Args:
            crisis_amplifier: Multiplier for downward rates during crisis.
            recovery_dampener: Multiplier for upward rates during crisis.
        """
        self._crisis_amplifier = crisis_amplifier
        self._recovery_dampener = recovery_dampener

    def amplify(
        self,
        rates: TransitionRates,
        crisis: bool,
    ) -> TransitionRates:
        """Amplify transition rates during crisis periods.

        Args:
            rates: Base transition rates.
            crisis: True if crisis conditions active.

        Returns:
            Amplified TransitionRates (passthrough if not crisis).
        """
        if not crisis:
            return rates

        return TransitionRates(
            fips=rates.fips,
            year=rates.year,
            dispossession=min(rates.dispossession * self._crisis_amplifier, 1.0),
            accumulation=min(rates.accumulation * self._recovery_dampener, 1.0),
            precaritization=min(rates.precaritization * self._crisis_amplifier, 1.0),
            stabilization=min(rates.stabilization * self._recovery_dampener, 1.0),
        )


__all__ = ["DefaultCrisisAmplifier"]
