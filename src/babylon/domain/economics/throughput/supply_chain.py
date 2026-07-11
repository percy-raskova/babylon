"""Supply chain depth analysis service.

Feature: 014-throughput-position
Date: 2026-02-02

This module implements supply chain depth computation for US counties.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Protocol

from babylon.domain.economics.tensor import NoDataSentinel
from babylon.domain.economics.throughput.naics_depth import (
    get_depth,
    validate_depth,
)
from babylon.domain.economics.throughput.types import WageShareEstimate

if TYPE_CHECKING:
    from babylon.domain.economics.throughput.calculator import ThroughputCalculator
    from babylon.domain.economics.throughput.data_sources import QCEWCountyNAICSSource

logger = logging.getLogger(__name__)

# Wage share thresholds per FR-008
LAMBDA_EXPECTED_MAX: float = 1.0
LAMBDA_WARNING_THRESHOLD: float = 1.0


class SupplyChainAnalyzer(Protocol):
    """Protocol for supply chain depth and wage share analysis.

    Computes:
    - D: Employment-weighted average supply chain depth for a county
    - λ_proxy: Wage share proxy for industry-county combinations

    Supply chain depth indicates where a county sits in the value chain:
    - D < 1.5: Extraction-oriented (mining, agriculture)
    - D ≈ 2.0: Manufacturing/transformation
    - D ≈ 3.0: Logistics/coordination
    - D > 4.0: Service/financial coordination

    Example:
        >>> analyzer = DefaultSupplyChainAnalyzer(qcew_source)
        >>> depth = analyzer.compute_depth("36061", 2022)  # Manhattan
        >>> print(f"Manhattan D = {depth:.2f}")
        Manhattan D = 4.3
    """

    def compute_depth(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute employment-weighted supply chain depth for a county.

        Formula: D = Σ(employment[naics] × depth[naics]) / Σ employment

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            D (0.0-5.0 scale), or NoDataSentinel if insufficient data.

        Raises:
            ValueError: If computed D is outside [0.0, 5.0] (indicates bug)
        """
        ...

    def get_naics_depth(self, naics: str) -> float | None:
        """Get supply chain depth value for a NAICS sector.

        Args:
            naics: 2-digit NAICS sector code

        Returns:
            Depth value (0.0-5.0), or None if unknown sector
        """
        ...

    def compute_wage_share_proxy(
        self, fips: str, naics: str, year: int
    ) -> WageShareEstimate | NoDataSentinel:
        """Compute wage share proxy for an industry-county combination.

        Formula: λ_proxy = avg_wage / τ_through

        Args:
            fips: 5-character county FIPS code
            naics: 2-digit NAICS sector code
            year: Calendar year

        Returns:
            WageShareEstimate container, or NoDataSentinel if unavailable
        """
        ...

    def get_sector_employment(self, fips: str, year: int) -> dict[str, int] | NoDataSentinel:
        """Get employment by NAICS sector for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Dict mapping NAICS codes to employment counts,
            or NoDataSentinel if county data unavailable.
        """
        ...

    def get_sector_coverage(self, fips: str, year: int) -> tuple[int, int, int] | NoDataSentinel:
        """Get sector coverage statistics for data quality assessment.

        Returns information about how many NAICS sectors had data available
        vs how many were mapped in the depth calculation. Used by
        ThroughputCalculator to set data_quality field.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Tuple of (sectors_with_data, sectors_mapped, employment_covered),
            or NoDataSentinel if county data unavailable.

            - sectors_with_data: Number of NAICS sectors with employment data
            - sectors_mapped: Number of sectors that have depth mappings
            - employment_covered: Total employment in mapped sectors
        """
        ...


class DefaultSupplyChainAnalyzer:
    """Default implementation of SupplyChainAnalyzer.

    Computes supply chain depth and wage share proxy using injected data sources.
    """

    def __init__(
        self,
        qcew_source: QCEWCountyNAICSSource,
        throughput_calculator: ThroughputCalculator | None = None,
    ) -> None:
        """Initialize the analyzer with data sources.

        Args:
            qcew_source: Source for county employment/wage data (QCEW)
            throughput_calculator: Optional calculator for τ_through (needed for λ_proxy)
        """
        self._qcew_source = qcew_source
        self._throughput_calculator = throughput_calculator

    def compute_depth(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute employment-weighted supply chain depth for a county.

        Formula: D = Σ(employment[naics] × depth[naics]) / Σ employment
        """
        # Get employment by NAICS
        sector_employment = self._qcew_source.get_county_employment_by_naics(fips, year)
        if not sector_employment:
            return NoDataSentinel(fips, year, f"No NAICS employment data for FIPS {fips} in {year}")

        # Compute weighted average depth
        total_weighted_depth = 0.0
        total_employment = 0

        for naics, employment in sector_employment.items():
            depth = get_depth(naics)
            if depth is not None:
                total_weighted_depth += employment * depth
                total_employment += employment
            else:
                logger.debug(
                    "Unknown NAICS %s in FIPS %s (employment=%d), skipping",
                    naics,
                    fips,
                    employment,
                )

        if total_employment == 0:
            return NoDataSentinel(
                fips,
                year,
                f"No employment in mapped NAICS sectors for FIPS {fips} in {year}",
            )

        # Compute D
        depth = total_weighted_depth / total_employment

        # Validate depth (should always pass if NAICS mapping is correct)
        if not validate_depth(depth):
            msg = f"Computed depth {depth} outside valid range [0.0, 5.0]"
            raise ValueError(msg)

        return depth

    def get_naics_depth(self, naics: str) -> float | None:
        """Get supply chain depth value for a NAICS sector."""
        return get_depth(naics)

    def compute_wage_share_proxy(
        self, fips: str, naics: str, year: int
    ) -> WageShareEstimate | NoDataSentinel:
        """Compute wage share proxy for an industry-county combination.

        Formula: λ_proxy = avg_wage / τ_through
        """
        # Get average weekly wage
        avg_weekly_wage = self._qcew_source.get_county_naics_wages(fips, naics, year)
        if avg_weekly_wage is None:
            return NoDataSentinel(
                fips, year, f"Wages unavailable for FIPS {fips} NAICS {naics} in {year}"
            )

        # Get employment for confidence calculation
        employment = self._qcew_source.get_county_naics_employment(fips, naics, year)

        # Get τ_through if calculator available
        if self._throughput_calculator is None:
            return NoDataSentinel(
                fips,
                year,
                "ThroughputCalculator not provided, cannot compute λ_proxy",
            )

        tau_through = self._throughput_calculator.compute_throughput_intensity(fips, year)
        if isinstance(tau_through, NoDataSentinel):
            return tau_through

        # Convert weekly wage to hourly (40 hours/week)
        avg_hourly_wage = avg_weekly_wage / 40.0

        # Compute λ_proxy = avg_wage / τ_through
        lambda_proxy = avg_hourly_wage / tau_through

        # Determine confidence level
        confidence = self._determine_confidence(employment, lambda_proxy)

        # Flag if λ_proxy > 1.0
        if lambda_proxy > LAMBDA_WARNING_THRESHOLD:
            logger.warning(
                "FIPS %s NAICS %s year %d: λ_proxy=%.2f > 1.0 indicates data quality issue",
                fips,
                naics,
                year,
                lambda_proxy,
            )

        return WageShareEstimate(
            fips=fips,
            naics=naics,
            year=year,
            lambda_proxy=lambda_proxy,
            confidence=confidence,
            avg_weekly_wage=avg_weekly_wage,
            employment=employment,
        )

    def get_sector_employment(self, fips: str, year: int) -> dict[str, int] | NoDataSentinel:
        """Get employment by NAICS sector for a county."""
        sector_employment = self._qcew_source.get_county_employment_by_naics(fips, year)
        if not sector_employment:
            return NoDataSentinel(fips, year, f"No NAICS employment data for FIPS {fips} in {year}")
        return sector_employment

    def get_sector_coverage(self, fips: str, year: int) -> tuple[int, int, int] | NoDataSentinel:
        """Get sector coverage statistics for data quality assessment.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Tuple of (sectors_with_data, sectors_mapped, employment_covered),
            or NoDataSentinel if county data unavailable.
        """
        sector_employment = self._qcew_source.get_county_employment_by_naics(fips, year)
        if not sector_employment:
            return NoDataSentinel(fips, year, f"No NAICS employment data for FIPS {fips} in {year}")

        sectors_with_data = len(sector_employment)
        sectors_mapped = 0
        employment_covered = 0

        for naics, employment in sector_employment.items():
            depth = get_depth(naics)
            if depth is not None:
                sectors_mapped += 1
                employment_covered += employment

        return (sectors_with_data, sectors_mapped, employment_covered)

    def _determine_confidence(
        self, employment: int | None, lambda_proxy: float
    ) -> Literal["high", "medium", "low"]:
        """Determine confidence level based on data quality indicators.

        Args:
            employment: Employment count (None if suppressed)
            lambda_proxy: Computed wage share proxy

        Returns:
            Confidence level: "high", "medium", or "low"
        """
        # Low confidence: data quality issues
        if lambda_proxy > LAMBDA_EXPECTED_MAX:
            return "low"

        # Low confidence: suppressed employment
        if employment is None:
            return "low"

        # Medium confidence: small sample
        if employment < 100:
            return "low"
        if employment < 1000:
            return "medium"

        # High confidence: sufficient data
        return "high"


__all__ = [
    "SupplyChainAnalyzer",
    "DefaultSupplyChainAnalyzer",
]
