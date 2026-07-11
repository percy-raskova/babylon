"""GammaIIICalculator service for computing reproductive labor visibility.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module implements the gamma_III computation per TVT Axiom I.5:
    gamma_III = L_paid_care / (L_paid_care + L_unpaid_care)

TVT Axiom Reference:
    - I.5: Department III (reproductive labor visibility)
    - Fortunati, "Arcane of Reproduction" (1981)

See Also:
    :mod:`babylon.domain.economics.gamma.adapters`: QCEW care sector adapter
    :mod:`babylon.domain.economics.gamma.data_sources`: Data source protocols
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from babylon.domain.economics.gamma.types import GammaIII
from babylon.domain.economics.gamma.validation import validate_gamma_iii
from babylon.domain.economics.protocol_kit import CachedSource
from babylon.domain.economics.tensor import NoDataSentinel

if TYPE_CHECKING:
    from babylon.domain.economics.gamma.data_sources import (
        PaidCareHoursSource,
        UnpaidCareHoursSource,
    )

logger = logging.getLogger(__name__)

# Year range for ATUS data availability
MIN_YEAR: int = 2003
MAX_YEAR: int = 2024


class GammaIIICalculator(Protocol):
    """Protocol for reproductive labor visibility computation.

    Gamma_III measures the fraction of care labor visible to the price system.
    A lower gamma_III indicates more unpaid/invisible reproductive labor.

    Formula:
        gamma_III = L_paid_care / (L_paid_care + L_unpaid_care)

    Example:
        >>> calculator = DefaultGammaIIICalculator(unpaid_source, paid_source)
        >>> result = calculator.compute(2022)
        >>> if result:  # Not NoDataSentinel
        ...     print(f"gamma_III = {result.gamma_iii:.3f}")
    """

    def compute(self, year: int) -> GammaIII | NoDataSentinel:
        """Compute gamma_III for a given year.

        Args:
            year: Calendar year (2003-2024 for ATUS availability).

        Returns:
            GammaIII result or NoDataSentinel with descriptive reason.
        """
        ...

    def get_paid_care_hours(self, year: int) -> float | NoDataSentinel:
        """Get paid care hours from QCEW data.

        Args:
            year: Calendar year.

        Returns:
            Paid care hours in billions, or NoDataSentinel.
        """
        ...

    def get_unpaid_care_hours(self, year: int) -> float | NoDataSentinel:
        """Get unpaid care hours from ATUS data.

        Args:
            year: Calendar year.

        Returns:
            Unpaid care hours in billions, or NoDataSentinel.
        """
        ...


class DefaultGammaIIICalculator(CachedSource[float]):
    """Default implementation of GammaIIICalculator using ATUS and QCEW data.

    Computes gamma_III = L_paid_care / (L_paid_care + L_unpaid_care) using
    real data sources injected via constructor.

    Args:
        unpaid_source: Data source for unpaid care hours (ATUS).
        paid_source: Data source for paid care hours (QCEW).

    Example:
        >>> calculator = DefaultGammaIIICalculator(atus_source, qcew_adapter)
        >>> result = calculator.compute(2022)
        >>> print(f"gamma_III = {result.gamma_iii:.3f}")
        gamma_III = 0.333
    """

    def __init__(
        self,
        unpaid_source: UnpaidCareHoursSource,
        paid_source: PaidCareHoursSource,
    ) -> None:
        """Initialize with data sources.

        Args:
            unpaid_source: Source for unpaid care hours (ATUS).
            paid_source: Source for paid care hours (QCEW).
        """
        super().__init__()
        self._unpaid_source = unpaid_source
        self._paid_source = paid_source

    def compute(self, year: int) -> GammaIII | NoDataSentinel:
        """Compute gamma_III for a given year.

        Returns distinct NoDataSentinel messages for ATUS vs QCEW failures
        to aid debugging (CHK030 pattern).

        Args:
            year: Calendar year (2003-2024).

        Returns:
            GammaIII result or NoDataSentinel.
        """
        if year < MIN_YEAR or year > MAX_YEAR:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"Year {year} outside ATUS data range [{MIN_YEAR}, {MAX_YEAR}]",
            )

        # Get unpaid care hours (distinct ATUS error message)
        unpaid = self.get_unpaid_care_hours(year)
        if isinstance(unpaid, NoDataSentinel):
            return unpaid

        # Get paid care hours (distinct QCEW error message)
        paid = self.get_paid_care_hours(year)
        if isinstance(paid, NoDataSentinel):
            return paid

        # Compute gamma_III
        total = paid + unpaid
        if total == 0.0:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason="Total care hours is zero (both paid and unpaid)",
            )

        gamma = paid / total

        # Fortunati exploitation rate: (1 - gamma) / gamma
        fortunati = (1.0 - gamma) / gamma if gamma > 0.0 else float("inf")

        # Validate and log
        valid, message = validate_gamma_iii(gamma)
        if message is not None:
            logger.warning("gamma_III validation: %s", message)
        if not valid:
            logger.error("gamma_III FAIL: %s", message)

        return GammaIII(
            year=year,
            paid_care_hours=paid,
            unpaid_care_hours=unpaid,
            gamma_iii=gamma,
            fortunati_exploitation=fortunati,
        )

    def get_paid_care_hours(self, year: int) -> float | NoDataSentinel:
        """Get paid care hours from QCEW adapter.

        Args:
            year: Calendar year.

        Returns:
            Paid care hours in billions, or NoDataSentinel.
        """
        hours = self._paid_source.get_paid_care_hours(year)
        if hours is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"QCEW paid care hours unavailable for year {year}",
            )
        return hours

    def get_unpaid_care_hours(self, year: int) -> float | NoDataSentinel:
        """Get unpaid care hours from ATUS data.

        Args:
            year: Calendar year.

        Returns:
            Unpaid care hours in billions, or NoDataSentinel.
        """
        hours = self._unpaid_source.get_unpaid_care_hours(year)
        if hours is None:
            return NoDataSentinel(
                fips="USA",
                year=year,
                reason=f"ATUS unpaid care hours unavailable for year {year}",
            )
        return hours


__all__ = ["DefaultGammaIIICalculator", "GammaIIICalculator"]
