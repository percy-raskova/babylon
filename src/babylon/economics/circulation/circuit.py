"""Circuit state functions for Capital Volume II.

Feature: 023-capital-volume-ii
Tasks: T028-T029

Pure functions for advancing capital through the M-C-P-C'-M' circuit
and initializing circuit state with proportional capital distribution.

The circuit is modeled as a continuous fractional flow: each tick,
a fraction (elapsed_days / phase_duration) of capital in each form
flows to the next form in the circuit.

See Also:
    :class:`babylon.economics.circulation.types.CircuitState`: Data model.
    :class:`babylon.economics.circulation.types.TurnoverProfile`: Phase durations.
"""

from __future__ import annotations

from babylon.economics.circulation.types import CircuitState, TurnoverProfile
from babylon.models.types import Currency

# Maximum elapsed days per tick (fixed upper bound for loop-free safety)
_MAX_ELAPSED_DAYS: int = 3650


def _phase_fraction(elapsed_days: int, phase_duration_days: int) -> float:
    """Compute fraction of capital that flows through a phase.

    Args:
        elapsed_days: Days elapsed in this tick.
        phase_duration_days: Duration of the phase in days.

    Returns:
        Fraction in [0.0, 1.0]. If phase_duration is 0, returns 1.0
        (instant transition).
    """
    if phase_duration_days <= 0:
        return 1.0
    return min(1.0, elapsed_days / phase_duration_days)


def advance_circuit(
    state: CircuitState,
    turnover: TurnoverProfile,
    surplus_value: Currency,
    elapsed_days: int,
) -> CircuitState:
    """Advance capital through M-C-P-C'-M' based on elapsed time.

    Each tick, capital flows between three forms simultaneously:

    - M -> P: fraction = elapsed_days / purchase_time_days
    - P -> C': fraction = elapsed_days / working_period_days (surplus created)
    - C' -> M: fraction = elapsed_days / sale_time_days

    Surplus value is created proportionally during the P->C' transition.
    Total capital is conserved except for surplus creation.

    Args:
        state: Current circuit state (M, P, C distribution).
        turnover: Sectoral turnover profile with phase durations.
        surplus_value: Surplus value generated per complete production cycle.
        elapsed_days: Days elapsed since last advance.

    Returns:
        New CircuitState with updated capital distribution.

    Raises:
        ValueError: If elapsed_days is negative.

    Example:
        >>> from babylon.economics.circulation.types import CircuitState, TurnoverProfile
        >>> from babylon.models.types import Currency
        >>> state = CircuitState(
        ...     fips_code="26163", year=2022,
        ...     money_capital=100.0, productive_capital=200.0,
        ...     commodity_capital=50.0, fixed_capital=120.0,
        ...     circulating_capital=80.0,
        ... )
        >>> profile = TurnoverProfile(
        ...     naics_code="31", working_period_days=30,
        ...     non_working_production_days=10, purchase_time_days=10,
        ...     sale_time_days=20, fixed_capital_ratio=0.6,
        ... )
        >>> result = advance_circuit(state, profile, Currency(25.0), 10)
        >>> result.total_capital >= state.total_capital
        True
    """
    if elapsed_days < 0:
        msg = f"elapsed_days must be non-negative, got {elapsed_days}"
        raise ValueError(msg)

    if elapsed_days == 0:
        return state

    # Compute fractional flows for each phase transition
    purchase_frac = _phase_fraction(elapsed_days, turnover.purchase_time_days)
    production_frac = _phase_fraction(elapsed_days, turnover.working_period_days)
    sale_frac = _phase_fraction(elapsed_days, turnover.sale_time_days)

    # Capital flowing between forms
    m_to_p = state.money_capital * purchase_frac
    p_to_c = state.productive_capital * production_frac
    c_to_m = state.commodity_capital * sale_frac

    # Surplus is created proportional to production fraction
    surplus_created = surplus_value * production_frac

    # Compute new capital in each form
    new_money = state.money_capital - m_to_p + c_to_m
    new_productive = state.productive_capital - p_to_c + m_to_p
    new_commodity = state.commodity_capital - c_to_m + p_to_c + surplus_created

    # Split productive capital into fixed and circulating
    new_fixed = new_productive * turnover.fixed_capital_ratio
    new_circulating = new_productive - new_fixed

    return CircuitState(
        fips_code=state.fips_code,
        year=state.year,
        money_capital=Currency(max(0.0, new_money)),
        productive_capital=Currency(max(0.0, new_productive)),
        commodity_capital=Currency(max(0.0, new_commodity)),
        fixed_capital=Currency(max(0.0, new_fixed)),
        circulating_capital=Currency(max(0.0, new_circulating)),
    )


def initialize_circuit_state(
    fips_code: str,
    year: int,
    total_capital: Currency,
    turnover: TurnoverProfile,
) -> CircuitState:
    """Distribute initial capital across M/P/C proportional to phase durations.

    The distribution reflects how capital at rest is distributed across
    the circuit: more capital sits in phases that take longer.

    - M fraction = (purchase_time + sale_time) / turnover_time
    - P fraction = working_period / turnover_time
    - C fraction = non_working_production / turnover_time

    If turnover_time is 0 (which requires working_period > 0 due to
    validation), all capital is placed in money form as a safe default.

    Args:
        fips_code: 5-digit county FIPS code.
        year: Calendar year.
        total_capital: Total capital to distribute.
        turnover: Sectoral turnover profile determining distribution.

    Returns:
        CircuitState with capital distributed across forms.

    Example:
        >>> from babylon.economics.circulation.types import TurnoverProfile
        >>> from babylon.models.types import Currency
        >>> profile = TurnoverProfile(
        ...     naics_code="31", working_period_days=30,
        ...     non_working_production_days=10, purchase_time_days=10,
        ...     sale_time_days=20, fixed_capital_ratio=0.6,
        ... )
        >>> state = initialize_circuit_state("26163", 2022, Currency(700.0), profile)
        >>> abs(state.total_capital - 700.0) < 0.01
        True
    """
    tt = turnover.turnover_time

    if tt == 0:
        # Defensive: all capital in money form
        return CircuitState(
            fips_code=fips_code,
            year=year,
            money_capital=total_capital,
            productive_capital=Currency(0.0),
            commodity_capital=Currency(0.0),
            fixed_capital=Currency(0.0),
            circulating_capital=Currency(0.0),
        )

    # Distribute proportionally to phase durations
    m_fraction = (turnover.purchase_time_days + turnover.sale_time_days) / tt
    p_fraction = turnover.working_period_days / tt
    c_fraction = turnover.non_working_production_days / tt

    money = total_capital * m_fraction
    productive = total_capital * p_fraction
    commodity = total_capital * c_fraction

    # Split productive into fixed and circulating
    fixed = productive * turnover.fixed_capital_ratio
    circulating = productive - fixed

    return CircuitState(
        fips_code=fips_code,
        year=year,
        money_capital=Currency(money),
        productive_capital=Currency(productive),
        commodity_capital=Currency(commodity),
        fixed_capital=Currency(fixed),
        circulating_capital=Currency(circulating),
    )


__all__ = ["advance_circuit", "initialize_circuit_state"]
