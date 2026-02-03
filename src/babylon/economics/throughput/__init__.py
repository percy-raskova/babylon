"""Throughput Position and Domestic Value Geography module.

This module implements domestic value geography analysis within the US (single
currency zone). Unlike international value transfer which operates through
visibility (γ) and ERDI differentials, domestic geography operates through
**throughput position** (π) - the relative flow of accumulated value through
a location.

Key Insight:
    Within a single currency zone, wages track THROUGHPUT, not value creation.
    A retail worker in Manhattan handles enormous throughput but captures little
    (low λ), while an extraction worker in Appalachia creates value but sees
    little flow through (low π).

Core Concepts:
    - **τ_through**: Throughput intensity ($/labor-hour) = GDP / (L × 2080)
    - **π**: Throughput position = τ_through / τ_national
    - **D**: Supply chain depth (0-5 scale, employment-weighted NAICS)
    - **λ_proxy**: Wage share proxy = avg_wage / τ_through

TVT Extension Reference:
    ai-docs/brainstorms/tensor/tvt_throughput_extension.md

Feature: 014-throughput-position
Date: 2026-02-02

Example:
    >>> from babylon.economics.throughput import (
    ...     DefaultThroughputCalculator,
    ...     DefaultSupplyChainAnalyzer,
    ...     NAICS_DEPTH_MAPPING,
    ... )
    >>> # Compute throughput position for Wayne County (Detroit)
    >>> supply_chain = DefaultSupplyChainAnalyzer(qcew_source)
    >>> calculator = DefaultThroughputCalculator(
    ...     gdp_source, qcew_source, supply_chain, melt_calc
    ... )
    >>> metrics = calculator.compute_metrics("26163", 2022)
    >>> print(f"Wayne County π = {metrics.pi:.2f}")
    Wayne County π = 0.90

See Also:
    :mod:`babylon.economics.melt`: National MELT calculation (Feature 013)
    :mod:`babylon.economics.tensor`: NoDataSentinel pattern
"""

from babylon.economics.throughput.adapters import (
    NAICS_2DIGIT_SECTORS,
    SQLiteBEACountyGDPSource,
    SQLiteQCEWCountyNAICSSource,
)
from babylon.economics.throughput.analysis import (
    CorrelationResult,
    compute_high_pi_wage_correlation,
    correlate_throughput_with_class,
)
from babylon.economics.throughput.calculator import (
    DefaultThroughputCalculator,
    ThroughputCalculator,
)
from babylon.economics.throughput.data_sources import (
    BEACountyGDPSource,
    QCEWCountyNAICSSource,
)
from babylon.economics.throughput.naics_depth import (
    NAICS_DEPTH_MAPPING,
    get_depth,
    validate_depth,
)
from babylon.economics.throughput.supply_chain import (
    DefaultSupplyChainAnalyzer,
    SupplyChainAnalyzer,
)
from babylon.economics.throughput.types import (
    ThroughputMetrics,
    WageShareEstimate,
)

__all__ = [
    # Types
    "ThroughputMetrics",
    "WageShareEstimate",
    # Constants
    "NAICS_DEPTH_MAPPING",
    # Utilities
    "get_depth",
    "validate_depth",
    # Data Source Protocols
    "BEACountyGDPSource",
    "QCEWCountyNAICSSource",
    # Service Protocols
    "ThroughputCalculator",
    "SupplyChainAnalyzer",
    # Default Implementations
    "DefaultThroughputCalculator",
    "DefaultSupplyChainAnalyzer",
    # SQLite Adapters
    "SQLiteBEACountyGDPSource",
    "SQLiteQCEWCountyNAICSSource",
    "NAICS_2DIGIT_SECTORS",
    # Correlation Analysis
    "CorrelationResult",
    "correlate_throughput_with_class",
    "compute_high_pi_wage_correlation",
]
