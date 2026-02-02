"""ClassPositionClassifier service for wage-based class position classification.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This module implements the wage-based class position classification
per TVT Axiom E2.

TVT Axiom Reference:
    - E1: V_reproduction (subsistence floor)
    - E2: Class position determination rules
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from babylon.economics.melt.types import ClassPosition

if TYPE_CHECKING:
    from babylon.economics.melt.parameters import NationalParameters


class ClassPositionClassifier(Protocol):
    """Protocol for class position classification service.

    This service classifies wages into class positions based on
    NationalParameters thresholds per TVT Axiom E2.

    Classification Rules:
        - LABOR_ARISTOCRACY: W > τ_effective (Φ_hour > 0, net extractor)
        - PROLETARIAT: τ_effective ≥ W > V_reproduction (exploited but reproducing)
        - SUBPROLETARIAT: W ≤ V_reproduction (working below reproduction cost)

    TVT Axiom Reference:
        - E2: Class position determination rules

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
        weights: Sequence[float] | None = None,
    ) -> dict[ClassPosition, float]:
        """Classify a wage distribution into class position shares.

        Args:
            wages: Sequence of hourly wages (each must be ≥ 0)
            params: National parameters containing thresholds
            weights: Optional employment weights for each wage

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


class DefaultClassPositionClassifier:
    """Default implementation of ClassPositionClassifier.

    This classifier implements the wage-based class position classification
    per TVT Axiom E2.

    TVT Axiom Reference:
        - E2: Class position determination rules

    Detroit Validation Case (FIPS codes):
        - Wayne County (Detroit proper): FIPS 26163 (domestic periphery)
        - Oakland County (suburbs): FIPS 26125 (domestic core)
        - Expected: Oakland LA share > Wayne LA share

    Example:
        >>> classifier = DefaultClassPositionClassifier()
        >>> params = NationalParameters(
        ...     year=2022,
        ...     tau=65.0,
        ...     tau_effective=44.2,
        ...     v_reproduction=12.0,
        ...     ...
        ... )
        >>> classifier.classify(50.0, params)
        <ClassPosition.LABOR_ARISTOCRACY: 1>
    """

    def classify(self, wage: float, params: NationalParameters) -> ClassPosition:
        """Classify a single wage rate into class position.

        Args:
            wage: Hourly wage in $/hour (must be ≥ 0)
            params: National parameters containing τ_effective and V_reproduction

        Returns:
            ClassPosition enum value representing the wage's class position
        """
        if wage > params.tau_effective:
            return ClassPosition.LABOR_ARISTOCRACY
        if wage > params.v_reproduction:
            return ClassPosition.PROLETARIAT
        return ClassPosition.SUBPROLETARIAT

    def classify_distribution(
        self,
        wages: Sequence[float],
        params: NationalParameters,
        weights: Sequence[float] | None = None,
    ) -> dict[ClassPosition, float]:
        """Classify a wage distribution into class position shares.

        Args:
            wages: Sequence of hourly wages (each must be ≥ 0)
            params: National parameters containing thresholds
            weights: Optional employment weights for each wage (defaults to equal weights)

        Returns:
            Dict mapping each ClassPosition to its share [0, 1].
            Shares sum to 1.0 (within floating-point tolerance).
        """
        # Handle empty input
        if not wages:
            # Return equal shares for empty distribution
            equal_share = 1.0 / 3.0
            return {
                ClassPosition.LABOR_ARISTOCRACY: equal_share,
                ClassPosition.PROLETARIAT: equal_share,
                ClassPosition.SUBPROLETARIAT: equal_share,
            }

        # Use equal weights if not provided
        if weights is None:
            weights = [1.0] * len(wages)

        # Validate weights length
        if len(weights) != len(wages):
            msg = f"Weights length ({len(weights)}) != wages length ({len(wages)})"
            raise ValueError(msg)

        # Accumulate weighted counts
        totals: dict[ClassPosition, float] = {
            ClassPosition.LABOR_ARISTOCRACY: 0.0,
            ClassPosition.PROLETARIAT: 0.0,
            ClassPosition.SUBPROLETARIAT: 0.0,
        }

        total_weight = sum(weights)

        for wage, weight in zip(wages, weights, strict=True):
            position = self.classify(wage, params)
            totals[position] += weight

        # Handle zero total weight
        if total_weight == 0:
            equal_share = 1.0 / 3.0
            return {
                ClassPosition.LABOR_ARISTOCRACY: equal_share,
                ClassPosition.PROLETARIAT: equal_share,
                ClassPosition.SUBPROLETARIAT: equal_share,
            }

        # Convert to shares
        return {position: count / total_weight for position, count in totals.items()}


__all__ = ["ClassPositionClassifier", "DefaultClassPositionClassifier"]
