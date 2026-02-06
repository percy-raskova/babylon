"""ShadowSubsidyCalculator service for computing shadow value transfers.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module implements shadow subsidy calculations:
    Phi_III = (1 - gamma_III) * L_unpaid * tau
    Phi_imperial = (1 - gamma_basket) * Consumption

TVT Axiom Reference:
    - I.2 Imperial Rent (Constitution)
    - I.5 Department III (Constitution)

See Also:
    :mod:`babylon.economics.gamma.gamma_iii`: Source for gamma_III
    :mod:`babylon.economics.gamma.gamma_basket`: Source for gamma_basket
    :mod:`babylon.economics.melt.melt_calculator`: Source for MELT (tau)
"""

from __future__ import annotations

import logging
from typing import Protocol

from babylon.economics.gamma.types import GammaBasket, GammaIII, ShadowSubsidy

logger = logging.getLogger(__name__)


class ShadowSubsidyCalculator(Protocol):
    """Protocol for shadow subsidy computation.

    Computes two types of shadow subsidies:
    1. Phi_III: Reproductive labor shadow subsidy (unpaid care)
    2. Phi_imperial: Imperial shadow subsidy (compressed peripheral labor)

    Example:
        >>> calculator = DefaultShadowSubsidyCalculator()
        >>> phi_iii = calculator.compute_phi_iii(gamma_iii_result, melt=65.0)
        >>> phi_imperial = calculator.compute_phi_imperial(gamma_basket_result, 15e12)
    """

    def compute_phi_iii(
        self,
        gamma_iii: GammaIII,
        melt: float | None,
    ) -> ShadowSubsidy:
        """Compute reproductive shadow subsidy Phi_III.

        Args:
            gamma_iii: GammaIII result with visibility coefficient.
            melt: MELT (tau) in $/labor-hour, or None if unavailable.

        Returns:
            ShadowSubsidy with phi_iii_labor_hours (always) and
            phi_iii_dollars (if MELT available).
        """
        ...

    def compute_phi_imperial(
        self,
        gamma_basket: GammaBasket,
        consumption: float,
    ) -> float:
        """Compute imperial shadow subsidy Phi_imperial.

        Args:
            gamma_basket: GammaBasket result with basket visibility.
            consumption: Total consumption in dollars.

        Returns:
            Phi_imperial in dollars.
        """
        ...

    def compute_total_shadow(
        self,
        phi_iii: ShadowSubsidy,
        phi_imperial: float,
    ) -> ShadowSubsidy:
        """Combine both shadow subsidies into a total.

        Args:
            phi_iii: ShadowSubsidy from compute_phi_iii.
            phi_imperial: Phi_imperial from compute_phi_imperial.

        Returns:
            ShadowSubsidy with total_shadow_dollars set (if MELT available).
        """
        ...


class DefaultShadowSubsidyCalculator:
    """Default implementation of ShadowSubsidyCalculator.

    Computes shadow subsidies from gamma visibility coefficients.
    Supports graceful degradation: when MELT is unavailable, returns
    labor-hour values without dollar conversion.

    Example:
        >>> calculator = DefaultShadowSubsidyCalculator()
        >>> gamma_iii = GammaIII(year=2022, paid_care_hours=16.5,
        ...     unpaid_care_hours=33.0, gamma_iii=0.333, fortunati_exploitation=2.0)
        >>> result = calculator.compute_phi_iii(gamma_iii, melt=65.0)
        >>> print(f"Phi_III = ${result.phi_iii_dollars/1e12:.1f}T")
    """

    def compute_phi_iii(
        self,
        gamma_iii: GammaIII,
        melt: float | None,
    ) -> ShadowSubsidy:
        """Compute reproductive shadow subsidy.

        Formula: Phi_III = (1 - gamma_III) * L_unpaid * tau

        When MELT unavailable, computes labor-hours only:
            phi_iii_labor_hours = (1 - gamma_III) * L_unpaid

        Args:
            gamma_iii: GammaIII result.
            melt: MELT (tau) in $/labor-hour, or None.

        Returns:
            ShadowSubsidy with phi_iii values.
        """
        invisible_fraction = 1.0 - gamma_iii.gamma_iii
        phi_labor_hours = invisible_fraction * gamma_iii.unpaid_care_hours

        phi_dollars: float | None = None
        melt_available = melt is not None

        if melt is not None:
            # Convert labor-hours (billions) to dollars
            phi_dollars = phi_labor_hours * 1_000_000_000 * melt

        return ShadowSubsidy(
            year=gamma_iii.year,
            phi_iii_dollars=phi_dollars,
            phi_iii_labor_hours=phi_labor_hours,
            phi_imperial=0.0,
            total_shadow_dollars=phi_dollars,
            melt_available=melt_available,
        )

    def compute_phi_imperial(
        self,
        gamma_basket: GammaBasket,
        consumption: float,
    ) -> float:
        """Compute imperial shadow subsidy.

        Formula: Phi_imperial = (1 - gamma_basket) * Consumption

        Args:
            gamma_basket: GammaBasket result.
            consumption: Total consumption in dollars.

        Returns:
            Phi_imperial in dollars.
        """
        subsidy_fraction = 1.0 - gamma_basket.gamma_basket
        phi_imperial = subsidy_fraction * consumption

        logger.debug(
            "Phi_imperial = (1 - %.3f) * $%.1fT = $%.1fT",
            gamma_basket.gamma_basket,
            consumption / 1e12,
            phi_imperial / 1e12,
        )

        return phi_imperial

    def compute_total_shadow(
        self,
        phi_iii: ShadowSubsidy,
        phi_imperial: float,
    ) -> ShadowSubsidy:
        """Combine both shadow subsidies.

        Args:
            phi_iii: Result from compute_phi_iii.
            phi_imperial: Result from compute_phi_imperial.

        Returns:
            Combined ShadowSubsidy.
        """
        total_dollars: float | None = None
        if phi_iii.phi_iii_dollars is not None:
            total_dollars = phi_iii.phi_iii_dollars + phi_imperial

        return ShadowSubsidy(
            year=phi_iii.year,
            phi_iii_dollars=phi_iii.phi_iii_dollars,
            phi_iii_labor_hours=phi_iii.phi_iii_labor_hours,
            phi_imperial=phi_imperial,
            total_shadow_dollars=total_dollars,
            melt_available=phi_iii.melt_available,
        )


__all__ = ["DefaultShadowSubsidyCalculator", "ShadowSubsidyCalculator"]
