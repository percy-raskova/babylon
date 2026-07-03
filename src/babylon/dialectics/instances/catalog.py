"""The production opposition catalog: Babylon's five bound contradictions.

:func:`build_default_registry` wires an
:class:`~babylon.dialectics.core.opposition.OppositionRegistry` over
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
- ``wage`` — mean wealth-asymmetry over WAGES edges, re-oriented to the
  SAME (labor = A, capital = B) convention as ``capital_labor`` so the
  balance sign is uniform (positive = capital dominant). Its rate is the
  crisis signal ``ConsciousnessSystem`` reads.
- ``tenancy`` — tenant wealth (A) vs the territory's ``rent_level`` (B)
  over TENANCY edges, with a degenerate guard: a territory charging no
  rent (``rent_level`` ~ 0) has NO tenancy contradiction, so the pair
  contributes 0.0 rather than the wealth-vs-0 form's spurious 1.0.
- ``atomization`` — gap = :func:`atomization_index` of the SOLIDARITY
  subgraph (1 = fully atomized), balance = ``2*cylinder_balance - 1`` so
  −1 is the atomized pole and +1 the unified pole.
- ``imperial`` — core↔periphery. The bridged world seeds no periphery
  entities, so this binds a NULL measure (gap 0, balance 0); Phase D
  rebinds it to the value-form defect Φ (the wage⇄value counit defect).

Design note (pole naming): the design contract names the ``wage`` poles
"price-of-labor-power" ⇄ "value-produced" — the true wage⇄value adjunction
defect (Fundamental Theorem: W_c > V_c). No per-edge "value produced"
scalar is persisted yet, so the honest available proxy is the WAGES-edge
endpoint wealth-asymmetry; Phase D replaces it. We therefore label the
poles for what is actually measured (labor ⇄ capital) and record the
aspirational reading in the spec's ``unity`` string.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import networkx as nx

from babylon.dialectics.core.opposition import (
    BoundOpposition,
    GapReading,
    OppositionRegistry,
    OppositionSpec,
)
from babylon.dialectics.instances.connectivity import atomization_index, connectivity_cylinder
from babylon.formulas.contradiction import (
    calculate_wealth_asymmetry_balance,
    calculate_wealth_asymmetry_gap,
)

__all__ = ["GraphInputs", "build_default_registry"]

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
        wages_pairs: ``(labor_wealth, capital_wealth)`` per WAGES edge,
            re-oriented from the edge's employer→worker direction so labor
            is always pole A.
        tenancy_pairs: ``(tenant_wealth, rent_level)`` per TENANCY edge.
        solidarity_subgraph: the undirected SOLIDARITY subgraph
            (from ``extract_solidarity_subgraph``) for the atomization
            cylinder; ``None`` is treated as empty.
    """

    exploitation_pairs: tuple[WealthPair, ...] = ()
    wages_pairs: tuple[WealthPair, ...] = ()
    tenancy_pairs: tuple[WealthPair, ...] = ()
    solidarity_subgraph: nx.Graph[str] | None = field(default=None)


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


def _wage_measure(inputs: GraphInputs) -> GapReading:
    """wage relation over WAGES edges (labor=A, capital=B)."""
    return _mean_asymmetry(inputs.wages_pairs)


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


def _imperial_measure(inputs: GraphInputs) -> GapReading:  # noqa: ARG001 - Protocol arity
    """core⇄periphery — NULL until Phase D binds it to the value-form defect Φ.

    The bridged world seeds no periphery entities, so there is nothing to
    measure cheaply here. Returns ``gap 0, balance 0`` rather than inventing
    an economics; Phase D (``instances/value_form.py``) rebinds this to the
    per-class signed counit defect ``(W_c - V_c)/V_c``.
    """
    return GapReading(gap=0.0, balance=0.0)


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
                antagonistic=True,
            ),
            measure=_capital_labor_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="wage",
                pole_a="labor (value produced)",
                pole_b="capital (price of labor-power advanced)",
                unity="the wage bargain: capital advances the price of labor-power, "
                "labor yields the value it produces (Phase D: Φ = W_c − V_c defect)",
            ),
            measure=_wage_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="tenancy",
                pole_a="tenant",
                pole_b="rent",
                unity="occupancy presupposes the ground rent it is charged",
            ),
            measure=_tenancy_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="atomization",
                pole_a="atomized",
                pole_b="unified",
                unity="a class exists only as the (dis)connection of its members",
            ),
            measure=_atomization_measure,
        ),
        BoundOpposition(
            spec=OppositionSpec(
                key="imperial",
                pole_a="core",
                pole_b="periphery",
                unity="core accumulation presupposes peripheral value transfer (Φ)",
                antagonistic=True,
            ),
            measure=_imperial_measure,
        ),
    ]
    return OppositionRegistry(bindings=bindings, rate_weight=rate_weight)
