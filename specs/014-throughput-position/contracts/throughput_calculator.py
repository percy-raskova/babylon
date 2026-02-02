"""ThroughputCalculator protocol contract.

Feature: 014-throughput-position
Date: 2026-02-02
Phase: 1 (Contracts)

This module defines the ThroughputCalculator protocol for computing
county-level throughput metrics (τ_through, π).

TVT Extension Reference:
    - τ_through = GDP[fips] / (employment[fips] × 2080)
    - π = τ_through / τ_national
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from babylon.economics.tensor import NoDataSentinel
    from babylon.economics.throughput.types import ThroughputMetrics

# Constants
HOURS_PER_YEAR: int = 2080  # 40 hours/week × 52 weeks/year

# Sanity range constants (per FR-008)
EXPECTED_TAU_THROUGH_MIN: float = 20.0
EXPECTED_TAU_THROUGH_MAX: float = 200.0
WARNING_TAU_THROUGH_MIN: float = 10.0
WARNING_TAU_THROUGH_MAX: float = 500.0

EXPECTED_PI_MIN: float = 0.2
EXPECTED_PI_MAX: float = 3.0


class ThroughputCalculator(Protocol):
    """Protocol for county-level throughput computation.

    Computes throughput metrics for US counties:
    - τ_through: Throughput intensity ($/labor-hour)
    - π: Throughput position (dimensionless ratio)

    Key Insight: Within a single currency zone, wages track THROUGHPUT,
    not value creation. τ_through measures accumulated value flow through
    a location, NOT local value creation.

    TVT Extension Reference:
        - τ_through = GDP[fips] / (employment[fips] × 2080)
        - π = τ_through / τ_national

    Example:
        >>> calculator = DefaultThroughputCalculator(bea_source, qcew_source, melt_calc)
        >>> metrics = calculator.compute_metrics("26163", 2022)  # Wayne County
        >>> print(f"Wayne County π = {metrics.pi:.2f}")
        Wayne County π = 0.90

    See Also:
        :class:`SupplyChainAnalyzer`: Computes supply chain depth (D)
        :class:`MELTCalculator`: Provides national MELT (τ) for π computation
    """

    def compute_throughput_intensity(
        self, fips: str, year: int
    ) -> float | NoDataSentinel:
        """Compute throughput intensity for a county.

        Formula: τ_through = GDP / (employment × 2080)

        Args:
            fips: 5-character county FIPS code (e.g., "26163")
            year: Calendar year (2001-2023 for available data)

        Returns:
            τ_through in $/labor-hour if data available, or NoDataSentinel
            with descriptive reason if data unavailable.

        Example:
            >>> tau = calculator.compute_throughput_intensity("26163", 2022)
            >>> tau
            58.5  # Wayne County throughput ~$58.50/labor-hour
        """
        ...

    def compute_throughput_position(
        self, fips: str, year: int
    ) -> float | NoDataSentinel:
        """Compute throughput position for a county.

        Formula: π = τ_through / τ_national

        π > 1.0 indicates coordination chokepoint (value flows through)
        π < 1.0 indicates value creation/export node (value flows out)

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            π (dimensionless ratio), or NoDataSentinel if unavailable.

        Example:
            >>> pi = calculator.compute_throughput_position("36061", 2022)
            >>> pi
            2.8  # Manhattan is a major coordination chokepoint
        """
        ...

    def compute_metrics(
        self, fips: str, year: int
    ) -> ThroughputMetrics | NoDataSentinel:
        """Compute full throughput metrics for a county.

        Computes τ_through, π, and integrates with SupplyChainAnalyzer
        for supply chain depth (D).

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            ThroughputMetrics container with all metrics, or NoDataSentinel
            if required data is unavailable.

        Example:
            >>> metrics = calculator.compute_metrics("26125", 2022)
            >>> metrics
            ThroughputMetrics(fips='26125', year=2022, tau_through=72.3,
                             pi=1.11, supply_chain_depth=3.8, ...)
        """
        ...

    def validate_throughput(
        self, tau_through: float
    ) -> tuple[bool, str | None]:
        """Validate throughput intensity against sanity ranges (FR-008).

        Sanity Ranges:
            - Expected: $20-200/hour (normal US county range)
            - Warning: $10-500/hour (unusual but possible)
            - Fail: <$10 or >$500/hour (indicates error)

        Args:
            tau_through: Throughput intensity to validate ($/labor-hour)

        Returns:
            Tuple of (valid, message):
            - valid=True, message=None: Within expected range
            - valid=True, message=str: Warning (unusual value)
            - valid=False, message=str: Fail (invalid value)

        Example:
            >>> calculator.validate_throughput(58.5)
            (True, None)
            >>> calculator.validate_throughput(8.0)
            (False, 'τ_through=8.0 outside valid range [10, 500]')
        """
        ...

    def validate_pi(self, pi: float) -> tuple[bool, str | None]:
        """Validate throughput position against expected ranges (FR-008).

        Sanity Ranges:
            - Expected: 0.2-3.0 (normal US county range)
            - Extreme: <0.2 or >3.0 (flag for review but don't cap)

        Args:
            pi: Throughput position to validate (dimensionless)

        Returns:
            Tuple of (valid, message)

        Example:
            >>> calculator.validate_pi(1.1)
            (True, None)
            >>> calculator.validate_pi(4.5)
            (True, 'WARNING: π=4.5 is extreme outlier, flagged for review')
        """
        ...


__all__ = [
    "ThroughputCalculator",
    "HOURS_PER_YEAR",
    "EXPECTED_TAU_THROUGH_MIN",
    "EXPECTED_TAU_THROUGH_MAX",
    "WARNING_TAU_THROUGH_MIN",
    "WARNING_TAU_THROUGH_MAX",
    "EXPECTED_PI_MIN",
    "EXPECTED_PI_MAX",
]
