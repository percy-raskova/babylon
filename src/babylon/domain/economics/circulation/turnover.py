"""Turnover time and annual surplus value computations.

Feature: 023-capital-volume-ii
Tasks: T035-T038

Functions for computing annualized surplus value adjusted for turnover
frequency, comparing turnover advantages between sectors, and resolving
turnover profiles by NAICS code.

Marx's key insight (Capital II Ch. 16): the annual rate of surplus value
can far exceed the single-cycle rate because variable capital turns over
multiple times per year. Faster turnover = more surplus extraction.

See Also:
    :mod:`babylon.domain.economics.circulation.types`: AnnualSurplusValue, TurnoverProfile.
    :mod:`babylon.domain.economics.circulation.defaults`: Default profiles by NAICS.
"""

from __future__ import annotations

from typing import Protocol

from babylon.domain.economics.circulation.defaults import (
    DEFAULT_TURNOVER_PROFILES,
    FALLBACK_PROFILE,
)
from babylon.domain.economics.circulation.types import (
    AnnualSurplusValue,
    TurnoverProfile,
)
from babylon.models.types import Currency

# Upper bound for iteration over industry weights (safety per coding rule 2)
_MAX_INDUSTRIES: int = 1000


def compute_annual_surplus_value(
    variable_capital: Currency,
    surplus_per_cycle: Currency,
    turnover_time_days: int,
    fips_code: str = "00000",
    year: int = 2022,
) -> AnnualSurplusValue:
    """Compute turnover-adjusted annual surplus value.

    Wraps the inputs into an AnnualSurplusValue model which provides
    computed fields for annual_surplus_value and annual_rate_of_surplus_value.

    Args:
        variable_capital: Variable capital (v) advanced per cycle.
        surplus_per_cycle: Surplus value (s) extracted per cycle.
        turnover_time_days: Days for one complete circuit.
        fips_code: 5-digit county FIPS code (default "00000").
        year: Calendar year (default 2022).

    Returns:
        AnnualSurplusValue with computed annual metrics.

    Example:
        >>> from babylon.models.types import Currency
        >>> result = compute_annual_surplus_value(
        ...     Currency(1000.0), Currency(1000.0), 60,
        ... )
        >>> abs(result.annual_rate_of_surplus_value - 6.083) < 0.01
        True
    """
    return AnnualSurplusValue(
        fips_code=fips_code,
        year=year,
        variable_capital_advanced=variable_capital,
        surplus_value_per_cycle=surplus_per_cycle,
        turnover_time_days=turnover_time_days,
    )


def compare_turnover_advantage(
    fast: AnnualSurplusValue,
    slow: AnnualSurplusValue,
) -> float:
    """Compare annual surplus between fast and slow turnover capitals.

    Args:
        fast: Capital with faster turnover (higher annual surplus expected).
        slow: Capital with slower turnover (lower annual surplus expected).

    Returns:
        Ratio of fast.annual_surplus_value / slow.annual_surplus_value.
        Returns 0.0 if slow.annual_surplus_value is zero.

    Example:
        >>> from babylon.models.types import Currency
        >>> fast = compute_annual_surplus_value(Currency(1000.0), Currency(1000.0), 60)
        >>> slow = compute_annual_surplus_value(Currency(1000.0), Currency(1000.0), 182)
        >>> ratio = compare_turnover_advantage(fast, slow)
        >>> abs(ratio - 3.033) < 0.01
        True
    """
    if slow.annual_surplus_value == 0.0:
        return 0.0
    return fast.annual_surplus_value / slow.annual_surplus_value


# =============================================================================
# TURNOVER PROFILE SOURCE (Protocol + Default Implementation)
# =============================================================================


class TurnoverProfileSource(Protocol):
    """Protocol for resolving turnover profiles by NAICS code.

    Implementations may look up profiles from a database, configuration
    file, or the default profiles dictionary.

    See Also:
        :class:`DefaultTurnoverProfileSource`: Default implementation.
    """

    def get_turnover_profile(self, naics_code: str) -> TurnoverProfile | None:
        """Resolve a turnover profile for the given NAICS code.

        Args:
            naics_code: NAICS industry code (2-6 digits).

        Returns:
            TurnoverProfile if found, None otherwise.
        """
        ...


class DefaultTurnoverProfileSource:
    """Default implementation resolving from built-in NAICS sector profiles.

    Resolution order:
    1. Exact match on the provided NAICS code.
    2. 2-digit sector prefix match.
    3. Fallback profile for unknown sectors.

    Example:
        >>> source = DefaultTurnoverProfileSource()
        >>> profile = source.get_turnover_profile("311210")
        >>> profile is not None
        True
        >>> profile.naics_code
        '31'
    """

    def __init__(self) -> None:
        """Initialize with default profiles from defaults module."""
        self._profiles: dict[str, TurnoverProfile] = DEFAULT_TURNOVER_PROFILES

    def get_turnover_profile(self, naics_code: str) -> TurnoverProfile | None:
        """Resolve a turnover profile for the given NAICS code.

        Tries exact match first, then 2-digit prefix, then fallback.

        Args:
            naics_code: NAICS industry code (2-6 digits).

        Returns:
            TurnoverProfile (never None for this implementation; fallback used).
        """
        # 1. Exact match
        if naics_code in self._profiles:
            return self._profiles[naics_code]

        # 2. 2-digit sector prefix
        prefix = naics_code[:2]
        if prefix in self._profiles:
            return self._profiles[prefix]

        # 3. Fallback
        return FALLBACK_PROFILE


def get_weighted_turnover_profile(
    industry_weights: dict[str, float],
    source: TurnoverProfileSource,
) -> TurnoverProfile | None:
    """Compute employment-weighted average turnover profile.

    For each industry, resolves its turnover profile from the source.
    Industries where the source returns None are skipped and their
    weights are redistributed among known industries.

    Args:
        industry_weights: Mapping of NAICS code to employment share.
        source: Turnover profile resolver.

    Returns:
        Weighted average TurnoverProfile with naics_code="WEIGHTED",
        or None if no profiles could be resolved.

    Example:
        >>> source = DefaultTurnoverProfileSource()
        >>> result = get_weighted_turnover_profile({"31": 0.7, "44": 0.3}, source)
        >>> result is not None
        True
    """
    if not industry_weights:
        return None

    # Resolve profiles and collect (weight, profile) pairs
    resolved: list[tuple[float, TurnoverProfile]] = []
    for count, (naics_code, weight) in enumerate(industry_weights.items()):
        if count >= _MAX_INDUSTRIES:
            break

        profile = source.get_turnover_profile(naics_code)
        if profile is not None and weight > 0.0:
            resolved.append((weight, profile))

    if not resolved:
        return None

    # Renormalize weights to sum to 1.0
    total_weight = sum(w for w, _ in resolved)
    if total_weight <= 0.0:
        return None

    # Compute weighted averages
    avg_working = 0.0
    avg_non_working = 0.0
    avg_purchase = 0.0
    avg_sale = 0.0
    avg_fixed_ratio = 0.0

    for weight, profile in resolved:
        normalized = weight / total_weight
        avg_working += profile.working_period_days * normalized
        avg_non_working += profile.non_working_production_days * normalized
        avg_purchase += profile.purchase_time_days * normalized
        avg_sale += profile.sale_time_days * normalized
        avg_fixed_ratio += profile.fixed_capital_ratio * normalized

    # Round day counts to integers (must be >= 1 for working_period)
    working_days = max(1, round(avg_working))
    non_working_days = max(0, round(avg_non_working))
    purchase_days = max(0, round(avg_purchase))
    sale_days = max(0, round(avg_sale))

    return TurnoverProfile(
        naics_code="WEIGHTED",
        working_period_days=working_days,
        non_working_production_days=non_working_days,
        purchase_time_days=purchase_days,
        sale_time_days=sale_days,
        fixed_capital_ratio=round(avg_fixed_ratio, 4),
    )


__all__ = [
    "DefaultTurnoverProfileSource",
    "TurnoverProfileSource",
    "compare_turnover_advantage",
    "compute_annual_surplus_value",
    "get_weighted_turnover_profile",
]
