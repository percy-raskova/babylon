"""Type definitions for throughput position analysis.

This module defines the Pydantic models for throughput metrics and wage share
estimates. These types follow the patterns established in Feature 013.

Feature: 014-throughput-position
Date: 2026-02-02
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ThroughputMetrics(BaseModel, frozen=True):
    """Container for county-level throughput analysis results.

    TVT Extension Reference:
        - τ_through: Throughput intensity ($/labor-hour)
        - π: Throughput position (dimensionless ratio)
        - D: Supply chain depth (0-5 scale)

    Attributes:
        fips: 5-character county FIPS code (e.g., "26163" for Wayne County)
        year: Calendar year for data
        tau_through: Throughput intensity in $/labor-hour (GDP / L)
        pi: Throughput position = τ_through / τ_national (None if MELT unavailable)
        supply_chain_depth: Employment-weighted NAICS depth (0.0-5.0)
        is_estimated: True if any values are estimated due to missing data
        data_quality: Confidence level based on data completeness

    Example:
        >>> metrics = ThroughputMetrics(
        ...     fips="26163",
        ...     year=2022,
        ...     tau_through=58.5,
        ...     pi=0.90,
        ...     supply_chain_depth=2.1,
        ...     is_estimated=False,
        ...     data_quality="high"
        ... )
    """

    fips: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    year: int = Field(..., ge=2001, le=2030)
    tau_through: float = Field(..., gt=0, description="Throughput intensity ($/labor-hour)")
    pi: float | None = Field(
        default=None,
        gt=0,
        description="Throughput position (dimensionless), None if MELT unavailable",
    )
    supply_chain_depth: float = Field(..., ge=0.0, le=5.0, description="Supply chain depth")
    is_estimated: bool = Field(default=False)
    data_quality: Literal["high", "medium", "low"] = Field(default="high")


class WageShareEstimate(BaseModel, frozen=True):
    """Container for industry-county wage share proxy.

    The wage share proxy (λ_proxy) measures the fraction of throughput
    captured as wages. This is a proxy for true institutional λ, which
    would require union density and bargaining power data.

    Formula:
        λ_proxy = avg_wage / τ_through

    Attributes:
        fips: 5-character county FIPS code
        naics: NAICS sector code (2-digit "44" or combined "44-45")
        year: Calendar year for data
        lambda_proxy: Wage share proxy (0.0-1.0 expected, may exceed 1.0 for data issues)
        confidence: Confidence level based on data quality
        avg_weekly_wage: Source average weekly wage from QCEW
        employment: Source employment count from QCEW

    Example:
        >>> estimate = WageShareEstimate(
        ...     fips="26163",
        ...     naics="44-45",  # Retail Trade (combined NAICS)
        ...     year=2022,
        ...     lambda_proxy=0.08,
        ...     confidence="high",
        ...     avg_weekly_wage=650.0,
        ...     employment=45000
        ... )
    """

    fips: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    naics: str = Field(..., min_length=2, max_length=5, pattern=r"^\d{2}(-\d{2})?$")
    year: int = Field(..., ge=2001, le=2030)
    lambda_proxy: float = Field(..., ge=0.0, description="Wage share proxy")
    confidence: Literal["high", "medium", "low"] = Field(default="high")
    avg_weekly_wage: float | None = Field(default=None, description="Source avg weekly wage")
    employment: int | None = Field(default=None, description="Source employment count")


__all__ = ["ThroughputMetrics", "WageShareEstimate"]
