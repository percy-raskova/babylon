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

from babylon.formulas.market import (
    calculate_ema,
    calculate_growth_drive,
    calculate_scissors_step,
)
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.market import MarketState

if TYPE_CHECKING:
    from babylon.config.defines import MarketDefines
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

#: Graph-metadata key carrying the axis (matches ``WorldState.market``).
MARKET_ATTR = "market"


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
        )
