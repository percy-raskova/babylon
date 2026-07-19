"""Endogenous national interest rate (Capital Vol. III Part V).

Marx (ch. 22): "There is no such thing as a 'natural' rate of interest." The
rate is not read off a curve — it is *computed* from the average rate of
profit it divides (the ceiling; ch. 22 "the maximum limit of interest is the
profit itself") and the competitive tightness of the loan market (ch. 22 "the
relation between the supply of loanable capital … and the demand for it …
decides the market level of interest").

Pure functions of their arguments: no RNG, no wall clock, no I/O. This module
lives in ``domain/`` and imports nothing from ``engine/``; the engine reads
it.
"""

from __future__ import annotations

from babylon.config.defines import GameDefines
from babylon.domain.economics.credit.types import EndogenousInterestRate

#: Reserved: the supply of idle money-capital (Capital Vol. III ch. 25) has no
#: graph quantity yet; base U9 sets it to zero so it neither raises nor lowers
#: loan-market tightness (see design §1.5 for the creating task).
_IDLE_MONEY_CAPITAL_SUPPLY: float = 0.0

#: Placeholder simulation year for this pure core, which only ever sees the
#: reduced ``(r, tau)`` pair and does not know the tick's real calendar year.
#: The producer (U9.7) overwrites this with the live year via
#: ``model_copy(update={"year": ...})``; the value must satisfy
#: ``EndogenousInterestRate.year``'s ``ge=2007`` schema bound, so it is the
#: schema's own minimum rather than ``0``.
_PLACEHOLDER_YEAR: int = 2007


def _clamp_unit(value: float) -> float:
    """Clamp ``value`` into the closed unit interval [0.0, 1.0]."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def endogenous_interest_rate(
    profit_rate: float | None,
    tightness: float,
    defines: GameDefines,
) -> EndogenousInterestRate:
    """Compute the national interest rate as a bounded share of profit.

    ``i = r * (base + (ceiling - base) * tau)`` for ``r > 0``; ``i = 0`` when
    no profit is measured (``profit_rate`` is ``None`` or ``<= 0``) — Capital
    Vol. III ch. 23: interest is *a portion of the profit*, so with no profit
    there is nothing to divide (never a fabricated positive floor,
    Constitution III.11).

    The precondition is genuine, not structural: ``r`` is the realized general
    rate of profit that
    :meth:`~babylon.domain.economics.tick.system.TickDynamicsSystem._economy_wide_profit_rate`
    computes in scope from this tick's county surplus/profit-rate tensors, so
    ``i = 0`` here means a run whose counties truly carry no realized profit
    (an empty or pre-boundary tick), NOT the every-tick zero the earlier
    graph-attr read produced by looking at a stripped graph.

    :param profit_rate: Economy-wide average rate of profit ``r``, or ``None``
        when no county carries a realized profit rate this tick.
    :param tightness: Loan-market tightness ``tau`` (clamped into [0, 1]).
    :param defines: Run-scoped ``GameDefines`` (reads ``capital_vol3``).
    :returns: A total :class:`EndogenousInterestRate` — never absent.
    """
    cvi = defines.capital_vol3
    base = cvi.interest_profit_share_base
    ceiling = cvi.interest_profit_share_ceiling
    tau = _clamp_unit(tightness)

    if profit_rate is None or profit_rate <= 0.0:
        return EndogenousInterestRate(
            year=_PLACEHOLDER_YEAR,
            profit_rate_ceiling=0.0,
            rate=0.0,
            fragility_premium=0.0,
            tightness=tau,
            reserve_army_signal=0.0,
        )

    share = base + (ceiling - base) * tau
    rate = profit_rate * share
    premium = profit_rate * (ceiling - base) * tau
    return EndogenousInterestRate(
        year=_PLACEHOLDER_YEAR,
        profit_rate_ceiling=profit_rate,
        rate=rate,
        fragility_premium=premium,
        tightness=tau,
        reserve_army_signal=0.0,
    )


def loan_market_tightness(reserve_army_signal: float, defines: GameDefines) -> float:
    """Loan-market tightness ``tau`` — the demand/supply balance of loanable
    money-capital (Capital Vol. III ch. 22).

    ``tau = clamp(g_r * s_r - S, 0, 1)``. The demand term is the reserve-army
    downturn signal ``s_r`` (the material scramble for means of payment as
    overproduction throws labour out; ch. 25). The supply term ``S`` — idle
    money-capital — has no graph quantity yet and is fixed at 0 (design §1.5),
    so base U9 reproduces low/rising/spike and defers only the stagnation
    collapse.

    :param reserve_army_signal: ``s_r`` in [0, 1] (see
        ``graph_bridge.reserve_army_signal``).
    :param defines: Run-scoped ``GameDefines`` (reads ``capital_vol3``).
    :returns: ``tau`` in [0, 1].
    """
    gain = defines.capital_vol3.interest_reserve_demand_gain
    demand = gain * reserve_army_signal
    return _clamp_unit(demand - _IDLE_MONEY_CAPITAL_SUPPLY)
