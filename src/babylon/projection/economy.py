"""The economy read-model — ``project_economy``, the T3 spine-C dossier.

Assembles a :class:`~babylon.projection.view_models.EconomyView` from the
post-tick world: the Fundamental Theorem verdict read verbatim off the
``wage`` opposition's Balance, the per-class/county Φ readings the
``fundamental_theorem`` graph stash carries, Φ's tri-decomposition (each
component's own named graph inputs are attempted at project time and fed
straight into the matching :mod:`~babylon.domain.dialectics.instances.
value_form` builder — genuinely absent tree-wide today, so every attempt
currently resolves ``None``, but the read sites are real: the first future
unit to publish a component's inputs makes that component light up with no
change to this module), the Volume III surplus split aggregated
RATIO-OF-SUMS across territories, and the metabolic matter-book.
Transport-neutral by construction — no Django, no engine imports, no
database connection; callers hand in the graph and world they already hold.

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
       ``phi_domestic``/``phi_iii_report``/``PhiDecomposition`` builders,
       §9.3). Each component attempts its own named graph reads at project
       time — NOT engine computation — and calls the matching builder only
       when every one of its inputs resolves:
       ``phi_unequal_exchange`` reads the ``"gamma_basket"`` (a
       :class:`~babylon.domain.economics.gamma.types.GammaBasket` dump) and
       ``"consumption"`` graph attrs; ``phi_reproduction`` reads
       ``"p_g2_labor_value"`` and ``"wage_paid_for_d_g2"``; ``phi_domestic``
       reads ``"l_unpaid"`` plus the national MELT τ already live on
       ``tick_dynamics.tick_summary.national_melt``; ``phi_iii_report``
       reads ``"gamma_iii"`` (a
       :class:`~babylon.domain.economics.gamma.types.GammaIII` dump) plus
       the same τ. ``phi_decomposition_total`` builds a real
       :class:`~babylon.domain.dialectics.instances.value_form.
       PhiDecomposition` and reads its ``total`` — but only once all THREE
       conservation components (unequal exchange, reproduction, domestic)
       resolve; ``phi_iii_report`` is report-only and never gates it.
       **None of these six graph attrs is published anywhere in the engine
       today** (verified tree-wide, 2026-07-22), so every read attempt
       currently resolves ``None`` and every component projects honest
       ``None`` (Constitution III.11) — this module never fabricates an
       input and never adds the missing engine-side computation. The read
       sites are real, though: the first future unit to publish any one
       input lights up that component with no change to this module.
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

from babylon.domain.dialectics.instances.value_form import (
    PhiDecomposition,
    phi_domestic,
    phi_iii_report,
    phi_reproduction,
    phi_unequal_exchange,
)
from babylon.domain.economics.gamma.types import GammaBasket, GammaIII
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


def _national_melt(graph: GraphProtocol) -> float | None:
    """Read the national MELT (τ) off the live ``tick_dynamics`` graph stash.

    ``TickDynamicsSystem`` writes ``state.tick_summary`` (a
    :class:`~babylon.domain.economics.tick.types.TickSummary` instance, not a
    dump) verbatim into the ``"tick_dynamics"`` graph attr's ``"tick_summary"``
    key (:func:`~babylon.domain.economics.tick.graph_bridge.
    write_tick_state_to_graph`) — read here via ``graph.get_graph_attr``
    through the SAME live in-memory graph object, never a round-tripped copy.

    :param graph: The post-tick graph.
    :returns: ``tick_dynamics.tick_summary.national_melt``, or ``None`` when
        the ``tick_dynamics`` stash or its ``tick_summary`` sub-object is
        absent this tick.
    """
    tick_dynamics = graph.get_graph_attr("tick_dynamics", None)
    if not isinstance(tick_dynamics, dict):
        return None
    tick_summary = tick_dynamics.get("tick_summary")
    if tick_summary is None:
        return None
    return float(tick_summary.national_melt)


def _phi_unequal_exchange(graph: GraphProtocol) -> float | None:
    """Emmanuel/Amin Φ_unequal_exchange, from its two named graph inputs.

    :param graph: The post-tick graph.
    :returns: :func:`~babylon.domain.dialectics.instances.value_form.
        phi_unequal_exchange` over the ``"gamma_basket"``/``"consumption"``
        graph attrs, or ``None`` when either is absent this tick.
    :raises pydantic.ValidationError: if a present ``"gamma_basket"`` dump is
        malformed.
    """
    raw_gamma_basket = graph.get_graph_attr("gamma_basket", None)
    consumption = graph.get_graph_attr("consumption", None)
    if raw_gamma_basket is None or consumption is None:
        return None
    gamma_basket = GammaBasket(**raw_gamma_basket)
    return phi_unequal_exchange(gamma_basket, float(consumption))


def _phi_reproduction(graph: GraphProtocol) -> float | None:
    """Meillassoux Φ_reproduction, from its two named graph inputs.

    :param graph: The post-tick graph.
    :returns: :func:`~babylon.domain.dialectics.instances.value_form.
        phi_reproduction` over the ``"p_g2_labor_value"``/
        ``"wage_paid_for_d_g2"`` graph attrs, or ``None`` when either is
        absent this tick.
    """
    p_g2_labor_value = graph.get_graph_attr("p_g2_labor_value", None)
    wage_paid_for_d_g2 = graph.get_graph_attr("wage_paid_for_d_g2", None)
    if p_g2_labor_value is None or wage_paid_for_d_g2 is None:
        return None
    return phi_reproduction(
        p_g2_labor_value=float(p_g2_labor_value),
        wage_paid_for_d_g2=float(wage_paid_for_d_g2),
    )


def _phi_domestic(graph: GraphProtocol) -> float | None:
    """Fortunati Φ_domestic (``τ · L_unpaid``), from its named graph inputs.

    :param graph: The post-tick graph.
    :returns: :func:`~babylon.domain.dialectics.instances.value_form.
        phi_domestic` over the ``"l_unpaid"`` graph attr and
        :func:`_national_melt`, or ``None`` when either is absent this tick.
    """
    l_unpaid = graph.get_graph_attr("l_unpaid", None)
    tau = _national_melt(graph)
    if l_unpaid is None or tau is None:
        return None
    return phi_domestic(tau, float(l_unpaid))


def _phi_iii_report(graph: GraphProtocol) -> float | None:
    """The kernel's narrower Φ_III report term, from its named graph inputs.

    :param graph: The post-tick graph.
    :returns: :func:`~babylon.domain.dialectics.instances.value_form.
        phi_iii_report` over the ``"gamma_iii"`` graph attr and
        :func:`_national_melt`, or ``None`` when either is absent this tick.
    :raises pydantic.ValidationError: if a present ``"gamma_iii"`` dump is
        malformed.
    """
    raw_gamma_iii = graph.get_graph_attr("gamma_iii", None)
    tau = _national_melt(graph)
    if raw_gamma_iii is None or tau is None:
        return None
    gamma_iii = GammaIII(**raw_gamma_iii)
    return phi_iii_report(gamma_iii, tau)


#: One Φ tri-decomposition tuple:
#: (unequal_exchange, reproduction, domestic, iii_report, decomposition_total).
_PhiTriDecomposition = tuple[float | None, float | None, float | None, float | None, float | None]


def _phi_tri_decomposition(graph: GraphProtocol) -> _PhiTriDecomposition:
    """Attempt every Φ tri-decomposition component's own named graph read.

    Each component is read and, where possible, built independently — a
    present ``phi_unequal_exchange`` does not require ``phi_domestic`` to
    also be present. ``phi_decomposition_total`` is the odd one out: it
    builds a real :class:`~babylon.domain.dialectics.instances.value_form.
    PhiDecomposition` and reads its ``total`` computed field, so it requires
    all THREE conservation components (unequal exchange, reproduction,
    domestic) to resolve — ``phi_iii_report`` is report-only (D2 kernel-fork
    resolution) and never gates it, matching
    :attr:`~babylon.domain.dialectics.instances.value_form.PhiDecomposition.total`'s
    own exclusion.

    :param graph: The post-tick graph.
    :returns: ``(phi_unequal_exchange, phi_reproduction, phi_domestic,
        phi_iii_report, phi_decomposition_total)`` — each independently
        ``None`` when its own inputs are absent this tick.
    """
    unequal_exchange = _phi_unequal_exchange(graph)
    reproduction = _phi_reproduction(graph)
    domestic = _phi_domestic(graph)
    iii_report = _phi_iii_report(graph)
    total: float | None = None
    if unequal_exchange is not None and reproduction is not None and domestic is not None:
        decomposition = PhiDecomposition(
            phi_unequal_exchange=unequal_exchange,
            phi_reproduction=reproduction,
            phi_domestic=domestic,
            phi_iii_report=iii_report if iii_report is not None else 0.0,
        )
        total = decomposition.total
    return (unequal_exchange, reproduction, domestic, iii_report, total)


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
        phi_unequal_exchange_reading,
        phi_reproduction_reading,
        phi_domestic_reading,
        phi_iii_report_reading,
        phi_decomposition_total_reading,
    ) = _phi_tri_decomposition(graph)
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
        # Φ's tri-decomposition (§9.3): each component reads its own named
        # graph inputs at project time (see :func:`_phi_tri_decomposition`
        # and this module's own docstring table) — genuinely absent
        # tree-wide today, so every attempt currently resolves None, but the
        # read sites are real and light up the moment a future unit
        # publishes the first input (Constitution III.11) — never engine
        # computation added here.
        phi_unequal_exchange=phi_unequal_exchange_reading,
        phi_reproduction=phi_reproduction_reading,
        phi_domestic=phi_domestic_reading,
        phi_iii_report=phi_iii_report_reading,
        phi_decomposition_total=phi_decomposition_total_reading,
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
