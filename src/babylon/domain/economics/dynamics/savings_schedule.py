"""Default savings rate schedule for class-based wealth accumulation.

Feature: 016-class-dynamics-engine
Date: 2026-02-06

This module provides the default class-based savings rate step function,
calibrated against Fed SCF data (Saez & Zucman 2020). Imperial rent
adjustment follows the formula from spec FR-001.

See Also:
    :mod:`babylon.domain.economics.dynamics.data_sources`: SavingsRateSource protocol
    ``specs/016-class-dynamics-engine/research.md``: Section 4
"""

from __future__ import annotations

from babylon.domain.economics.melt.types import ClassPosition
from babylon.formulas.constants import HOURS_PER_YEAR

# Default savings rates per ClassPosition (Fed SCF calibrated)
_DEFAULT_RATES: dict[ClassPosition, float] = {
    ClassPosition.BOURGEOISIE: 0.38,
    ClassPosition.PETIT_BOURGEOISIE: 0.20,
    ClassPosition.LABOR_ARISTOCRACY: 0.12,
    ClassPosition.PROLETARIAT: 0.03,
    ClassPosition.LUMPENPROLETARIAT: 0.00,
}

# Maximum imperial rent adjustment (5 percentage points)
_DEFAULT_PHI_CAP: float = 0.05


class DefaultSavingsRateSchedule:
    """Default class-based savings rate schedule.

    Provides one base savings rate per ClassPosition, adjusted upward
    by imperial rent subsidy effect. Rates are calibrated against
    Fed Survey of Consumer Finances (Saez & Zucman 2020).

    Formula:
        effective_savings = base_rate + phi_adjustment
        phi_adjustment = min(phi_hour * HOURS_PER_YEAR / wage, phi_cap)

    Args:
        phi_cap: Maximum imperial rent adjustment. Default 0.05.

    Example:
        >>> schedule = DefaultSavingsRateSchedule()
        >>> schedule.get_savings_rate(ClassPosition.PROLETARIAT)
        0.03
        >>> schedule.get_phi_adjustment(phi_hour=3.50, wage=45000.0)
        0.16...
    """

    def __init__(self, phi_cap: float = _DEFAULT_PHI_CAP) -> None:
        """Initialize with optional phi cap override.

        Args:
            phi_cap: Maximum imperial rent adjustment [0, 0.10].
        """
        self._phi_cap = phi_cap

    def get_savings_rate(self, class_position: ClassPosition) -> float:
        """Get base savings rate for a class position.

        Args:
            class_position: The class position to look up.

        Returns:
            Base savings rate [0, 1].
        """
        return _DEFAULT_RATES[class_position]

    def get_phi_adjustment(self, phi_hour: float, wage: float) -> float:
        """Get imperial rent adjustment to savings rate.

        Formula: min(phi_hour * HOURS_PER_YEAR / wage, phi_cap)

        Guards:
            - wage == 0.0 -> returns 0.0 (no division by zero)
            - phi_hour == 0.0 -> returns 0.0 (no adjustment)

        Args:
            phi_hour: Imperial rent per hour ($).
            wage: Annual wage ($).

        Returns:
            Savings rate adjustment [0, phi_cap].
        """
        if wage == 0.0 or phi_hour == 0.0:
            return 0.0
        return min(phi_hour * HOURS_PER_YEAR / wage, self._phi_cap)


__all__ = ["DefaultSavingsRateSchedule", "HOURS_PER_YEAR"]
