"""ClassPositionClassifier service for wealth-based class position classification.

Feature: 013-melt-basket-visibility
Date: 2026-02-01
Revision: 2026-02-02 (wealth-based classification)

This module implements wealth-based class position classification per
TVT Axiom E1 (revised). Class position is determined by wealth percentile
(stock), NOT income threshold (flow).

Theoretical Background:
    Class position and imperial rent extraction are separate concerns:
    - **Class position**: Structural relationship to means of production,
      determined by accumulated wealth (stock)
    - **Imperial rent (Φ_hour)**: Flow-based extraction rate through consumption

    A proletarian CAN have Φ_hour > 0 (benefit from cheap imports) while
    remaining proletarian. They consume the imperial subsidy rather than
    accumulating it as wealth.

TVT Axiom Reference (Revised):
    - E1: Wealth-based classification thresholds
    - E2: Imperial rent is separate from class position

Data Sources:
    - National: Fed SCF (Survey of Consumer Finances) for wealth percentiles
    - County: ACS home ownership rate as primary wealth proxy
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from babylon.economics.melt.types import ClassPosition

if TYPE_CHECKING:
    from babylon.economics.melt.parameters import NationalParameters


class ClassPositionClassifier(Protocol):
    """Protocol for class position classification service.

    This service classifies individuals into class positions based on
    wealth percentile (primary method) or wage income (deprecated method).

    Classification (Wealth-Based):
        | Class             | Wealth Percentile | Pop Share |
        |-------------------|-------------------|-----------|
        | BOURGEOISIE       | ≥ 99%             | 1%        |
        | PETIT_BOURGEOISIE | 90% - 99%         | 9%        |
        | LABOR_ARISTOCRACY | 50% - 90%         | 40%       |
        | PROLETARIAT       | < 50%, employed   | ~35%      |
        | LUMPENPROLETARIAT | < 50%, excluded   | ~15%      |

    Key Insight:
        LA = 40% emerges naturally from wealth distribution (50th-90th
        percentile = 40 percentage points). No parameter tuning required.

    TVT Axiom Reference:
        - E1 (Revised): Wealth-based classification

    Example:
        >>> classifier = DefaultClassPositionClassifier()
        >>> # Wealth-based (primary method)
        >>> position = classifier.classify_by_wealth_percentile(75.0)
        >>> position
        <ClassPosition.LABOR_ARISTOCRACY: 3>
        >>> # With employment status for bottom 50%
        >>> position = classifier.classify_by_wealth_and_employment(30.0, employed=True)
        >>> position
        <ClassPosition.PROLETARIAT: 4>

    See Also:
        :class:`ClassPosition`: The enumeration of possible positions
        :class:`NationalParameters`: Parameters containing thresholds
        :class:`ImperialRentCalculator`: Flow-based extraction (separate concern)
    """

    def classify_by_wealth_percentile(self, wealth_percentile: float) -> ClassPosition:
        """Classify by national wealth percentile (primary method).

        This is the canonical classification method. Class position is
        determined by accumulated wealth, not income flow.

        Args:
            wealth_percentile: Wealth percentile 0-100 (from Fed SCF or proxy)

        Returns:
            ClassPosition enum value (BOURGEOISIE, PETIT_BOURGEOISIE,
            LABOR_ARISTOCRACY, or PROLETARIAT for bottom 50%)

        Note:
            For bottom 50%, returns PROLETARIAT by default. Use
            classify_by_wealth_and_employment() to distinguish
            PROLETARIAT from LUMPENPROLETARIAT.

        Example:
            >>> classifier.classify_by_wealth_percentile(99.5)
            <ClassPosition.BOURGEOISIE: 1>
            >>> classifier.classify_by_wealth_percentile(95.0)
            <ClassPosition.PETIT_BOURGEOISIE: 2>
            >>> classifier.classify_by_wealth_percentile(70.0)
            <ClassPosition.LABOR_ARISTOCRACY: 3>
        """
        ...

    def classify_by_wealth_and_employment(
        self, wealth_percentile: float, employed: bool
    ) -> ClassPosition:
        """Full classification including lumpenproletariat distinction.

        For bottom 50% wealth, distinguishes between employed (PROLETARIAT)
        and excluded from labor market (LUMPENPROLETARIAT).

        Args:
            wealth_percentile: Wealth percentile 0-100
            employed: True if formally employed, False if excluded from labor market

        Returns:
            Full ClassPosition including LUMPENPROLETARIAT for excluded workers

        Example:
            >>> classifier.classify_by_wealth_and_employment(30.0, employed=True)
            <ClassPosition.PROLETARIAT: 4>
            >>> classifier.classify_by_wealth_and_employment(30.0, employed=False)
            <ClassPosition.LUMPENPROLETARIAT: 5>
        """
        ...

    def classify(self, wage: float, params: NationalParameters) -> ClassPosition:
        """DEPRECATED: Classify by wage income (backward compatibility).

        This income-based method is kept for backward compatibility but
        conflates imperial rent extraction with class position.

        Use classify_by_wealth_percentile() or classify_by_wealth_and_employment()
        for the canonical wealth-based classification.

        Args:
            wage: Hourly wage in $/hour (must be ≥ 0)
            params: National parameters containing τ_effective and V_reproduction

        Returns:
            ClassPosition (maps to 3-class model for backward compatibility):
            - LABOR_ARISTOCRACY if W > τ_effective
            - PROLETARIAT if τ_effective ≥ W > V_reproduction
            - LUMPENPROLETARIAT if W ≤ V_reproduction (was SUBPROLETARIAT)

        .. deprecated::
            Use wealth-based classification instead. Income-based
            classification conflates extraction rate with class position.
        """
        ...

    def classify_distribution(
        self,
        wages: Sequence[float],
        params: NationalParameters,
        weights: Sequence[float] | None = None,
    ) -> dict[ClassPosition, float]:
        """DEPRECATED: Classify wage distribution into class shares.

        This income-based method is kept for backward compatibility.
        For wealth-based distribution, use classify_wealth_distribution().

        Args:
            wages: Sequence of hourly wages (each must be ≥ 0)
            params: National parameters containing thresholds
            weights: Optional employment weights for each wage

        Returns:
            Dict mapping ClassPosition to share [0, 1].
            Uses 3-class model (LA, PROLETARIAT, LUMPENPROLETARIAT).

        .. deprecated::
            Use wealth-based classification instead.
        """
        ...

    def classify_wealth_distribution(
        self,
        wealth_percentiles: Sequence[float],
        employment_statuses: Sequence[bool] | None = None,
        weights: Sequence[float] | None = None,
    ) -> dict[ClassPosition, float]:
        """Classify wealth distribution into class shares (primary method).

        This is the canonical distribution method. Uses all 5 class positions.

        Args:
            wealth_percentiles: Sequence of wealth percentiles (0-100)
            employment_statuses: Optional employment status for each entry
                               (needed to distinguish PROLETARIAT/LUMPENPROLETARIAT)
            weights: Optional population weights for each entry

        Returns:
            Dict mapping all 5 ClassPosition values to their shares [0, 1].
            Shares sum to 1.0.

        Example:
            >>> percentiles = [99.5, 95.0, 70.0, 30.0, 20.0]
            >>> shares = classifier.classify_wealth_distribution(percentiles)
            >>> shares[ClassPosition.BOURGEOISIE]
            0.2  # 1/5
        """
        ...


class DefaultClassPositionClassifier:
    """Default implementation of ClassPositionClassifier.

    This classifier implements wealth-based class position classification
    per TVT Axiom E1 (revised). Includes backward-compatible income-based
    methods marked as deprecated.

    Wealth Percentile Thresholds (from Fed SCF data):
        - BOURGEOISIE: ≥ 99th percentile (top 1%)
        - PETIT_BOURGEOISIE: 90th-99th percentile
        - LABOR_ARISTOCRACY: 50th-90th percentile (40% of population)
        - PROLETARIAT/LUMPENPROLETARIAT: < 50th percentile

    Key Insight:
        LA = 40% emerges naturally from wealth distribution (50th-90th
        percentile = 40 percentage points). This resolves the 30-50%
        vs 50-70% debate without parameter tuning.

    Detroit Validation Case (FIPS codes):
        - Wayne County (Detroit proper): FIPS 26163 (lower homeownership)
        - Oakland County (suburbs): FIPS 26125 (higher homeownership)
        - Expected: Oakland LA share > Wayne LA share

    Example:
        >>> classifier = DefaultClassPositionClassifier()
        >>> # Wealth-based (canonical)
        >>> classifier.classify_by_wealth_percentile(75.0)
        <ClassPosition.LABOR_ARISTOCRACY: 3>
        >>> # Income-based (deprecated, backward compatible)
        >>> classifier.classify(50.0, params)
        <ClassPosition.LABOR_ARISTOCRACY: 3>
    """

    # Wealth percentile thresholds (from Fed SCF data)
    BOURGEOISIE_THRESHOLD = 99.0  # Top 1%
    PETIT_BOURGEOISIE_THRESHOLD = 90.0  # 90th percentile
    LABOR_ARISTOCRACY_THRESHOLD = 50.0  # 50th percentile (median)

    def classify_by_wealth_percentile(self, wealth_percentile: float) -> ClassPosition:
        """Classify by national wealth percentile (primary method).

        Args:
            wealth_percentile: Wealth percentile 0-100 (from Fed SCF or proxy)

        Returns:
            ClassPosition enum value. For bottom 50%, returns PROLETARIAT
            by default (use classify_by_wealth_and_employment for lumpen).
        """
        if wealth_percentile >= self.BOURGEOISIE_THRESHOLD:
            return ClassPosition.BOURGEOISIE
        if wealth_percentile >= self.PETIT_BOURGEOISIE_THRESHOLD:
            return ClassPosition.PETIT_BOURGEOISIE
        if wealth_percentile >= self.LABOR_ARISTOCRACY_THRESHOLD:
            return ClassPosition.LABOR_ARISTOCRACY
        # Bottom 50% - default to PROLETARIAT
        # Use classify_by_wealth_and_employment for lumpen distinction
        return ClassPosition.PROLETARIAT

    def classify_by_wealth_and_employment(
        self, wealth_percentile: float, employed: bool
    ) -> ClassPosition:
        """Full classification including lumpenproletariat distinction.

        Args:
            wealth_percentile: Wealth percentile 0-100
            employed: True if formally employed, False if excluded

        Returns:
            Full ClassPosition including LUMPENPROLETARIAT for excluded workers
        """
        if wealth_percentile >= self.LABOR_ARISTOCRACY_THRESHOLD:
            return self.classify_by_wealth_percentile(wealth_percentile)
        if employed:
            return ClassPosition.PROLETARIAT
        return ClassPosition.LUMPENPROLETARIAT

    def classify(self, wage: float, params: NationalParameters) -> ClassPosition:
        """DEPRECATED: Classify by wage income (backward compatibility).

        .. deprecated::
            Use classify_by_wealth_percentile() instead. This method
            conflates imperial rent extraction with class position.

        Args:
            wage: Hourly wage in $/hour (must be ≥ 0)
            params: National parameters containing τ_effective and V_reproduction

        Returns:
            ClassPosition using 3-class mapping for backward compatibility
        """
        warnings.warn(
            "Income-based classify() is deprecated. Use classify_by_wealth_percentile() "
            "for wealth-based classification. Income-based classification conflates "
            "extraction rate (Φ_hour) with class position.",
            DeprecationWarning,
            stacklevel=2,
        )
        if wage > params.tau_effective:
            return ClassPosition.LABOR_ARISTOCRACY
        if wage > params.v_reproduction:
            return ClassPosition.PROLETARIAT
        # Map old SUBPROLETARIAT to LUMPENPROLETARIAT
        return ClassPosition.LUMPENPROLETARIAT

    def classify_distribution(
        self,
        wages: Sequence[float],
        params: NationalParameters,
        weights: Sequence[float] | None = None,
    ) -> dict[ClassPosition, float]:
        """DEPRECATED: Classify wage distribution into class shares.

        .. deprecated::
            Use classify_wealth_distribution() instead.

        Args:
            wages: Sequence of hourly wages (each must be ≥ 0)
            params: National parameters containing thresholds
            weights: Optional employment weights for each wage

        Returns:
            Dict mapping 3 ClassPosition values to their shares [0, 1].
            Uses LA, PROLETARIAT, LUMPENPROLETARIAT for backward compat.
        """
        # Handle empty input
        if not wages:
            # Return equal shares for empty distribution (3-class model)
            equal_share = 1.0 / 3.0
            return {
                ClassPosition.LABOR_ARISTOCRACY: equal_share,
                ClassPosition.PROLETARIAT: equal_share,
                ClassPosition.LUMPENPROLETARIAT: equal_share,
            }

        # Use equal weights if not provided
        if weights is None:
            weights = [1.0] * len(wages)

        # Validate weights length
        if len(weights) != len(wages):
            msg = f"Weights length ({len(weights)}) != wages length ({len(wages)})"
            raise ValueError(msg)

        # Accumulate weighted counts (3-class model for backward compat)
        totals: dict[ClassPosition, float] = {
            ClassPosition.LABOR_ARISTOCRACY: 0.0,
            ClassPosition.PROLETARIAT: 0.0,
            ClassPosition.LUMPENPROLETARIAT: 0.0,
        }

        total_weight = sum(weights)

        for wage, weight in zip(wages, weights, strict=True):
            # Use internal classification without deprecation warning
            if wage > params.tau_effective:
                position = ClassPosition.LABOR_ARISTOCRACY
            elif wage > params.v_reproduction:
                position = ClassPosition.PROLETARIAT
            else:
                position = ClassPosition.LUMPENPROLETARIAT
            totals[position] += weight

        # Handle zero total weight
        if total_weight == 0:
            equal_share = 1.0 / 3.0
            return {
                ClassPosition.LABOR_ARISTOCRACY: equal_share,
                ClassPosition.PROLETARIAT: equal_share,
                ClassPosition.LUMPENPROLETARIAT: equal_share,
            }

        # Convert to shares
        return {position: count / total_weight for position, count in totals.items()}

    def classify_wealth_distribution(
        self,
        wealth_percentiles: Sequence[float],
        employment_statuses: Sequence[bool] | None = None,
        weights: Sequence[float] | None = None,
    ) -> dict[ClassPosition, float]:
        """Classify wealth distribution into class shares (primary method).

        Args:
            wealth_percentiles: Sequence of wealth percentiles (0-100)
            employment_statuses: Optional employment status for each entry
            weights: Optional population weights for each entry

        Returns:
            Dict mapping all 5 ClassPosition values to their shares [0, 1].
        """
        # Handle empty input - return population-typical shares
        if not wealth_percentiles:
            return {
                ClassPosition.BOURGEOISIE: 0.01,
                ClassPosition.PETIT_BOURGEOISIE: 0.09,
                ClassPosition.LABOR_ARISTOCRACY: 0.40,
                ClassPosition.PROLETARIAT: 0.35,
                ClassPosition.LUMPENPROLETARIAT: 0.15,
            }

        # Use equal weights if not provided
        if weights is None:
            weights = [1.0] * len(wealth_percentiles)

        # Validate weights length
        if len(weights) != len(wealth_percentiles):
            msg = (
                f"Weights length ({len(weights)}) != percentiles length ({len(wealth_percentiles)})"
            )
            raise ValueError(msg)

        # Default employment status to True (employed) if not provided
        if employment_statuses is None:
            employment_statuses = [True] * len(wealth_percentiles)
        elif len(employment_statuses) != len(wealth_percentiles):
            msg = f"Employment length ({len(employment_statuses)}) != percentiles length ({len(wealth_percentiles)})"
            raise ValueError(msg)

        # Initialize totals for all 5 classes
        totals: dict[ClassPosition, float] = {
            ClassPosition.BOURGEOISIE: 0.0,
            ClassPosition.PETIT_BOURGEOISIE: 0.0,
            ClassPosition.LABOR_ARISTOCRACY: 0.0,
            ClassPosition.PROLETARIAT: 0.0,
            ClassPosition.LUMPENPROLETARIAT: 0.0,
        }

        total_weight = sum(weights)

        for percentile, employed, weight in zip(
            wealth_percentiles, employment_statuses, weights, strict=True
        ):
            position = self.classify_by_wealth_and_employment(percentile, employed)
            totals[position] += weight

        # Handle zero total weight
        if total_weight == 0:
            return {
                ClassPosition.BOURGEOISIE: 0.01,
                ClassPosition.PETIT_BOURGEOISIE: 0.09,
                ClassPosition.LABOR_ARISTOCRACY: 0.40,
                ClassPosition.PROLETARIAT: 0.35,
                ClassPosition.LUMPENPROLETARIAT: 0.15,
            }

        # Convert to shares
        return {position: count / total_weight for position, count in totals.items()}


__all__ = ["ClassPositionClassifier", "DefaultClassPositionClassifier"]
