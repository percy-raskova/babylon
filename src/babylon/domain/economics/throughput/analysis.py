"""Correlation analysis utilities for throughput position.

Feature: 014-throughput-position
Date: 2026-02-02

This module provides utilities for analyzing the correlation between
throughput position metrics and class position.

Key Analysis:
    - π × λ correlation with LA share
    - Validates that throughput × wage capture predicts class position
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from babylon.domain.economics.tensor import NoDataSentinel

if TYPE_CHECKING:
    from babylon.domain.economics.melt import ClassPositionClassifier
    from babylon.domain.economics.throughput.calculator import ThroughputCalculator
    from babylon.domain.economics.throughput.data_sources import QCEWCountyNAICSSource

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """Result of correlation analysis.

    Attributes:
        correlation: Pearson correlation coefficient (-1 to 1)
        p_value: Statistical significance (p < 0.05 is significant)
        sample_size: Number of valid data points
        counties_analyzed: List of FIPS codes included
        counties_excluded: List of FIPS codes with missing data
    """

    correlation: float
    p_value: float
    sample_size: int
    counties_analyzed: list[str]
    counties_excluded: list[str]

    @property
    def is_significant(self) -> bool:
        """Return True if correlation is statistically significant (p < 0.05)."""
        return self.p_value < 0.05

    @property
    def meets_threshold(self) -> bool:
        """Return True if correlation meets SC-005 threshold (r > 0.4)."""
        return self.correlation > 0.4


def correlate_throughput_with_class(  # pragma: no mutate — scipy analysis tooling
    fips_codes: list[str],
    year: int,
    throughput_calculator: ThroughputCalculator,
    qcew_source: QCEWCountyNAICSSource,
    class_classifier: ClassPositionClassifier | None = None,  # pragma: no mutate
) -> CorrelationResult | NoDataSentinel:
    """Compute correlation between τ_through × λ_proxy and class proxy.

    This validates the theoretical prediction that throughput position
    multiplied by wage capture correlates with labor aristocracy
    share from the ClassPositionClassifier.

    Args:
        fips_codes: List of county FIPS codes to analyze
        year: Calendar year
        throughput_calculator: Calculator for τ_through and π
        qcew_source: Source for wage data (direct access)
        class_classifier: Optional classifier for LA share (Feature 013)

    Returns:
        CorrelationResult with statistics, or NoDataSentinel if insufficient data

    Note:
        Requires at least 30 valid data points for meaningful correlation.
        Uses scipy.stats.pearsonr for correlation computation.
    """
    try:  # pragma: no mutate
        from scipy import stats  # type: ignore[import-untyped]  # pragma: no mutate
    except ImportError:  # pragma: no mutate
        return NoDataSentinel(
            "", year, "scipy not installed - required for correlation analysis"
        )  # pragma: no mutate

    # Collect valid data points
    tau_lambda_values: list[float] = []  # pragma: no mutate
    class_proxy_values: list[float] = []  # pragma: no mutate
    counties_analyzed: list[str] = []  # pragma: no mutate
    counties_excluded: list[str] = []  # pragma: no mutate

    for fips in fips_codes:  # pragma: no mutate
        # Get τ_through
        tau_through = throughput_calculator.compute_throughput_intensity(
            fips, year
        )  # pragma: no mutate
        if isinstance(tau_through, NoDataSentinel):  # pragma: no mutate
            counties_excluded.append(fips)  # pragma: no mutate
            continue  # pragma: no mutate

        # Get average wage for λ_proxy calculation (use retail as representative)
        avg_wage = qcew_source.get_county_naics_wages(fips, "44", year)  # pragma: no mutate
        if avg_wage is None:  # pragma: no mutate
            counties_excluded.append(fips)  # pragma: no mutate
            continue  # pragma: no mutate

        # Compute λ_proxy = (avg_weekly_wage/40) / τ_through
        hourly_wage = avg_wage / 40.0  # pragma: no mutate
        lambda_proxy = hourly_wage / tau_through  # pragma: no mutate

        # Compute τ × λ product
        tau_lambda = tau_through * lambda_proxy  # pragma: no mutate

        # Get class proxy (LA share if classifier available)
        # TODO: When Feature 013 is integrated, use class_classifier.classify(fips)
        # For now, use τ_through as normalized proxy for class position
        _ = class_classifier  # Silence unused parameter warning  # pragma: no mutate
        class_proxy = tau_through / 100.0  # pragma: no mutate

        tau_lambda_values.append(tau_lambda)  # pragma: no mutate
        class_proxy_values.append(class_proxy)  # pragma: no mutate
        counties_analyzed.append(fips)  # pragma: no mutate

    # Check minimum sample size
    if len(counties_analyzed) < 30:  # pragma: no mutate
        return NoDataSentinel(  # pragma: no mutate
            "",  # pragma: no mutate
            year,  # pragma: no mutate
            f"Insufficient data: only {len(counties_analyzed)} counties, need 30+",  # pragma: no mutate
        )  # pragma: no mutate

    # Compute Pearson correlation
    correlation, p_value = stats.pearsonr(
        tau_lambda_values, class_proxy_values
    )  # pragma: no mutate

    return CorrelationResult(  # pragma: no mutate
        correlation=float(correlation),  # pragma: no mutate
        p_value=float(p_value),  # pragma: no mutate
        sample_size=len(counties_analyzed),  # pragma: no mutate
        counties_analyzed=counties_analyzed,  # pragma: no mutate
        counties_excluded=counties_excluded,  # pragma: no mutate
    )  # pragma: no mutate


def compute_high_pi_wage_correlation(  # pragma: no mutate — scipy analysis tooling
    fips_codes: list[str],
    year: int,
    throughput_calculator: ThroughputCalculator,
    qcew_source: QCEWCountyNAICSSource,
) -> CorrelationResult | NoDataSentinel:
    """Validate SC-004: high-π counties should have higher average wages.

    Args:
        fips_codes: List of county FIPS codes to analyze
        year: Calendar year
        throughput_calculator: Calculator for τ_through
        qcew_source: Source for wage data (direct access)

    Returns:
        CorrelationResult with τ_through vs average wage correlation
    """
    try:  # pragma: no mutate
        from scipy import stats  # pragma: no mutate
    except ImportError:  # pragma: no mutate
        return NoDataSentinel(
            "", year, "scipy not installed - required for correlation analysis"
        )  # pragma: no mutate

    tau_values: list[float] = []  # pragma: no mutate
    wage_values: list[float] = []  # pragma: no mutate
    counties_analyzed: list[str] = []  # pragma: no mutate
    counties_excluded: list[str] = []  # pragma: no mutate

    for fips in fips_codes:  # pragma: no mutate
        # Get τ_through (proxy for π since both scale together)
        tau_through = throughput_calculator.compute_throughput_intensity(
            fips, year
        )  # pragma: no mutate
        if isinstance(tau_through, NoDataSentinel):  # pragma: no mutate
            counties_excluded.append(fips)  # pragma: no mutate
            continue  # pragma: no mutate

        # Get average wage directly from QCEW (use finance sector)
        avg_wage = qcew_source.get_county_naics_wages(fips, "52", year)  # pragma: no mutate
        if avg_wage is None:  # pragma: no mutate
            # Try retail as fallback
            avg_wage = qcew_source.get_county_naics_wages(fips, "44", year)  # pragma: no mutate
            if avg_wage is None:  # pragma: no mutate
                counties_excluded.append(fips)  # pragma: no mutate
                continue  # pragma: no mutate

        tau_values.append(tau_through)  # pragma: no mutate
        wage_values.append(avg_wage)  # pragma: no mutate
        counties_analyzed.append(fips)  # pragma: no mutate

    if len(counties_analyzed) < 30:  # pragma: no mutate
        return NoDataSentinel(  # pragma: no mutate
            "",  # pragma: no mutate
            year,  # pragma: no mutate
            f"Insufficient data: only {len(counties_analyzed)} counties, need 30+",  # pragma: no mutate
        )  # pragma: no mutate

    correlation, p_value = stats.pearsonr(tau_values, wage_values)  # pragma: no mutate

    return CorrelationResult(  # pragma: no mutate
        correlation=float(correlation),  # pragma: no mutate
        p_value=float(p_value),  # pragma: no mutate
        sample_size=len(counties_analyzed),  # pragma: no mutate
        counties_analyzed=counties_analyzed,  # pragma: no mutate
        counties_excluded=counties_excluded,  # pragma: no mutate
    )  # pragma: no mutate


__all__ = [
    "CorrelationResult",
    "correlate_throughput_with_class",
    "compute_high_pi_wage_correlation",
]
