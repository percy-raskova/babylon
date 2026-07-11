"""Data source protocols for the Class Dynamics Engine.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

This module defines Protocol classes for dependency injection of data sources.
Each protocol has a Default implementation and can be mocked for testing.

Protocols:
    - DispossessionDataSource: Foreclosure, bankruptcy, eviction rates
    - SavingsRateSource: Class-based savings rates with imperial rent adjustment
    - AccumulationCalculator: Wealth accumulation computation
    - DispossessionCalculator: Composite dispossession risk
    - ClassTransitionEngine: Main engine orchestrating transitions
    - CrisisAmplifier: Crisis-period rate amplification

See Also:
    :mod:`babylon.domain.economics.dynamics.hardcoded_data`: MVP implementation
    :mod:`babylon.domain.economics.dynamics.savings_schedule`: Default savings schedule
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from babylon.domain.economics.dynamics.types import (
        AccumulationResult,
        ClassDistribution,
        DispossessionRisk,
        EconomicConditions,
        TransitionRates,
    )
    from babylon.domain.economics.melt.types import ClassPosition
    from babylon.domain.economics.tensor import NoDataSentinel
    from babylon.domain.economics.tick.types import CrisisPhase


class DispossessionDataSource(Protocol):
    """Protocol for dispossession rate data providers.

    MVP implementation uses hardcoded national averages.
    Future implementations will load per-county data from
    Eviction Lab, US Courts, and ATTOM/CoreLogic.

    Example:
        >>> source = HardcodedNationalDispossessionSource()
        >>> rate = source.get_foreclosure_rate("26163", 2015)
    """

    def get_foreclosure_rate(self, fips: str, year: int) -> float | None:
        """Get foreclosure rate for a county-year.

        Args:
            fips: County FIPS code.
            year: Calendar year.

        Returns:
            Foreclosure rate [0, 1] or None if unavailable.
        """
        ...

    def get_bankruptcy_rate(self, fips: str, year: int) -> float | None:
        """Get bankruptcy rate for a county-year.

        Args:
            fips: County FIPS code.
            year: Calendar year.

        Returns:
            Bankruptcy rate [0, 1] or None if unavailable.
        """
        ...

    def get_eviction_rate(self, fips: str, year: int) -> float | None:
        """Get eviction rate for a county-year.

        Args:
            fips: County FIPS code.
            year: Calendar year.

        Returns:
            Eviction rate [0, 1] or None if unavailable.
        """
        ...


class SavingsRateSource(Protocol):
    """Protocol for class-based savings rate providers.

    Example:
        >>> schedule = DefaultSavingsRateSchedule()
        >>> rate = schedule.get_savings_rate(ClassPosition.PROLETARIAT)
    """

    def get_savings_rate(self, class_position: ClassPosition) -> float:
        """Get base savings rate for a class position.

        Args:
            class_position: The class position to look up.

        Returns:
            Base savings rate [0, 1].
        """
        ...

    def get_phi_adjustment(self, phi_hour: float, wage: float) -> float:
        """Get imperial rent adjustment to savings rate.

        Args:
            phi_hour: Imperial rent per hour ($).
            wage: Annual wage ($).

        Returns:
            Savings rate adjustment [0, phi_cap].
        """
        ...


class AccumulationCalculator(Protocol):
    """Protocol for wealth accumulation computation.

    Example:
        >>> calc = DefaultAccumulationCalculator(savings_schedule)
        >>> result = calc.compute(wage=60000.0, phi_hour=3.50,
        ...                       class_position=ClassPosition.PROLETARIAT)
    """

    def compute(
        self,
        wage: float,
        phi_hour: float,
        class_position: ClassPosition,
    ) -> AccumulationResult:
        """Compute annual wealth accumulation.

        Args:
            wage: Annual wage income ($).
            phi_hour: Imperial rent per hour ($).
            class_position: Worker's current class position.

        Returns:
            AccumulationResult with computed wealth change.
        """
        ...


class DispossessionCalculator(Protocol):
    """Protocol for composite dispossession risk computation.

    Example:
        >>> calc = DefaultDispossessionCalculator(data_source)
        >>> risk = calc.compute(fips="26163", year=2015)
    """

    def compute(self, fips: str, year: int) -> DispossessionRisk | NoDataSentinel:
        """Compute composite dispossession risk.

        Args:
            fips: County FIPS code.
            year: Calendar year.

        Returns:
            DispossessionRisk or NoDataSentinel if data unavailable.
        """
        ...


class ClassTransitionEngine(Protocol):
    """Protocol for the main class transition engine.

    Example:
        >>> engine = DefaultClassTransitionEngine(acc, disp, crisis)
        >>> new_dist = engine.simulate_transitions(dist, conditions)
    """

    def simulate_transitions(
        self,
        dist: ClassDistribution,
        conditions: EconomicConditions,
        crisis_phase: CrisisPhase | None = None,
    ) -> ClassDistribution | NoDataSentinel:
        """Simulate one period of class distribution transitions.

        Args:
            dist: Current class distribution.
            conditions: Economic conditions for this period.
            crisis_phase: Optional crisis phase for phased amplification.

        Returns:
            Updated ClassDistribution or NoDataSentinel if data unavailable.
        """
        ...


class CrisisAmplifier(Protocol):
    """Protocol for crisis-period transition rate amplification.

    Example:
        >>> amp = DefaultCrisisAmplifier()
        >>> amplified = amp.amplify(rates, crisis=True)
    """

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
        ...


__all__ = [
    "AccumulationCalculator",
    "ClassTransitionEngine",
    "CrisisAmplifier",
    "DispossessionCalculator",
    "DispossessionDataSource",
    "SavingsRateSource",
]
