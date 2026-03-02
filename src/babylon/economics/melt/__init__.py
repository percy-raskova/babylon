"""MELT and Basket Visibility module for class position and imperial rent computation.

This module implements the Topological Value Theory (TVT) framework for:
1. Wealth-based class position classification (primary, canonical)
2. Imperial rent (Φ_hour) calculation (flow-based extraction metric)

Theoretical Clarification (2026-02-02):
    Class position and imperial rent are now treated as SEPARATE CONCERNS:
    - **Class position**: Determined by wealth percentile (stock)
    - **Imperial rent (Φ_hour)**: Flow-based extraction rate through consumption

    A proletarian (bottom 50% wealth) CAN have Φ_hour > 0 (benefit from cheap
    imports) while remaining proletarian. They consume the imperial subsidy
    rather than accumulating it as wealth.

    LA = 40% emerges naturally from wealth distribution (50th-90th percentile).
    This resolves the 30-50% vs 50-70% debate without parameter tuning.

Core Concepts:
    - **MELT (τ)**: Monetary Expression of Labor Time = GDP / L ($/labor-hour)
    - **γ_basket**: Basket visibility coefficient measuring imperial subsidy
    - **τ_effective**: Imperial rent break-even wage = τ × γ_basket
    - **ClassPosition**: Wealth-based class position (5 classes)
    - **Φ_hour**: Imperial rent per hour (flow, separate from class)

TVT Axiom References:
    - B3-B4: Single-System Temporalism (one τ per currency zone)
    - C1: ERDI (Exchange Rate Deviation Index) = GDP_PPP / GDP_MER
    - D3-D4: Basket visibility derivation
    - E1 (Revised): Wealth-based class position
    - E2 (Revised): Imperial rent separate from class
    - E3-E4: Imperial rent formulas (unchanged)

Feature: 013-melt-basket-visibility
Date: 2026-02-01
Revision: 2026-02-02 (wealth-based classification)

Integration Patterns (CHK039, CHK040):
    This module follows the service patterns established in Feature 012
    (CapitalStockCalculator) and the TensorRegistry caching pattern from
    ``babylon.economics.tensor``. Key integration points:

    - **NoDataSentinel**: Returned when data is unavailable
    - **Service Protocol**: All calculators define protocols for DI
    - **Immutable Parameters**: NationalParameters is frozen for caching
    - **Annual Caching**: Parameters cached by year key

Example:
    >>> from babylon.economics.melt import (
    ...     ClassPosition,
    ...     DefaultClassPositionClassifier,
    ...     DefaultImperialRentCalculator,
    ...     NationalParameters,
    ... )
    >>> classifier = DefaultClassPositionClassifier()
    >>> # Wealth-based classification (canonical)
    >>> classifier.classify_by_wealth_percentile(70.0)
    <ClassPosition.LABOR_ARISTOCRACY: 3>
    >>> # Imperial rent is separate concern
    >>> rent_calc = DefaultImperialRentCalculator()
    >>> rent_calc.compute_phi_hour(wage=50.0, params=params)
    0.13  # Extraction rate, NOT class position

See Also:
    :mod:`babylon.economics.tensor`: NoDataSentinel pattern
    :mod:`babylon.economics.capital_stock`: Service pattern reference
    :mod:`babylon.economics.reproduction`: Emmanuel-Amin imperial rent (alternative)
"""

from babylon.economics.melt.basket_visibility import (
    BasketVisibilityCalculator,
    DefaultBasketVisibilityCalculator,
)
from babylon.economics.melt.class_position import (
    ClassPositionClassifier,
    DefaultClassPositionClassifier,
)
from babylon.economics.melt.filtration import (
    FiltrationResult,
    apply_filtration,
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
from babylon.economics.melt.rent_differential import (
    DefaultRentDifferentialCalculator,
    RentDifferentialCalculator,
    RentDifferentialResult,
)
from babylon.economics.melt.types import SUBPROLETARIAT, ClassPosition, PrecarityStatus
from babylon.economics.melt.unified_classifier import (
    DefaultUnifiedClassifier,
    DualCriteriaResult,
    UnifiedClassifier,
)
from babylon.economics.melt.wealth_proxy import (
    DefaultWealthProxyCalculator,
    WealthProxyCalculator,
)

__all__ = [
    # Types
    "ClassPosition",
    "PrecarityStatus",
    "SUBPROLETARIAT",  # Deprecated alias for backward compatibility
    # Parameters
    "NationalParameters",
    # Protocols
    "MELTCalculator",
    "BasketVisibilityCalculator",
    "ClassPositionClassifier",
    "ImperialRentCalculator",
    "WealthProxyCalculator",
    "UnifiedClassifier",
    # Default implementations
    "DefaultMELTCalculator",
    "DefaultBasketVisibilityCalculator",
    "DefaultClassPositionClassifier",
    "DefaultImperialRentCalculator",
    "DefaultRentDifferentialCalculator",
    "DefaultWealthProxyCalculator",
    "DefaultUnifiedClassifier",
    # Result types (Feature 038)
    "DualCriteriaResult",
    "FiltrationResult",
    "RentDifferentialResult",
    # Protocols (Feature 038)
    "RentDifferentialCalculator",
    # Functions (Feature 038)
    "apply_filtration",
]
