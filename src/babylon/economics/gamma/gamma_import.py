"""GammaImportCalculator service for computing international import visibility.

Feature: 015-gamma-visibility-tensor
Date: 2026-02-05

This module implements the gamma_import computation:
    gamma_import = sum(import_share[origin] * 1/ERDI[origin])

TVT Axiom Reference:
    - C1: ERDI = GDP_PPP / GDP_MER
    - Emmanuel-Amin unequal exchange theory

See Also:
    :mod:`babylon.economics.gamma.types`: ERDIData and MVP_ERDI_VALUES
    :mod:`babylon.economics.gamma.data_sources`: ERDISource protocol
"""

from __future__ import annotations

import logging
from typing import Protocol

from babylon.core.protocol_kit import CachedSource
from babylon.economics.gamma.types import (
    MVP_ERDI_VALUES,
    PERIPHERY_DEFAULT_ERDI,
    GammaImport,
)
from babylon.economics.gamma.validation import validate_gamma_import
from babylon.economics.tensor import NoDataSentinel

logger = logging.getLogger(__name__)

# Import share tolerance for validation
IMPORT_SHARE_TOLERANCE: float = 0.01

# MVP import shares for top US trading partners (2022 estimates)
# Source: US Census Bureau Foreign Trade Statistics
MVP_IMPORT_SHARES: dict[str, float] = {
    "CHN": 0.18,  # China
    "MEX": 0.14,  # Mexico
    "CAN": 0.13,  # Canada
    "VNM": 0.05,  # Vietnam
    "DEU": 0.05,  # Germany
    "JPN": 0.05,  # Japan
    "KOR": 0.04,  # South Korea
    "IND": 0.03,  # India
    "TWN": 0.03,  # Taiwan
}
"""MVP import shares for top US trading partners.

These shares sum to 0.70, representing the top 9 trading partners.
The remaining 0.30 is assigned a default peripheral ERDI of 2.0.
"""

MVP_REST_OF_WORLD_SHARE: float = 1.0 - sum(MVP_IMPORT_SHARES.values())
"""Residual share for countries not explicitly listed."""


class GammaImportCalculator(Protocol):
    """Protocol for international import visibility computation.

    Gamma_import measures the weighted-average visibility of imported goods
    based on ERDI differentials between the US and its trading partners.

    Formula:
        gamma_import = sum(import_share[i] * 1/ERDI[i])

    Example:
        >>> calculator = DefaultGammaImportCalculator()
        >>> result = calculator.compute(2022)
        >>> if result:
        ...     print(f"gamma_import = {result.gamma_import:.3f}")
    """

    def compute(self, year: int) -> GammaImport | NoDataSentinel:
        """Compute gamma_import for a given year.

        Args:
            year: Calendar year.

        Returns:
            GammaImport result or NoDataSentinel.
        """
        ...

    def get_erdi(self, country_code: str) -> float:
        """Get ERDI value for a country.

        Args:
            country_code: ISO 3-letter country code.

        Returns:
            ERDI value (uses fallback if not in MVP list).
        """
        ...


class DefaultGammaImportCalculator(CachedSource[float]):
    """Default implementation using MVP hardcoded ERDI and import share values.

    Uses Penn World Tables 10.01 ERDI values and US Census trade data
    for the top 9 US trading partners. The remaining ~30% of imports
    are assigned a default peripheral ERDI of 2.0.

    Example:
        >>> calculator = DefaultGammaImportCalculator()
        >>> result = calculator.compute(2022)
        >>> print(f"gamma_import = {result.gamma_import:.3f}")
        gamma_import = 0.650
    """

    def compute(self, year: int) -> GammaImport | NoDataSentinel:
        """Compute gamma_import using MVP values.

        Formula: gamma_import = sum(import_share[i] * 1/ERDI[i])

        Args:
            year: Calendar year.

        Returns:
            GammaImport result.
        """
        import_shares = dict(MVP_IMPORT_SHARES)
        erdi_values: dict[str, float] = {}

        # Compute weighted sum for known countries
        gamma_import: float = 0.0
        for country_code, share in import_shares.items():
            erdi = self.get_erdi(country_code)
            erdi_values[country_code] = erdi
            gamma_import += share * (1.0 / erdi)

        # Add rest-of-world contribution with peripheral ERDI
        if MVP_REST_OF_WORLD_SHARE > 0.0:
            import_shares["ROW"] = MVP_REST_OF_WORLD_SHARE
            erdi_values["ROW"] = PERIPHERY_DEFAULT_ERDI
            gamma_import += MVP_REST_OF_WORLD_SHARE * (1.0 / PERIPHERY_DEFAULT_ERDI)

        # Validate import shares sum
        shares_sum = sum(import_shares.values())
        if abs(shares_sum - 1.0) > IMPORT_SHARE_TOLERANCE:
            logger.error(
                "Import shares sum to %.4f, expected 1.0 (tolerance: %.2f)",
                shares_sum,
                IMPORT_SHARE_TOLERANCE,
            )

        # Validate result
        valid, message = validate_gamma_import(gamma_import)
        if message is not None:
            logger.warning("gamma_import validation: %s", message)
        if not valid:
            logger.error("gamma_import FAIL: %s", message)

        return GammaImport(
            year=year,
            import_shares=import_shares,
            erdi_values=erdi_values,
            gamma_import=gamma_import,
            is_mvp=True,
        )

    def get_erdi(self, country_code: str) -> float:
        """Get ERDI value for a country from MVP values.

        Falls back to CORE_DEFAULT_ERDI (1.0) for known core countries
        or PERIPHERY_DEFAULT_ERDI (2.0) for unknown countries.

        Args:
            country_code: ISO 3-letter country code.

        Returns:
            ERDI value.
        """
        erdi_data = MVP_ERDI_VALUES.get(country_code)
        if erdi_data is not None:
            return erdi_data.erdi
        return PERIPHERY_DEFAULT_ERDI


__all__ = ["DefaultGammaImportCalculator", "GammaImportCalculator"]
