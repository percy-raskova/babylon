"""GammaBasketCalculator service for computing consumption basket visibility.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module implements the gamma_basket computation per TVT Axiom D3:
    gamma_basket = 1 / (alpha/gamma_import + (1-alpha))

TVT Axiom Reference:
    - D3: Basket visibility derivation
    - D4: tau_effective = tau * gamma_basket

See Also:
    :mod:`babylon.domain.economics.melt.basket_visibility`: Original melt basket visibility
    :mod:`babylon.domain.economics.gamma.gamma_import`: Source for gamma_import values
"""

from __future__ import annotations

import logging
from typing import Protocol

from babylon.domain.economics.gamma.types import GammaBasket
from babylon.domain.economics.gamma.validation import validate_gamma_basket
from babylon.domain.economics.protocol_kit import CachedSource
from babylon.domain.economics.tensor import NoDataSentinel

logger = logging.getLogger(__name__)


class GammaBasketCalculator(Protocol):
    """Protocol for composite basket visibility computation.

    Combines domestic (gamma=1) and imported (gamma=gamma_import) goods
    into a weighted-average basket visibility using harmonic mean.

    Formula:
        gamma_basket = 1 / (alpha/gamma_import + (1-alpha))

    Example:
        >>> calculator = DefaultGammaBasketCalculator()
        >>> result = calculator.compute(2022, alpha=0.35, gamma_import=0.65)
        >>> if result:
        ...     print(f"gamma_basket = {result.gamma_basket:.3f}")
    """

    def compute(
        self,
        year: int,
        alpha: float,
        gamma_import: float,
    ) -> GammaBasket | NoDataSentinel:
        """Compute gamma_basket for given alpha and gamma_import.

        Args:
            year: Calendar year.
            alpha: Import share of consumption [0, 1].
            gamma_import: Import visibility coefficient (0, 1].

        Returns:
            GammaBasket result or NoDataSentinel.
        """
        ...


class DefaultGammaBasketCalculator(CachedSource[float]):
    """Default implementation of GammaBasketCalculator.

    Uses the harmonic mean formula from TVT Axiom D3. This is the same
    formula used in ``melt/basket_visibility.py`` but with Penn World Tables
    values rather than MVP hardcoded constants.

    Example:
        >>> calculator = DefaultGammaBasketCalculator()
        >>> result = calculator.compute(2022, alpha=0.35, gamma_import=0.65)
        >>> print(f"gamma_basket = {result.gamma_basket:.3f}")
        gamma_basket = 0.740
    """

    def compute(
        self,
        year: int,
        alpha: float,
        gamma_import: float,
    ) -> GammaBasket | NoDataSentinel:
        """Compute gamma_basket using harmonic mean formula.

        Formula: gamma_basket = 1 / (alpha/gamma_import + (1-alpha))

        Edge Cases:
            - alpha = 0: Returns gamma_basket = 1.0 (no imports, no subsidy)
            - alpha = 1: Returns gamma_basket = gamma_import (100% imports)

        Args:
            year: Calendar year.
            alpha: Import share of consumption [0, 1].
            gamma_import: Import visibility coefficient (0, 1].

        Returns:
            GammaBasket result or NoDataSentinel.
        """
        # Validate inputs
        if alpha < 0.0 or alpha > 1.0:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"alpha={alpha:.3f} outside valid range [0, 1]",
            )
        if gamma_import <= 0.0 or gamma_import > 1.0:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"gamma_import={gamma_import:.3f} outside valid range (0, 1]",
            )

        # Edge case: no imports (alpha = 0)
        if alpha == 0.0:
            gamma_basket = 1.0
        # Edge case: 100% imports (alpha = 1)
        elif alpha == 1.0:
            gamma_basket = gamma_import
        # Standard formula: gamma_basket = 1 / (alpha/gamma_import + (1-alpha))
        else:
            denominator = alpha / gamma_import + (1.0 - alpha)
            gamma_basket = 1.0 / denominator

        # Validate constraint: gamma_basket >= gamma_import
        # This is mathematically guaranteed by the harmonic mean when alpha in [0,1]
        # but we check defensively
        if gamma_basket < gamma_import:
            logger.error(
                "Constraint violation: gamma_basket=%.4f < gamma_import=%.4f",
                gamma_basket,
                gamma_import,
            )

        # Validate and log
        valid, message = validate_gamma_basket(gamma_basket)
        if message is not None:
            logger.warning("gamma_basket validation: %s", message)
        if not valid:
            logger.error("gamma_basket FAIL: %s", message)

        return GammaBasket(
            year=year,
            alpha=alpha,
            gamma_import=gamma_import,
            gamma_basket=gamma_basket,
        )


__all__ = ["DefaultGammaBasketCalculator", "GammaBasketCalculator"]
