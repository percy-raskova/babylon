"""Market-scissors system — Phase 1 SHADOW ONLY (Program 23, ADR077).

Position 17.8: immediately BEFORE ContradictionSystem @18 so the
``price_value`` shadow opposition measures a fresh scissors the same tick.

Evolves the national price⟷value axis: the log price-to-value ratio and log
fictitious-to-real ratio as damped-driven oscillators
(:mod:`babylon.formulas.market`), driven by the realized value flow already
on the graph — ``Σ v_produced`` (demand pull on prices) and
``Σ max(v_produced − w_paid, 0)`` (return-chasing on fictitious capital),
with price momentum feeding speculation (``momentum_coupling``).

PHASE 1 SCOPE (binding): observe-only shadow.

- State home: ``G.graph["market"]`` metadata (the ``wealth_distribution``
  round-trip pattern; ``WorldState.market`` carries it across facade ticks).
- Nothing reads it to change tick outputs: no correction feedback into
  wealth, credit, or the reserve army (Phase 2, owner-gated), so the sampled
  qa:regression checkpoints stay byte-identical.
- Honest absence: a graph with no paid-worker accounting gets NO market —
  the phenomenal form cannot precede its substance (Constitution III.11).
- Deterministic: coefficients from ``GameDefines.market``, nodes iterated in
  sorted-id order, zero RNG (Constitution III.7).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from babylon.engine.systems.wealth_distribution import (
    MARKET_CORRECTION_SHOCK_ATTR,
    _coerce_role,
    bracket_of_role,
)
from babylon.formulas.market import (
    calculate_correction_snap,
    calculate_ema,
    calculate_growth_drive,
    calculate_overhang,
    calculate_scissors_step,
    calculate_serviceable_divergence,
)
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.enums import EventType
from babylon.models.market import MarketState

if TYPE_CHECKING:
    from babylon.config.defines import MarketDefines
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

#: Graph-metadata key carrying the axis (matches ``WorldState.market``).
MARKET_ATTR = "market"

#: Wealth brackets holding the fictitious claims (ADR075 fold): 0 = top-1%
#: bourgeoisies, 1 = petty bourgeoisie. Brackets 2/3 hold labor, not claims.
_CLAIM_HOLDER_BRACKETS = (0, 1)


def _aggregate_wage_value(graph: GraphProtocol) -> tuple[float, float] | None:
    """``(Σ w_paid, Σ v_produced)`` over active paid-worker nodes, or ``None``.

    Same selection rule as ``ContradictionSystem._build_graph_inputs``:
    presence of BOTH attrs marks a paid worker class; inactive nodes skip.
    Sorted-id iteration fixes the float summation order (III.7). ``None``
    (not zeros) when no node carries the accounting pair — honest absence.
    """
    wages = 0.0
    value = 0.0
    found = False
    for node in sorted(graph.query_nodes(), key=lambda n: n.id):
        attrs = node.attributes
        if not attrs.get("active", True):
            continue
        if "w_paid" not in attrs or "v_produced" not in attrs:
            continue
        wages += float(attrs["w_paid"])
        value += float(attrs["v_produced"])
        found = True
    return (wages, value) if found else None


class MarketScissorsSystem(SystemBase):
    """Phase 1 SHADOW: the national price⟷value scissors axis."""

    name: ClassVar[str] = "Market Scissors"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Seed (first observation) or advance the scissors oscillators."""
        defines = services.defines.market
        tick = context.get("tick", 0) if isinstance(context, dict) else getattr(context, "tick", 0)
        metadata = getattr(graph, "graph", None)
        if not isinstance(metadata, dict):  # pragma: no cover — BabylonGraph always has it
            return
        flow = _aggregate_wage_value(graph)
        if flow is None:
            return  # no value substrate, no phenomenal form (III.11)
        wages, value = flow
        surplus = max(value - wages, 0.0)
        prior_raw = metadata.get(MARKET_ATTR)
        if isinstance(prior_raw, dict):
            state = self._advance(MarketState(**prior_raw), surplus, value, defines, int(tick))
        else:
            state = MarketState(
                price_log=0.0,
                price_velocity=0.0,
                fictitious_log=0.0,
                fictitious_velocity=0.0,
                surplus_ema=surplus,
                value_ema=value,
                tick=int(tick),
            )
        if defines.feedback_enabled:
            state = self._maybe_correct(graph, services, state, defines, int(tick))
        metadata[MARKET_ATTR] = state.model_dump()

    @staticmethod
    def _advance(
        prior: MarketState,
        surplus: float,
        value: float,
        defines: MarketDefines,
        tick: int,
    ) -> MarketState:
        """One deterministic oscillator step of both scissors.

        Prices chase value-output growth (demand pull) against the law-of-
        value reversion; fictitious capitalization chases realized-surplus
        growth PLUS price momentum (speculation rides the boom) against a
        weaker gravity — bubbles outlive price swings.
        """
        price_drive = calculate_growth_drive(
            value, prior.value_ema, sensitivity=defines.price_drive_sensitivity
        )
        price_log, price_velocity = calculate_scissors_step(
            prior.price_log,
            prior.price_velocity,
            price_drive,
            reversion=defines.price_reversion,
            damping=defines.price_damping,
            max_abs_log=defines.max_abs_log,
        )
        fictitious_drive = (
            calculate_growth_drive(
                surplus, prior.surplus_ema, sensitivity=defines.fictitious_drive_sensitivity
            )
            + defines.momentum_coupling * price_velocity
        )
        fictitious_log, fictitious_velocity = calculate_scissors_step(
            prior.fictitious_log,
            prior.fictitious_velocity,
            fictitious_drive,
            reversion=defines.fictitious_reversion,
            damping=defines.fictitious_damping,
            max_abs_log=defines.max_abs_log,
        )
        return MarketState(
            price_log=price_log,
            price_velocity=price_velocity,
            fictitious_log=fictitious_log,
            fictitious_velocity=fictitious_velocity,
            surplus_ema=calculate_ema(prior.surplus_ema, surplus, alpha=defines.surplus_ema_alpha),
            value_ema=calculate_ema(prior.value_ema, value, alpha=defines.surplus_ema_alpha),
            tick=tick,
            corrections=prior.corrections,
            last_correction_tick=prior.last_correction_tick,
        )

    # ------------------------------------------------------------------
    # Phase 2 (ADR078): the correction — the violent re-identification
    # of the phenomenal form with its substance, fed into the material base.
    # ------------------------------------------------------------------

    def _maybe_correct(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        state: MarketState,
        defines: MarketDefines,
        tick: int,
    ) -> MarketState:
        """Snap iff the overhang is unserviceable and the cooldown elapsed.

        The serviceability line is set by the realized rate of profit
        (:func:`~babylon.formulas.market.calculate_serviceable_divergence`):
        the same bubble that a healthy profit rate carries becomes unpayable
        when the rate falls — crisis as the meeting of Vol. III part 3 and
        part 5. Everything below is deterministic: sorted-id node iteration,
        coefficients from ``GameDefines.market``, zero RNG.
        """
        profit_rate = _mean_profit_rate(graph)
        serviceable = calculate_serviceable_divergence(
            profit_rate,
            base=defines.correction_threshold_base,
            slope=defines.correction_profit_slope,
        )
        overhang = calculate_overhang(state.fictitious_log, serviceable)
        if overhang <= 0.0:
            return state
        if (
            state.last_correction_tick is not None
            and tick - state.last_correction_tick < defines.correction_cooldown_ticks
        ):
            return state

        fictitious_log, fictitious_velocity = calculate_correction_snap(
            state.fictitious_log,
            state.fictitious_velocity,
            severity=defines.correction_severity,
        )
        price_log, price_velocity = calculate_correction_snap(
            state.price_log,
            state.price_velocity,
            severity=defines.correction_price_severity,
        )
        self._evaporate_wealth(graph, overhang, defines)
        self._swell_reserve_army(graph, overhang, defines)
        graph.set_graph_attr(MARKET_CORRECTION_SHOCK_ATTR, {"tick": tick, "overhang": overhang})
        corrected = state.model_copy(
            update={
                "price_log": price_log,
                "price_velocity": price_velocity,
                "fictitious_log": fictitious_log,
                "fictitious_velocity": fictitious_velocity,
                "corrections": state.corrections + 1,
                "last_correction_tick": tick,
            }
        )
        services.event_bus.publish(
            Event(
                type=EventType.MARKET_CORRECTION,
                tick=tick,
                payload={
                    "overhang": overhang,
                    "serviceable": serviceable,
                    "profit_rate": profit_rate,
                    "fictitious_log_before": state.fictitious_log,
                    "fictitious_log_after": fictitious_log,
                    "price_log_before": state.price_log,
                    "price_log_after": price_log,
                },
            )
        )
        return corrected

    @staticmethod
    def _evaporate_wealth(graph: GraphProtocol, overhang: float, defines: MarketDefines) -> None:
        """Destroy claim-holder wealth: the paper was counted; the snap un-counts.

        Applies only to active ``social_class`` nodes folding into the
        claim-holding brackets (:data:`_CLAIM_HOLDER_BRACKETS`, the ratified
        ADR075 role→bracket correspondence). Labor brackets hold no claims —
        their wealth is untouched here; the crisis reaches them through the
        reserve army instead.
        """
        fraction = min(defines.evaporation_gain * overhang, 1.0)
        if fraction <= 0.0:
            return
        for node in sorted(graph.query_nodes(node_type="social_class"), key=lambda n: n.id):
            if not node.attributes.get("active", True):
                continue
            role = _coerce_role(node.attributes.get("role"))
            if role is None or bracket_of_role(role) not in _CLAIM_HOLDER_BRACKETS:
                continue
            wealth = node.attributes.get("wealth")
            if not isinstance(wealth, (int, float)):
                continue
            graph.update_node(node.id, wealth=float(wealth) * (1.0 - fraction))

    @staticmethod
    def _swell_reserve_army(graph: GraphProtocol, overhang: float, defines: MarketDefines) -> None:
        """Crisis unemployment where the wage relation exists.

        Bumps ``reserve_ratio`` on active ``territory`` nodes carrying a
        ``median_wage`` (the wage relation's territorial marker — the same
        attribute ``ReserveArmySystem`` discounts); territories without one
        have no employment substrate to shed (honest absence, III.11). The
        @5 system converts the ratio into wage pressure NEXT tick.
        """
        influx = defines.unemployment_gain * overhang
        if influx <= 0.0:
            return
        for node in sorted(graph.query_nodes(node_type="territory"), key=lambda n: n.id):
            attrs = node.attributes
            if not attrs.get("active", True):
                continue
            wage = attrs.get("median_wage")
            if not isinstance(wage, (int, float)) or float(wage) <= 0.0:
                continue
            current = attrs.get("reserve_ratio")
            base = float(current) if isinstance(current, (int, float)) else 0.0
            graph.update_node(node.id, reserve_ratio=min(base + influx, 1.0))


def _mean_profit_rate(graph: GraphProtocol) -> float | None:
    """Mean territory ``tick_profit_rate``, or ``None`` when none carry it.

    The same year-boundary observable the bridge aggregates for
    ``tick_summary.profit_rate``. Sorted-id iteration fixes the float
    summation order (III.7); absence returns ``None`` — the serviceability
    law then falls back to its base (no rate is fabricated, III.11).
    """
    total = 0.0
    count = 0
    for node in sorted(graph.query_nodes(node_type="territory"), key=lambda n: n.id):
        attrs = node.attributes
        if not attrs.get("active", True):
            continue
        rate = attrs.get("tick_profit_rate")
        if isinstance(rate, (int, float)):
            total += float(rate)
            count += 1
    return total / count if count else None
