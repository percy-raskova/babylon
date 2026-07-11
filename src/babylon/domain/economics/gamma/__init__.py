"""Gamma Visibility Tensor module for reproductive and imperial shadow subsidies.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module implements the visibility coefficient framework from TVT
(Topological Value Theory), quantifying two hidden value transfers:

1. **Reproductive Shadow Subsidy (Phi_III)**: Unpaid care labor naturalized
   as "women's work" that subsidizes capital by suppressing V (variable capital).
   Measured by gamma_III = L_paid_care / (L_paid_care + L_unpaid_care).

2. **Imperial Shadow Subsidy (Phi_imperial)**: Compressed peripheral labor
   that cheapens the consumption basket for core workers. Measured by
   gamma_basket = 1 / (alpha/gamma_import + (1-alpha)).

Core Concepts:
    - **gamma_III**: Reproductive labor visibility [0.20, 0.40] typical US
    - **gamma_import**: Import basket visibility [0.40, 0.70] typical US
    - **gamma_basket**: Composite basket visibility [0.60, 0.85] typical US
    - **Phi_III**: Reproductive shadow subsidy (~$2.2T/year)
    - **Phi_imperial**: Imperial shadow subsidy (~$3.9T/year)

TVT Axiom References:
    - I.5: Department III (reproductive labor)
    - C1: ERDI (Exchange Rate Deviation Index)
    - D3-D4: Basket visibility derivation

Example:
    >>> from babylon.domain.economics.gamma import (
    ...     DefaultGammaIIICalculator,
    ...     DefaultGammaImportCalculator,
    ...     DefaultGammaBasketCalculator,
    ...     DefaultShadowSubsidyCalculator,
    ... )

See Also:
    :mod:`babylon.domain.economics.melt`: MELT and basket visibility (Feature 013)
    :mod:`babylon.domain.economics.tensor`: NoDataSentinel pattern
"""

from babylon.domain.economics.gamma.adapters import QCEWCareAdapter
from babylon.domain.economics.gamma.gamma_basket import (
    DefaultGammaBasketCalculator,
    GammaBasketCalculator,
)
from babylon.domain.economics.gamma.gamma_iii import (
    DefaultGammaIIICalculator,
    GammaIIICalculator,
)
from babylon.domain.economics.gamma.gamma_import import (
    DefaultGammaImportCalculator,
    GammaImportCalculator,
)
from babylon.domain.economics.gamma.shadow_subsidy import (
    DefaultShadowSubsidyCalculator,
    ShadowSubsidyCalculator,
)
from babylon.domain.economics.gamma.types import (
    CORE_DEFAULT_ERDI,
    MVP_ERDI_VALUES,
    PERIPHERY_DEFAULT_ERDI,
    ERDIData,
    GammaBasket,
    GammaIII,
    GammaImport,
    ShadowSubsidy,
    weighted_average_gamma,
)
from babylon.domain.economics.gamma.validation import (
    validate_gamma_basket,
    validate_gamma_iii,
    validate_gamma_import,
)

__all__ = [
    # Types
    "GammaIII",
    "GammaImport",
    "GammaBasket",
    "ShadowSubsidy",
    "ERDIData",
    # Constants
    "MVP_ERDI_VALUES",
    "CORE_DEFAULT_ERDI",
    "PERIPHERY_DEFAULT_ERDI",
    # Utilities
    "weighted_average_gamma",
    # Validation
    "validate_gamma_iii",
    "validate_gamma_import",
    "validate_gamma_basket",
    # Protocols
    "GammaIIICalculator",
    "GammaImportCalculator",
    "GammaBasketCalculator",
    "ShadowSubsidyCalculator",
    # Default implementations
    "DefaultGammaIIICalculator",
    "DefaultGammaImportCalculator",
    "DefaultGammaBasketCalculator",
    "DefaultShadowSubsidyCalculator",
    # Adapters
    "QCEWCareAdapter",
]
