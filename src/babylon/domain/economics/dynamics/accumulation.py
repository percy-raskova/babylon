"""Wealth accumulation calculator for class dynamics transitions.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

Implements FR-001: Annual wealth accumulation rate where consumption
is derived as ``wage * (1 - savings_rate)`` and annual accumulation
is ``(wage - consumption) * savings_rate``.

See Also:
    :mod:`babylon.domain.economics.dynamics.savings_schedule`: Default savings rates
    :mod:`babylon.domain.economics.dynamics.data_sources`: AccumulationCalculator protocol
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.domain.economics.dynamics.types import AccumulationResult

if TYPE_CHECKING:
    from babylon.domain.economics.dynamics.data_sources import SavingsRateSource
    from babylon.domain.economics.melt.types import ClassPosition

# Default Fed SCF p50 net worth threshold for LA entry
_DEFAULT_WEALTH_THRESHOLD: float = 142_000.0


class DefaultAccumulationCalculator:
    """Default implementation of AccumulationCalculator.

    Computes annual wealth accumulation using class-based savings rates
    with imperial rent adjustment per FR-001.

    Formula:
        effective_savings = base_rate + phi_adjustment
        consumption = wage * (1 - effective_savings)
        annual_accumulation = (wage - consumption) * effective_savings

    Which simplifies to:
        annual_accumulation = wage * effective_savings^2

    Args:
        savings_source: Source for class-based savings rates.
        wealth_threshold: Wealth needed to enter LA class. Default $142,000.

    Example:
        >>> calc = DefaultAccumulationCalculator(DefaultSavingsRateSchedule())
        >>> result = calc.compute(wage=60000.0, phi_hour=3.50,
        ...                       class_position=ClassPosition.LABOR_ARISTOCRACY)
        >>> result.annual_accumulation > 0
        True
    """

    def __init__(
        self,
        savings_source: SavingsRateSource,
        wealth_threshold: float = _DEFAULT_WEALTH_THRESHOLD,
    ) -> None:
        """Initialize with savings rate source.

        Args:
            savings_source: Source for class-based savings rates.
            wealth_threshold: Wealth needed to enter LA class ($).
        """
        self._savings_source = savings_source
        self._wealth_threshold = wealth_threshold

    def compute(
        self,
        wage: float,
        phi_hour: float,
        class_position: ClassPosition,
    ) -> AccumulationResult:
        """Compute annual wealth accumulation for a worker.

        Args:
            wage: Annual wage income ($).
            phi_hour: Imperial rent per hour ($).
            class_position: Worker's current class position.

        Returns:
            AccumulationResult with computed wealth change.
        """
        base_rate = self._savings_source.get_savings_rate(class_position)
        phi_adj = self._savings_source.get_phi_adjustment(phi_hour, wage)
        effective_savings = min(base_rate + phi_adj, 1.0)

        consumption = wage * (1.0 - effective_savings)
        accumulation = (wage - consumption) * effective_savings

        years: float | None = None
        if accumulation > 0.0:
            years = self._wealth_threshold / accumulation

        return AccumulationResult(
            wage=wage,
            consumption=consumption,
            savings_rate=effective_savings,
            phi_adjustment=phi_adj,
            annual_accumulation=accumulation,
            years_to_threshold=years,
        )


__all__ = ["DefaultAccumulationCalculator"]
