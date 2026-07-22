"""Sovereign fiscal ledger — the debt half of the funding identity (P25 U9, ADR135).

The endogenous interest RATE has been live since Vol III (ADR089:
``NationalFinancialParameters.endogenous_interest``), but no sovereign debt
STOCK existed anywhere — :class:`~babylon.domain.economics.distribution.types.
DebtAccumulation` models per-county ENTERPRISE deficits and is never
constructed in production. This module is the missing carrier plus the pure
laws around it:

- ``debt_service = rate × stock`` — the third term of the funding identity
  ``SW_deliverable = min(SW_promised, t_claim + φ_share·Φ_inflow − debt_service)``
  (:func:`babylon.formulas.politics.sw_deliverable`).
- **Bond discipline** (the-electoral-question.md §2.4 arm 2): once
  ``debt_service / t_claim`` crosses ``politics.bond_discipline_threshold``,
  deficit financing is refused — the serviceability tightener.
- **Deficit financing**: an unfunded promise borrows
  ``politics.debt_finance_share`` of its shortfall; the borrowed principal
  compounds the stock, next tick's service shrinks the funded ceiling —
  O'Connor's fiscal crisis of the state as arithmetic.

The state is carried in a graph-attr register owned by PolicySystem @17.47
(the ``opposition_states`` durability class: survives the engine's in-place
graph across ticks, dropped by the ``WorldState`` round-trip like every
system-owned graph attr).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SovereignFiscalState(BaseModel):
    """Per-sovereign debt ledger carried across ticks (frozen).

    :ivar sovereign_id: The owning sovereign's id (``SOV_*``).
    :ivar debt_stock: Accumulated borrowed principal, never negative.
    :ivar last_borrowed: Principal borrowed on the most recent enactment
        tick (0.0 when the last agenda pass borrowed nothing).
    """

    model_config = ConfigDict(frozen=True)

    sovereign_id: str
    debt_stock: float = Field(default=0.0, ge=0.0)
    last_borrowed: float = Field(default=0.0, ge=0.0)


def sovereign_debt_service(debt_stock: float, interest_rate: float) -> float:
    """Per-tick debt service: ``max(0, stock) × max(0, rate)``.

    :param debt_stock: Sovereign borrowed principal.
    :param interest_rate: The live endogenous rate
        (``NationalFinancialParameters.endogenous_interest.rate``).
    :returns: Non-negative service claim on this tick's fiscal room.
    """
    return max(0.0, debt_stock) * max(0.0, interest_rate)


def bond_discipline_binds(debt_service: float, t_claim: float, threshold: float) -> bool:
    """The serviceability tightener (§2.4 arm 2).

    :param debt_service: This tick's service claim.
    :param t_claim: The sovereign's live tax claim (Σ ``tick_taxes_on_surplus``
        over its claimed territories).
    :param threshold: ``politics.bond_discipline_threshold``.
    :returns: ``True`` when further deficit financing is refused. A sovereign
        with live service and no tax base cannot borrow at all — the ratio is
        undefined, the discipline is total. Zero service never binds.
    """
    if debt_service <= 0.0:
        return False
    if t_claim <= 0.0:
        return True
    return debt_service / t_claim > threshold


def finance_shortfall(shortfall: float, finance_share: float, disciplined: bool) -> float:
    """Principal borrowed against an unfunded promise.

    :param shortfall: ``delivery_gap(promised, funded)`` — never mints when
        negative (a fully funded promise borrows nothing).
    :param finance_share: ``politics.debt_finance_share``.
    :param disciplined: Result of :func:`bond_discipline_binds`.
    :returns: Borrowed principal, 0.0 under discipline.
    """
    if disciplined:
        return 0.0
    return max(0.0, shortfall) * min(max(finance_share, 0.0), 1.0)


def borrow(state: SovereignFiscalState, borrowed: float) -> SovereignFiscalState:
    """Advance the ledger by one borrowing event (pure).

    :param state: Prior fiscal state.
    :param borrowed: Principal from :func:`finance_shortfall`.
    :returns: New frozen state with the stock compounded and
        ``last_borrowed`` recording this event.
    """
    return SovereignFiscalState(
        sovereign_id=state.sovereign_id,
        debt_stock=state.debt_stock + max(0.0, borrowed),
        last_borrowed=max(0.0, borrowed),
    )


__all__ = [
    "SovereignFiscalState",
    "bond_discipline_binds",
    "borrow",
    "finance_shortfall",
    "sovereign_debt_service",
]
