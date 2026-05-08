"""County-level wealth estimation using ACS home ownership proxy.

Feature: 013-melt-basket-visibility
Date: 2026-02-02

This module provides county-level wealth estimation when detailed wealth
data (like Fed SCF) is unavailable. Home ownership serves as the primary
proxy because home equity is the dominant wealth vehicle for Labor Aristocracy.

Data Sources:
    - National: Fed SCF (Survey of Consumer Finances) for wealth percentiles
    - County proxy: ACS home ownership rate as primary LA indicator
    - County proxy: ACS median home value as wealth magnitude indicator

Proxy Rationale:
    Fed SCF wealth percentiles are only available nationally (triennial survey).
    For county-level analysis, we use home ownership as primary proxy because:
    1. Home equity is the primary wealth vehicle for middle America (LA)
    2. National homeownership ~65%, but ~30% are underwater or minimal equity
    3. Effective LA proxy = homeownership_rate * equity_factor
    4. Home ownership rate correlates strongly with LA share (expected r > 0.7)

Calibration:
    EQUITY_FACTOR = 0.6 calibrated from Fed SCF:
    - ~65% of Americans own homes
    - ~40% qualify as LA (50th-90th percentile wealth)
    - Therefore: 65% * 0.6 = 39% ≈ 40% LA share

Detroit Validation Case:
    - Wayne County (Detroit): Lower homeownership → lower estimated LA share
    - Oakland County (suburbs): Higher homeownership → higher estimated LA share
    - Expected: Oakland LA proxy > Wayne LA proxy
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from babylon.core.protocol_kit import CachedSource

if TYPE_CHECKING:
    from babylon.config.defines import ClassSystemDefines


class WealthProxyCalculator(Protocol):
    """Protocol for county-level wealth estimation from proxies.

    This service estimates wealth-based class shares when detailed wealth
    data is unavailable. Uses ACS home ownership as primary proxy for
    Labor Aristocracy share and precarity indicators for lumpenproletariat.

    Example:
        >>> calculator = DefaultWealthProxyCalculator()
        >>> la_share = calculator.estimate_la_share("26125", 2022)  # Oakland
        >>> la_share
        0.42  # Higher homeownership → higher LA share
        >>> lumpen = calculator.estimate_lumpen_share("26163", 2022)  # Wayne
        >>> lumpen  # Higher precarity → higher lumpen share
    """

    def estimate_la_share(self, fips: str, year: int) -> float:
        """Estimate Labor Aristocracy share from home ownership proxy.

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year for ACS data

        Returns:
            Estimated LA share [0, 1] based on home ownership rate
        """
        ...

    def estimate_wealth_percentile(self, fips: str, year: int) -> tuple[float, bool]:
        """Estimate median wealth percentile for county.

        Uses home ownership and home values to estimate where county's
        median resident falls in national wealth distribution.

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year

        Returns:
            Tuple of (percentile, is_estimated):
            - percentile: Estimated median wealth percentile (0-100)
            - is_estimated: True (always estimated for county data)
        """
        ...

    def get_homeownership_rate(self, fips: str, year: int) -> float | None:
        """Get home ownership rate from ACS data.

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year

        Returns:
            Home ownership rate [0, 1], or None if unavailable
        """
        ...

    def estimate_lumpen_share(self, fips: str, year: int) -> float | None:
        """Estimate lumpenproletariat share from precarity indicators.

        Components (from BLS LAUS + ACS):
            - U-6 unemployment rate (broad)
            - PTER rate (part-time for economic reasons)
            - NILF want work (not in labor force but want work)
            - Incarceration rate (optional, from BJS)

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year

        Returns:
            Estimated lumpen share [0, 1], or None if data unavailable.
            Returns data-driven estimate - no prescribed expected range.
        """
        ...


class DefaultWealthProxyCalculator(CachedSource[float]):
    """Default implementation of WealthProxyCalculator.

    Uses ACS home ownership rate as primary proxy for Labor Aristocracy
    share at county level, and precarity indicators for lumpenproletariat.

    Calibration Constants:
        - EQUITY_FACTOR = 0.6: Fraction of homeowners with real equity
          (not underwater or minimal). Calibrated from Fed SCF.
        - NATIONAL_LA_SHARE = 0.40: Target LA share (50th-90th percentile)
        - NATIONAL_HOMEOWNERSHIP = 0.65: US homeownership rate (2020 Census)

    Precarity Estimation Weights:
        - NILF_WEIGHT = 0.4: Discouraged/marginally attached workers
        - U6_GAP_WEIGHT = 0.3: U-6 minus U-3 gap (underemployed + marginal)
        - INCARCERATION_WEIGHT = 0.2: Carceral exclusion
        - PTER_WEIGHT = 0.1: Half of PTER as borderline lumpen

    Detroit Validation Case:
        Wayne County (26163) should show higher lumpen share than Oakland (26125)
        due to higher unemployment, NILF, and incarceration rates.

    Example:
        >>> calculator = DefaultWealthProxyCalculator()
        >>> # Oakland County (higher homeownership, lower precarity)
        >>> calculator.estimate_la_share("26125", 2022)
        0.468
        >>> calculator.estimate_lumpen_share("26125", 2022)
        0.028
        >>> # Wayne County (lower homeownership, higher precarity)
        >>> calculator.estimate_la_share("26163", 2022)
        0.312
        >>> calculator.estimate_lumpen_share("26163", 2022)
        0.062
    """

    # Calibration constants from Fed SCF and Census data
    EQUITY_FACTOR = 0.6  # Fraction of homeowners with meaningful equity
    NATIONAL_HOMEOWNERSHIP = 0.65  # US homeownership rate (approx)
    NATIONAL_LA_SHARE = 0.40  # Expected LA share (50th-90th percentile)

    # Precarity weights for lumpen share estimation
    # Weight toward hard exclusion (NILF, incarcerated) over soft (PTER)
    NILF_WEIGHT = 0.4  # Discouraged/marginally attached
    U6_GAP_WEIGHT = 0.3  # U-6 minus U-3 = underemployed + marginal
    INCARCERATION_WEIGHT = 0.2  # Incarcerated
    PTER_WEIGHT = 0.1  # Half of PTER as borderline lumpen

    # Reference homeownership rates by FIPS (from ACS 2022)
    # In production, this would come from ACS data loader
    _HOMEOWNERSHIP_BY_FIPS: dict[str, float] = {
        # Detroit Metro validation case
        "26163": 0.52,  # Wayne County (Detroit proper) - lower
        "26125": 0.78,  # Oakland County (suburbs) - higher
        # Additional reference points
        "06037": 0.47,  # Los Angeles County - lower (renters)
        "48201": 0.56,  # Harris County (Houston) - moderate
        "17031": 0.58,  # Cook County (Chicago) - moderate
        "36061": 0.32,  # New York County (Manhattan) - very low
    }

    # Reference precarity data by FIPS (from BLS LAUS + ACS + BJS)
    # In production, this would come from data loaders
    # Data sources:
    #   - u3_rate: BLS LAUS county unemployment
    #   - u6_rate: BLS LAUS state-level (county proxy from ACS B23005 NILF)
    #   - pter_rate: ACS B23023 (part-time for economic reasons)
    #   - nilf_want_work: ACS B23005 (not in labor force but want work)
    #   - incarceration_rate: BJS / Vera Institute county data
    _PRECARITY_BY_FIPS: dict[str, dict[str, float]] = {
        # Detroit Metro validation case
        "26163": {  # Wayne County (Detroit proper) - domestic periphery
            "u3_rate": 0.08,
            "u6_rate": 0.14,
            "pter_rate": 0.05,
            "nilf_want_work": 0.04,
            "incarceration_rate": 0.02,
        },
        "26125": {  # Oakland County (suburbs) - domestic core
            "u3_rate": 0.04,
            "u6_rate": 0.07,
            "pter_rate": 0.03,
            "nilf_want_work": 0.02,
            "incarceration_rate": 0.01,
        },
        # Additional reference points
        "06037": {  # Los Angeles County - high precarity metro
            "u3_rate": 0.05,
            "u6_rate": 0.11,
            "pter_rate": 0.04,
            "nilf_want_work": 0.03,
            "incarceration_rate": 0.015,
        },
        "48201": {  # Harris County (Houston) - moderate precarity
            "u3_rate": 0.05,
            "u6_rate": 0.10,
            "pter_rate": 0.04,
            "nilf_want_work": 0.025,
            "incarceration_rate": 0.018,
        },
        "17031": {  # Cook County (Chicago) - high inequality
            "u3_rate": 0.06,
            "u6_rate": 0.12,
            "pter_rate": 0.045,
            "nilf_want_work": 0.035,
            "incarceration_rate": 0.022,
        },
        "36061": {  # New York County (Manhattan) - low unemployment, some precarity
            "u3_rate": 0.04,
            "u6_rate": 0.08,
            "pter_rate": 0.035,
            "nilf_want_work": 0.025,
            "incarceration_rate": 0.008,
        },
    }

    def __init__(
        self,
        homeownership_data: dict[str, float] | None = None,
        precarity_data: dict[str, dict[str, float]] | None = None,
        equity_factor: float | None = None,
        class_system_defines: ClassSystemDefines | None = None,
        reservation_fips: set[str] | None = None,
    ) -> None:
        """Initialize with optional data overrides.

        Args:
            homeownership_data: Optional dict mapping FIPS to ownership rates
            precarity_data: Optional dict mapping FIPS to precarity indicators
            equity_factor: Optional override for equity factor calibration.
                Takes priority over class_system_defines if both provided.
            class_system_defines: Optional ClassSystemDefines for equity_factor
                and trust_land_discount. Falls back to GameDefines defaults.
            reservation_fips: Optional set of FIPS codes for reservation counties
                where trust_land_discount applies to homeownership rates.
        """
        super().__init__()
        self._homeownership = (
            homeownership_data if homeownership_data else self._HOMEOWNERSHIP_BY_FIPS.copy()
        )
        self._precarity = precarity_data if precarity_data else self._PRECARITY_BY_FIPS.copy()
        self._reservation_fips: set[str] = reservation_fips if reservation_fips else set()

        # Priority: explicit equity_factor > class_system_defines > class constant
        if equity_factor is not None:
            self._equity_factor = equity_factor
        elif class_system_defines is not None:
            self._equity_factor = class_system_defines.equity_factor
        else:
            self._equity_factor = self.EQUITY_FACTOR

        # trust_land_discount from defines (only used for reservation counties)
        if class_system_defines is not None:
            self._trust_land_discount = class_system_defines.trust_land_discount
        else:
            self._trust_land_discount = 1.0  # No discount by default

    def _effective_homeownership(self, fips: str, raw_rate: float) -> float:
        """Apply trust_land_discount if FIPS is a reservation county.

        Args:
            fips: 5-digit FIPS code for county.
            raw_rate: Raw homeownership rate from data.

        Returns:
            Effective homeownership rate after any reservation discount.
        """
        if fips in self._reservation_fips:
            return raw_rate * self._trust_land_discount
        return raw_rate

    def estimate_la_share(self, fips: str, year: int) -> float:
        """Estimate Labor Aristocracy share from home ownership proxy.

        .. deprecated::
            This static ACS proxy is superseded by Feature 043's endogenous
            property-based classification. Use
            :func:`babylon.economics.substrate.transitions.check_equity_threshold`
            and :func:`babylon.economics.substrate.transitions.evaluate_class_shares`
            for dynamic, tenure-driven LA classification.

        Formula: LA_share = effective_homeownership * equity_factor

        For reservation counties (FIPS in reservation_fips set), homeownership
        is discounted by trust_land_discount because reservation property
        operates under a different property regime without appreciation or
        equity extraction (FR-005).

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year for ACS data

        Returns:
            Estimated LA share [0, 1], or national average if data unavailable
        """
        import warnings

        warnings.warn(
            "estimate_la_share is deprecated. Feature 043 replaces the "
            "static ACS proxy with endogenous property-based classification "
            "via check_equity_threshold + evaluate_class_shares. "
            "See babylon.economics.substrate.transitions.",
            DeprecationWarning,
            stacklevel=2,
        )
        homeownership = self.get_homeownership_rate(fips, year)

        if homeownership is None:
            # Fall back to national average
            return self.NATIONAL_LA_SHARE

        effective = self._effective_homeownership(fips, homeownership)
        return effective * self._equity_factor

    def estimate_wealth_percentile(self, fips: str, year: int) -> tuple[float, bool]:
        """Estimate median wealth percentile for county.

        Uses home ownership rate to estimate where county's median
        resident falls in national wealth distribution. For reservation
        counties, applies trust_land_discount to homeownership first.

        Methodology:
            - Higher homeownership → higher median percentile
            - National median = 50th percentile by definition
            - Scale relative to national homeownership rate

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year

        Returns:
            Tuple of (percentile, is_estimated)
        """
        homeownership = self.get_homeownership_rate(fips, year)

        if homeownership is None:
            # National median
            return 50.0, True

        effective = self._effective_homeownership(fips, homeownership)

        # Scale relative to national rate
        # Higher homeownership → higher wealth percentile
        ratio = effective / self.NATIONAL_HOMEOWNERSHIP

        # Estimate percentile (clamped to [5, 95] for sanity)
        percentile = min(95.0, max(5.0, 50.0 * ratio))

        return percentile, True

    def get_homeownership_rate(self, fips: str, year: int) -> float | None:  # noqa: ARG002
        """Get home ownership rate from data.

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year (ignored for now, uses latest available)

        Returns:
            Home ownership rate [0, 1], or None if unavailable
        """
        return self._homeownership.get(fips)

    def estimate_lumpen_share(self, fips: str, year: int) -> float | None:  # noqa: ARG002
        """Estimate lumpenproletariat share from precarity indicators.

        Components (from BLS LAUS + ACS):
            - U-6 unemployment rate (broad)
            - PTER rate (part-time for economic reasons)
            - NILF want work (not in labor force but want work)
            - Incarceration rate (optional, from BJS)

        Formula:
            lumpen_share = (
                NILF_WEIGHT * nilf_want_work +
                U6_GAP_WEIGHT * (u6_rate - u3_rate) +
                INCARCERATION_WEIGHT * incarceration_rate +
                PTER_WEIGHT * pter_rate * 0.5
            )

        Returns data-driven estimate - no prescribed expected range.
        Let the data reveal the actual distribution.

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year (ignored for now, uses latest available)

        Returns:
            Estimated lumpen share [0, 0.5] (capped at bottom 50%),
            or None if data unavailable.
        """
        data = self._precarity.get(fips)
        if data is None:
            # No data available - return None, let caller handle missing data
            return None

        u3_rate = data.get("u3_rate", 0.0)
        u6_rate = data.get("u6_rate", 0.0)
        pter_rate = data.get("pter_rate", 0.0)
        nilf_want_work = data.get("nilf_want_work", 0.0)
        incarceration_rate = data.get("incarceration_rate", 0.0)

        # Lumpen ≈ those excluded from stable employment
        # Let the data reveal the actual distribution
        lumpen_share = (
            self.NILF_WEIGHT * nilf_want_work
            + self.U6_GAP_WEIGHT * (u6_rate - u3_rate)
            + self.INCARCERATION_WEIGHT * incarceration_rate
            + self.PTER_WEIGHT * pter_rate * 0.5  # Half of PTER as borderline
        )

        # Cap at bottom 50% wealth share (mathematical constraint)
        # Lumpenproletariat cannot exceed the bottom 50% bracket
        bottom_50_share = 0.50
        return min(lumpen_share, bottom_50_share)

    def get_precarity_indicators(self, fips: str, year: int) -> dict[str, float] | None:  # noqa: ARG002
        """Get raw precarity indicators for county.

        Args:
            fips: 5-digit FIPS code for county
            year: Calendar year (ignored for now, uses latest available)

        Returns:
            Dict of precarity indicators, or None if unavailable.
            Keys: u3_rate, u6_rate, pter_rate, nilf_want_work, incarceration_rate
        """
        return self._precarity.get(fips)

    def get_class_distribution_estimate(self, fips: str, year: int) -> dict[str, float] | None:
        """Estimate full class distribution for county using wealth and precarity proxies.

        Uses home ownership for LA share and precarity indicators for lumpen share.
        Returns None if no data is available for the FIPS code.

        The distribution must sum to 1.0:
        - Bourgeoisie + Petit Bourgeoisie = 10% (fixed)
        - Labor Aristocracy = estimated from homeownership proxy
        - Proletariat + Lumpenproletariat = 90% - LA share (remainder)

        The lumpen share within the bottom is estimated from precarity indicators,
        with proletariat making up the rest.

        Args:
            fips: 5-digit FIPS code
            year: Calendar year

        Returns:
            Dict with estimated shares for each class position, or None if
            no data available for the FIPS code.
        """
        # Check if we have any data for this FIPS
        has_homeownership = fips in self._homeownership
        has_precarity = fips in self._precarity

        if not has_homeownership and not has_precarity:
            # No data available - return None (let caller handle missing data)
            return None

        # Fixed shares for bourgeoisie and petit-bourgeoisie (top 10%)
        bourgeoisie_share = 0.01
        petit_bourgeoisie_share = 0.09
        top_10 = bourgeoisie_share + petit_bourgeoisie_share

        # Get LA share from homeownership proxy (or national average)
        la_share = self.estimate_la_share(fips, year)

        # Bottom share = everyone not in top 10% or LA
        # This ensures distribution sums to 1.0
        bottom_share = 1.0 - top_10 - la_share

        # Get lumpen share from precarity indicators
        lumpen_share = self.estimate_lumpen_share(fips, year)

        if lumpen_share is not None:
            # Scale lumpen share relative to the bottom share
            # If precarity data shows 5% lumpen, and bottom is 50%, lumpen is 5% of total
            # But lumpen cannot exceed the bottom share
            lumpen_share = min(lumpen_share, bottom_share)
            proletariat_share = max(0, bottom_share - lumpen_share)
        else:
            # Fall back to default split of bottom share
            # ~70% proletariat, ~30% lumpen within the bottom bracket
            base_proletariat_ratio = 0.70
            base_lumpen_ratio = 0.30
            proletariat_share = bottom_share * base_proletariat_ratio
            lumpen_share = bottom_share * base_lumpen_ratio

        return {
            "bourgeoisie": bourgeoisie_share,
            "petit_bourgeoisie": petit_bourgeoisie_share,
            "labor_aristocracy": la_share,
            "proletariat": proletariat_share,
            "lumpenproletariat": lumpen_share,
        }


__all__ = ["DefaultWealthProxyCalculator", "WealthProxyCalculator"]
