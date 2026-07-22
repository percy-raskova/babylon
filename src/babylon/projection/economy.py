"""The economy read-model — ``project_economy``, the T3 spine-C dossier.

Assembles a :class:`~babylon.projection.view_models.EconomyView` from the
post-tick world: the Fundamental Theorem verdict read verbatim off the
``wage`` opposition's Balance, the per-class/county Φ readings the
``fundamental_theorem`` graph stash carries, Φ's tri-decomposition (wired
here as a pure read of graph inputs — genuinely absent tree-wide today), the
Volume III surplus split aggregated RATIO-OF-SUMS across territories, and
the metabolic matter-book. Transport-neutral by construction — no Django, no
engine imports, no database connection; callers hand in the graph and world
they already hold.

**One producer per field** (mirrors the WO-3 ruling
:mod:`babylon.projection.county` records):

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``wage_balance`` / ``labor_aristocracy_verdict``
     - The ``wage`` opposition's ``balance`` on the ``opposition_states``
       graph attribute (``ContradictionSystem``,
       ``OPPOSITION_STATES_ATTR`` = ``"opposition_states"``) — ``balance =
       (value_produced − price_of_labor_power) / (value_produced +
       price_of_labor_power)`` (catalog.py's ``_wage_value_reading``).
       ``balance > 0`` IS ``W_c > V_c`` BY CONSTRUCTION; this module never
       recomputes a parallel theorem.
   * - ``class_phi_readings``
     - The ``fundamental_theorem`` graph attribute
       (``ContradictionSystem._stash_fundamental_theorem``,
       ``FUNDAMENTAL_THEOREM_ATTR`` = ``"fundamental_theorem"``), a
       ``{entity_id: ClassPhiReading.model_dump()}`` dump computed by
       :func:`~babylon.domain.dialectics.instances.value_form.
       compute_fundamental_theorem`, hydrated verbatim and sorted by
       ``entity_id``.
   * - ``phi_unequal_exchange`` / ``phi_reproduction`` / ``phi_domestic`` /
       ``phi_iii_report`` / ``phi_decomposition_total``
     - Φ's tri-decomposition (:mod:`~babylon.domain.dialectics.instances.
       value_form`'s ``phi_unequal_exchange``/``phi_reproduction``/
       ``phi_domestic``/``phi_iii_report`` builders, §9.3). Wired here as a
       pure read of graph inputs at project time — NOT engine computation.
       Each component needs its own raw input (``γ_basket`` + consumption
       for unequal exchange; ``p_g2_labor_value`` + wages-for-rearing for
       reproduction; unpaid reproductive labor-hours for domestic) and
       **none of these five inputs is published to the graph anywhere in
       the engine today** (verified tree-wide, 2026-07-22 — not even the
       national MELT τ alone, itself live on
       ``tick_dynamics.tick_summary.national_melt``, can complete
       ``τ · L_unpaid`` without ``L_unpaid``). All five project as honest
       ``None`` until a future unit lands the first missing input, one
       component at a time (Constitution III.11) — this module never
       fabricates them and never adds the missing engine-side computation.
   * - ``surplus_produced`` / ``profit_of_enterprise`` / ``interest_burden``
       / ``ground_rent`` / ``taxes_on_surplus`` / ``rentier_share`` /
       ``financialization_share``
     - The Volume III surplus split's ``tick_``-prefixed territory
       attributes (``domain/economics/tick/graph_bridge.py``,
       ``write_tick_state_to_graph`` — U1's surplus-split publication
       completion). The five dollar terms are RATIO-OF-SUMS (extensive
       sums across territories, presented directly); the two shares are
       re-derived as ``Σr/Σs``/``Σi/Σs`` from those SAME sums — never by
       averaging the per-territory ``tick_rentier_share``/
       ``tick_financialization_share`` readings (the named
       intensive-aggregation error class).
   * - ``total_consumption`` / ``total_biocapacity`` / ``overshoot_ratio`` /
       ``biocapacity_ceiling``
     - ``WorldState.total_consumption``/``total_biocapacity`` (the
       extensive-sum shape ``world_state.py`` already computes over
       ``Territory.biocapacity``/entity ``consumption_needs``) plus a
       locally-summed ``Territory.max_biocapacity`` ceiling. NEVER the
       ``v_*_value_aggregate`` views' ``biocapacity_sum`` column — that is
       a STATIC seed placeholder never ticked (``hex_hydrator.py``).
       ``overshoot_ratio`` is computed HONESTLY here (``None`` on a
       non-positive denominator), never via
       ``WorldState.overshoot_ratio``'s own fabricated ``999.0`` sentinel.
   * - ``energy_beta_j``
     - No producer. Always ``None`` — the energy vertex is genuinely absent
       tree-wide (no EROI/joule/power-density accounting anywhere in the
       engine, per ``ai/_inbox/math/metabolic-calculus.md``'s own
       tree-wide verification). Never derived from the money-form
       quantities above.

Absence discipline (Constitution III.11): every quantity above projects as
``None`` when its own graph input is absent this tick — never a defaulted
zero. A present-but-malformed source value fails loud through the relevant
Pydantic validation (:class:`~babylon.projection.view_models.
ClassPhiReadingView`, the constrained field types) — only a *missing* value
is absence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.models.enums.topology import NodeType
from babylon.projection.view_models import ClassPhiReadingView, EconomyView

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.world_state import WorldState

__all__ = ["project_economy"]


def _fundamental_theorem_verdict(graph: GraphProtocol) -> tuple[float | None, bool | None]:
    """Read the ``wage`` opposition's Balance verdict verbatim off the graph.

    Never recomputes W_c/V_c independently — the Balance IS the theorem
    (``opposition_states["wage"].balance``, positive meaning the wage
    exceeds value produced).

    :param graph: The post-tick graph.
    :returns: ``(wage_balance, labor_aristocracy_verdict)`` — both ``None``
        when the opposition registry is unwired or ``wage`` is not a
        registered key this run.
    """
    states = graph.get_graph_attr("opposition_states", {}) or {}
    wage_state = states.get("wage") if isinstance(states, dict) else None
    if not isinstance(wage_state, dict) or "balance" not in wage_state:
        return (None, None)
    balance = float(wage_state["balance"])
    return (balance, balance > 0.0)


def _class_phi_readings(graph: GraphProtocol) -> tuple[ClassPhiReadingView, ...] | None:
    """Hydrate the ``fundamental_theorem`` graph stash into sorted readings.

    :param graph: The post-tick graph.
    :returns: readings sorted by ``entity_id``, or ``None`` when the graph
        attribute itself is absent (the registry never ran this tick). An
        attributed-but-empty dict yields an empty tuple — a real, different
        fact from "never computed".
    :raises pydantic.ValidationError: if a present reading is malformed.
    """
    raw = graph.get_graph_attr("fundamental_theorem", None)
    if raw is None:
        return None
    return tuple(ClassPhiReadingView(**data) for _, data in sorted(raw.items()))


#: One RATIO-OF-SUMS tuple: (s, p, i, r, t, rentier_share, financialization_share).
_SurplusSplit = tuple[
    float | None, float | None, float | None, float | None, float | None, float | None, float | None
]


def _surplus_split(graph: GraphProtocol) -> _SurplusSplit:
    """Territory-wide Vol III surplus split, RATIO-OF-SUMS (U1's tick_ attrs).

    Sums the five extensive dollar terms (s, p, i, r, t) across every
    territory that carries ``tick_total_surplus`` this tick, then derives
    the two intensive shares as genuine ratios of the summed totals
    (``Σr/Σs``, ``Σi/Σs``) — never by averaging the per-territory
    ``tick_rentier_share``/``tick_financialization_share`` readings (a
    territory producing a sliver of national surplus must not swing the
    national share as hard as one producing the bulk of it).

    Territories are visited in sorted-id order so the float summation order
    is fixed (Constitution III.7).

    :param graph: The post-tick graph.
    :returns: ``(s, p, i, r, t, rentier_share, financialization_share)`` —
        all seven ``None`` when no territory carries ``tick_total_surplus``
        (the economics tick bridge never ran this tick); the two shares
        independently ``None`` when Σs is not positive.
    """
    sum_s = sum_p = sum_i = sum_r = sum_t = 0.0
    saw_any = False
    for territory in sorted(graph.query_nodes(node_type=NodeType.TERRITORY), key=lambda n: n.id):
        attrs = territory.attributes
        if "tick_total_surplus" not in attrs:
            continue
        saw_any = True
        sum_s += float(attrs.get("tick_total_surplus", 0.0))
        sum_p += float(attrs.get("tick_profit_of_enterprise", 0.0))
        sum_i += float(attrs.get("tick_interest_burden", 0.0))
        sum_r += float(attrs.get("tick_ground_rent", 0.0))
        sum_t += float(attrs.get("tick_taxes_on_surplus", 0.0))
    if not saw_any:
        return (None, None, None, None, None, None, None)
    rentier_share = sum_r / sum_s if sum_s > 0.0 else None
    financialization_share = sum_i / sum_s if sum_s > 0.0 else None
    return (sum_s, sum_p, sum_i, sum_r, sum_t, rentier_share, financialization_share)


#: One matter-book tuple: (total_consumption, total_biocapacity, overshoot, ceiling).
_MatterBook = tuple[float | None, float | None, float | None, float | None]


def _matter_book(world: WorldState) -> _MatterBook:
    """The metabolic matter-book: consumption, biocapacity, overshoot, ceiling.

    Reuses ``WorldState.total_consumption``/``total_biocapacity`` verbatim
    — the same extensive-sum shape (Σ ``Territory.biocapacity``, Σ entity
    ``consumption_needs``) rather than re-deriving it — but computes
    ``overshoot_ratio`` honestly here rather than reusing
    ``WorldState.overshoot_ratio``'s own ``999.0`` fabricated sentinel on a
    zero-biocapacity denominator (Constitution III.11 forbids a substituted
    default standing in for absence). The monotone ceiling M̄ has no
    existing ``WorldState`` property, so it is summed directly here.

    LANDMINE avoided: the ``v_*_value_aggregate`` views' ``biocapacity_sum``
    column is a STATIC seed placeholder never ticked (``hex_hydrator.py``)
    — this reads the LIVE ``Territory.biocapacity``/``max_biocapacity``
    model fields instead, which do survive the post-tick round trip.

    :param world: The post-tick world state.
    :returns: ``(total_consumption, total_biocapacity, overshoot_ratio,
        biocapacity_ceiling)`` — all four ``None`` when the world carries no
        territory; ``overshoot_ratio`` independently ``None`` when total
        biocapacity is not positive.
    """
    if not world.territories:
        return (None, None, None, None)
    total_consumption = float(world.total_consumption)
    total_biocapacity = float(world.total_biocapacity)
    overshoot = total_consumption / total_biocapacity if total_biocapacity > 0.0 else None
    ceiling = float(sum(t.max_biocapacity for t in world.territories.values()))
    return (total_consumption, total_biocapacity, overshoot, ceiling)


def project_economy(
    economy_id: str,
    *,
    graph: GraphProtocol,
    world: WorldState,
    tick: int,
) -> EconomyView:
    """Project the whole economy's post-tick state into an :class:`EconomyView`.

    Read strictly *post-tick*, exactly like :func:`~babylon.projection.
    county.project_county`/:func:`~babylon.projection.national.
    project_national`. See :class:`~babylon.projection.view_models.
    EconomyView`'s docstring for the full field-by-field producer ruling.

    :param economy_id: The economy's identity (``"USA"`` today).
    :param graph: The committed post-tick graph.
    :param world: The committed post-tick world state.
    :param tick: The committed tick this dossier is projected from.
    :returns: The frozen, validated economy dossier.
    :raises pydantic.ValidationError: when a present source value violates
        its constrained type — a wrong value fails loud, only a *missing*
        one is absence.
    """
    wage_balance, labor_aristocracy_verdict = _fundamental_theorem_verdict(graph)
    class_phi_readings = _class_phi_readings(graph)
    (
        surplus_produced,
        profit_of_enterprise,
        interest_burden,
        ground_rent,
        taxes_on_surplus,
        rentier_share,
        financialization_share,
    ) = _surplus_split(graph)
    (
        total_consumption,
        total_biocapacity,
        overshoot_ratio,
        biocapacity_ceiling,
    ) = _matter_book(world)

    return EconomyView(
        economy_id=economy_id,
        verified_tick=tick,
        wage_balance=wage_balance,
        labor_aristocracy_verdict=labor_aristocracy_verdict,
        class_phi_readings=class_phi_readings,
        # Φ's tri-decomposition (§9.3): genuinely absent tree-wide today —
        # no engine producer publishes gamma_basket/consumption (unequal
        # exchange), p_g2_labor_value/wage_paid_for_d_g2 (reproduction), or
        # l_unpaid (domestic labor's unpaid-hours half; national MELT tau
        # IS live elsewhere, but alone cannot complete tau * l_unpaid).
        # Wired to light up the moment any ONE producer lands, one
        # component at a time (Constitution III.11) — never engine
        # computation added here (see this module's own docstring table).
        phi_unequal_exchange=None,
        phi_reproduction=None,
        phi_domestic=None,
        phi_iii_report=None,
        phi_decomposition_total=None,
        surplus_produced=surplus_produced,
        profit_of_enterprise=profit_of_enterprise,
        interest_burden=interest_burden,
        ground_rent=ground_rent,
        taxes_on_surplus=taxes_on_surplus,
        rentier_share=rentier_share,
        financialization_share=financialization_share,
        total_consumption=total_consumption,
        total_biocapacity=total_biocapacity,
        overshoot_ratio=overshoot_ratio,
        biocapacity_ceiling=biocapacity_ceiling,
        # The energy vertex beta_J: always None, genuinely absent tree-wide
        # (no EROI/joule/power-density accounting anywhere in the engine).
        # Never derived from the money-form quantities above.
        energy_beta_j=None,
    )
