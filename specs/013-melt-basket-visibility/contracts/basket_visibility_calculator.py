"""Contract: BasketVisibilityCalculator service protocol.

Feature: 013-melt-basket-visibility
Date: 2026-02-01

This contract defines the interface for computing basket visibility (γ_basket)
from import shares and ERDI data, with MVP fallback support.
"""

from __future__ import annotations

from typing import Protocol


class BasketVisibilityCalculator(Protocol):
    """Protocol for basket visibility (γ_basket) computation.

    Basket visibility measures the imperial subsidy on the US consumption
    basket per TVT Axiom D3:

        γ_basket = 1 / (α/γ_import + (1-α))

    where:
        - α = import share of consumption basket [0, 1]
        - γ_import = weighted average visibility of imported goods (0, 1]

    Interpretation:
        - γ_basket = 1.0: No imperial subsidy (α = 0, no imports)
        - γ_basket < 1.0: Consumption subsidized by compressed peripheral labor
        - γ_basket ≈ 0.68: Typical US value (~32% consumption subsidy)

    MVP Mode:
        When import/ERDI data is unavailable, returns hardcoded γ_basket = 0.68
        with estimated=True flag. This enables class position analysis without
        requiring Penn World Tables loader.

    Example:
        >>> calculator = DefaultBasketVisibilityCalculator()
        >>> gamma, estimated = calculator.get_gamma_basket(2022)
        >>> if estimated:
        ...     print(f"MVP estimate: γ_basket = {gamma}")
        ... else:
        ...     print(f"Computed: γ_basket = {gamma}")

    See Also:
        :class:`NationalParameters`: Uses γ_basket as a field
        :class:`MELTCalculator`: Companion service for τ
    """

    def get_gamma_basket(
        self,
        year: int,
        alpha: float | None = None,
        gamma_import: float | None = None,
    ) -> tuple[float, bool]:
        """Compute basket visibility for a given year.

        Formula: γ_basket = 1 / (α/γ_import + (1-α))

        Edge Cases:
            - α = 0: Returns γ_basket = 1.0 (no imports, no subsidy)
            - α = 1: Returns γ_basket = γ_import (100% imports)

        Args:
            year: Calendar year (for data lookup if params not provided)
            alpha: Import share [0, 1] (optional, uses data source if None)
            gamma_import: Peripheral visibility (0, 1] (optional, uses data if None)

        Returns:
            Tuple of (γ_basket, estimated) where:
            - γ_basket: Visibility coefficient (0, 1]
            - estimated: True if using MVP hardcoded value (data unavailable)

        Example:
            >>> # With explicit parameters
            >>> calculator.get_gamma_basket(2022, alpha=0.25, gamma_import=0.35)
            (0.683, False)

            >>> # MVP mode (no data available)
            >>> calculator.get_gamma_basket(2022)
            (0.68, True)

            >>> # Edge case: no imports
            >>> calculator.get_gamma_basket(2022, alpha=0.0, gamma_import=0.35)
            (1.0, False)

            >>> # Edge case: 100% imports
            >>> calculator.get_gamma_basket(2022, alpha=1.0, gamma_import=0.35)
            (0.35, False)
        """
        ...

    def validate_gamma_basket(self, gamma: float) -> tuple[bool, str | None]:
        """Validate γ_basket against sanity ranges per FR-010.

        Sanity Ranges:
            - Expected: 0.60-0.80 (typical US basket visibility)
            - Warning: 0.40-0.95 (unusual but possible)
            - Fail: <0.1 or >1.0 (indicates error)

        Args:
            gamma: Basket visibility to validate

        Returns:
            Tuple of (valid, message):
            - valid=True, message=None: Within expected range
            - valid=True, message=str: Warning (unusual value)
            - valid=False, message=str: Fail (invalid value)

        Example:
            >>> calculator.validate_gamma_basket(0.68)
            (True, None)
            >>> calculator.validate_gamma_basket(0.50)
            (True, 'WARNING: γ_basket=0.50 outside expected range [0.60, 0.80]')
            >>> calculator.validate_gamma_basket(0.05)
            (False, 'γ_basket=0.05 outside valid range [0.1, 1.0]')
        """
        ...

    @property
    def mvp_gamma_basket(self) -> float:
        """MVP hardcoded value for γ_basket.

        Returns:
            0.68 (derived from α ≈ 0.25, γ_import ≈ 0.35 per A-004)
        """
        ...

    @property
    def mvp_alpha(self) -> float:
        """MVP hardcoded value for import share α.

        Returns:
            0.25 (25% import share per Hickel et al. methodology)
        """
        ...

    @property
    def mvp_gamma_import(self) -> float:
        """MVP hardcoded value for peripheral visibility γ_import.

        Returns:
            0.35 (weighted average ERDI of US trading partners)
        """
        ...
