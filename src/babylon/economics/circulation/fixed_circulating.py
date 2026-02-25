"""Fixed and circulating capital decomposition for Capital Volume II.

Feature: 023-capital-volume-ii
Tasks: T040-T047 (FR-008, FR-009, FR-010, FR-011)

Implements constant capital decomposition into fixed/circulating portions,
depreciation fund dynamics, and moral depreciation (technological
obsolescence) per Marx Capital Volume II Part II (Chapters 8-11).

Fixed capital transfers value gradually over many production cycles
(machinery, buildings). Circulating capital is consumed entirely in each
cycle (raw materials, labor power). The distinction creates the
replacement fund dynamic that drives investment cycles.

See Also:
    :mod:`babylon.economics.circulation.types`: Frozen Pydantic models.
    :class:`DepreciationFundState`: Fund adequacy and replacement cycle.
    :class:`MoralDepreciation`: Technological obsolescence factor.
"""

from __future__ import annotations

from babylon.economics.circulation.types import (
    DepreciationFundState,
    MoralDepreciation,
)
from babylon.models.types import Currency


def decompose_constant_capital(
    total_c: Currency,
    fixed_capital_ratio: float,
) -> tuple[Currency, Currency]:
    """Split constant capital into fixed and circulating portions.

    Fixed capital (machinery, buildings) transfers value gradually across
    many production cycles. Circulating capital (raw materials, labor power)
    is consumed entirely in each cycle.

    Args:
        total_c: Total constant capital to decompose.
        fixed_capital_ratio: Fraction allocated to fixed capital, in [0, 1].

    Returns:
        Tuple of (fixed_capital, circulating_capital) where their sum
        equals total_c.

    Raises:
        ValueError: If fixed_capital_ratio is outside [0, 1].

    Example:
        >>> decompose_constant_capital(Currency(100.0), 0.6)
        (60.0, 40.0)
    """
    if fixed_capital_ratio < 0.0 or fixed_capital_ratio > 1.0:
        msg = f"fixed_capital_ratio must be in [0, 1], got {fixed_capital_ratio}"
        raise ValueError(msg)

    fixed = Currency(total_c * fixed_capital_ratio)
    circulating = Currency(total_c * (1.0 - fixed_capital_ratio))
    return fixed, circulating


def update_depreciation_fund(
    previous: DepreciationFundState,
    annual_depreciation: Currency,
    replacement_expenditure: Currency,
) -> DepreciationFundState:
    """Update depreciation fund state for one period.

    Accumulates the annual depreciation charge onto the existing fund
    and records the replacement expenditure for the new period. The
    resulting fund adequacy and replacement cycle position are computed
    automatically by the DepreciationFundState model.

    Args:
        previous: Depreciation fund state from the prior period.
        annual_depreciation: Annual depreciation charge for this period.
        replacement_expenditure: Actual replacement investment this period.

    Returns:
        New DepreciationFundState with updated accumulation, incremented
        year, and recalculated cycle position.

    Example:
        >>> from babylon.economics.circulation.types import DepreciationFundState
        >>> prev = DepreciationFundState(
        ...     fips_code="26163", year=2020,
        ...     total_fixed_capital=1000000.0,
        ...     accumulated_depreciation=100000.0,
        ...     annual_depreciation_flow=100000.0,
        ...     replacement_expenditure=80000.0,
        ... )
        >>> result = update_depreciation_fund(prev, Currency(100000.0), Currency(90000.0))
        >>> result.accumulated_depreciation
        200000.0
    """
    new_accumulated = Currency(previous.accumulated_depreciation + annual_depreciation)

    return DepreciationFundState(
        fips_code=previous.fips_code,
        year=previous.year + 1,
        total_fixed_capital=previous.total_fixed_capital,
        accumulated_depreciation=new_accumulated,
        annual_depreciation_flow=annual_depreciation,
        replacement_expenditure=replacement_expenditure,
    )


def compute_moral_depreciation(
    naics_code: str,
    physical_remaining_life: float,
    economic_remaining_life: float,
) -> MoralDepreciation:
    """Create MoralDepreciation from industry data.

    Moral depreciation occurs when fixed capital loses value not through
    physical wear but through technological supersession. A machine may
    still function physically but become economically obsolete when a
    more productive machine is introduced.

    Args:
        naics_code: NAICS industry code identifying the sector.
        physical_remaining_life: Years of physical service remaining (>= 0).
        economic_remaining_life: Years of economic viability remaining (>= 0).

    Returns:
        MoralDepreciation model with computed obsolescence_factor.

    Example:
        >>> result = compute_moral_depreciation("334", 10.0, 3.0)
        >>> result.obsolescence_factor
        0.3
    """
    return MoralDepreciation(
        naics_code=naics_code,
        physical_remaining_life=physical_remaining_life,
        economic_remaining_life=economic_remaining_life,
    )


__all__ = [
    "compute_moral_depreciation",
    "decompose_constant_capital",
    "update_depreciation_fund",
]
