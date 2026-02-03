"""Throughput calculator service.

Feature: 014-throughput-position
Date: 2026-02-02

This module implements the throughput position computation for US counties.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Protocol

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.throughput.types import ThroughputMetrics

if TYPE_CHECKING:
    from babylon.economics.melt import MELTCalculator
    from babylon.economics.throughput.data_sources import (
        BEACountyGDPSource,
        QCEWCountyNAICSSource,
    )
    from babylon.economics.throughput.supply_chain import SupplyChainAnalyzer

logger = logging.getLogger(__name__)

# Standard work-year hours (40 hours/week × 52 weeks)
HOURS_PER_YEAR: int = 2080

# Sanity range thresholds per FR-008
TAU_THROUGH_EXPECTED_MIN: float = 20.0  # $/hour
TAU_THROUGH_EXPECTED_MAX: float = 200.0  # $/hour
TAU_THROUGH_WARNING_MIN: float = 10.0  # $/hour
TAU_THROUGH_WARNING_MAX: float = 500.0  # $/hour
PI_EXPECTED_MIN: float = 0.2
PI_EXPECTED_MAX: float = 3.0

# Analytical thresholds per spec
MINIMUM_EMPLOYMENT_THRESHOLD: int = 1000  # INSUFFICIENT_DATA threshold


class ThroughputCalculator(Protocol):
    """Protocol for throughput position computation.

    Computes:
        - τ_through = GDP / (employment × 2080) - throughput intensity
        - π = τ_through / τ_national - throughput position

    Example:
        >>> calculator = DefaultThroughputCalculator(bea_source, qcew_source, melt_calc)
        >>> metrics = calculator.compute_metrics("26163", 2022)
        >>> print(f"Wayne County π = {metrics.pi:.2f}")
        Wayne County π = 0.90
    """

    def compute_throughput_intensity(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute throughput intensity for a county.

        Formula: τ_through = GDP / (employment × 2080)

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            τ_through in $/labor-hour, or NoDataSentinel if unavailable
        """
        ...

    def compute_throughput_position(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute throughput position for a county.

        Formula: π = τ_through / τ_national

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            π (dimensionless), or NoDataSentinel if unavailable
        """
        ...

    def compute_metrics(self, fips: str, year: int) -> ThroughputMetrics | NoDataSentinel:
        """Compute full throughput metrics for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            ThroughputMetrics container, or NoDataSentinel if unavailable
        """
        ...

    def validate_throughput(self, tau_through: float) -> tuple[bool, str | None]:
        """Validate throughput intensity against sanity ranges.

        Args:
            tau_through: Throughput intensity to validate

        Returns:
            Tuple of (valid, warning_message)
        """
        ...


class DefaultThroughputCalculator:
    """Default implementation of ThroughputCalculator.

    Computes throughput metrics using injected data sources.
    """

    def __init__(
        self,
        gdp_source: BEACountyGDPSource,
        qcew_source: QCEWCountyNAICSSource,
        supply_chain_analyzer: SupplyChainAnalyzer,
        melt_calculator: MELTCalculator | None = None,
    ) -> None:
        """Initialize the calculator with data sources.

        Args:
            gdp_source: Source for county GDP data (BEA CAGDP1)
            qcew_source: Source for county employment data (QCEW)
            supply_chain_analyzer: Analyzer for supply chain depth
            melt_calculator: Optional MELT calculator for π computation
        """
        self._gdp_source = gdp_source
        self._qcew_source = qcew_source
        self._supply_chain = supply_chain_analyzer
        self._melt_calculator = melt_calculator

    def compute_throughput_intensity(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute throughput intensity for a county.

        Formula: τ_through = GDP / (employment × 2080)
        """
        # Get county GDP
        gdp = self._gdp_source.get_county_gdp(fips, year)
        if gdp is None:
            return NoDataSentinel(fips, year, f"GDP unavailable for FIPS {fips} in {year}")

        # Get county employment
        employment = self._qcew_source.get_county_total_employment(fips, year)
        if employment is None:
            return NoDataSentinel(fips, year, f"Employment unavailable for FIPS {fips} in {year}")

        # Check analytical threshold
        if employment < MINIMUM_EMPLOYMENT_THRESHOLD:
            return NoDataSentinel(
                fips,
                year,
                f"INSUFFICIENT_DATA: county employment {employment} below "
                f"{MINIMUM_EMPLOYMENT_THRESHOLD} analytical threshold",
            )

        # Compute τ_through = GDP / (L × 2080)
        labor_hours = employment * HOURS_PER_YEAR
        tau_through = gdp / labor_hours

        return tau_through

    def compute_throughput_position(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute throughput position for a county.

        Formula: π = τ_through / τ_national
        """
        # Compute τ_through
        tau_through = self.compute_throughput_intensity(fips, year)
        if isinstance(tau_through, NoDataSentinel):
            return tau_through

        # Check if MELT calculator available
        if self._melt_calculator is None:
            return NoDataSentinel(fips, year, "MELT unavailable: MELTCalculator not provided")

        # Get national MELT
        tau_national = self._melt_calculator.get_melt(year)
        if isinstance(tau_national, NoDataSentinel):
            return NoDataSentinel(
                fips, year, f"MELT unavailable for year {year}: {tau_national.reason}"
            )

        # Compute π = τ_through / τ_national
        pi = tau_through / tau_national

        return pi

    def compute_metrics(self, fips: str, year: int) -> ThroughputMetrics | NoDataSentinel:
        """Compute full throughput metrics for a county."""
        # Compute τ_through (required)
        tau_through = self.compute_throughput_intensity(fips, year)
        if isinstance(tau_through, NoDataSentinel):
            return tau_through

        # Validate τ_through
        is_valid, warning = self.validate_throughput(tau_through)
        if warning:
            logger.warning("FIPS %s year %d: %s", fips, year, warning)

        # Compute supply chain depth (required)
        depth = self._supply_chain.compute_depth(fips, year)
        if isinstance(depth, NoDataSentinel):
            return depth

        # Compute π (optional - depends on MELT availability)
        pi: float | None = None
        if self._melt_calculator is not None:
            pi_result = self.compute_throughput_position(fips, year)
            if not isinstance(pi_result, NoDataSentinel):
                pi = pi_result
                # Validate π
                if pi < PI_EXPECTED_MIN or pi > PI_EXPECTED_MAX:
                    logger.warning(
                        "FIPS %s year %d: π=%.2f outside expected range [%.1f, %.1f]",
                        fips,
                        year,
                        pi,
                        PI_EXPECTED_MIN,
                        PI_EXPECTED_MAX,
                    )

        # Determine data quality based on sector coverage
        data_quality: Literal["high", "medium", "low"] = "high"
        is_estimated = False

        sector_coverage = self._supply_chain.get_sector_coverage(fips, year)
        if not isinstance(sector_coverage, NoDataSentinel):
            sectors_with_data, sectors_mapped, _ = sector_coverage
            if sectors_with_data > 0:
                coverage_ratio = sectors_mapped / sectors_with_data
                if coverage_ratio < 0.5:
                    data_quality = "low"
                    is_estimated = True
                elif coverage_ratio < 0.8:
                    data_quality = "medium"
                    is_estimated = True
                # else: high quality (>= 80% coverage)

        return ThroughputMetrics(
            fips=fips,
            year=year,
            tau_through=tau_through,
            pi=pi,
            supply_chain_depth=depth,
            is_estimated=is_estimated,
            data_quality=data_quality,
        )

    def validate_throughput(self, tau_through: float) -> tuple[bool, str | None]:
        """Validate throughput intensity against sanity ranges."""
        if tau_through < TAU_THROUGH_WARNING_MIN:
            return (
                False,
                f"τ_through=${tau_through:.2f}/hour below minimum ${TAU_THROUGH_WARNING_MIN}/hour",
            )
        if tau_through > TAU_THROUGH_WARNING_MAX:
            return (
                False,
                f"τ_through=${tau_through:.2f}/hour above maximum ${TAU_THROUGH_WARNING_MAX}/hour",
            )
        if tau_through < TAU_THROUGH_EXPECTED_MIN:
            return (
                True,
                f"τ_through=${tau_through:.2f}/hour below expected minimum "
                f"${TAU_THROUGH_EXPECTED_MIN}/hour",
            )
        if tau_through > TAU_THROUGH_EXPECTED_MAX:
            return (
                True,
                f"τ_through=${tau_through:.2f}/hour above expected maximum "
                f"${TAU_THROUGH_EXPECTED_MAX}/hour",
            )
        return (True, None)


__all__ = [
    "ThroughputCalculator",
    "DefaultThroughputCalculator",
    "HOURS_PER_YEAR",
    "MINIMUM_EMPLOYMENT_THRESHOLD",
]
