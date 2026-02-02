"""Contract: ClassPosition enum and ClassPositionClassifier service.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This contract defines the interface for wage-based class position classification.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol, Sequence

if TYPE_CHECKING:
    from babylon.economics.national_parameters import NationalParameters


class ClassPosition(Enum):
    """Wage-based class position for imperial rent analysis.

    This enumeration represents the three wage-based class positions
    derived from TVT (Topological Value Theory) Axiom E2.

    Scope Limitation:
        This classification is *wage-based* only. It classifies workers by
        their wage relative to value thresholds. It does NOT identify:

        - **Bourgeoisie**: Non-wage income from capital ownership
        - **Lumpen**: Excluded from production entirely (V_produced ≈ 0)

        Note: Subproletariat ≠ Lumpen. A subproletarian is *working* but paid
        below reproduction cost. A lumpen is *excluded* from wage labor entirely.

    Classification Rules:
        - LABOR_ARISTOCRACY: W > τ_effective (Φ_hour > 0, net extractor)
        - PROLETARIAT: τ_effective ≥ W > V_reproduction (exploited but reproducing)
        - SUBPROLETARIAT: W ≤ V_reproduction (working below reproduction cost)

    Example:
        >>> from babylon.economics import ClassPosition, NationalParameters
        >>> params = NationalParameters(year=2022, tau=65.0, tau_effective=44.0, ...)
        >>> if wage > params.tau_effective:
        ...     position = ClassPosition.LABOR_ARISTOCRACY
        >>> elif wage > params.v_reproduction:
        ...     position = ClassPosition.PROLETARIAT
        >>> else:
        ...     position = ClassPosition.SUBPROLETARIAT

    See Also:
        :class:`NationalParameters`: Contains threshold values
        :class:`ClassPositionClassifier`: Service for classification
    """

    LABOR_ARISTOCRACY = auto()
    """W > τ_effective: Net extractor of peripheral labor (Φ_hour > 0)."""

    PROLETARIAT = auto()
    """τ_effective ≥ W > V_reproduction: Exploited but self-reproducing."""

    SUBPROLETARIAT = auto()
    """W ≤ V_reproduction: Working but below reproduction cost."""


class ClassPositionClassifier(Protocol):
    """Protocol for class position classification service.

    This service classifies wages into class positions based on
    NationalParameters thresholds per TVT Axiom E2.

    Example:
        >>> classifier = DefaultClassPositionClassifier()
        >>> params = get_national_parameters(2022)
        >>> position = classifier.classify(wage=50.0, params=params)
        >>> position
        <ClassPosition.LABOR_ARISTOCRACY: 1>

    See Also:
        :class:`ClassPosition`: The enumeration of possible positions
        :class:`NationalParameters`: Parameters containing thresholds
    """

    def classify(self, wage: float, params: NationalParameters) -> ClassPosition:
        """Classify a single wage rate into class position.

        Args:
            wage: Hourly wage in $/hour (must be ≥ 0)
            params: National parameters containing τ_effective and V_reproduction

        Returns:
            ClassPosition enum value representing the wage's class position

        Example:
            >>> classifier.classify(wage=50.0, params=params)
            <ClassPosition.LABOR_ARISTOCRACY: 1>
            >>> classifier.classify(wage=25.0, params=params)
            <ClassPosition.PROLETARIAT: 2>
            >>> classifier.classify(wage=8.0, params=params)
            <ClassPosition.SUBPROLETARIAT: 3>
        """
        ...

    def classify_distribution(
        self,
        wages: Sequence[float],
        params: NationalParameters,
    ) -> dict[ClassPosition, float]:
        """Classify a wage distribution into class position shares.

        Args:
            wages: Sequence of hourly wages (each must be ≥ 0)
            params: National parameters containing thresholds

        Returns:
            Dict mapping each ClassPosition to its share [0, 1].
            Shares sum to 1.0 (within floating-point tolerance).

        Example:
            >>> wages = [50.0, 50.0, 25.0, 25.0, 8.0]  # 5 workers
            >>> shares = classifier.classify_distribution(wages, params)
            >>> shares[ClassPosition.LABOR_ARISTOCRACY]
            0.4  # 2/5 workers
            >>> shares[ClassPosition.PROLETARIAT]
            0.4  # 2/5 workers
            >>> shares[ClassPosition.SUBPROLETARIAT]
            0.2  # 1/5 workers
        """
        ...
