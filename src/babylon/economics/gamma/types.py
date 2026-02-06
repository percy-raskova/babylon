"""Type definitions for the Gamma Visibility Tensor module.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module defines frozen Pydantic models for visibility coefficients
and shadow subsidies in the TVT (Topological Value Theory) framework.

Models:
    - GammaIII: Reproductive labor visibility coefficient
    - GammaImport: International import visibility coefficient
    - GammaBasket: Composite consumption basket visibility
    - ShadowSubsidy: Shadow subsidy value transfers
    - ERDIData: Exchange Rate Deviation Index reference data

See Also:
    :mod:`babylon.economics.gamma.validation`: Three-tier validation functions
    :mod:`babylon.economics.melt.types`: ClassPosition type definitions
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# GAMMA III - Reproductive Labor Visibility
# =============================================================================


class GammaIII(BaseModel):
    """Reproductive labor visibility coefficient.

    Measures the fraction of care labor that is commodified (visible to
    the price system) versus naturalized as unpaid household work (invisible).

    Formula:
        gamma_III = L_paid_care / (L_paid_care + L_unpaid_care)

    TVT Axiom Reference:
        - I.5 Department III (Constitution)
        - Fortunati, "Arcane of Reproduction" (1981)

    Example:
        >>> GammaIII(
        ...     year=2022,
        ...     paid_care_hours=16.5,
        ...     unpaid_care_hours=33.0,
        ...     gamma_iii=0.333,
        ...     fortunati_exploitation=2.003,
        ... )
        GammaIII(year=2022, ...)
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2003, le=2030, description="Calendar year (ATUS available from 2003)")
    paid_care_hours: float = Field(..., ge=0.0, description="Annual paid care hours (billions)")
    unpaid_care_hours: float = Field(..., ge=0.0, description="Annual unpaid care hours (billions)")
    gamma_iii: float = Field(..., ge=0.0, le=1.0, description="Visibility coefficient")
    fortunati_exploitation: float = Field(
        ..., ge=0.0, description="Fortunati exploitation rate: (1 - gamma_III) / gamma_III"
    )
    is_estimated: bool = Field(default=False, description="True if using estimated/default values")


# =============================================================================
# GAMMA IMPORT - International Import Visibility
# =============================================================================


class GammaImport(BaseModel):
    """International import visibility coefficient.

    Measures weighted-average visibility of imported goods based on ERDI
    (Exchange Rate Deviation Index) differentials.

    Formula:
        gamma_import = sum(import_share[origin] * 1/ERDI[origin])

    TVT Axiom Reference:
        - C1: ERDI = GDP_PPP / GDP_MER
        - Emmanuel-Amin unequal exchange theory

    Example:
        >>> GammaImport(
        ...     year=2022,
        ...     import_shares={"CHN": 0.18, "MEX": 0.14},
        ...     erdi_values={"CHN": 1.80, "MEX": 1.50},
        ...     gamma_import=0.65,
        ... )
        GammaImport(year=2022, ...)
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2000, le=2030, description="Reference year")
    import_shares: dict[str, float] = Field(..., description="Country code -> import share [0, 1]")
    erdi_values: dict[str, float] = Field(
        ..., description="Country code -> ERDI (>= 1.0 for periphery)"
    )
    gamma_import: float = Field(
        ..., gt=0.0, le=1.0, description="Weighted average import visibility"
    )
    is_mvp: bool = Field(default=True, description="True if using hardcoded MVP values")


# =============================================================================
# GAMMA BASKET - Composite Consumption Basket Visibility
# =============================================================================


class GammaBasket(BaseModel):
    """Composite consumption basket visibility.

    Combines domestic (gamma=1) and imported (gamma=gamma_import) goods into
    weighted-average basket visibility using harmonic mean.

    Formula:
        gamma_basket = 1 / (alpha/gamma_import + (1-alpha))

    TVT Axiom Reference:
        - D3: Basket visibility derivation
        - D4: tau_effective = tau * gamma_basket

    Example:
        >>> GammaBasket(year=2022, alpha=0.35, gamma_import=0.65, gamma_basket=0.74)
        GammaBasket(year=2022, ...)
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2000, le=2030, description="Reference year")
    alpha: float = Field(..., ge=0.0, le=1.0, description="Import share of consumption")
    gamma_import: float = Field(..., gt=0.0, le=1.0, description="From GammaImport calculation")
    gamma_basket: float = Field(..., gt=0.0, le=1.0, description="Composite basket visibility")


# =============================================================================
# SHADOW SUBSIDY - Value Transfer Quantification
# =============================================================================


class ShadowSubsidy(BaseModel):
    """Shadow subsidy value transfers.

    Quantifies hidden value transfers from:
    1. Reproductive labor naturalization (Phi_III)
    2. Imperial compression of peripheral labor (Phi_imperial)

    Formulas:
        Phi_III = (1 - gamma_III) * L_unpaid * tau
        Phi_imperial = (1 - gamma_basket) * Consumption

    TVT Axiom Reference:
        - I.2 Imperial Rent (Constitution)
        - I.5 Department III (Constitution)

    Example:
        >>> ShadowSubsidy(
        ...     year=2022,
        ...     phi_iii_labor_hours=33.0,
        ...     phi_imperial=3.9e12,
        ... )
        ShadowSubsidy(year=2022, ...)
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2000, le=2030, description="Reference year")

    # Reproductive shadow subsidy
    phi_iii_dollars: float | None = Field(
        default=None, ge=0.0, description="Phi_III in dollars (if MELT available)"
    )
    phi_iii_labor_hours: float = Field(
        ..., ge=0.0, description="Phi_III in labor-hours (always available)"
    )

    # Imperial shadow subsidy
    phi_imperial: float = Field(default=0.0, ge=0.0, description="Phi_imperial in dollars")

    # Combined
    total_shadow_dollars: float | None = Field(
        default=None, ge=0.0, description="Phi_III + Phi_imperial (if both available)"
    )

    # Metadata
    melt_available: bool = Field(
        default=False, description="Whether MELT was available for conversion"
    )


# =============================================================================
# ERDI DATA - Exchange Rate Deviation Index
# =============================================================================


class ERDIData(BaseModel):
    """ERDI (Exchange Rate Deviation Index) by country.

    ERDI = GDP_PPP / GDP_MER

    Interpretation:
        - ERDI = 1.0: Core country (market rates reflect purchasing power)
        - ERDI > 1.0: Periphery (currency undervalued, labor compressed)
        - ERDI = 2.0: Typical periphery (labor worth 50% of nominal)

    Source: Penn World Tables 10.01 (2019 reference year)

    Example:
        >>> ERDIData(
        ...     country_code="CHN",
        ...     country_name="China",
        ...     erdi=1.80,
        ...     reference_year=2019,
        ... )
        ERDIData(country_code='CHN', ...)
    """

    model_config = ConfigDict(frozen=True)

    country_code: str = Field(..., min_length=2, max_length=3, description="ISO country code")
    country_name: str = Field(..., description="Full country name")
    erdi: float = Field(..., gt=0.0, description="ERDI value")
    reference_year: int = Field(..., ge=2000, le=2030, description="Data year")
    source: str = Field(
        default="Penn World Tables 10.01",
        description="Data source citation",
    )


# =============================================================================
# MVP CONSTANTS
# =============================================================================


MVP_ERDI_VALUES: dict[str, ERDIData] = {
    "CHN": ERDIData(country_code="CHN", country_name="China", erdi=1.80, reference_year=2019),
    "MEX": ERDIData(country_code="MEX", country_name="Mexico", erdi=1.50, reference_year=2019),
    "CAN": ERDIData(country_code="CAN", country_name="Canada", erdi=1.10, reference_year=2019),
    "VNM": ERDIData(country_code="VNM", country_name="Vietnam", erdi=2.50, reference_year=2019),
    "DEU": ERDIData(country_code="DEU", country_name="Germany", erdi=1.00, reference_year=2019),
    "JPN": ERDIData(country_code="JPN", country_name="Japan", erdi=1.00, reference_year=2019),
    "KOR": ERDIData(country_code="KOR", country_name="South Korea", erdi=1.10, reference_year=2019),
    "IND": ERDIData(country_code="IND", country_name="India", erdi=2.80, reference_year=2019),
    "TWN": ERDIData(country_code="TWN", country_name="Taiwan", erdi=1.20, reference_year=2019),
}
"""MVP ERDI values from Penn World Tables 10.01 (2019 reference year).

These are hardcoded for the MVP implementation. Future versions will load
from the Penn World Tables database dynamically.
"""

CORE_DEFAULT_ERDI: float = 1.0
"""Fallback ERDI for core countries not in MVP list."""

PERIPHERY_DEFAULT_ERDI: float = 2.0
"""Fallback ERDI for periphery countries not in MVP list."""


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def weighted_average_gamma(
    gammas: list[float],
    weights: list[float],
) -> float:
    """Compute intensive weighted average of gamma values per FR-011.

    This is an intensive aggregation: the result represents the average
    visibility coefficient, NOT a sum. The weights determine contribution
    but the result stays in [0, 1] regardless of total weight.

    Formula: gamma_avg = sum(weight_i * gamma_i) / sum(weight_i)

    Args:
        gammas: List of gamma visibility coefficients [0, 1].
        weights: List of corresponding weights (e.g., population, GDP).

    Returns:
        Weighted average gamma value.

    Raises:
        ValueError: If lists have different lengths or total weight is zero.

    Example:
        >>> weighted_average_gamma([0.30, 0.35], [100.0, 200.0])
        0.3333333333333333
    """
    if len(gammas) != len(weights):
        msg = f"gammas ({len(gammas)}) and weights ({len(weights)}) must have same length"
        raise ValueError(msg)

    total_weight = sum(weights)
    if total_weight == 0.0:
        msg = "Total weight must be positive"
        raise ValueError(msg)

    weighted_sum = sum(g * w for g, w in zip(gammas, weights, strict=True))
    return weighted_sum / total_weight


__all__ = [
    "CORE_DEFAULT_ERDI",
    "ERDIData",
    "GammaBasket",
    "GammaIII",
    "GammaImport",
    "MVP_ERDI_VALUES",
    "PERIPHERY_DEFAULT_ERDI",
    "ShadowSubsidy",
    "weighted_average_gamma",
]
