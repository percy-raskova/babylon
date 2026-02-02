# Data Model: Throughput Position and Domestic Value Geography

**Feature**: 014-throughput-position
**Date**: 2026-02-02
**Phase**: 1 (Data Model & Contracts)

## Overview

This document defines the data models and type contracts for the throughput position feature. All types are Pydantic models following the patterns established in Feature 013 (MELT and Basket Visibility).

## Core Types

### ThroughputMetrics

Container for county-level throughput analysis results.

```python
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
        pi: Throughput position = τ_through / τ_national
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
    pi: float = Field(..., gt=0, description="Throughput position (dimensionless)")
    supply_chain_depth: float = Field(..., ge=0.0, le=5.0, description="Supply chain depth")
    is_estimated: bool = Field(default=False)
    data_quality: Literal["high", "medium", "low"] = Field(default="high")
```

### WageShareEstimate

Container for industry-county wage share proxy.

```python
class WageShareEstimate(BaseModel, frozen=True):
    """Container for industry-county wage share proxy.

    The wage share proxy (λ_proxy) measures the fraction of throughput
    captured as wages. This is a proxy for true institutional λ, which
    would require union density and bargaining power data.

    Formula: λ_proxy = avg_wage / τ_through

    Attributes:
        fips: 5-character county FIPS code
        naics: 2-digit NAICS sector code
        year: Calendar year for data
        lambda_proxy: Wage share proxy (0.0-1.0 expected, may exceed 1.0 for data issues)
        confidence: Confidence level based on data quality
        avg_weekly_wage: Source average weekly wage from QCEW
        employment: Source employment count from QCEW

    Example:
        >>> estimate = WageShareEstimate(
        ...     fips="26163",
        ...     naics="44",  # Retail
        ...     year=2022,
        ...     lambda_proxy=0.08,
        ...     confidence="high",
        ...     avg_weekly_wage=650.0,
        ...     employment=45000
        ... )
    """

    fips: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    naics: str = Field(..., min_length=2, max_length=2, pattern=r"^\d{2}$")
    year: int = Field(..., ge=2001, le=2030)
    lambda_proxy: float = Field(..., ge=0.0, description="Wage share proxy")
    confidence: Literal["high", "medium", "low"] = Field(default="high")
    avg_weekly_wage: float | None = Field(default=None, description="Source avg weekly wage")
    employment: int | None = Field(default=None, description="Source employment count")
```

### NAICSDepthMapping

Frozen constant mapping NAICS 2-digit sectors to supply chain depth values.

```python
from typing import Final

NAICS_DEPTH_MAPPING: Final[dict[str, float]] = {
    "11": 0.0,   # Agriculture, Forestry, Fishing, Hunting - Extraction
    "21": 0.0,   # Mining, Quarrying, Oil and Gas - Extraction
    "22": 2.0,   # Utilities - Infrastructure coordination
    "23": 2.0,   # Construction - Secondary transformation
    "31": 1.5,   # Manufacturing (31-33 spans primary and secondary)
    "32": 1.5,   # Manufacturing
    "33": 1.5,   # Manufacturing
    "42": 3.0,   # Wholesale Trade - Distribution coordination
    "44": 4.0,   # Retail Trade - Final realization
    "45": 4.0,   # Retail Trade
    "48": 3.0,   # Transportation and Warehousing - Logistics
    "49": 3.0,   # Transportation and Warehousing
    "51": 4.0,   # Information - Knowledge coordination
    "52": 5.0,   # Finance and Insurance - Highest coordination
    "53": 5.0,   # Real Estate - Fictitious capital
    "54": 4.0,   # Professional, Scientific, Technical Services
    "55": 5.0,   # Management of Companies - Control coordination
    "56": 3.0,   # Administrative and Support
    "61": 4.0,   # Educational Services - Social reproduction
    "62": 4.0,   # Health Care and Social Assistance
    "71": 4.0,   # Arts, Entertainment, Recreation
    "72": 4.0,   # Accommodation and Food Services
    "81": 3.0,   # Other Services
    "92": 4.0,   # Public Administration
}
"""NAICS 2-digit sector to supply chain depth mapping.

Depth values are theoretically derived from position in the supply chain funnel:
- Depth 0: Primary extraction (mines, farms, wells)
- Depth 1-2: Transformation (refineries, factories)
- Depth 3: Logistics coordination (ports, warehouses, wholesale)
- Depth 4: Service/realization (retail, healthcare, education)
- Depth 5: Financial coordination (banks, management, real estate)

Manufacturing (31-33) uses 1.5 as weighted average of primary (depth 1) and
secondary (depth 2) manufacturing activities.

Reference: TVT Throughput Extension (ai-docs/brainstorms/tensor/tvt_throughput_extension.md)
"""
```

## Data Source Protocols

### BEACountyGDPSource

Protocol for BEA CAGDP1 county GDP data.

```python
from typing import Protocol

class BEACountyGDPSource(Protocol):
    """Protocol for BEA county-level GDP data (CAGDP1).

    Data Source:
        BEA CAGDP1 (County Annual GDP Summary)
        https://apps.bea.gov/api/data/

    Units:
        GDP in current dollars (nominal, not chained).

    Example:
        >>> source = SQLiteBEACountyGDPSource("path/to/data.sqlite")
        >>> gdp = source.get_county_gdp("26163", 2022)
        >>> print(f"Wayne County 2022 GDP: ${gdp:,.0f}")
        Wayne County 2022 GDP: $95,000,000,000
    """

    def get_county_gdp(self, fips: str, year: int) -> float | None:
        """Get county GDP for a given FIPS code and year.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year (2001-2023 for available data)

        Returns:
            GDP in current dollars, or None if data unavailable
        """
        ...

    def get_all_counties(self, year: int) -> dict[str, float]:
        """Get GDP for all counties in a given year.

        Args:
            year: Calendar year

        Returns:
            Dict mapping FIPS codes to GDP values
        """
        ...
```

### QCEWCountyNAICSSource

Protocol for QCEW county employment by NAICS sector.

```python
class QCEWCountyNAICSSource(Protocol):
    """Protocol for QCEW county employment by NAICS sector.

    Data Source:
        BLS QCEW (Quarterly Census of Employment and Wages)
        https://www.bls.gov/cew/

    Units:
        Employment in persons (headcount, not FTE).
        Wages in dollars per week.

    Example:
        >>> source = SQLiteQCEWCountyNAICSSource("path/to/data.sqlite")
        >>> emp = source.get_county_naics_employment("26163", "52", 2022)
        >>> print(f"Wayne County Finance employment: {emp:,}")
        Wayne County Finance employment: 25,000
    """

    def get_county_naics_employment(
        self, fips: str, naics: str, year: int
    ) -> int | None:
        """Get employment for a county-NAICS combination.

        Args:
            fips: 5-character county FIPS code
            naics: 2-digit NAICS sector code
            year: Calendar year

        Returns:
            Employment count (persons), or None if suppressed/unavailable
        """
        ...

    def get_county_employment_by_naics(
        self, fips: str, year: int
    ) -> dict[str, int]:
        """Get employment by NAICS sector for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Dict mapping NAICS codes to employment counts
            (suppressed sectors excluded)
        """
        ...

    def get_county_total_employment(self, fips: str, year: int) -> int | None:
        """Get total employment for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            Total employment count, or None if unavailable
        """
        ...

    def get_county_naics_wages(
        self, fips: str, naics: str, year: int
    ) -> float | None:
        """Get average weekly wage for a county-NAICS combination.

        Args:
            fips: 5-character county FIPS code
            naics: 2-digit NAICS sector code
            year: Calendar year

        Returns:
            Average weekly wage ($/week), or None if suppressed/unavailable
        """
        ...
```

## Service Protocols

### ThroughputCalculator

Core service for computing throughput metrics.

```python
from babylon.economics.tensor import NoDataSentinel

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

    def compute_throughput_intensity(
        self, fips: str, year: int
    ) -> float | NoDataSentinel:
        """Compute throughput intensity for a county.

        Formula: τ_through = GDP / (employment × 2080)

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            τ_through in $/labor-hour, or NoDataSentinel if unavailable
        """
        ...

    def compute_throughput_position(
        self, fips: str, year: int
    ) -> float | NoDataSentinel:
        """Compute throughput position for a county.

        Formula: π = τ_through / τ_national

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            π (dimensionless), or NoDataSentinel if unavailable
        """
        ...

    def compute_metrics(
        self, fips: str, year: int
    ) -> ThroughputMetrics | NoDataSentinel:
        """Compute full throughput metrics for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            ThroughputMetrics container, or NoDataSentinel if unavailable
        """
        ...

    def validate_throughput(
        self, tau_through: float
    ) -> tuple[bool, str | None]:
        """Validate throughput intensity against sanity ranges.

        Sanity Ranges (per FR-008):
            - Expected: $20-200/hour (normal US county range)
            - Warning: $10-500/hour (unusual but possible)
            - Fail: <$10 or >$500/hour (indicates error)

        Args:
            tau_through: Throughput intensity to validate

        Returns:
            Tuple of (valid, message)
        """
        ...
```

### SupplyChainAnalyzer

Service for computing supply chain depth.

```python
class SupplyChainAnalyzer(Protocol):
    """Protocol for supply chain depth analysis.

    Computes employment-weighted average supply chain depth for a county
    based on NAICS sector employment distribution.

    Formula: D = Σ(employment[naics] × depth[naics]) / Σ employment

    Example:
        >>> analyzer = DefaultSupplyChainAnalyzer(qcew_source)
        >>> depth = analyzer.compute_depth("36061", 2022)  # Manhattan
        >>> print(f"Manhattan D = {depth:.2f}")
        Manhattan D = 4.3
    """

    def compute_depth(self, fips: str, year: int) -> float | NoDataSentinel:
        """Compute supply chain depth for a county.

        Args:
            fips: 5-character county FIPS code
            year: Calendar year

        Returns:
            D (0.0-5.0 scale), or NoDataSentinel if unavailable
        """
        ...

    def get_naics_depth(self, naics: str) -> float | None:
        """Get depth value for a NAICS sector.

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
```

## Validation Ranges

Per FR-008, the following sanity ranges apply:

### Throughput Intensity (τ_through)

| Range | Description | Action |
|-------|-------------|--------|
| $20-200/hour | Expected | Pass |
| $10-500/hour | Warning | Pass with warning |
| <$10 or >$500/hour | Fail | Flag for review |

### Throughput Position (π)

| Range | Description | Action |
|-------|-------------|--------|
| 0.2-3.0 | Expected | Pass |
| <0.2 or >3.0 | Extreme | Flag for review |

### Supply Chain Depth (D)

| Range | Description | Action |
|-------|-------------|--------|
| 0.0-5.0 | By definition | Error if outside |

### Wage Share Proxy (λ_proxy)

| Range | Description | Action |
|-------|-------------|--------|
| 0.0-1.0 | Theoretical | Pass |
| >1.0 | Data quality issue | Flag for review |

## Relationship to Feature 013

This feature extends Feature 013 by adding geographic analysis within the US currency zone:

```
Feature 013 (International Value Transfer)    Feature 014 (Domestic Geography)
├── τ (national MELT)                         ├── τ_through (county throughput)
├── γ_basket (visibility)             vs      ├── π (throughput position)
├── Φ_hour (imperial rent)                    ├── D (supply chain depth)
└── ClassPosition (LA/P/SP)                   └── λ_proxy (wage share)
```

Key integration point: `π = τ_through / τ_national` requires Feature 013's `MELTCalculator.get_melt()`.
