"""The production opposition catalog: Babylon's fourteen bound contradictions.

:func:`build_default_registry` wires an
:class:`~babylon.domain.dialectics.core.opposition.OppositionRegistry` over
:class:`GraphInputs` — a small frozen snapshot the engine's
``ContradictionSystem`` fills once per tick from the live graph. Keeping
the snapshot as pre-extracted views (not the graph itself) keeps this
module free of any ``babylon.engine`` import, so the dialectics package
stays a pure downstream of ``formulas`` + ``models`` and cannot form an
import cycle with the system that consumes it.

The fourteen oppositions, and the honest measure each is bound to. The first
five were verified against a 30-tick single-county bridged probe
(2026-07-02); ``price_value`` was promoted to CANONICAL by ADR078; the
four Volume III money oppositions were bound by the Vol III money-scissors
work (2026-07-18); ``national`` landed SHADOW-first (task #42-C, 2026-07-20);
``value_usevalue``, ``labor_laborpower`` and ``absolute_relative_surplus``
landed SHADOW-first (Vol I value-production program U6, ADR103's reserved
namespace lit, 2026-07-21):

- ``capital_labor`` — mean wealth-asymmetry over EXPLOITATION edges
  (labor = pole A / source, capital = pole B / target). Antagonistic.
- ``wage`` — the true wage⇄value counit defect Φ (Phase D5): mean
  wealth-asymmetry over the per-class ``(w_paid, v_produced)`` pairs,
  ordered ``(value-produced = A, price-of-labor-power = B)`` so a positive
  balance means the wage exceeds the value produced — the imperial bribe
  (Fundamental Theorem ``W_c > V_c``). Empty pairs → ``(0, 0)``; there is NO
  fallback to endpoint wealth (the old proxy is removed — empty means no
  data). Its rate is the crisis signal ``ConsciousnessSystem`` reads.
- ``tenancy`` — tenant wealth (A) vs the territory's ``rent_level`` (B)
  over TENANCY edges, with a degenerate guard: a territory charging no
  rent (``rent_level`` ~ 0) has NO tenancy contradiction, so the pair
  contributes 0.0 rather than the wealth-vs-0 form's spurious 1.0.
- ``atomization`` — gap = :func:`atomization_index` of the SOLIDARITY
  subgraph (1 = fully atomized), balance = ``2*cylinder_balance - 1`` so
  −1 is the atomized pole and +1 the unified pole.
- ``imperial`` — core↔periphery. Rebound in Phase D5 to the SAME wage⇄value
  counit defect as ``wage``, read at the frame level: gap = mean asymmetry
  ``|w−v|/(w+v)`` (the bounded computable proxy for ``|Φ_class|``), balance =
  mean signed ``(w−v)/(w+v)`` (positive = wages exceed value = imperial-rent
  inflow = core pole dominant). It shares ``wage``'s inputs but carries the
  core/periphery poles and the frame level; that shared-input coupling is
  encoded as ``wage feeds imperial`` in the default coupling graph.
- ``price_value`` — the Market Scissors axis (Program 23, ADR077/ADR078)
  read as an adjunction defect: gap and balance come from the pre-derived
  ``GraphInputs.market_balance``, the engine's ``tanh(price_log / scale)``.
  CANONICAL: it competes for principal contradiction.
- ``surplus_distribution`` — enterprise⇄rentier: the rentier share
  ``(i + r + t) / s``, the division of one county's produced surplus among
  the capitals claiming it. Balance crosses zero where the claims exactly
  extinguish enterprise profit.
- ``debt_spiral`` — solvent⇄indebted: accumulated enterprise-profit
  shortfall over annual surplus, scaled by the engine against
  ``capital_vol3.debt_spiral_threshold`` so balance crosses zero AT the
  spiral threshold. Zero debt reads gap 0 (no contradiction), balance −1
  (the solvent pole leads).
- ``credit`` — accommodation⇄fragility: ``default_rate * spread``, scaled by
  the engine against its crisis reference so balance crosses zero AT the
  threshold. National; unplaced on the level lattice.
- ``financial`` — real⇄fictitious: claims on future value over present
  production, read from the scissors' ``fictitious_log`` in ratio space.
  National; unplaced on the level lattice.
- ``national`` — national-chauvinism⇄internationalism: the settler bribe
  that trades international class unity for a national privilege, versus
  the solidarity that refuses it (Lenin, *Imperialism and the Split in
  Socialism*; owner ruling 2026-07-15, doctrine tag NATIONAL_CHAUVINISM /
  negation INTERNATIONALISM). Read from each ``BalkanizationFaction``'s
  ``colonial_stance`` (spec-070 FR-002), weighted by its territorial
  INFLUENCES reach (FR-014/FR-015) — UPHOLD is the chauvinist pole,
  ABOLISH the internationalist pole, IGNORE the RED_OGV middle (FR-032).
  SHADOW (task #42-C): the 5 canonical scenarios construct no
  BalkanizationFaction at all, so this reads absent (0, 0) there BY
  CONSTRUCTION, exactly as ``price_value`` did at its ADR077 landing.
  National; unplaced on the level lattice.
- ``value_usevalue`` — use-value (A) vs value (B) (Capital Vol. I ch. 1): does
  the value a class has accumulated (``wealth``, the abstract, generalized
  form) actually supply the use-values it must consume to reproduce itself
  (``subsistence_threshold``, the concrete floor Survival Calculus already
  prices)? Reads ``GraphInputs.wealth_subsistence_ratio`` — Σwealth /
  Σsubsistence_threshold over every active ``social_class`` node, a RATIO
  OF SUMS — through the shared ``_ratio_reading`` family; the natural zero
  point is exact parity. SHADOW (U6). National aggregate; unplaced.
- ``labor_laborpower`` — labor (A) vs labor-power (B) (Capital Vol. I ch. 6):
  the wage form presents itself as payment for a day's LABOR; what is
  actually bought is LABOR-POWER, priced at its own reproduction cost and
  independent of what using it yields — "the secret of profit-making".
  Reads the IDENTICAL ``(w_paid, v_produced)`` defect ``wage``/``imperial``
  already read (Phase D4), under its third framing — see the "shared
  defect, different poles" design note below. SHADOW (U6). County level.
- ``absolute_relative_surplus`` — absolute-surplus-value (A) vs
  relative-surplus-value (B) (Capital Vol. I chs. 10, 12, 15): capital has
  exactly two levers for extracting more surplus value from the same
  labor-power — lengthening the working day, or cheapening labor-power's
  reproduction via rising productivity/intensity. Reads
  ``GraphInputs.surplus_strategy_ratio`` (the engine's
  ``labor_intensity_index * relative_hours_threshold / avg_weekly_hours``,
  from the SAME FRED-backed ``WorkingDayState`` U4 wired — §2e's classifier,
  no new ingestion) through ``_ratio_reading``. SHADOW (U6). National
  aggregate (the wired adapter is itself national-uniform); unplaced.

All four Volume III bindings, plus ``value_usevalue`` and
``absolute_relative_surplus`` (U6), share ``_ratio_reading``'s zero-parameter
saturating map; every one of the six is ``antagonistic=False`` — INTRA-class
or structural rather than the rupture-producing class antagonisms, which stay
reserved for ``capital_labor``, ``imperial`` and ``national``.

Design note (shared defect, different poles): ``wage``, ``imperial`` and
(U6) ``labor_laborpower`` all read the identical ``(w_paid, v_produced)``
defect but bind different poles — ``wage`` names the per-class relation
(value-produced ⇄ price-of-labor-power, the Fundamental Theorem's Φ),
``imperial`` names the frame (core ⇄ periphery), ``labor_laborpower`` names
Ch. 6's wage-form mystification (labor ⇄ labor-power). The measure is
:func:`babylon.domain.dialectics.instances.value_form.phi_class` in spirit; the
catalog uses the bounded asymmetry form from ``formulas.contradiction`` so the
gap stays in ``[0, 1]`` (the raw ``(w−v)/v`` is unbounded). See
:mod:`babylon.domain.dialectics.instances.value_form` for the full adjunction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from babylon.topology.graph import BabylonUGraph

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from babylon.domain.dialectics.core.coupling import Coupling, CouplingGraph
from babylon.domain.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
    PoleSample,
)
from babylon.domain.dialectics.instances.connectivity import (
    atomization_index,
    connectivity_cylinder,
)
from babylon.formulas.contradiction import calculate_wealth_asymmetry_balance

__all__ = [
    "VOL_I_RESERVED_OPPOSITIONS",
    "VOL_II_RESERVED_OPPOSITIONS",
    "GraphInputs",
    "build_default_coupling_graph",
    "build_default_registry",
]

logger = logging.getLogger(__name__)

# Pair convention across capital_labor + wage: (labor_wealth, capital_wealth),
# i.e. (pole_a, pole_b), so balance > 0 == capital dominant for BOTH.
WealthPair = tuple[float, float]

_RENT_EPSILON = 1e-9
"""Below this rent_level a TENANCY edge is treated as rent-free (no contradiction)."""


@dataclass(frozen=True)
class GraphInputs:
    """One tick's pre-extracted views for the bound opposition measures.

    Cheap to construct (plain tuples + one undirected subgraph) and free of
    any engine type, so the catalog imports nothing from ``babylon.engine``.

    Attributes:
        exploitation_pairs: ``(labor_wealth, capital_wealth)`` per
            EXPLOITATION edge (source=labor, target=capital).
        wage_value_pairs: ``(w_paid, v_produced)`` per paid worker class node
            (Phase D4) — the wage⇄value counit-defect pair the value-form
            ``wage`` and ``imperial`` measures read. ``w_paid`` is total wages
            transferred; ``v_produced`` is productivity captured.
        tenancy_pairs: ``(tenant_wealth, rent_level)`` per TENANCY edge.
        solidarity_subgraph: the undirected SOLIDARITY subgraph
            (from ``extract_solidarity_subgraph``) for the atomization
            cylinder; ``None`` is treated as empty.
        exploitation_id_pairs: ``(source_id, target_id, labor_wealth,
            capital_wealth)`` per EXPLOITATION edge — the id-carrying twin
            of ``exploitation_pairs`` feeding the per-node pole measures
            (ADR070); built in the same loop, same skip rules.
        wage_value_id_pairs: ``(node_id, w_paid, v_produced)`` per paid
            worker class node — the id-carrying twin of ``wage_value_pairs``.
        tenancy_id_pairs: ``(source_id, target_id, tenant_wealth,
            rent_level)`` per TENANCY edge — id-carrying twin of
            ``tenancy_pairs``; no pole measure reads it yet (a
            landlord/tenant axis is a natural later binding).
        market_balance: pre-derived scissors ``Balance`` in [-1, 1] from the
            Market Scissors axis (Program 23, ADR077) — the engine computes
            ``tanh(price_log / scale)`` with the defines-owned scale so the
            catalog stays defines-free; ``None`` = no market axis this tick.
        rentier_share: NATIONAL aggregate ``(i + r + t) / s`` — the share of
            produced surplus value claimed by interest, ground rent and taxes
            rather than retained by the functioning capitalist (Capital Vol.
            III part 5). Computed by the engine as ``Σclaims / Σsurplus``
            across counties — an EXTENSIVE ratio-of-sums, never a mean of
            per-county ratios. ``None`` = no county carries a surplus
            distribution this tick.
        debt_ratio: NATIONAL ``Σ accumulated_debt / Σ annual surplus`` — the
            cumulative enterprise-profit shortfall measured against the
            surplus that would have to service it. ``None`` = no county
            carries a debt accumulation this tick.
        credit_fragility: ``default_rate * spread``, pre-divided by the
            defines-owned crisis reference so 1.0 IS the crisis threshold
            (the engine owns the scale, exactly as it owns the ``tanh``
            scale for ``market_balance``, keeping this module defines-free).
            ``None`` = no national credit state published this tick.
        financialization_index: fictitious claims over real production. Read
            from the scissors' ``fictitious_log`` in ratio space
            (``exp``), which the monetary anchor calibrates to
            ``FictitiousCapitalStock.ratio_to_real`` while real data exists —
            one axis, materially grounded at its origin, endogenous
            thereafter. ``None`` = no market axis this tick.
        national_balance: pre-derived national-axis ``Balance`` in [-1, 1]
            (task #42-C) — the engine's INFLUENCES-weighted mean of every
            BalkanizationFaction's ``colonial_stance``, scaled the same
            division-of-labour way ``market_balance`` is (no coefficient, so
            the catalog stays defines-free). ``None`` = no faction carries
            both a recognized stance and positive territorial influence this
            tick (the 5 canonical scenarios, permanently, by construction).
        wealth_subsistence_ratio: NATIONAL ``Σwealth / Σsubsistence_threshold``
            over every active ``social_class`` node (Vol I U6, Capital Vol. I
            ch. 1) — an EXTENSIVE ratio-of-sums (never a mean of per-class
            ratios), the ``value_usevalue`` opposition's feed: does the value
            a class holds (wealth) supply the use-values it must consume to
            reproduce itself (``subsistence_threshold``)? ``None`` = no
            active class carries a positive subsistence sum this tick (an
            empty world).
        surplus_strategy_ratio: pre-derived ``labor_intensity_index *
            relative_hours_threshold / avg_weekly_hours`` (Vol I U6, Capital
            Vol. I chs. 10, 12, 15) — the ``absolute_relative_surplus``
            opposition's feed, from the SAME FRED-backed ``WorkingDayState``
            U4's ``productivity_data_source`` wires (§2e's classifier); the
            engine owns the ``relative_hours_threshold`` scale, keeping the
            catalog defines-free, the same division of labour
            ``market_balance``'s ``tanh`` scale uses. ``None`` = no
            ``productivity_data_source`` wired, or no data for this tick's
            year.
    """

    exploitation_pairs: tuple[WealthPair, ...] = ()
    wage_value_pairs: tuple[tuple[float, float], ...] = ()
    tenancy_pairs: tuple[WealthPair, ...] = ()
    solidarity_subgraph: BabylonUGraph | None = field(default=None)
    exploitation_id_pairs: tuple[tuple[str, str, float, float], ...] = ()
    wage_value_id_pairs: tuple[tuple[str, float, float], ...] = ()
    tenancy_id_pairs: tuple[tuple[str, str, float, float], ...] = ()
    market_balance: float | None = field(default=None)
    rentier_share: float | None = field(default=None)
    debt_ratio: float | None = field(default=None)
    credit_fragility: float | None = field(default=None)
    financialization_index: float | None = field(default=None)
    national_balance: float | None = field(default=None)
    wealth_subsistence_ratio: float | None = field(default=None)
    surplus_strategy_ratio: float | None = field(default=None)


_ASYMMETRY_EPSILON: Final[float] = 1e-9
"""Degenerate-pair guard, mirroring ``calculate_wealth_asymmetry_*``'s epsilon default."""


def _mean_asymmetry(pairs: Sequence[WealthPair]) -> GapReading:
    """Wealth-weighted asymmetry gap and balance over ``(pole_a, pole_b)`` pairs.

    Each pair's bounded reading (``|b−a|/(a+b)``, ``(b−a)/(a+b)``) is weighted
    by the wealth engaged in the relationship (``a+b`` — an extensive
    magnitude), which telescopes algebraically to the exact ratio of sums:
    ``gap = Σ|b−a| / Σ(a+b)``, ``balance = Σ(b−a) / Σ(a+b)``. An unweighted
    mean lets a tiny pair swing the field reading as hard as an enormous one —
    the intensive-aggregation error class (U7.6 sensor; owner ruling
    2026-07-19). Lawverian reading: the opposition's counit defect integrated
    over the relationship field, with material wealth as the measure.

    Pairs whose pole sum falls below ``_ASYMMETRY_EPSILON`` carry no wealth
    mass and are skipped — under the per-pair formulas they read 0.0 and here
    they contribute zero weight, so the two forms agree on the degenerate
    case. Empty input (or all pairs degenerate) → ``gap 0.0, balance 0.0``
    (an absent edge set carries no contradiction), per the design contract.
    Summation runs in input order, which the engine constructs
    deterministically (III.7).
    """
    gap_mass = 0.0
    balance_mass = 0.0
    weight_total = 0.0
    for a, b in pairs:
        pole_sum = a + b
        if pole_sum < _ASYMMETRY_EPSILON:
            continue
        gap_mass += abs(b - a)
        balance_mass += b - a
        weight_total += pole_sum
    if weight_total <= 0.0:
        return GapReading(gap=0.0, balance=0.0)
    gap = min(1.0, max(0.0, gap_mass / weight_total))
    balance = min(1.0, max(-1.0, balance_mass / weight_total))
    return GapReading(gap=gap, balance=balance)


def _capital_labor_measure(inputs: GraphInputs) -> GapReading:
    """capital⇄labor over EXPLOITATION edges (labor=A, capital=B)."""
    return _mean_asymmetry(inputs.exploitation_pairs)


def _wage_value_reading(inputs: GraphInputs) -> GapReading:
    """Mean wage⇄value counit defect over the ``(w_paid, v_produced)`` pairs.

    Reorders each stored ``(w_paid, v_produced)`` to ``(value-produced = A,
    price-of-labor-power = B)`` and takes the bounded asymmetry: gap
    ``|w−v|/(w+v)``, balance ``(w−v)/(w+v)``, so a positive balance means the
    wage exceeds the value produced — the imperial bribe. Empty pairs →
    ``(0, 0)`` (no data, no dual path). Both ``wage`` (per-class relation) and
    ``imperial`` (core↔periphery frame) read this same defect.
    """
    return _mean_asymmetry([(value, wage) for wage, value in inputs.wage_value_pairs])


def _wage_measure(inputs: GraphInputs) -> GapReading:
    """wage: value-produced (A) ⇄ price-of-labor-power (B) — the Φ counit defect."""
    return _wage_value_reading(inputs)


def _tenancy_measure(inputs: GraphInputs) -> GapReading:
    """tenant⇄rent over TENANCY edges, with the rent-free degenerate guard."""
    guarded: list[WealthPair] = [
        (tenant, rent) for tenant, rent in inputs.tenancy_pairs if rent > _RENT_EPSILON
    ]
    return _mean_asymmetry(guarded)


def _atomization_measure(inputs: GraphInputs) -> GapReading:
    """atomized⇄unified over the SOLIDARITY subgraph.

    gap = atomization_index (1 = every class its own component); balance =
    ``2*cylinder_balance - 1`` so −1 is the atomized (skeleton) pole and +1
    the unified (sheaf) pole. Empty/absent subgraph → gap 0, balance 0.
    """
    graph = inputs.solidarity_subgraph
    if graph is None or graph.number_of_nodes() == 0:
        return GapReading(gap=0.0, balance=0.0)
    gap = atomization_index(graph)
    cylinder_balance = connectivity_cylinder().balance(graph)
    balance = 2.0 * cylinder_balance - 1.0
    return GapReading(gap=gap, balance=max(-1.0, min(1.0, balance)))


def _capital_labor_poles(inputs: GraphInputs) -> tuple[PoleSample, ...]:
    """Per-node labor⇄capital position over ALL EXPLOITATION participations.

    Each edge's signed asymmetry balance is credited to BOTH endpoints:
    the source (labor position) negated — capital dominance pushes it
    toward pole A — and the target (capital position) as-is. A node
    appearing on both sides across different edges (an intermediate
    stratum) gets the mean of its participations, honestly. Nodes with no
    EXPLOITATION participation are absent (UNPOSITIONED), never 0.0.
    """
    accumulator: dict[str, list[float]] = {}
    for source_id, target_id, labor_wealth, capital_wealth in inputs.exploitation_id_pairs:
        balance = calculate_wealth_asymmetry_balance(labor_wealth, capital_wealth)
        accumulator.setdefault(source_id, []).append(-balance)
        accumulator.setdefault(target_id, []).append(balance)
    return tuple(
        PoleSample(entity_id=node_id, sigma=sum(values) / len(values))
        for node_id, values in sorted(accumulator.items())
    )


def _wage_poles(inputs: GraphInputs) -> tuple[PoleSample, ...]:
    """Per-node wage⇄value defect sign from the node's own ``(w_paid, v_produced)``.

    Reorders to ``(value-produced = A, price-of-labor-power = B)`` exactly
    as :func:`_wage_value_reading` does for the aggregate, so a positive
    sigma means the wage exceeds the value produced — the imperial bribe,
    pole B. Nodes without the accounting pair are absent (UNPOSITIONED).
    """
    return tuple(
        PoleSample(entity_id=node_id, sigma=calculate_wealth_asymmetry_balance(value, wage))
        for node_id, wage, value in sorted(inputs.wage_value_id_pairs)
    )


#: ``imperial`` reads the IDENTICAL defect under core/periphery pole names
#: (the D5 shared-defect design) — reused verbatim, not reimplemented. This
#: alias is the Program 10 landing seam: its data-grounded per-node sigma
#: (OCC / capital intensity / integrated labor content) replaces this proxy
#: as a new pole_measure on the ``imperial`` binding, with every consumer
#: of :class:`PoleReading` unchanged.
_imperial_poles = _wage_poles


def _imperial_measure(inputs: GraphInputs) -> GapReading:
    """core⇄periphery — the SAME wage⇄value Φ defect, read at the frame level.

    Rebound in Phase D5 (was NULL). Reads the same ``(w_paid, v_produced)``
    pairs as ``wage`` via :func:`_wage_value_reading`: a positive balance means
    wages exceed value produced — imperial-rent inflow, core pole dominant.
    Differs from ``wage`` only in poles (core/periphery) and level (the frame),
    not in arithmetic — see the module docstring and
    :mod:`babylon.domain.dialectics.instances.value_form`.
    """
    return _wage_value_reading(inputs)


def _labor_laborpower_measure(inputs: GraphInputs) -> GapReading:
    """labor (A) ⇄ labor-power (B) — Ch. 6's wage-form mystification.

    Vol I U6 (vol1-value-production program). Reads the SAME ``(w_paid,
    v_produced)`` defect as ``wage``/``imperial`` (Phase D4's shared feed)
    under its THIRD framing: the wage form presents itself as payment for a
    day's LABOR (as though the whole product were bought), while what is
    actually sold is LABOR-POWER — priced at its own reproduction cost,
    independent of what using it happens to yield. A positive balance reads
    "labor's product (v_produced) exceeds what was paid for the labor-power
    that performed it (w_paid)" — Marx's "secret of profit-making". Differs
    from ``wage``'s own framing (the ACTUAL wage bargained, read as the
    Fundamental Theorem's imperial bribe) only in which historical question
    the identical arithmetic answers — see the module docstring's "shared
    defect, different poles" design note.
    """
    return _wage_value_reading(inputs)


#: ``price_value`` per-node positions read the IDENTICAL ``(w_paid,
#: v_produced)`` defect as ``wage`` — labor-power is the ONE commodity
#: carrying a per-node price AND value accounting, so the node's position in
#: the price⟷value adjunction is observed there (the D5 shared-defect
#: precedent, exactly as ``_imperial_poles``). A per-node claims/portfolio
#: sigma (who HOLDS the fictitious paper) replaces this proxy when per-node
#: financial data lands — every :class:`PoleReading` consumer unchanged.
_price_value_poles = _wage_poles


def _price_value_measure(inputs: GraphInputs) -> GapReading:
    """value (A) ⇄ price (B) — the scissors as a measured adjunction defect.

    Reads the pre-derived Balance (the engine owns the tanh scale — see
    ``GraphInputs.market_balance``). ``None`` → ``(0, 0)``: no market axis,
    no contradiction (a phenomenal form cannot diverge from an absent
    substance, Constitution III.11). Positive balance = price above value —
    the form pole dominant, fictitious validation outrunning production.
    """
    if inputs.market_balance is None:
        return GapReading(gap=0.0, balance=0.0)
    balance = max(-1.0, min(1.0, inputs.market_balance))
    return GapReading(gap=abs(balance), balance=balance)


def _ratio_reading(ratio: float | None) -> GapReading:
    """Map a non-negative claim/substance ratio onto ``(gap, balance)``.

    The shared measure family for every Volume III money opposition, plus
    (Vol I U6) ``value_usevalue`` and ``absolute_relative_surplus``. Each
    reads a ratio of a CLAIM on (or strategy toward) a substance to the
    substance that must validate it — rentier claims to surplus produced,
    accumulated debt to annual surplus, credit fragility to its crisis
    reference, fictitious capital to real production, wealth to the
    subsistence it must buy, relative-surplus intensity to absolute-surplus
    hours — so all six share one zero-parameter map::

        gap     = x / (1 + x)
        balance = (x - 1) / (x + 1) = 2 * gap - 1

    Reading the two outputs materially: the balance crosses zero exactly
    at ``x = 1``, the point where the claim equals the substance claimed
    (enterprise profit exactly extinguished, fragility exactly at
    threshold, paper exactly at parity with production). Below it the
    substance leads (pole A); above it the claim leads (pole B). The gap
    is 0 only where the claim is absent altogether — a surplus no rentier
    touches carries no rentier contradiction — and saturates toward 1 as
    the claim runs away from what produces it.

    The family is deliberately scale-free (no coefficient, so this module
    stays defines-free per its import contract); any scaling a ratio needs
    is applied by the engine before it reaches :class:`GraphInputs`, the
    same division of labour ``market_balance`` already uses.

    Args:
        ratio: The claim/substance ratio, or ``None`` when the underlying
            data is absent.

    Returns:
        ``GapReading(0.0, 0.0)`` — the catalog's canonical ABSENT reading —
        when ``ratio`` is ``None`` or negative (a ratio of two non-negative
        magnitudes cannot be negative, so a negative value is corrupt input
        and absence is the honest answer, Constitution III.11). Otherwise
        the saturating reading above.
    """
    if ratio is None or ratio < 0.0:
        return GapReading(gap=0.0, balance=0.0)
    gap = ratio / (1.0 + ratio)
    return GapReading(gap=gap, balance=2.0 * gap - 1.0)


def _surplus_distribution_measure(inputs: GraphInputs) -> GapReading:
    """enterprise (A) ⇄ rentier (B) — the division of surplus among capitals."""
    return _ratio_reading(inputs.rentier_share)


def _debt_spiral_measure(inputs: GraphInputs) -> GapReading:
    """solvent (A) ⇄ indebted (B) — accumulated shortfall against annual surplus."""
    return _ratio_reading(inputs.debt_ratio)


def _credit_measure(inputs: GraphInputs) -> GapReading:
    """accommodation (A) ⇄ fragility (B) — ``default_rate * spread`` in threshold units."""
    return _ratio_reading(inputs.credit_fragility)


def _financial_measure(inputs: GraphInputs) -> GapReading:
    """real (A) ⇄ fictitious (B) — claims on future value over present production."""
    return _ratio_reading(inputs.financialization_index)


def _value_usevalue_measure(inputs: GraphInputs) -> GapReading:
    """use-value (A) ⇄ value (B) — Capital Vol. I ch. 1's commodity dialectic.

    Vol I U6. Reads the pre-derived ``GraphInputs.wealth_subsistence_ratio``
    (the engine's Σwealth / Σsubsistence_threshold over every active
    ``social_class`` node) through the shared ratio family: the natural zero
    point is exact parity — wealth exactly covering the use-values a class
    must consume to reproduce itself. Below parity the concrete reproduction
    requirement (use-value) leads; above it the value-form's own surplus
    over that requirement leads. ``None`` → ``(0, 0)``: no active class this
    tick, no contradiction to measure (Constitution III.11).
    """
    return _ratio_reading(inputs.wealth_subsistence_ratio)


def _absolute_relative_surplus_measure(inputs: GraphInputs) -> GapReading:
    """absolute-surplus-value (A) ⇄ relative-surplus-value (B) — Chs. 10, 12, 15.

    Vol I U6. Reads the pre-derived ``GraphInputs.surplus_strategy_ratio``
    (the engine's ``labor_intensity_index * relative_hours_threshold /
    avg_weekly_hours``, from the SAME FRED-backed ``WorkingDayState`` U4
    wired) through the shared ratio family: below parity the working day's
    own length dominates (absolute extraction — lengthening the hours);
    above it, productivity/intensity gains dominate (relative extraction —
    mechanization). Marx's two strategies for extracting more surplus value
    from the same labor-power. ``None`` → ``(0, 0)``: ``productivity_data_source``
    unwired, or no data for this tick's year.
    """
    return _ratio_reading(inputs.surplus_strategy_ratio)


def _national_measure(inputs: GraphInputs) -> GapReading:
    """national-chauvinism (A) ⇄ internationalism (B) — task #42-C.

    Reads the pre-derived Balance (the engine owns the INFLUENCES-weighting —
    see ``GraphInputs.national_balance``). ``None`` → ``(0, 0)``: no faction
    carries a recognized stance with positive territorial reach, so there is
    no national contradiction to measure (Constitution III.11) — the honest,
    by-construction reading in every one of the 5 canonical scenarios, which
    build no BalkanizationFaction at all. Positive balance = internationalism
    (pole B) dominant.
    """
    if inputs.national_balance is None:
        return GapReading(gap=0.0, balance=0.0)
    balance = max(-1.0, min(1.0, inputs.national_balance))
    return GapReading(gap=abs(balance), balance=balance)


def build_default_registry(rate_weight: float = 10.0) -> OppositionRegistry[GraphInputs]:
    """Build the production opposition registry (fourteen bindings).

    Args:
        rate_weight: Weight of ``|rate|`` in principal-contradiction scoring;
            wired from ``defines.tension.principal_rate_weight`` by the engine.

    Returns:
        An :class:`OppositionRegistry` over :class:`GraphInputs` binding all
        fourteen oppositions named in the module docstring above (keys
        lexicographically ordered inside the registry).
    """
    bindings: list[BoundOpposition[GraphInputs]] = [
        BoundOpposition(
            spec=OppositionSpec(
                key="capital_labor",
                pole_a="wage-labor",
                pole_b="capital",
                unity="wage labor presupposes capital; capital presupposes wage labor",
                level_name="county",
                antagonistic=True,
            ),
            measure=_capital_labor_measure,
            pole_measure=_capital_labor_poles,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="wage",
                pole_a="value-produced",
                pole_b="price-of-labor-power",
                unity="the wage⇄value adjunction: the price of labor-power (the wage) "
                "commands the value produced; their gap is Φ (Fundamental Theorem W_c > V_c) "
                "— see dialectics.instances.value_form",
                level_name="county",
            ),
            measure=_wage_measure,
            pole_measure=_wage_poles,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="tenancy",
                pole_a="tenant",
                pole_b="rent",
                unity="occupancy presupposes the ground rent it is charged",
                level_name="county",
            ),
            measure=_tenancy_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="atomization",
                pole_a="atomized",
                pole_b="unified",
                unity="a class exists only as the (dis)connection of its members",
                level_name="class",
            ),
            measure=_atomization_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="imperial",
                pole_a="core",
                pole_b="periphery",
                unity="core accumulation presupposes peripheral value transfer; the wage⇄value "
                "counit defect Φ made observable at the frame level "
                "— see dialectics.instances.value_form",
                level_name="bloc",
                antagonistic=True,
            ),
            measure=_imperial_measure,
            pole_measure=_imperial_poles,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="price_value",
                pole_a="value",
                pole_b="price",
                unity="the price-form presupposes the value it expresses; MELT is the "
                "unit of their adjunction and the scissors its measured defect "
                "(Capital Vol. I ch. 1 §3 / Vol. III ch. 10) — Program 23, ADR077",
                # level_name stays "" (unplaced): the national scissors sits
                # on no county/bloc lattice rung yet.
                antagonistic=False,
            ),
            measure=_price_value_measure,
            pole_measure=_price_value_poles,
            # CANONICAL since ADR078 (the promotion ceremony): the scissors
            # competes for principal contradiction — crisis-as-principal
            # falls out of the frames/rupture/regime machinery. It was born
            # shadow (ADR077) to prove byte-inertness first; the generic
            # shadow mechanism remains for Amendment T's future bindings.
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="surplus_distribution",
                pole_a="enterprise",
                pole_b="rentier",
                unity="the functioning capitalist can only set production going with "
                "capital the money-capitalist, the landowner and the state advance or "
                "levy against it; interest, ground rent and taxes are therefore not "
                "deductions from an alien fund but the shares in which the one surplus "
                "value the workers produced is divided among the capitals that claim "
                "it (Capital Vol. III parts 4-6)",
                level_name="county",
                antagonistic=False,
            ),
            measure=_surplus_distribution_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="debt_spiral",
                pole_a="solvent",
                pole_b="indebted",
                unity="when the rentier claims outrun the surplus produced, the "
                "shortfall is not settled but carried: the enterprise borrows to pay "
                "the interest it already owes, and the debt is a claim on surplus "
                "value not yet extracted from any worker — solvency and indebtedness "
                "are the same accumulation read at two moments (Capital Vol. III ch. 30-32)",
                level_name="county",
                antagonistic=False,
            ),
            measure=_debt_spiral_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="credit",
                pole_a="accommodation",
                pole_b="fragility",
                unity="credit is the lever that carries accumulation past the limits "
                "of the individual capital, and by exactly the same act it makes each "
                "capital's reproduction depend on every other's payment: the system "
                "that accommodates the boom IS the system that transmits the default "
                "(Capital Vol. III ch. 27, 30)",
                # level_name stays "" (unplaced): the credit system is national;
                # it sits on no county/bloc lattice rung.
                antagonistic=False,
            ),
            measure=_credit_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="financial",
                pole_a="real",
                pole_b="fictitious",
                unity="a bond, a share and a mortgage are titles to future surplus "
                "value, not the value itself; they are bought and sold as capital "
                "while the labour that must validate them has not been performed — "
                "the paper presupposes the production it has already outrun (Capital "
                "Vol. III ch. 25, 29)",
                # level_name stays "" (unplaced): the fictitious-capital stock and
                # the scissors axis reading it are both national.
                antagonistic=False,
            ),
            measure=_financial_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="national",
                pole_a="national-chauvinism",
                pole_b="internationalism",
                unity="the settler bribe that trades international class unity for a "
                "national privilege, and the solidarity that refuses it, are the same "
                "relation to the imperial nation-state read at its two poles (Lenin, "
                "Imperialism and the Split in Socialism) — owner ruling 2026-07-15 named "
                "the reactionary pole NATIONAL_CHAUVINISM, its negation INTERNATIONALISM "
                "already live as the SolidaritySystem",
                # level_name stays "" (unplaced): the axis aggregates faction stance
                # NATIONALLY (all INFLUENCES reach, no county/class rung), same as
                # credit/financial.
                antagonistic=True,
            ),
            measure=_national_measure,
            # SHADOW (task #42-C): measured every tick, excluded from principal
            # scoring/frames/rupture; states ride shadow_opposition_states,
            # exactly the ADR077 discipline price_value was born under.
            shadow=True,
        ),
        # === CAPITAL VOL I — production-layer bindings (U6, ADR103's
        # reserved namespace lit) ===
        BoundOpposition(
            spec=OppositionSpec(
                key="value_usevalue",
                pole_a="use-value",
                pole_b="value",
                unity="a commodity is a use-value the instant it exists, but only a "
                "value insofar as the abstract social labor congealed in it is "
                "socially validated; value has no life of its own — it must always "
                "crystallize as a really-consumed use-value or it is nothing at all "
                "(Capital Vol. I ch. 1)",
                # level_name stays "" (unplaced): the ratio aggregates NATIONALLY
                # over every active social_class node, no county/class rung.
                antagonistic=False,
            ),
            measure=_value_usevalue_measure,
            # SHADOW (U6): measured every tick, excluded from principal
            # scoring/frames/rupture, the same ADR077 discipline
            # price_value/national were born under.
            shadow=True,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="labor_laborpower",
                pole_a="labor",
                pole_b="labor-power",
                unity="the wage form presents itself as payment for a day's LABOR; "
                "what is actually bought and sold is LABOR-POWER, priced at its own "
                "reproduction cost and entirely independent of the value using it "
                "happens to yield — 'the secret of profit-making' (Capital Vol. I "
                "ch. 6)",
                level_name="county",
                antagonistic=False,
            ),
            measure=_labor_laborpower_measure,
            shadow=True,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="absolute_relative_surplus",
                pole_a="absolute-surplus-value",
                pole_b="relative-surplus-value",
                unity="capital has exactly two levers for extracting more surplus "
                "value from the same labor-power: lengthening the working day "
                "(absolute) or cheapening labor-power's reproduction through "
                "rising productivity and intensity (relative) — two strategies for "
                "one end (Capital Vol. I chs. 10, 12, 15)",
                # level_name stays "" (unplaced): the wired FRED adapter is itself
                # national-level and uniform (program prompt §2c).
                antagonistic=False,
            ),
            measure=_absolute_relative_surplus_measure,
            shadow=True,
        ),
    ]
    return OppositionRegistry(bindings=bindings, rate_weight=rate_weight)


# ============================================================================
# CAPITAL VOL I ∥ VOL II CONTRACT  (ADR103 · §10 parallel-build protocol)
# ============================================================================
# The fork gate for the two-volume parallel build. These tuples originally
# RESERVED the opposition keys each lane would register, WITHOUT registering
# any live binding — proved byte-identical by
# ``test_reserved_oppositions_are_dormant`` at the contract commit. Vol I's
# three keys are now LIT (U6, vol1-value-production program): bound above in
# ``build_default_registry``, with real ``GraphInputs`` fields and measures.
# The tuple below stays as the documented record of Vol I's namespace; Vol
# II's four keys remain genuinely reserved-but-dormant until its own lane
# binds them (test_contract.py checks Vol II's disjointness only, now that
# Vol I's is deliberately, loudly, no longer disjoint).
#
# GraphInputs field partition (collision convention): Vol I adds production-layer
# fields (value/use-value, labor/labor-power, surplus-method pairs); Vol II adds
# circulation-layer fields (realization, reproduction, disproportionality). Add
# fields only within your volume's group; never rename or reorder existing ones.
VOL_I_RESERVED_OPPOSITIONS: tuple[str, ...] = (
    "value_usevalue",
    "labor_laborpower",
    "absolute_relative_surplus",
)
VOL_II_RESERVED_OPPOSITIONS: tuple[str, ...] = (
    "circulation",
    "realization",
    "reproduction",
    "disproportionality",
)


# The ratified crisis-producer map. Every edge is DERIVED — read off the code
# against ``coupling.py``'s operational definitions of the five kinds, not
# authored from theory — and carries its citation, because the graph is a
# CLAIM ABOUT THE CODE and drifts from it the moment either side changes.
# (That drift is exactly how the two Vol III ``transforms`` edges below sat
# dormant and undetected for months.) The builder keeps only edges whose BOTH
# endpoints are registered; it never invents a null binding for an absent one.
_DEFAULT_COUPLINGS: tuple[Coupling, ...] = (
    # crisis producers: source's output becomes target's input prices.
    # Still unbound — the two Volume II circulation oppositions are out of
    # scope for the Vol III money work and are NOT faked.
    Coupling(source="circulation", target="realization", kind="transforms"),
    Coupling(source="reproduction", target="disproportionality", kind="transforms"),
    # CAPITAL VOL I production-layer feeds (ADR103 contract commit's reserved
    # skeleton; LIT by U6, vol1-value-production program). The first two
    # connect Ch.1's commodity dialectic through Ch.6's wage-form
    # mystification into Chs.10/12/15's two surplus-value strategies; the
    # third bridges that surplus-method axis into the LIVE ``wage`` axis (the
    # Fundamental Theorem Wᶜ > Vᶜ) — production's own expository order,
    # commodity to wage-labor to accumulation. All three now survive
    # ``build_default_coupling_graph`` (both endpoints registered).
    Coupling(source="value_usevalue", target="labor_laborpower", kind="feeds"),
    Coupling(source="labor_laborpower", target="absolute_relative_surplus", kind="feeds"),
    Coupling(source="absolute_relative_surplus", target="wage", kind="feeds"),
    # DebtAccumulation.update consumes profit_of_enterprise — the residual of
    # the surplus distribution (economics/tick/system/__init__.py, the annual
    # county financial block): the distribution's output IS the debt tracker's
    # input. Reserved since Phase D; live since the Vol III binding.
    Coupling(source="surplus_distribution", target="debt_spiral", kind="transforms"),
    # Credit conditions become fictitious accumulation's input: the default
    # rate and spread that price credit are what the claims on future value
    # are capitalized against. Reserved since Phase D; live since the Vol III
    # binding.
    Coupling(source="credit", target="financial", kind="transforms"),
    # the two antagonistic class contradictions are mutually antagonistic
    Coupling(source="capital_labor", target="imperial", kind="antagonizes"),
    # capital_labor's development presupposes the wage relation it reads
    Coupling(source="wage", target="capital_labor", kind="feeds"),
    # wage and imperial read the SAME (w_paid, v_produced) defect (D5): the
    # per-class wage relation feeds the frame-level imperial-rent reading.
    Coupling(source="wage", target="imperial", kind="feeds"),
    # the realized wage⇄value flow IS the scissors' drive term (ADR078): the
    # market axis integrates what the wage relation produces each tick.
    Coupling(source="wage", target="price_value", kind="feeds"),
    #
    # The reciprocal pair below is not a modelling flourish: the two edges
    # fire at DIFFERENT moments of one cycle, and both are readable in
    # engine/systems/market_scissors.py.
    #
    # Expansion — fictitious_drive includes ``momentum_coupling *
    # price_velocity`` (market_scissors.py fictitious-drive block): the
    # fictitious step READS the price observation, so ``feeds``.
    Coupling(source="price_value", target="financial", kind="feeds"),
    # Correction — calculate_correction_snap pulls price_log down from the
    # fictitious overhang (market_scissors.py correction block): the price
    # step READS the fictitious observation, so ``feeds`` back. CouplingGraph
    # requires no acyclicity, and the cycle is the honest record.
    Coupling(source="financial", target="price_value", kind="feeds"),
    # The interest burden i/s sets serviceable_divergence — the ceiling on
    # fictitious_log before the snap — so the distribution LIMITS the
    # financial axis's reachable state space: ``constrains``, not ``feeds``.
    Coupling(source="surplus_distribution", target="financial", kind="constrains"),
)


def build_default_coupling_graph(
    registry: OppositionRegistry[GraphInputs],
) -> CouplingGraph:
    """Build the production coupling graph, skipping edges with unbound endpoints.

    Encodes the ratified crisis-producer map (:data:`_DEFAULT_COUPLINGS`). Any
    coupling whose source or target is not yet registered in ``registry`` is
    skipped and logged at INFO — no null binding is invented for it. As Phase D
    and E bind the value-form oppositions, those ``transforms`` edges begin to
    survive automatically.

    Args:
        registry: The opposition registry the couplings are validated against;
            typically :func:`build_default_registry`'s five-opposition registry.

    Returns:
        A :class:`~babylon.domain.dialectics.core.coupling.CouplingGraph` over the
        subset of couplings whose endpoints are both registered (plus any
        ``contains`` edges auto-derived from nesting).
    """
    keys = set(registry.keys)
    bound: list[Coupling] = []
    for coupling in _DEFAULT_COUPLINGS:
        if coupling.source in keys and coupling.target in keys:
            bound.append(coupling)
        else:
            logger.info(
                "Skipping coupling %s -> %s (%s): endpoint(s) not yet registered",
                coupling.source,
                coupling.target,
                coupling.kind,
            )
    return CouplingGraph(bound, registry)
