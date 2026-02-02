"""Contract: ImperialRentCalculator service protocol (TVT formulas).

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This contract defines the interface for computing imperial rent metrics
using TVT Axioms E3 and E4.

Note: This is distinct from the Emmanuel-Amin imperial rent calculator
in babylon.economics.reproduction. Both theoretical frameworks coexist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from babylon.economics.national_parameters import NationalParameters


class ImperialRentCalculator(Protocol):
    """Protocol for imperial rent computation (TVT Axioms E3-E4).

    This service computes hourly imperial rent metrics:

    Φ_hour (Imperial Rent per Hour):
        Φ_hour = (W/τ) × (1/γ_basket) - 1

        Interpretation:
        - Φ_hour > 0: Worker extracts labor from periphery (Labor Aristocracy)
        - Φ_hour = 0: Break-even (wage equals τ_effective)
        - Φ_hour < 0: Worker is net exploited (Proletariat/Subproletariat)

    L_commanded (Labor Commanded per Hour):
        L_commanded = (W/τ) × (1/γ_basket)

        Interpretation:
        - L_commanded > 1: Commands more labor than expended (Labor Aristocracy)
        - L_commanded = 1: Break-even
        - L_commanded < 1: Commands less labor than expended (exploited)

    Break-Even Algebra:
        At W = τ_effective = τ × γ_basket:
        Φ_hour = (τ × γ_basket / τ) × (1/γ_basket) - 1
               = γ_basket × (1/γ_basket) - 1
               = 1 - 1 = 0 ✓

    Example:
        >>> calculator = DefaultImperialRentCalculator()
        >>> params = get_national_parameters(2022)
        >>> phi = calculator.compute_phi_hour(wage=65.0, params=params)
        >>> print(f"Worker extracts {phi:.2f} hours of peripheral labor per hour worked")

    See Also:
        :class:`NationalParameters`: Contains τ, γ_basket thresholds
        :mod:`babylon.economics.reproduction`: Emmanuel-Amin framework (alternative)
    """

    def compute_phi_hour(self, wage: float, params: NationalParameters) -> float:
        """Compute imperial rent per hour worked (TVT Axiom E3).

        Formula: Φ_hour = (W/τ) × (1/γ_basket) - 1

        Args:
            wage: Hourly wage in $/hour (W)
            params: National parameters containing τ and γ_basket

        Returns:
            Φ_hour in labor-hours extracted per hour worked.
            Can be negative (worker is net exploited).

        Example:
            >>> # Labor Aristocracy: $65/hr with τ=$65, γ_basket=0.68
            >>> calculator.compute_phi_hour(65.0, params)
            0.47  # Extracts 0.47 hours of peripheral labor per hour

            >>> # Proletariat: $30/hr with τ=$65, γ_basket=0.68
            >>> calculator.compute_phi_hour(30.0, params)
            -0.32  # Net exploited, gives 0.32 hours more than receives

            >>> # Break-even: $44/hr (= τ_effective)
            >>> calculator.compute_phi_hour(44.0, params)
            0.0  # Neither extracts nor is extracted
        """
        ...

    def compute_labor_commanded(self, wage: float, params: NationalParameters) -> float:
        """Compute labor hours commanded per hour worked (TVT Axiom E4).

        Formula: L_commanded = (W/τ) × (1/γ_basket)

        This is the labor-time equivalent of the worker's wage when
        adjusted for basket visibility (imperial subsidy).

        Args:
            wage: Hourly wage in $/hour (W)
            params: National parameters containing τ and γ_basket

        Returns:
            L_commanded in labor-hours per hour worked (always ≥ 0).

        Relationship to Φ_hour:
            Φ_hour = L_commanded - 1

        Example:
            >>> # At τ=$65, γ_basket=0.68
            >>> calculator.compute_labor_commanded(65.0, params)
            1.47  # Commands 1.47 hours of labor per hour worked

            >>> calculator.compute_labor_commanded(30.0, params)
            0.68  # Commands only 0.68 hours per hour worked
        """
        ...

    def is_labor_aristocracy(self, wage: float, params: NationalParameters) -> bool:
        """Check if wage qualifies for Labor Aristocracy position.

        A worker is Labor Aristocracy iff:
            L_commanded > 1 (equivalently, W > τ_effective)

        This means they command MORE labor through consumption than they
        expend in production - they are net extractors of peripheral labor.

        Args:
            wage: Hourly wage in $/hour
            params: National parameters containing thresholds

        Returns:
            True if L_commanded > 1, False otherwise

        Example:
            >>> # τ=$65, γ_basket=0.68, τ_effective=$44.20
            >>> calculator.is_labor_aristocracy(50.0, params)
            True  # $50 > $44.20 threshold
            >>> calculator.is_labor_aristocracy(40.0, params)
            False  # $40 < $44.20 threshold
        """
        ...

    def get_theoretical_bounds(
        self,
        params: NationalParameters,
    ) -> dict[str, float]:
        """Get theoretical bounds for imperial rent metrics.

        Returns bounds useful for understanding the metric space:
        - phi_at_zero: Φ_hour when W → 0 (approaches -1)
        - phi_at_threshold: Φ_hour when W = τ_effective (equals 0)
        - phi_at_tau: Φ_hour when W = τ (depends on γ_basket)

        Args:
            params: National parameters

        Returns:
            Dict with keys: phi_at_zero, phi_at_threshold, phi_at_tau,
            l_cmd_at_threshold, etc.

        Example:
            >>> bounds = calculator.get_theoretical_bounds(params)
            >>> bounds['phi_at_zero']
            -1.0  # Limit as W → 0
            >>> bounds['phi_at_threshold']
            0.0  # By definition of τ_effective
        """
        ...
