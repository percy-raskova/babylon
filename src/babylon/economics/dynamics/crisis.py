"""Crisis amplification for class dynamics transition rates.

Feature: 016-class-dynamics-engine (DefaultCrisisAmplifier)
Feature: 018-crisis-devaluation-mechanics (PhasedCrisisAmplifier)

DefaultCrisisAmplifier: Legacy flat multiplier (Feature 016, FR-009).
PhasedCrisisAmplifier: Phase-dependent multipliers (Feature 018, FR-006).

See Also:
    :mod:`babylon.economics.dynamics.data_sources`: CrisisAmplifier protocol
    :mod:`babylon.economics.tick.types`: CrisisPhase, PhasedAmplificationProfile
"""

from __future__ import annotations

from babylon.economics.dynamics.types import TransitionRates
from babylon.economics.tick.types import CrisisPhase, PhasedAmplificationProfile

# Default amplification factors (research.md §5)
_DEFAULT_CRISIS_AMPLIFIER: float = 2.5
_DEFAULT_RECOVERY_DAMPENER: float = 0.3

# FR-006: Phase-dependent amplification profiles
_DEFAULT_PROFILES: dict[CrisisPhase, PhasedAmplificationProfile] = {
    CrisisPhase.NORMAL: PhasedAmplificationProfile(
        dispossession_multiplier=1.0,
        precaritization_multiplier=1.0,
        accumulation_multiplier=1.0,
        stabilization_multiplier=1.0,
    ),
    CrisisPhase.ONSET: PhasedAmplificationProfile(
        dispossession_multiplier=1.2,
        precaritization_multiplier=1.5,
        accumulation_multiplier=0.8,
        stabilization_multiplier=0.7,
    ),
    CrisisPhase.EARLY: PhasedAmplificationProfile(
        dispossession_multiplier=1.8,
        precaritization_multiplier=2.5,
        accumulation_multiplier=0.4,
        stabilization_multiplier=0.4,
    ),
    CrisisPhase.DEEP: PhasedAmplificationProfile(
        dispossession_multiplier=3.0,
        precaritization_multiplier=3.5,
        accumulation_multiplier=0.1,
        stabilization_multiplier=0.2,
    ),
    CrisisPhase.RECOVERY: PhasedAmplificationProfile(
        dispossession_multiplier=1.3,
        precaritization_multiplier=1.2,
        accumulation_multiplier=0.6,
        stabilization_multiplier=0.5,
    ),
}


class DefaultCrisisAmplifier:
    """Default crisis amplification implementation (legacy).

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


class PhasedCrisisAmplifier:
    """Phase-dependent crisis amplification (Feature 018).

    Applies FR-006 multiplier table based on crisis phase. Preserves
    the CrisisAmplifier protocol (C-002): ``amplify(rates, crisis=True)``
    maps to DEEP phase amplification.

    Args:
        profiles: Optional custom phase profiles. Defaults to FR-006 table.

    Example:
        >>> amp = PhasedCrisisAmplifier()
        >>> amplified = amp.amplify_phased(rates, CrisisPhase.DEEP)
        >>> amplified.dispossession  # 3.0x base rate
    """

    def __init__(
        self,
        profiles: dict[CrisisPhase, PhasedAmplificationProfile] | None = None,
    ) -> None:
        self._profiles = profiles if profiles is not None else _DEFAULT_PROFILES

    def amplify(
        self,
        rates: TransitionRates,
        crisis: bool,
    ) -> TransitionRates:
        """CrisisAmplifier protocol: amplify with boolean crisis flag.

        Maps crisis=True to DEEP, crisis=False to NORMAL (passthrough).

        Args:
            rates: Base transition rates.
            crisis: True if crisis conditions active.

        Returns:
            Amplified TransitionRates.
        """
        phase = CrisisPhase.DEEP if crisis else CrisisPhase.NORMAL
        return self.amplify_phased(rates, phase)

    def amplify_phased(
        self,
        rates: TransitionRates,
        phase: CrisisPhase,
    ) -> TransitionRates:
        """Apply phase-dependent amplification to transition rates.

        Args:
            rates: Base transition rates.
            phase: Current crisis phase.

        Returns:
            Amplified TransitionRates with rates clamped to [0, 1].
        """
        profile = self._profiles.get(phase)
        if profile is None:
            return rates

        return TransitionRates(
            fips=rates.fips,
            year=rates.year,
            dispossession=min(rates.dispossession * profile.dispossession_multiplier, 1.0),
            accumulation=min(rates.accumulation * profile.accumulation_multiplier, 1.0),
            precaritization=min(rates.precaritization * profile.precaritization_multiplier, 1.0),
            stabilization=min(rates.stabilization * profile.stabilization_multiplier, 1.0),
        )


__all__ = ["DefaultCrisisAmplifier", "PhasedCrisisAmplifier"]
