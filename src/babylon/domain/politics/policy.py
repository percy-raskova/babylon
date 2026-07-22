"""The LEGISLATE resolver — agenda item → gauntlet → funding → overlay (P25 U9, ADR135).

``resolve_legislate`` is the pipeline the-electoral-question.md §2.4 names
(the resolver ``resolve_legislate`` did not exist before this unit; the
StateAction→Action conversion misclassified a selected LEGISLATE as REPRESS).
Everything here is pure: the PolicySystem @17.47 gathers the terrain from the
graph, calls the resolver, and applies the resolution back.

The gauntlet order is jurisdictional-before-judicial-before-fiscal:

1. **Federal preemption** (§2.4 arm 4) — a lower sovereign on the ADMINISTERS
   DAG enacting past ``politics.preemption_envelope`` is nullified. The
   municipal-socialism ceiling.
2. **Judicial strike-down** (§2.4 arm 3) — an RSA_JUDICIAL bench voids
   incidence past ``judicial_tolerance_scale × liberal_technocratic``.
3. **The funding identity** (§2.4, L-CEILING) — ``SW_deliverable =
   min(SW_promised, t_claim + φ_share·Φ_inflow − debt_service)`` plus
   deficit financing under bond discipline.
4. **Capital strike** (§2.4 arm 1) — incidence past ``capital_tolerance``
   arms the equalization operator; the PolicySystem applies the county-grain
   migration (this module only raises the flag — the operator needs the
   spatial terrain).

Reform redistributes, it never mints value: the resolver's delivery can never
exceed the measured claim (``creates_value=False`` on the consuming system).
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from babylon.formulas.politics import delivery_gap, delivery_ratio, sw_deliverable
from babylon.models.enums.politics import PolicyAxis

if TYPE_CHECKING:
    from babylon.config.defines.politics import PoliticsDefines

from babylon.domain.economics.distribution.sovereign_fiscal import (
    bond_discipline_binds,
    finance_shortfall,
    sovereign_debt_service,
)

#: Axes whose overlay magnitude IS the policy incidence on measured surplus
#: (regulatory redistribution: no state funding moves, but capital bears the
#: cost — a wage floor or organizing-legality regime claims surplus share
#: directly). ``social_wage`` derives incidence from its funded promise
#: instead; the state-apparatus axes (police_budget/border_regime/war_posture)
#: carry ZERO capital incidence — capital does not strike against its own
#: protection.
_REGULATORY_REDISTRIBUTIVE: frozenset[PolicyAxis] = frozenset(
    {PolicyAxis.WAGE_FLOOR, PolicyAxis.LABOR_LAW}
)


class PolicyResolutionKind(StrEnum):
    """Terminal verdict of one agenda item's pass through the gauntlet."""

    ENACTED = "enacted"
    STRUCK = "struck"
    PREEMPTED = "preempted"


class PolicyAgendaItem(BaseModel):
    """One drafted policy awaiting the LEGISLATE resolver (frozen).

    :ivar sovereign_id: The enacting sovereign (``SOV_*``).
    :ivar axis: The policy-space axis the overlay writes.
    :ivar magnitude: Overlay magnitude in [0, 1] (axis-normalized).
    :ivar promised: Currency promise for funded axes (``social_wage``);
        0.0 for regulatory/state-apparatus axes.
    :ivar drafted_tick: Tick the item entered the agenda register.
    :ivar source_org_id: The drafting organization ("" when scenario-seeded).
    """

    model_config = ConfigDict(frozen=True)

    sovereign_id: str
    axis: PolicyAxis
    magnitude: float = Field(ge=0.0, le=1.0)
    promised: float = Field(default=0.0, ge=0.0)
    drafted_tick: int = Field(ge=0)
    source_org_id: str = ""


class FiscalTerrain(BaseModel):
    """The enacting sovereign's live fiscal facts, gathered @17.47 (frozen).

    All quantities are current-tick-fresh territory-node sums (written by
    TickDynamics @4.0) except ``debt_stock``, which is the sovereign fiscal
    register's carried principal.
    """

    model_config = ConfigDict(frozen=True)

    t_claim: float = Field(ge=0.0)
    phi_inflow: float = Field(ge=0.0)
    interest_rate: float = Field(ge=0.0)
    debt_stock: float = Field(ge=0.0)
    total_surplus: float = Field(ge=0.0)


class VetoGauntlet(BaseModel):
    """The veto terrain: who may nullify this sovereign's enactments (frozen).

    :ivar administers_parent: The higher sovereign on the ADMINISTERS DAG
        (``None`` for the apex — the apex is never preempted).
    :ivar judicial_benches: ``(institution_id, liberal_technocratic)`` pairs,
        deterministically ordered by the caller (sorted institution id).
    """

    model_config = ConfigDict(frozen=True)

    administers_parent: str | None = None
    judicial_benches: tuple[tuple[str, float], ...] = ()


class PolicyResolution(BaseModel):
    """The resolver's full verdict for one agenda item (frozen)."""

    model_config = ConfigDict(frozen=True)

    kind: PolicyResolutionKind
    incidence: float = Field(ge=0.0)
    promised: float = Field(default=0.0, ge=0.0)
    delivered: float = Field(default=0.0, ge=0.0)
    ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    gap: float = Field(default=0.0, ge=0.0)
    borrowed: float = Field(default=0.0, ge=0.0)
    capital_strike: bool = False
    striking_institution: str = ""
    preempting_sovereign: str = ""


def policy_incidence(item: PolicyAgendaItem, total_surplus: float) -> float:
    """Policy incidence on measured surplus ``s`` (§2.4).

    ``social_wage``: the promise as a share of measured surplus (a promise
    against zero measured surplus claims everything — clamped to 1.0, honest
    rather than infinite). Regulatory-redistributive axes: the magnitude IS
    the incidence share. State-apparatus axes: zero — capital does not
    strike against its own protection.
    """
    if item.axis is PolicyAxis.SOCIAL_WAGE:
        if item.promised <= 0.0:
            return 0.0
        if total_surplus <= 0.0:
            return 1.0
        return min(1.0, item.promised / total_surplus)
    if item.axis in _REGULATORY_REDISTRIBUTIVE:
        return item.magnitude
    return 0.0


def resolve_legislate(
    item: PolicyAgendaItem,
    terrain: FiscalTerrain,
    gauntlet: VetoGauntlet,
    defines: PoliticsDefines,
) -> PolicyResolution:
    """Run one agenda item through the §2.4 pipeline (pure).

    :param item: The drafted policy.
    :param terrain: The sovereign's live fiscal facts.
    :param gauntlet: The veto terrain (ADMINISTERS parent, judicial benches).
    :param defines: ``GameDefines.politics`` — Θ, never mutated.
    :returns: The full verdict; the caller applies overlays/registers/events.
    """
    incidence = policy_incidence(item, terrain.total_surplus)

    # Arm 4 — federal preemption: jurisdiction is checked before the bench
    # ever sees the item. The apex (no ADMINISTERS parent) is never preempted.
    if gauntlet.administers_parent is not None and item.magnitude > defines.preemption_envelope:
        return PolicyResolution(
            kind=PolicyResolutionKind.PREEMPTED,
            incidence=incidence,
            promised=item.promised,
            preempting_sovereign=gauntlet.administers_parent,
        )

    # Arm 3 — judicial strike-down: the first bench (caller-sorted) whose
    # class-balance tolerance the incidence exceeds voids the overlay.
    for institution_id, liberal_weight in gauntlet.judicial_benches:
        tolerance = defines.judicial_tolerance_scale * liberal_weight
        if incidence > tolerance:
            return PolicyResolution(
                kind=PolicyResolutionKind.STRUCK,
                incidence=incidence,
                promised=item.promised,
                striking_institution=institution_id,
            )

    # The funding identity (L-CEILING) — only funded promises pass through
    # it; regulatory and state-apparatus overlays need no funding.
    if item.promised > 0.0:
        service = sovereign_debt_service(terrain.debt_stock, terrain.interest_rate)
        phi_slice = defines.phi_social_share * terrain.phi_inflow
        funded = sw_deliverable(
            promised=item.promised,
            t_claim=terrain.t_claim,
            phi_slice=phi_slice,
            debt_service=service,
        )
        shortfall = delivery_gap(item.promised, funded)
        disciplined = bond_discipline_binds(
            service, terrain.t_claim, defines.bond_discipline_threshold
        )
        borrowed = finance_shortfall(shortfall, defines.debt_finance_share, disciplined)
        delivered = min(item.promised, funded + borrowed)
        return PolicyResolution(
            kind=PolicyResolutionKind.ENACTED,
            incidence=incidence,
            promised=item.promised,
            delivered=delivered,
            ratio=delivery_ratio(delivered, item.promised),
            gap=delivery_gap(item.promised, delivered),
            borrowed=borrowed,
            capital_strike=incidence > defines.capital_tolerance,
        )

    return PolicyResolution(
        kind=PolicyResolutionKind.ENACTED,
        incidence=incidence,
        capital_strike=incidence > defines.capital_tolerance,
    )


__all__ = [
    "FiscalTerrain",
    "PolicyAgendaItem",
    "PolicyResolution",
    "PolicyResolutionKind",
    "VetoGauntlet",
    "policy_incidence",
    "resolve_legislate",
]
