"""Market-scissors system (Program 23, ADR077/ADR078 — correction feedback LIVE).

Position 17.8: immediately BEFORE ContradictionSystem @18 so the
``price_value`` shadow opposition measures a fresh scissors the same tick.

Evolves the national price⟷value axis: the log price-to-value ratio and log
fictitious-to-real ratio as damped-driven oscillators
(:mod:`babylon.formulas.market`), driven by the realized value flow already
on the graph — ``Σ v_produced`` (demand pull on prices) and
``Σ max(v_produced − w_paid, 0)`` (return-chasing on fictitious capital),
with price momentum feeding speculation (``momentum_coupling``).

PHASE 2 SCOPE (current, ADR078 promotion ceremony): the correction feeds
back into the material base by default (``GameDefines.market.feedback_enabled``).

- State home: ``G.graph["market"]`` metadata (the ``wealth_distribution``
  round-trip pattern; ``WorldState.market`` carries it across facade ticks).
- The correction snap DOES change tick outputs: it evaporates claim-holder
  wealth, swells the reserve army, and publishes ``MARKET_CORRECTION``
  (``feedback_enabled=False`` restores the old Phase-1 observe-only
  behavior for byte-comparison runs).
- Honest absence: a graph with no paid-worker accounting gets NO market —
  the phenomenal form cannot precede its substance (Constitution III.11).
- Deterministic: coefficients from ``GameDefines.market``, nodes iterated in
  sorted-id order, zero RNG (Constitution III.7).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from babylon.engine.systems.wealth_distribution import (
    MARKET_CORRECTION_SHOCK_ATTR,
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
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import EventType, SocialRole
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

#: Graph-metadata key carrying the per-county axes (ADR078):
#: ``{county_fips: MarketState dump}`` — matches ``WorldState.market_county``.
#: Observe-only exposure: county oscillators integrate their county's own
#: flow; the correction (one national credit system) does NOT snap them.
MARKET_COUNTY_ATTR = "market_county"

#: Territory node attr projecting its county's ``price_log`` (the map lens
#: reading). De-positioned territories get an honest ``None``, never a stale
#: value — the sigma-channel pattern (Constitution III.11).
PRICE_DIVERGENCE_ATTR = "price_divergence"


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


def _aggregate_wage_value_by_county(graph: GraphProtocol) -> dict[str, tuple[float, float]]:
    """Per-county ``(Σ w_paid, Σ v_produced)`` over active paid-worker nodes.

    Same selection rule as :func:`_aggregate_wage_value`, additionally
    requiring a ``county_fips`` — placeless nodes feed the national axis
    only. Sorted-id iteration fixes the per-county float summation order
    (III.7). Empty dict when no node carries a county — the qa scenarios'
    synthetic single-county graphs stay axis-free (honest absence).
    """
    flows: dict[str, tuple[float, float]] = {}
    for node in sorted(graph.query_nodes(), key=lambda n: n.id):
        attrs = node.attributes
        if not attrs.get("active", True):
            continue
        if "w_paid" not in attrs or "v_produced" not in attrs:
            continue
        fips = attrs.get("county_fips")
        if fips is None:
            continue
        wages, value = flows.get(str(fips), (0.0, 0.0))
        flows[str(fips)] = (
            wages + float(attrs["w_paid"]),
            value + float(attrs["v_produced"]),
        )
    return flows


class MarketScissorsSystem(SystemBase):
    """The national price⟷value scissors axis (Phase 2: correction feedback live by default)."""

    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 17.8

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
        tick = context.tick
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
        self._step_county_axes(graph, metadata, defines, int(tick))

    def _step_county_axes(
        self,
        graph: GraphProtocol,
        metadata: dict[str, object],
        defines: MarketDefines,
        tick: int,
    ) -> None:
        """Seed/advance the per-county axes and project the map reading.

        Counties whose substrate vanished are DROPPED (no flow, no phenomenal
        form — III.11), and their territories' ``price_divergence`` goes to an
        honest ``None`` via :meth:`_project_price_divergence`. The correction
        never snaps county oscillators — credit is one national system; a
        county's exposure is its own flow history.
        """
        flows = _aggregate_wage_value_by_county(graph)
        prior_raw = metadata.get(MARKET_COUNTY_ATTR)
        priors = prior_raw if isinstance(prior_raw, dict) else {}
        county_states: dict[str, dict[str, object]] = {}
        for fips in sorted(flows):  # bounded by counties present this tick
            wages, value = flows[fips]
            surplus = max(value - wages, 0.0)
            prior = priors.get(fips)
            if isinstance(prior, dict):
                state = self._advance(MarketState(**prior), surplus, value, defines, tick)
            else:
                state = MarketState(
                    price_log=0.0,
                    price_velocity=0.0,
                    fictitious_log=0.0,
                    fictitious_velocity=0.0,
                    surplus_ema=surplus,
                    value_ema=value,
                    tick=tick,
                )
            county_states[fips] = state.model_dump()
        if county_states:
            metadata[MARKET_COUNTY_ATTR] = county_states
        else:
            metadata.pop(MARKET_COUNTY_ATTR, None)
        if county_states or priors:
            self._project_price_divergence(graph, county_states)

    @staticmethod
    def _project_price_divergence(
        graph: GraphProtocol, county_states: dict[str, dict[str, object]]
    ) -> None:
        """Write each territory's county ``price_log`` (the map-lens reading).

        Active territories whose county carries an axis get the value; a
        territory that HELD the attr but lost its axis gets ``None`` (the
        sigma de-positioning rule) — never a stale reading, never a
        fabricated 0.0 for a county with no axis at all.
        """
        for node in sorted(graph.query_nodes(node_type="territory"), key=lambda n: n.id):
            attrs = node.attributes
            if not attrs.get("active", True):
                continue
            fips = attrs.get("county_fips")
            axis = county_states.get(str(fips)) if fips is not None else None
            if axis is not None:
                graph.update_node(node.id, **{PRICE_DIVERGENCE_ATTR: float(axis["price_log"])})  # type: ignore[arg-type]
            elif PRICE_DIVERGENCE_ATTR in attrs:
                graph.update_node(node.id, **{PRICE_DIVERGENCE_ATTR: None})

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
            role = SocialRole.coerce(node.attributes.get("role"))
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


def _capital_weighted_mean(
    graph: GraphProtocol, node_type: str, attr: str, *, weight_attr: str = "tick_capital_stock"
) -> float | None:
    """Capital-weighted mean of an intensive attribute across active nodes.

    The aggregate of a rate/ratio across space is
    ``Sum(value_i * weight_i) / Sum(weight_i)``, never an unweighted mean of
    the per-node ratios — an unweighted mean lets a tiny node swing the
    national reading as hard as a large one (the intensive-aggregation
    class, §3.6/§3.7 of the Vol III money design). A node missing
    ``weight_attr`` (or carrying a non-positive one) contributes weight
    1.0, so fixtures that never stamp capital stock keep their prior
    unweighted reading. Sorted-id iteration fixes the float summation
    order (III.7); ``None`` — never zero — when no active node carries
    ``attr`` (honest absence, III.11).
    """
    weighted_total = 0.0
    weight_total = 0.0
    found = False
    for node in sorted(graph.query_nodes(node_type=node_type), key=lambda n: n.id):
        attrs = node.attributes
        if not attrs.get("active", True):
            continue
        value = attrs.get(attr)
        if not isinstance(value, (int, float)):
            continue
        weight_raw = attrs.get(weight_attr)
        weight = (
            float(weight_raw) if isinstance(weight_raw, (int, float)) and weight_raw > 0.0 else 1.0
        )
        weighted_total += float(value) * weight
        weight_total += weight
        found = True
    return weighted_total / weight_total if found else None


def _mean_profit_rate(graph: GraphProtocol) -> float | None:
    """Capital-weighted mean territory ``tick_profit_rate``, or ``None``.

    The aggregate rate of profit is ``Sum(s) / Sum(c+v)``, not
    ``mean(r_i)`` — an unweighted mean lets a tiny county swing the
    national serviceability line as hard as Wayne. ``tick_capital_stock``
    (``c+v``) is the :func:`_capital_weighted_mean` weight; absence
    returns ``None`` — the serviceability law then falls back to its base
    (no rate is fabricated, III.11).
    """
    return _capital_weighted_mean(graph, "territory", "tick_profit_rate")
