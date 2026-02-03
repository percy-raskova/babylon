"""Throughput calculator service.

Feature: 014-throughput-position
Date: 2026-02-02

This module implements the throughput position computation for US counties.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Protocol

from babylon.economics.tensor import NoDataSentinel
from babylon.economics.throughput.types import CommuterAdjustedMetrics, ThroughputMetrics

if TYPE_CHECKING:
    from babylon.economics.melt import MELTCalculator
    from babylon.economics.throughput.data_sources import (
        BEACountyGDPSource,
        LODESCommuterFlowSource,
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

    def compute_all_counties(self, year: int) -> dict[str, ThroughputMetrics | NoDataSentinel]:
        """Compute throughput metrics for all counties with available data.

        Batch processing method for computing metrics across all US counties.
        Performance target: 3,000+ counties in <30s.

        Args:
            year: Calendar year

        Returns:
            Dict mapping FIPS codes to ThroughputMetrics or NoDataSentinel
        """
        ...


class DefaultThroughputCalculator:
    """Default implementation of ThroughputCalculator.

    Computes throughput metrics using injected data sources.
    Optionally supports commuter-adjusted metrics via LODES data.
    """

    def __init__(
        self,
        gdp_source: BEACountyGDPSource,
        qcew_source: QCEWCountyNAICSSource,
        supply_chain_analyzer: SupplyChainAnalyzer,
        melt_calculator: MELTCalculator | None = None,
        commuter_source: LODESCommuterFlowSource | None = None,
    ) -> None:
        """Initialize the calculator with data sources.

        Args:
            gdp_source: Source for county GDP data (BEA CAGDP1)
            qcew_source: Source for county employment data (QCEW)
            supply_chain_analyzer: Analyzer for supply chain depth
            melt_calculator: Optional MELT calculator for π computation
            commuter_source: Optional LODES commuter flow source for
                commuter-adjusted metrics (T034-T036)
        """
        self._gdp_source = gdp_source
        self._qcew_source = qcew_source
        self._supply_chain = supply_chain_analyzer
        self._melt_calculator = melt_calculator
        self._commuter_source = commuter_source

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

    def compute_all_counties(self, year: int) -> dict[str, ThroughputMetrics | NoDataSentinel]:
        """Compute throughput metrics for all counties with available data.

        Batch processing for computing metrics across all US counties.
        Uses the GDP source's get_all_counties() to find available counties.

        Args:
            year: Calendar year

        Returns:
            Dict mapping FIPS codes to ThroughputMetrics or NoDataSentinel
        """
        results: dict[str, ThroughputMetrics | NoDataSentinel] = {}

        # Get all counties with GDP data
        all_counties = self._gdp_source.get_all_counties(year)
        if not all_counties:
            return results

        # Compute metrics for each county
        for fips in all_counties:
            metrics = self.compute_metrics(fips, year)
            results[fips] = metrics

        return results

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

    # =========================================================================
    # Commuter-Adjusted Methods (T034-T036)
    # =========================================================================

    def compute_residence_throughput(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute throughput intensity using residence-based employment.

        Instead of using workplace employment (jobs located in county),
        uses residence employment (workers who LIVE in county) from LODES.

        Formula: τ_residence = GDP / (residence_employment × 2080)

        This is useful for bedroom communities where workers commute to
        nearby job centers. Their "connection" to throughput is better
        captured by where they work (and thus what throughput they handle)
        rather than jobs in their home county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            τ_residence in $/labor-hour, or NoDataSentinel if unavailable
        """
        if self._commuter_source is None:
            return NoDataSentinel(
                fips, year, "Commuter source unavailable: LODESCommuterFlowSource not provided"
            )

        # Get county GDP
        gdp = self._gdp_source.get_county_gdp(fips, year)
        if gdp is None:
            return NoDataSentinel(fips, year, f"GDP unavailable for FIPS {fips} in {year}")

        # Get residence employment from LODES
        residence_emp = self._commuter_source.get_residence_employment(fips, year)
        if residence_emp is None:
            return NoDataSentinel(
                fips, year, f"LODES residence employment unavailable for FIPS {fips} in {year}"
            )

        # Check analytical threshold
        if residence_emp < MINIMUM_EMPLOYMENT_THRESHOLD:
            return NoDataSentinel(
                fips,
                year,
                f"INSUFFICIENT_DATA: residence employment {residence_emp} below "
                f"{MINIMUM_EMPLOYMENT_THRESHOLD} analytical threshold",
            )

        # Compute τ_residence = GDP / (L_residence × 2080)
        labor_hours = residence_emp * HOURS_PER_YEAR
        tau_residence = gdp / labor_hours

        return tau_residence

    def compute_commuter_adjusted_metrics(
        self, fips: str, year: int
    ) -> CommuterAdjustedMetrics | NoDataSentinel:
        """Compute full commuter-adjusted throughput metrics for a county.

        Combines standard workplace-based metrics with residence-based metrics
        from LODES data to provide a complete picture of throughput position
        adjusted for commuter flows.

        Key insight:
            For bedroom communities (net job exporters):
            - τ_workplace underestimates worker throughput (few local jobs)
            - τ_residence better reflects where workers actually engage throughput
            - pi_residence should be closer to nearby job center's pi_workplace

            For job centers (net job importers):
            - τ_workplace reflects actual job-based throughput
            - τ_residence shows what residents alone could sustain
            - The gap indicates dependence on commuter workforce

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            CommuterAdjustedMetrics container, or NoDataSentinel if unavailable
        """
        # First compute standard workplace-based throughput (required)
        tau_workplace = self.compute_throughput_intensity(fips, year)
        if isinstance(tau_workplace, NoDataSentinel):
            return tau_workplace

        # Compute workplace π (optional - depends on MELT)
        pi_workplace: float | None = None
        if self._melt_calculator is not None:
            pi_result = self.compute_throughput_position(fips, year)
            if not isinstance(pi_result, NoDataSentinel):
                pi_workplace = pi_result

        # Default values for when commuter data unavailable
        tau_residence: float | None = None
        pi_residence: float | None = None
        net_commuter_balance: int = 0
        commuter_ratio: float | None = None
        is_job_importer: bool = False
        has_commuter_data: bool = False

        # Try to get commuter-adjusted metrics
        if self._commuter_source is not None:
            # Get net commuter balance
            balance = self._commuter_source.get_net_commuter_balance(fips, year)
            if balance is not None:
                has_commuter_data = True
                net_commuter_balance = balance
                is_job_importer = balance > 0

                # Compute residence-based throughput
                tau_res_result = self.compute_residence_throughput(fips, year)
                if not isinstance(tau_res_result, NoDataSentinel):
                    tau_residence = tau_res_result

                    # Compute residence π if MELT available
                    if self._melt_calculator is not None:
                        tau_national = self._melt_calculator.get_melt(year)
                        if not isinstance(tau_national, NoDataSentinel):
                            pi_residence = tau_residence / tau_national

                # Compute commuter ratio (residence_emp / workplace_emp)
                residence_emp = self._commuter_source.get_residence_employment(fips, year)
                workplace_emp = self._qcew_source.get_county_total_employment(fips, year)
                if residence_emp is not None and workplace_emp is not None and workplace_emp > 0:
                    commuter_ratio = residence_emp / workplace_emp

        return CommuterAdjustedMetrics(
            fips=fips,
            year=year,
            tau_through_workplace=tau_workplace,
            pi_workplace=pi_workplace,
            tau_through_residence=tau_residence,
            pi_residence=pi_residence,
            net_commuter_balance=net_commuter_balance,
            commuter_ratio=commuter_ratio,
            is_job_importer=is_job_importer,
            has_commuter_data=has_commuter_data,
        )


__all__ = [
    "ThroughputCalculator",
    "DefaultThroughputCalculator",
    "HOURS_PER_YEAR",
    "MINIMUM_EMPLOYMENT_THRESHOLD",
]
