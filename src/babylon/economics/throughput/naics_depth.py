"""NAICS-to-Depth mapping constant.

Feature: 014-throughput-position
Date: 2026-02-02

This module defines the NAICS 2-digit sector to supply chain depth mapping.
Depth values are theoretically derived from position in the supply chain funnel,
not empirically calibrated.

TVT Extension Reference:
    The supply chain funnel model from ai-docs/brainstorms/tensor/tvt_throughput_extension.md

Depth Scale:
    0 = Extraction (value creation at origin)
    1 = Primary transformation
    2 = Secondary transformation
    3 = Logistics/wholesale coordination
    4 = Service/retail realization
    5 = Financial/management coordination (highest throughput)
"""

from __future__ import annotations

from typing import Final

NAICS_DEPTH_MAPPING: Final[dict[str, float]] = {
    # Depth 0: Extraction - Primary value creation
    "11": 0.0,  # Agriculture, Forestry, Fishing and Hunting
    "21": 0.0,  # Mining, Quarrying, and Oil and Gas Extraction
    # Depth 1.5-2: Transformation - Value processing
    "31": 1.5,  # Manufacturing (spans primary and secondary)
    "32": 1.5,  # Manufacturing
    "33": 1.5,  # Manufacturing
    "22": 2.0,  # Utilities - Infrastructure coordination
    "23": 2.0,  # Construction - Secondary transformation
    # Depth 3: Logistics - Distribution coordination
    "42": 3.0,  # Wholesale Trade
    "48": 3.0,  # Transportation and Warehousing
    "49": 3.0,  # Transportation and Warehousing
    "56": 3.0,  # Administrative and Support Services
    "81": 3.0,  # Other Services (mixed)
    # Depth 4: Services - Final realization and social reproduction
    "44": 4.0,  # Retail Trade
    "45": 4.0,  # Retail Trade
    "51": 4.0,  # Information
    "54": 4.0,  # Professional, Scientific, Technical Services
    "61": 4.0,  # Educational Services
    "62": 4.0,  # Health Care and Social Assistance
    "71": 4.0,  # Arts, Entertainment, Recreation
    "72": 4.0,  # Accommodation and Food Services
    "92": 4.0,  # Public Administration
    # Depth 5: Financial coordination - Highest throughput capture
    "52": 5.0,  # Finance and Insurance
    "53": 5.0,  # Real Estate and Rental and Leasing
    "55": 5.0,  # Management of Companies and Enterprises
}
"""NAICS 2-digit sector to supply chain depth mapping.

Theoretical Basis:
    Value is created at extraction points (depth 0) and flows upward through
    coordination nodes. At each layer, wages are proportional to accumulated
    throughput, not local value creation.

    | Depth | Layer | Examples | Characteristic |
    |-------|-------|----------|----------------|
    | d=0 | Extraction | Mines, farms, wells | Creates value, captures little |
    | d=1 | Processing | Refineries, mills | Initial transformation |
    | d=2 | Manufacturing | Factories, assembly | Secondary transformation |
    | d=3 | Logistics | Ports, warehouses | Coordination chokepoints |
    | d=4 | Services | Retail, healthcare | High throughput, variable λ |
    | d=5 | Finance | Banks, management | Highest throughput capture |

Manufacturing Note:
    NAICS 31-33 uses depth=1.5 as a weighted average because Manufacturing
    spans both primary processing (depth 1) and secondary assembly (depth 2).
    Future enhancement FE-001 could use 3-digit NAICS for finer granularity.

Retail Paradox:
    Retail (depth 4) has high throughput but low wage share (λ ≈ 0.05-0.10).
    This explains why retail workers remain proletariat despite handling
    enormous value flow - they have high τ_through but capture little.

Reference:
    - TVT Throughput Extension: ai-docs/brainstorms/tensor/tvt_throughput_extension.md
    - BLS NAICS Codes: https://www.bls.gov/cew/classifications/industry/
"""


def get_depth(naics: str) -> float | None:
    """Get supply chain depth for a 2-digit NAICS sector.

    Args:
        naics: 2-digit NAICS sector code (e.g., "52" for Finance)

    Returns:
        Depth value (0.0-5.0), or None if sector not in mapping

    Example:
        >>> get_depth("21")  # Mining
        0.0
        >>> get_depth("52")  # Finance
        5.0
        >>> get_depth("31")  # Manufacturing
        1.5
        >>> get_depth("99")  # Unknown
        None
    """
    return NAICS_DEPTH_MAPPING.get(naics)


def validate_depth(depth: float) -> bool:
    """Validate that a depth value is in valid range [0.0, 5.0].

    Args:
        depth: Computed depth value

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_depth(3.5)
        True
        >>> validate_depth(5.5)
        False
        >>> validate_depth(-0.1)
        False
    """
    return 0.0 <= depth <= 5.0


__all__ = [
    "NAICS_DEPTH_MAPPING",
    "get_depth",
    "validate_depth",
]
