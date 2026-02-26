"""VisibilityMetric adapter wrapping the gamma module (Feature 015).

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Adapts DefaultGammaIIICalculator and DefaultShadowSubsidyCalculator outputs
into the VisibilityMetric and ShadowSubsidyTensor types defined for the
tensor hierarchy.

The gamma module computes g_33 (Dept III visibility) from ATUS/QCEW data.
Departments I, IIa, IIb are assigned g ≈ 1.0 since their labor is almost
entirely paid/visible (QCEW covers ~97% of wage employment).

See Also:
    :mod:`babylon.economics.gamma`: Feature 015 gamma visibility module.
    :mod:`babylon.economics.tensor_hierarchy.types`: VisibilityMetric, ShadowSubsidyTensor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.tensor_hierarchy.types import (
    ShadowSubsidyTensor,
    VisibilityMetric,
)

if TYPE_CHECKING:
    from babylon.economics.gamma.gamma_iii import GammaIIICalculator
    from babylon.economics.gamma.shadow_subsidy import ShadowSubsidyCalculator

logger = logging.getLogger(__name__)

# Productive departments (I, IIa, IIb) are nearly fully commodified.
# These constants represent the visible fraction of labor in each department.
_G_PRODUCTIVE = 0.97  # 97% visibility for Depts I, IIa, IIb (QCEW coverage rate)


class DefaultVisibilitySource:
    """Wraps gamma module to produce VisibilityMetric and ShadowSubsidyTensor.

    Calls DefaultGammaIIICalculator to obtain g_33 from ATUS data,
    and assigns g_11 = g_22a = g_22b = 0.97 (QCEW coverage for productive depts).

    The resulting 4-vector g_diagonal = [g_11, g_22a, g_22b, g_33] forms the
    diagonal of the visibility tensor G, where G[i,i] = fraction of dept i
    labor that is commodified (paid/visible in national accounts).

    Args:
        gamma_calculator: GammaIIICalculator instance (from Feature 015).
        shadow_calculator: ShadowSubsidyCalculator instance (from Feature 015).

    Example:
        >>> from babylon.economics.gamma.gamma_iii import DefaultGammaIIICalculator
        >>> from babylon.economics.gamma.shadow_subsidy import DefaultShadowSubsidyCalculator
        >>> source = DefaultVisibilitySource(
        ...     gamma_calculator=DefaultGammaIIICalculator(...),
        ...     shadow_calculator=DefaultShadowSubsidyCalculator(...),
        ... )
        >>> metric = source.get_visibility(2021)
    """

    def __init__(
        self,
        gamma_calculator: GammaIIICalculator,
        shadow_calculator: ShadowSubsidyCalculator,
    ) -> None:
        """Initialize with gamma module calculators.

        Args:
            gamma_calculator: Computes g_33 from ATUS/QCEW data.
            shadow_calculator: Computes Phi_III shadow subsidy.
        """
        self._gamma = gamma_calculator
        self._shadow = shadow_calculator

    def get_visibility(self, year: int) -> VisibilityMetric | NoDataSentinel:
        """Compute 4-department visibility vector for a given year.

        Args:
            year: Calendar year.

        Returns:
            VisibilityMetric with g_diagonal = [g_11, g_22a, g_22b, g_33],
            or NoDataSentinel if ATUS data is unavailable for that year.
        """
        gamma_result = self._gamma.compute(year)
        if isinstance(gamma_result, NoDataSentinel):
            return gamma_result

        g_33 = float(gamma_result.gamma_iii)
        g_diag = np.array([_G_PRODUCTIVE, _G_PRODUCTIVE, _G_PRODUCTIVE, g_33])

        return VisibilityMetric(
            year=year,
            g_diagonal=g_diag,
            g_11=_G_PRODUCTIVE,
            g_22a=_G_PRODUCTIVE,
            g_22b=_G_PRODUCTIVE,
            g_33=g_33,
            is_estimated=True,
        )

    def get_shadow_subsidy(self, year: int) -> ShadowSubsidyTensor | NoDataSentinel:
        """Compute shadow subsidy tensor for Dept III reproductive labor.

        Args:
            year: Calendar year.

        Returns:
            ShadowSubsidyTensor with phi_iii_labor_hours and phi_iii_dollars,
            or NoDataSentinel if data is unavailable for that year.
        """
        gamma_result = self._gamma.compute(year)
        if isinstance(gamma_result, NoDataSentinel):
            return gamma_result

        # compute_phi_iii requires the GammaIII object, not just the year.
        # Pass melt=None since MELT availability is handled inside the calculator.
        shadow_result = self._shadow.compute_phi_iii(gamma_result, melt=None)

        return ShadowSubsidyTensor(
            year=year,
            phi_iii_labor_hours=float(shadow_result.phi_iii_labor_hours),
            phi_iii_dollars=shadow_result.phi_iii_dollars,
            melt_available=bool(shadow_result.melt_available),
        )


__all__ = ["DefaultVisibilitySource"]
