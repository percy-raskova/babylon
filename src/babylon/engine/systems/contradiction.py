"""Contradiction system — Lawverian opposition registry (Phase C1.3).

Position 18 in the pipeline. This is the rewrite that retires the saturating,
add-only edge-``tension`` accumulator (the "Formula" + "Consumption" inertness
bugs of ``project/06-lawverian-dialectics.md`` §2). Each tick the system:

1. writes per-edge ``tension`` as the *fresh* wealth-asymmetry gap of that edge
   (EXPLOITATION / WAGES / TENANCY) — scale-free, recomputed from current
   wealth, never accumulated;
2. steps the :class:`~babylon.domain.dialectics.core.opposition.OppositionRegistry`
   (wired by :meth:`ServicesProtocol.create`) over a :class:`GraphInputs`
   snapshot built from the live graph, deriving each opposition's gap, rate,
   and the Maoist principal contradiction;
3. derives ``contradiction_frames`` from the registry states (intensity ← gap,
   aspect_balance ← rate, principal_aspect ← leading_pole; frame
   principal/secondary = registry principal + runner-up);
3b. corrects the ranking against the injected ``CouplingGraph``: a
    ``transforms`` target cannot rank principal while the source supplying
    its input reads absent (Vol III money scissors, U5). This runs BEFORE
    frames/rupture/regime so every consumer sees one principal;
4. fires RUPTURE on the principal opposition's gap exceeding the defines
   threshold **AND rising** (rate > 0) — Mao's "condition AND level", never on
   hitting a ceiling.

Cross-tick + handoff channel.
    The registry snapshot is stashed on the **graph attribute**
    ``opposition_states`` (not ``context.persistent_data``). The bridged
    headless runner recreates a fresh ``TickContext`` every tick
    (``engine/headless_runner/runner.py`` ``_advance_tick``), so
    ``persistent_data`` is not a cross-tick channel there; the graph, by
    contrast, persists in-place across ticks in both the bridged runner and
    the in-memory ``Simulation`` facade. The graph attribute is therefore the
    reliable place to (a) recover the previous tick's gaps for rate/inertia,
    (b) hand the capital_labor gap to the pre-position-18 consumers
    (ImperialRent @9, Struggle @16, Consciousness @17 read *last* tick's
    snapshot), and (c) let the bridge's ``persist_tick`` read the snapshot.
    This is the same channel ``contradiction_frames`` already uses.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, ClassVar

from babylon.domain.dialectics.core.coupling import StanceIntervention, apply_interventions
from babylon.domain.dialectics.core.opposition import OppositionState, PoleReading
from babylon.domain.dialectics.core.regime import classify_regime
from babylon.domain.dialectics.instances.catalog import GraphInputs
from babylon.domain.dialectics.instances.levels import level_index_for, spatial_lattice_for_counties
from babylon.domain.economics.distribution.types import (
    DebtAccumulation,
    SurplusValueDistribution,
)
from babylon.domain.economics.tick.graph_bridge import (
    NATIONAL_FINANCIAL_ATTR,
    TICK_DYNAMICS_KEY,
)
from babylon.engine.topology_monitor import extract_solidarity_subgraph
from babylon.formulas.contradiction import calculate_wealth_asymmetry_gap
from babylon.formulas.market import calculate_scissors_balance
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.kernel.tick_partition import TickPartition
from babylon.models.entities.contradiction import Contradiction, ContradictionFrame
from babylon.models.enums import (
    ColonialStance,
    ContradictionType,
    EdgeMode,
    EdgeType,
    EventType,
    NodeType,
)
from babylon.sentinels.partition.registry import cell_name

if TYPE_CHECKING:
    from babylon.domain.dialectics.core.opposition import OppositionRegistry, OppositionSpec
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

#: Graph attribute holding ``{key: OppositionState.model_dump()}`` for the tick.
OPPOSITION_STATES_ATTR = "opposition_states"

#: Graph attribute holding ``{key: OppositionState.model_dump()}`` for SHADOW
#: bindings (ADR077): measured every tick, adjudicating nothing. Kept apart
#: from ``opposition_states`` so the pre-position-18 consumers and the frames/
#: rupture/regime machinery never see a shadow key. Same cross-tick channel
#: semantics (the graph persists in-place; the facade recomputes fresh each
#: tick). Written only when shadow bindings are registered, so pre-ADR077
#: graphs carry no new key.
SHADOW_OPPOSITION_STATES_ATTR = "shadow_opposition_states"

#: Graph attribute holding this tick's fixed-point regime (Phase E2):
#: ``{"regime": <reproduction|crisis|sublation>, "principal": key, "rate": float}``.
DIALECTICAL_REGIME_ATTR = "dialectical_regime"

#: County-chain level index of the capital_labor field the regime probes.
_COUNTY_LEVEL_INDEX = 1

#: Graph attribute holding a list of ``StanceIntervention`` dumps to apply this
#: tick. Written by verb/OODA systems (spec-071), read + CLEARED here
#: (consumed-once). No producer writes it yet; unit tests set it directly.
OPPOSITION_INTERVENTIONS_ATTR = "opposition_interventions"

#: Graph attribute holding the per-node pole channel (Program 19, ADR070):
#: ``{opposition_key: {entity_id: PoleReading.model_dump()}}`` — this tick's
#: snapshot AND next tick's tie-inertia source, on the same cross-tick
#: channel as ``opposition_states``.
POLE_READINGS_ATTR = "pole_readings"

#: The two principal axes whose sigma is written per node (Phase 1 shadow).
#: ``imperial`` stays in the graph-attr channel only — its Phase-1 proxy
#: sigma is identical to ``wage``'s by construction (the D5 shared defect).
_SIGMA_NODE_ATTRS: dict[str, str] = {
    "capital_labor": "sigma_capital_labor",
    "wage": "sigma_wage",
}

#: The derived-cell vocabulary is NOT defined here: writer and sentinel share
#: ONE source of truth — :mod:`babylon.sentinels.partition.registry` (layer
#: 0.5, importable from the engine) — so the cell strings cannot drift from
#: the sentinel's declared crosswalk. Cells are NOT SocialRole names; the
#: crosswalk to seeded roles is the sentinel's EVIDENCE, never an input here.

#: Below this rent_level a TENANCY edge carries no contradiction (rent-free).
_RENT_EPSILON = 1e-9

#: Edge types that receive a fresh per-edge wealth-asymmetry ``tension``.
_TENSION_EDGE_TYPES: tuple[EdgeType, ...] = (
    EdgeType.EXPLOITATION,
    EdgeType.WAGES,
    EdgeType.TENANCY,
)

#: Task #42-C: colonial_stance (spec-070 FR-002) positioned on the national
#: axis. 1.0 = the chauvinism pole (settler sovereignty defended/intensified),
#: 0.0 = the internationalism pole (the settler relation dismantled), 0.5 =
#: IGNORE's RED_OGV middle (class-only focus, neither pole — spec-070 FR-032).
#: A hardcoded categorical map, not a GameDefines coefficient — the same
#: division as ``formulas.balkanization._STANCE_TO_POLICY``.
_STANCE_CHAUVINISM_SCORE: dict[ColonialStance, float] = {
    ColonialStance.UPHOLD: 1.0,
    ColonialStance.IGNORE: 0.5,
    ColonialStance.ABOLISH: 0.0,
}


class ContradictionSystem(SystemBase):
    """Phase 18: fresh-gap tension + opposition-registry contradiction frames."""

    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 18.0

    name: ClassVar[str] = "Contradiction Tension"
    # Spec 053 INV-001: does not mutate hex c+v+s; opted in by default-deny.
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        """Write fresh per-edge tension, then step the opposition registry."""

        tick: int = context.get("tick", 0)
        self._write_edge_tensions(graph)
        self._step_registry(graph, services, tick)

    # ------------------------------------------------------------------
    # 1. Fresh per-edge tension (replaces the add-only accumulator)
    # ------------------------------------------------------------------

    def _write_edge_tensions(self, graph: GraphProtocol) -> None:
        """Set ``tension`` on each EXPLOITATION/WAGES/TENANCY edge to its gap."""
        for edge_type in _TENSION_EDGE_TYPES:
            for edge in graph.query_edges(edge_type=edge_type):
                src = graph.get_node(edge.source_id)
                tgt = graph.get_node(edge.target_id)
                if src is None or tgt is None:
                    continue
                if not src.attributes.get("active", True):
                    continue
                if not tgt.attributes.get("active", True):
                    continue
                src_wealth = float(src.attributes.get("wealth", 0.0))
                if edge_type is EdgeType.TENANCY:
                    rent = float(tgt.attributes.get("rent_level", 0.0))
                    tension = (
                        0.0
                        if rent <= _RENT_EPSILON
                        else calculate_wealth_asymmetry_gap(src_wealth, rent)
                    )
                else:
                    tgt_wealth = float(tgt.attributes.get("wealth", 0.0))
                    tension = calculate_wealth_asymmetry_gap(src_wealth, tgt_wealth)
                graph.update_edge(edge.source_id, edge.target_id, edge.edge_type, tension=tension)

    # ------------------------------------------------------------------
    # 2. Opposition registry step + frames + rupture
    # ------------------------------------------------------------------

    def _step_registry(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
    ) -> None:
        """Step the registry, derive frames, fire rupture, stash the snapshot."""
        registry: OppositionRegistry[GraphInputs] | None = services.opposition_registry
        if registry is None:  # No registry wired (custom container): nothing to do.
            return

        previous = self._read_previous(graph)
        inputs = self._build_graph_inputs(graph, services)
        states = registry.step(inputs, tick, previous)
        if not states:
            return

        # Player-verb stances are signed shoves on balances (spec-071 writes
        # them; consumed-once here). Applied AFTER the measure so a stance can
        # flip a leading pole, BEFORE frames/rupture/stash so downstream sees it.
        states = self._apply_interventions(graph, states)

        shadow_keys = registry.shadow_keys
        canonical = tuple(s for s in states if s.key not in shadow_keys)
        shadow = tuple(s for s in states if s.key in shadow_keys)

        if canonical:
            # The coupling graph corrects the ranking BEFORE anything reads it,
            # so frames, rupture, the regime classifier and the stash all agree
            # on one principal contradiction.
            canonical = self._respect_coupling_direction(canonical, services)
            self._write_frames(graph, services, registry, canonical)
            self._maybe_rupture(services, canonical, tick)
            self._classify_regime(graph, services, registry, canonical, tick)
        graph.set_graph_attr(
            OPPOSITION_STATES_ATTR, {state.key: state.model_dump() for state in canonical}
        )
        if shadow:
            graph.set_graph_attr(
                SHADOW_OPPOSITION_STATES_ATTR,
                {state.key: state.model_dump() for state in shadow},
            )
        self._step_pole_channel(graph, registry, inputs)

    @staticmethod
    def _apply_interventions(
        graph: GraphProtocol, states: tuple[OppositionState, ...]
    ) -> tuple[OppositionState, ...]:
        """Apply + clear the ``opposition_interventions`` attr (consumed-once)."""
        raw: list[dict[str, Any]] = graph.get_graph_attr(OPPOSITION_INTERVENTIONS_ATTR, []) or []
        if not raw:
            return states
        interventions = [StanceIntervention(**dump) for dump in raw]
        applied = apply_interventions(states, interventions)
        graph.set_graph_attr(OPPOSITION_INTERVENTIONS_ATTR, [])
        return applied

    def _respect_coupling_direction(
        self,
        states: tuple[OppositionState, ...],
        services: ServicesProtocol,
    ) -> tuple[OppositionState, ...]:
        """Forbid a ``transforms`` TARGET from leading while its SOURCE is absent.

        The coupling graph's first production duty (Constitution III.10: no
        construct ships as vocabulary). ``coupling.py`` defines ``transforms``
        as "the source's output becomes the target's input prices" — so a
        target whose input has no reading cannot honestly be the contradiction
        whose development leads all others. Crisis has a direction of travel;
        this is what knows it.

        Absence is read off the measure, not guessed: ``gap == 0.0 AND
        balance == 0.0`` is the catalog's canonical no-data reading (empty
        pair sets, ``None`` market balance, ``None`` money ratio). A real
        reading of *nothing claimed* — gap 0 with the substance pole leading
        at balance −1 — is PRESENT, and does not demote anything.

        Only the principal is re-ranked; no gap, balance, rate or leading
        pole is touched. When every eligible candidate is blocked the
        original principal stands: a tick must never end without one.

        Args:
            states: This tick's canonical (non-shadow) states, already
                intervened.
            services: The container carrying ``coupling_graph`` and
                ``defines.tension.principal_rate_weight``.

        Returns:
            The same states, with at most one ``is_principal`` flag moved.
        """
        coupling_graph = services.coupling_graph
        if coupling_graph is None:
            return states
        principal = next((state for state in states if state.is_principal), None)
        if principal is None:
            return states

        absent = {state.key for state in states if state.gap == 0.0 and state.balance == 0.0}
        if not absent:
            return states
        blocked = {
            state.key
            for state in states  # bounded by registered bindings
            if any(
                edge.kind == "transforms" and edge.source in absent
                for edge in coupling_graph.upstream_for(state.key)
            )
        }
        if principal.key not in blocked:
            return states

        rate_weight = float(services.defines.tension.principal_rate_weight)
        eligible = sorted(
            (state for state in states if state.key not in blocked and state.key not in absent),
            key=lambda state: (-self._score(state, rate_weight), state.key),
        )
        if not eligible:
            return states
        successor_key = eligible[0].key
        return tuple(
            state.model_copy(update={"is_principal": state.key == successor_key})
            for state in states
        )

    @staticmethod
    def _read_previous(graph: GraphProtocol) -> dict[str, OppositionState]:
        """Reconstruct last tick's states from BOTH opposition attrs.

        Shadow states (ADR077) live on ``shadow_opposition_states`` but need
        the same rate/inertia continuity as canonical ones; registry keys are
        unique, so the merge cannot collide.
        """
        raw: dict[str, Any] = {
            **(graph.get_graph_attr(OPPOSITION_STATES_ATTR, {}) or {}),
            **(graph.get_graph_attr(SHADOW_OPPOSITION_STATES_ATTR, {}) or {}),
        }
        return {key: OppositionState(**value) for key, value in raw.items()}

    def _build_graph_inputs(self, graph: GraphProtocol, services: ServicesProtocol) -> GraphInputs:
        """Pre-extract the per-tick views the catalog measures read.

        The ``*_id_pairs`` twins (ADR070) are built in the SAME loops as the
        float pairs — identical skip rules, zero extra graph traversal —
        feeding the per-node pole measures. The market Balance (Program 23)
        is derived here from the fresh ``market`` axis (@17.8 runs first)
        because the tanh scale is a define and the catalog stays defines-free.
        The national Balance (task #42-C) is derived the same way from the
        FACTION/INFLUENCES political-topology layer (spec-070), though here
        no coefficient is owned at all — the weighting is a plain ratio.
        """
        exploitation: list[tuple[float, float]] = []
        exploitation_ids: list[tuple[str, str, float, float]] = []
        for edge in graph.query_edges(edge_type=EdgeType.EXPLOITATION):
            pair = self._edge_wealths(graph, edge.source_id, edge.target_id)
            if pair is not None:  # (labor=source=A, capital=target=B)
                exploitation.append(pair)
                exploitation_ids.append((edge.source_id, edge.target_id, *pair))

        tenancy: list[tuple[float, float]] = []
        tenancy_ids: list[tuple[str, str, float, float]] = []
        for edge in graph.query_edges(edge_type=EdgeType.TENANCY):
            src = graph.get_node(edge.source_id)
            tgt = graph.get_node(edge.target_id)
            if src is None or tgt is None:
                continue
            pair = (
                float(src.attributes.get("wealth", 0.0)),
                float(tgt.attributes.get("rent_level", 0.0)),
            )
            tenancy.append(pair)
            tenancy_ids.append((edge.source_id, edge.target_id, *pair))

        # Phase D4: one (w_paid, v_produced) pair per paid worker class node.
        # Only the wages phase writes both attrs (on classes it actually paid),
        # so presence-of-both selects exactly those nodes without a node-type
        # filter; skip inactive nodes as the edge extractors do.
        wage_value: list[tuple[float, float]] = []
        wage_value_ids: list[tuple[str, float, float]] = []
        for node in graph.query_nodes():
            attrs = node.attributes
            if not attrs.get("active", True):
                continue
            if "w_paid" not in attrs or "v_produced" not in attrs:
                continue
            wage_value.append((float(attrs["w_paid"]), float(attrs["v_produced"])))
            wage_value_ids.append((node.id, float(attrs["w_paid"]), float(attrs["v_produced"])))

        market_balance: float | None = None
        market_raw = graph.get_graph_attr("market", None)
        if isinstance(market_raw, dict) and "price_log" in market_raw:
            market_balance = calculate_scissors_balance(
                float(market_raw["price_log"]),
                scale=float(services.defines.market.scissors_balance_scale),
            )

        rentier_share, debt_ratio = self._county_money_ratios(
            graph, float(services.defines.capital_vol3.debt_spiral_threshold)
        )

        financialization_index: float | None = None
        if isinstance(market_raw, dict) and "fictitious_log" in market_raw:
            # The fictitious axis IS a log-ratio around the value anchor, so
            # exp() returns it as the fictitious/real ratio directly — one
            # axis, calibrated to FictitiousCapitalStock.ratio_to_real by the
            # monetary anchor while real data exists, endogenous after 2024.
            # The axis's own bound is the overflow clamp: a log outside it is
            # corrupt input, and raising OverflowError mid-tick helps nobody.
            bound = float(services.defines.market.max_abs_log)
            clamped = max(-bound, min(bound, float(market_raw["fictitious_log"])))
            financialization_index = math.exp(clamped)

        return GraphInputs(
            exploitation_pairs=tuple(exploitation),
            wage_value_pairs=tuple(wage_value),
            tenancy_pairs=tuple(tenancy),
            solidarity_subgraph=extract_solidarity_subgraph(graph),
            exploitation_id_pairs=tuple(exploitation_ids),
            wage_value_id_pairs=tuple(wage_value_ids),
            tenancy_id_pairs=tuple(tenancy_ids),
            market_balance=market_balance,
            national_balance=self._national_chauvinism_balance(graph),
            rentier_share=rentier_share,
            debt_ratio=debt_ratio,
            credit_fragility=self._credit_fragility(
                graph, float(services.defines.capital_vol3.credit_fragility_scale)
            ),
            financialization_index=financialization_index,
        )

    @staticmethod
    def _national_chauvinism_balance(graph: GraphProtocol) -> float | None:
        """National-axis Balance (task #42-C): colonial_stance, INFLUENCES-weighted.

        Each ``BalkanizationFaction`` (spec-070 FR-005) positions itself on
        the national-chauvinism<->internationalism axis via its
        ``colonial_stance`` (FR-002); its material weight is the total
        INFLUENCES ``influence_level`` (FR-014/FR-015) it holds across every
        Territory it reaches — a faction with no territorial reach carries no
        weight, the same "wealth engaged in the relationship" convention
        ``_mean_asymmetry`` uses (unweighted means of an intensive quantity
        across differently-sized material bases is the named
        intensive-aggregation error class). A RATIO OF SUMS
        (``Σ influence*score / Σ influence``), never a mean of per-faction
        ratios.

        Returns:
            ``None`` when no FACTION node carries both a recognized
            ``colonial_stance`` and positive summed influence — absent, not a
            fabricated neutral (Constitution III.11). This is the permanent,
            by-construction reading in all 5 canonical scenarios, which
            construct no BalkanizationFaction/INFLUENCES edge at all.
            Otherwise ``1.0 - 2.0 * weighted_mean_score`` so a positive
            reading is internationalism (pole B) dominant, matching the
            ``market_balance``/``_price_value_measure`` sign convention.
        """
        influence_by_faction: dict[str, float] = {}
        for edge in graph.query_edges(edge_type=EdgeType.INFLUENCES):
            level = float(edge.attributes.get("influence_level", 0.0))
            if level <= 0.0:
                continue
            influence_by_faction[edge.source_id] = (
                influence_by_faction.get(edge.source_id, 0.0) + level
            )

        weighted_score = 0.0
        weight_total = 0.0
        for node in graph.query_nodes(node_type=NodeType.FACTION):
            weight = influence_by_faction.get(node.id, 0.0)
            if weight <= 0.0:
                continue
            stance_raw = node.attributes.get("colonial_stance")
            if not isinstance(stance_raw, str):
                continue
            try:
                stance = ColonialStance(stance_raw)
            except ValueError:
                continue
            weighted_score += weight * _STANCE_CHAUVINISM_SCORE[stance]
            weight_total += weight

        if weight_total <= 0.0:
            return None
        return 1.0 - 2.0 * (weighted_score / weight_total)

    @staticmethod
    def _county_money_ratios(
        graph: GraphProtocol, debt_spiral_threshold: float
    ) -> tuple[float | None, float | None]:
        """``(rentier_share, debt_ratio)`` aggregated over the county layer.

        Both are RATIOS OF SUMS — ``Σclaims / Σsurplus`` and
        ``Σdebt / Σsurplus`` — never means of per-county ratios. That
        distinction is the named *intensive-aggregation* error class: an
        unweighted mean of an intensive across space lets a county producing
        one dollar of surplus swing the national reading exactly as hard as
        Wayne.

        Counties are visited in sorted FIPS order so the float summation
        order is fixed (Constitution III.7).

        Args:
            graph: The live graph.
            debt_spiral_threshold: ``defines.capital_vol3.debt_spiral_threshold``
                (in ``[0, 1]`` by schema). Scales the raw debt/surplus ratio
                so 1.0 means "exactly at the debt spiral".

        Returns:
            ``(None, None)`` when no county carries a
            :class:`SurplusValueDistribution`, or when the summed surplus is
            not positive — a ratio with no denominator is absent, not zero
            and not infinite (Constitution III.11). ``debt_ratio`` is
            ``None`` on its own when distributions exist but no county
            carries a :class:`DebtAccumulation`.
        """
        tick_data = graph.get_graph_attr(TICK_DYNAMICS_KEY, None)
        if not isinstance(tick_data, dict):
            return (None, None)
        county_states = tick_data.get("county_states")
        if not isinstance(county_states, dict):
            return (None, None)

        total_surplus = 0.0
        total_claims = 0.0
        total_debt = 0.0
        saw_distribution = False
        saw_debt = False
        for fips in sorted(county_states):  # bounded by the county layer
            county = county_states[fips]
            distribution = getattr(county, "surplus_distribution", None)
            if isinstance(distribution, SurplusValueDistribution):
                saw_distribution = True
                total_surplus += distribution.total_surplus_produced
                total_claims += (
                    distribution.interest_payments
                    + distribution.ground_rent
                    + distribution.taxes_on_surplus
                )
            debt = getattr(county, "debt_accumulation", None)
            if isinstance(debt, DebtAccumulation):
                saw_debt = True
                total_debt += debt.accumulated_debt

        if not saw_distribution or total_surplus <= 0.0:
            return (None, None)
        # DEBT_SPIRAL_THRESHOLD (§3.6 row 10) was a dead constant designed as a
        # crisis signal. Dividing here — not in the defines-free catalog — makes
        # 1.0 mean "exactly at the debt spiral", so _ratio_reading's balance
        # crosses zero AT the threshold rather than at an arbitrary debt/surplus
        # parity nobody argued for.
        debt_ratio = (total_debt / total_surplus) / debt_spiral_threshold if saw_debt else None
        return (total_claims / total_surplus, debt_ratio)

    @staticmethod
    def _credit_fragility(graph: GraphProtocol, scale: float) -> float | None:
        """National ``default_rate * spread``, divided by its crisis reference.

        Read from the published :data:`NATIONAL_FINANCIAL_ATTR` dump, whose
        ``credit_state`` block carries ``credit_fragility`` as a Pydantic
        computed field. Dividing here (not in the catalog) keeps the catalog
        defines-free — the same division of labour ``market_balance`` uses
        for its ``tanh`` scale — and makes 1.0 mean "exactly at the crisis
        threshold" for the shared ratio map.

        Args:
            graph: The live graph.
            scale: ``defines.capital_vol3.credit_fragility_scale`` (> 0 by schema).

        Returns:
            The scaled fragility, or ``None`` when no national financial
            state, no credit state, or no numeric fragility is published.
        """
        raw = graph.get_graph_attr(NATIONAL_FINANCIAL_ATTR, None)
        if not isinstance(raw, dict):
            return None
        credit_state = raw.get("credit_state")
        if not isinstance(credit_state, dict):
            return None
        fragility = credit_state.get("credit_fragility")
        if not isinstance(fragility, (int, float)) or isinstance(fragility, bool):
            return None
        return float(fragility) / scale

    @staticmethod
    def _edge_wealths(
        graph: GraphProtocol, source_id: str, target_id: str
    ) -> tuple[float, float] | None:
        """(source_wealth, target_wealth), skipping inactive endpoints."""
        src = graph.get_node(source_id)
        tgt = graph.get_node(target_id)
        if src is None or tgt is None:
            return None
        if not src.attributes.get("active", True) or not tgt.attributes.get("active", True):
            return None
        return (
            float(src.attributes.get("wealth", 0.0)),
            float(tgt.attributes.get("wealth", 0.0)),
        )

    # ------------------------------------------------------------------
    # 2b. Per-node pole channel — the shadow partition (Program 19, ADR070)
    # ------------------------------------------------------------------

    def _step_pole_channel(
        self,
        graph: GraphProtocol,
        registry: OppositionRegistry[GraphInputs],
        inputs: GraphInputs,
    ) -> None:
        """Derive, stash, and shadow-write the per-node pole channel.

        Phase 1 is SHADOW ONLY: nothing in the pipeline adjudicates on these
        attrs — they exist so the seeded-vs-derived disagreement becomes
        measurable (the partition sentinel reads them). Reuses the tick's
        ``inputs`` snapshot (no second graph traversal); last tick's readings
        come from :data:`POLE_READINGS_ATTR` for the σ=0 tie inertia.
        """
        previous = self._read_previous_poles(graph)
        readings = registry.read_poles(inputs, previous)
        self._write_pole_shadow(graph, readings, previous)
        stash: dict[str, dict[str, dict[str, Any]]] = {}
        for reading in readings:
            stash.setdefault(reading.opposition_key, {})[reading.entity_id] = reading.model_dump()
        graph.set_graph_attr(POLE_READINGS_ATTR, stash)

    @staticmethod
    def _read_previous_poles(graph: GraphProtocol) -> dict[tuple[str, str], PoleReading]:
        """Reconstruct last tick's readings from :data:`POLE_READINGS_ATTR`."""
        raw: dict[str, dict[str, dict[str, Any]]] = (
            graph.get_graph_attr(POLE_READINGS_ATTR, {}) or {}
        )
        return {
            (key, entity_id): PoleReading(**dump)
            for key, per_entity in raw.items()
            for entity_id, dump in per_entity.items()
        }

    @staticmethod
    def _write_pole_shadow(
        graph: GraphProtocol,
        readings: tuple[PoleReading, ...],
        previous: dict[tuple[str, str], PoleReading],
    ) -> None:
        """Write ``sigma_*`` per positioned node; the cell needs BOTH axes.

        A node with no participation on an axis is left untouched — absence
        over fabrication (Constitution III.11). A node that LOSES an axis it
        held last tick gets an honest ``None`` (never a stale sigma), and
        loses its cell the same way. Node ids are iterated sorted (the
        readings are already sorted; the union with previously-written ids
        re-sorts defensively).
        """
        current: dict[str, dict[str, PoleReading]] = {}
        for reading in readings:
            if reading.opposition_key in _SIGMA_NODE_ATTRS:
                current.setdefault(reading.entity_id, {})[reading.opposition_key] = reading

        previously_written = {entity_id for key, entity_id in previous if key in _SIGMA_NODE_ATTRS}

        for entity_id in sorted(current.keys() | previously_written):
            if graph.get_node(entity_id) is None:
                continue
            axes = current.get(entity_id, {})
            updates: dict[str, Any] = {}
            for key, attr in _SIGMA_NODE_ATTRS.items():
                axis_reading = axes.get(key)
                if axis_reading is not None:
                    updates[attr] = axis_reading.sigma
                elif (key, entity_id) in previous:
                    updates[attr] = None  # de-positioned: honest null, not stale
            had_cell = ("capital_labor", entity_id) in previous and (
                "wage",
                entity_id,
            ) in previous
            cell = cell_name({key: reading.side for key, reading in axes.items()})
            if cell is not None:
                updates["derived_class_cell"] = cell
            elif had_cell:
                updates["derived_class_cell"] = None
            if updates:
                graph.update_node(entity_id, **updates)

    def _write_frames(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        registry: OppositionRegistry[GraphInputs],
        states: tuple[OppositionState, ...],
    ) -> None:
        """Derive the single ``global`` frame from principal + runner-up."""
        rate_weight = float(services.defines.tension.principal_rate_weight)
        principal_state = next((s for s in states if s.is_principal), states[0])
        ranked = sorted(
            (s for s in states if s.key != principal_state.key),
            key=lambda s: (-self._score(s, rate_weight), s.key),
        )
        secondary_state = ranked[0] if ranked else principal_state
        frame = ContradictionFrame(
            principal=self._contradiction(principal_state, registry.spec_for(principal_state.key)),
            secondary=self._contradiction(secondary_state, registry.spec_for(secondary_state.key)),
        )
        graph.set_graph_attr("contradiction_frames", {"global": frame.model_dump()})

    @staticmethod
    def _score(state: OppositionState, rate_weight: float) -> float:
        """Registry's principal score: gap * (1 + rate_weight * |rate|)."""
        return state.gap * (1.0 + rate_weight * abs(state.rate))

    @staticmethod
    def _contradiction(state: OppositionState, spec: OppositionSpec) -> Contradiction:
        """Map an :class:`OppositionState` onto the existing Contradiction model."""
        ctype = ContradictionType.IMPERIAL if spec.key == "imperial" else ContradictionType.CLASS
        return Contradiction(
            id=spec.key,
            type=ctype,
            aspect_a=spec.pole_a,
            aspect_b=spec.pole_b,
            principal_aspect=state.leading_pole,
            identity=0.5,
            intensity=state.gap,
            aspect_balance=state.rate,
            form_of_struggle=EdgeMode.EXTRACTIVE,
            is_antagonistic=spec.antagonistic,
        )

    def _maybe_rupture(
        self,
        services: ServicesProtocol,
        states: tuple[OppositionState, ...],
        tick: int,
    ) -> None:
        """Fire RUPTURE iff the principal gap exceeds threshold AND is rising."""
        threshold = float(services.defines.tension.rupture_gap_threshold)
        principal = next((s for s in states if s.is_principal), None)
        if principal is None:
            return
        if principal.gap > threshold and principal.rate > 0.0:
            services.event_bus.publish(
                Event(
                    type=EventType.RUPTURE,
                    tick=tick,
                    payload={
                        "opposition": principal.key,
                        "gap": principal.gap,
                        "rate": principal.rate,
                    },
                )
            )

    # ------------------------------------------------------------------
    # 3. Fixed-point regime classification (Phase E2, §9.4)
    # ------------------------------------------------------------------

    def _classify_regime(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        registry: OppositionRegistry[GraphInputs],
        states: tuple[OppositionState, ...],
        tick: int,
    ) -> None:
        """Classify the tick's regime and publish LEVEL_TRANSITION on sublation.

        Rupture (fired by :meth:`_maybe_rupture`) is the crisis regime's boiling
        point; this classifies the CAPITAL_LABOR opposition — the canonical
        spatial antagonism whose per-county field E2 builds — as reproduction,
        crisis, or sublation, stashes it on the ``dialectical_regime`` graph
        attribute, and (only on the sublation branch) publishes
        :data:`EventType.LEVEL_TRANSITION` (the production Aufhebung signal; the
        TopologyMonitor has no runner call site).

        Note (field-vs-principal resolution, flagged for review): the design's
        E2 both "classifies the principal" AND "builds the per-county
        capital_labor field". Those agree only when capital_labor IS principal;
        in a real world a large STATIC gap (e.g. atomization = 1.0 in a
        disconnected county) can hold the Maoist principal slot while
        capital_labor is the one actually DEVELOPING. The field and the rate
        must describe the SAME opposition, so we classify capital_labor (falling
        back to the principal only if capital_labor is absent).
        """
        target = next((state for state in states if state.key == "capital_labor"), None)
        if target is None:
            target = next((state for state in states if state.is_principal), None)
        if target is None:
            return

        field = self._capital_labor_field(graph)
        counties = sorted(field)
        lattice = spatial_lattice_for_counties(counties) if counties else None
        level_index = level_index_for(registry.spec_for(target.key).level_name)
        if level_index is None or level_index < _COUNTY_LEVEL_INDEX:
            level_index = _COUNTY_LEVEL_INDEX  # the capital_labor field's own level
        rate_epsilon = float(services.defines.tension.regime_rate_epsilon)

        # classify_regime reads the is_principal state's rate; hand it the target
        # marked principal so the field and the rate name the SAME opposition.
        probe_states = (target.model_copy(update={"is_principal": True}),)
        regime = classify_regime(
            probe_states, lattice, field, level_index, rate_epsilon=rate_epsilon
        )
        graph.set_graph_attr(
            DIALECTICAL_REGIME_ATTR,
            {"regime": regime, "opposition": target.key, "rate": target.rate},
        )

        if regime == "sublation" and lattice is not None:
            to_level = lattice.aufhebung_of(level_index, [field])
            if to_level is not None:
                services.event_bus.publish(
                    Event(
                        type=EventType.LEVEL_TRANSITION,
                        tick=tick,
                        payload={
                            "opposition": target.key,
                            "from_level": registry.spec_for(target.key).level_name,
                            "to_level": to_level.name,
                            "gap": target.gap,
                            "rate": target.rate,
                        },
                    )
                )

    @staticmethod
    def _capital_labor_field(graph: GraphProtocol) -> dict[str, float]:
        """Per-county mean EXPLOITATION-edge ``tension`` (the capital_labor field).

        Keyed by the labor (source) node's ``county_fips``; the same per-county
        extraction the C1.6 bridged test reads. Edges whose source lacks a
        county or whose tension is unset are skipped. Empty when no county data
        (single-county in-memory tests) — the caller then classifies rate-only.
        """
        by_county: dict[str, list[float]] = {}
        for edge in graph.query_edges(edge_type=EdgeType.EXPLOITATION):
            src = graph.get_node(edge.source_id)
            if src is None:
                continue
            county = src.attributes.get("county_fips")
            tension = edge.attributes.get("tension")
            if county is None or not isinstance(tension, (int, float)):
                continue
            by_county.setdefault(str(county), []).append(float(tension))
        return {county: sum(values) / len(values) for county, values in by_county.items()}
