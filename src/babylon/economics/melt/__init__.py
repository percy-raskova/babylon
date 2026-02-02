"""MELT and Basket Visibility module for Labor Aristocracy threshold computation.

This module implements the Topological Value Theory (TVT) framework for determining
class positions based on wage thresholds. It bridges labor-time and money-price
domains through the MELT coefficient and basket visibility measure.

Core Concepts:
    - **MELT (τ)**: Monetary Expression of Labor Time = GDP / L ($/labor-hour)
    - **γ_basket**: Basket visibility coefficient measuring imperial subsidy on consumption
    - **τ_effective**: Labor Aristocracy threshold wage = τ × γ_basket
    - **ClassPosition**: Wage-based class position (LA, Proletariat, Subproletariat)
    - **Φ_hour**: Imperial rent per hour worked

TVT Axiom References:
    - B3-B4: Single-System Temporalism (one τ per currency zone)
    - C1: ERDI (Exchange Rate Deviation Index) = GDP_PPP / GDP_MER
    - D3-D4: Basket visibility derivation from import share and peripheral visibility
    - E1-E4: Class position and imperial rent formulas

Feature: 013-melt-basket-visibility
Date: 2026-02-01

Integration Patterns (CHK039, CHK040):
    This module follows the service patterns established in Feature 012
    (CapitalStockCalculator) and the TensorRegistry caching pattern from
    ``babylon.economics.tensor``. Key integration points:

    - **NoDataSentinel**: Returned when data is unavailable (same pattern as TensorRegistry)
    - **Service Protocol**: All calculators define protocols for dependency injection
    - **Immutable Parameters**: NationalParameters is frozen for thread-safe caching
    - **Annual Caching**: Parameters cached by year key, invalidated on data refresh

Cache Invalidation Strategy (CHK042):
    - Annual parameters cached by (year) key in caller code
    - Cache invalidated on: data source refresh, year boundary crossing
    - Thread-safe access guaranteed by NationalParameters immutability
    - Callers should use ``functools.lru_cache`` or similar for caching

Example:
    >>> from babylon.economics.melt import (
    ...     MELTCalculator,
    ...     BasketVisibilityCalculator,
    ...     ClassPositionClassifier,
    ...     ImperialRentCalculator,
    ...     NationalParameters,
    ...     ClassPosition,
    ... )
    >>> from babylon.economics.melt import (
    ...     DefaultMELTCalculator,
    ...     DefaultBasketVisibilityCalculator,
    ...     DefaultClassPositionClassifier,
    ...     DefaultImperialRentCalculator,
    ... )

See Also:
    :mod:`babylon.economics.tensor`: NoDataSentinel pattern
    :mod:`babylon.economics.capital_stock`: Service pattern reference (Feature 012)
    :mod:`babylon.economics.reproduction`: Emmanuel-Amin imperial rent (alternative framework)
"""

from babylon.economics.melt.basket_visibility import (
    BasketVisibilityCalculator,
    DefaultBasketVisibilityCalculator,
)
from babylon.economics.melt.class_position import (
    ClassPositionClassifier,
    DefaultClassPositionClassifier,
)
from babylon.economics.melt.imperial_rent import (
    DefaultImperialRentCalculator,
    ImperialRentCalculator,
)
from babylon.economics.melt.melt_calculator import (
    DefaultMELTCalculator,
    MELTCalculator,
)
from babylon.economics.melt.parameters import NationalParameters
from babylon.economics.melt.types import ClassPosition

__all__ = [
    # Types
    "ClassPosition",
    # Parameters
    "NationalParameters",
    # Protocols
    "MELTCalculator",
    "BasketVisibilityCalculator",
    "ClassPositionClassifier",
    "ImperialRentCalculator",
    # Default implementations
    "DefaultMELTCalculator",
    "DefaultBasketVisibilityCalculator",
    "DefaultClassPositionClassifier",
    "DefaultImperialRentCalculator",
]
