"""The production opposition catalog: Babylon's five bound contradictions.

:func:`build_default_registry` wires an
:class:`~babylon.domain.dialectics.core.opposition.OppositionRegistry` over
:class:`GraphInputs` — a small frozen snapshot the engine's
``ContradictionSystem`` fills once per tick from the live graph. Keeping
the snapshot as pre-extracted views (not the graph itself) keeps this
module free of any ``babylon.engine`` import, so the dialectics package
stays a pure downstream of ``formulas`` + ``models`` and cannot form an
import cycle with the system that consumes it.

The five oppositions, and the honest measure each is bound to on this
branch (verified against a 30-tick single-county bridged probe,
2026-07-02):

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

Design note (shared defect, different poles): ``wage`` and ``imperial`` read
the identical ``(w_paid, v_produced)`` defect but bind different poles —
``wage`` names the per-class relation (value-produced ⇄ price-of-labor-power),
``imperial`` names the frame (core ⇄ periphery). The measure is
:func:`babylon.domain.dialectics.instances.value_form.phi_class` in spirit; the
catalog uses the bounded asymmetry form from ``formulas.contradiction`` so the
gap stays in ``[0, 1]`` (the raw ``(w−v)/v`` is unbounded). See
:mod:`babylon.domain.dialectics.instances.value_form` for the full adjunction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from babylon.formulas.contradiction import (
    calculate_wealth_asymmetry_balance,
    calculate_wealth_asymmetry_gap,
)

__all__ = ["GraphInputs", "build_default_coupling_graph", "build_default_registry"]

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
    """

    exploitation_pairs: tuple[WealthPair, ...] = ()
    wage_value_pairs: tuple[tuple[float, float], ...] = ()
    tenancy_pairs: tuple[WealthPair, ...] = ()
    solidarity_subgraph: BabylonUGraph | None = field(default=None)
    exploitation_id_pairs: tuple[tuple[str, str, float, float], ...] = ()
    wage_value_id_pairs: tuple[tuple[str, float, float], ...] = ()
    tenancy_id_pairs: tuple[tuple[str, str, float, float], ...] = ()


def _mean_asymmetry(pairs: Sequence[WealthPair]) -> GapReading:
    """Mean wealth-asymmetry gap and balance over ``(pole_a, pole_b)`` pairs.

    Empty input → ``gap 0.0, balance 0.0`` (an absent edge set carries no
    contradiction), per the design contract.
    """
    if not pairs:
        return GapReading(gap=0.0, balance=0.0)
    n = len(pairs)
    gap = sum(calculate_wealth_asymmetry_gap(a, b) for a, b in pairs) / n
    balance = sum(calculate_wealth_asymmetry_balance(a, b) for a, b in pairs) / n
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


def build_default_registry(rate_weight: float = 10.0) -> OppositionRegistry[GraphInputs]:
    """Build the production five-opposition registry.

    Args:
        rate_weight: Weight of ``|rate|`` in principal-contradiction scoring;
            wired from ``defines.tension.principal_rate_weight`` by the engine.

    Returns:
        An :class:`OppositionRegistry` over :class:`GraphInputs` binding
        ``capital_labor``, ``wage``, ``tenancy``, ``atomization`` and
        ``imperial`` (keys lexicographically ordered inside the registry).
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
    ]
    return OppositionRegistry(bindings=bindings, rate_weight=rate_weight)


# The ratified crisis-producer map. The four ``transforms`` edges reference
# Phase D/E value-form oppositions (Circulation, Reproduction, Credit, ...) not
# yet bound on this branch; the two class edges are bound today. The builder
# keeps only edges whose BOTH endpoints are registered — it never invents a
# null binding for an absent endpoint.
_DEFAULT_COUPLINGS: tuple[Coupling, ...] = (
    # crisis producers: source's output becomes target's input prices
    Coupling(source="circulation", target="realization", kind="transforms"),
    Coupling(source="reproduction", target="disproportionality", kind="transforms"),
    Coupling(source="surplus_distribution", target="debt_spiral", kind="transforms"),
    Coupling(source="credit", target="financial", kind="transforms"),
    # the two antagonistic class contradictions are mutually antagonistic
    Coupling(source="capital_labor", target="imperial", kind="antagonizes"),
    # capital_labor's development presupposes the wage relation it reads
    Coupling(source="wage", target="capital_labor", kind="feeds"),
    # wage and imperial read the SAME (w_paid, v_produced) defect (D5): the
    # per-class wage relation feeds the frame-level imperial-rent reading.
    Coupling(source="wage", target="imperial", kind="feeds"),
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
