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

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.domain.dialectics.core.coupling import StanceIntervention, apply_interventions
from babylon.domain.dialectics.core.opposition import OppositionState, PoleReading
from babylon.domain.dialectics.core.regime import classify_regime
from babylon.domain.dialectics.instances.catalog import GraphInputs
from babylon.domain.dialectics.instances.levels import level_index_for, spatial_lattice_for_counties
from babylon.engine.topology_monitor import extract_solidarity_subgraph
from babylon.formulas.contradiction import calculate_wealth_asymmetry_gap
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import ContextType
from babylon.models.entities.contradiction import Contradiction, ContradictionFrame
from babylon.models.enums import ContradictionType, EdgeMode, EdgeType, EventType
from babylon.sentinels.partition.registry import cell_name

if TYPE_CHECKING:
    from babylon.domain.dialectics.core.opposition import OppositionRegistry, OppositionSpec
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

#: Graph attribute holding ``{key: OppositionState.model_dump()}`` for the tick.
OPPOSITION_STATES_ATTR = "opposition_states"

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


class ContradictionSystem(SystemBase):
    """Phase 18: fresh-gap tension + opposition-registry contradiction frames."""

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
        inputs = self._build_graph_inputs(graph)
        states = registry.step(inputs, tick, previous)
        if not states:
            return

        # Player-verb stances are signed shoves on balances (spec-071 writes
        # them; consumed-once here). Applied AFTER the measure so a stance can
        # flip a leading pole, BEFORE frames/rupture/stash so downstream sees it.
        states = self._apply_interventions(graph, states)

        self._write_frames(graph, services, registry, states)
        self._maybe_rupture(services, states, tick)
        self._classify_regime(graph, services, registry, states, tick)
        graph.set_graph_attr(
            OPPOSITION_STATES_ATTR, {state.key: state.model_dump() for state in states}
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

    @staticmethod
    def _read_previous(graph: GraphProtocol) -> dict[str, OppositionState]:
        """Reconstruct last tick's states from the ``opposition_states`` attr."""
        raw: dict[str, Any] = graph.get_graph_attr(OPPOSITION_STATES_ATTR, {}) or {}
        return {key: OppositionState(**value) for key, value in raw.items()}

    def _build_graph_inputs(self, graph: GraphProtocol) -> GraphInputs:
        """Pre-extract the per-tick views the catalog measures read.

        The ``*_id_pairs`` twins (ADR070) are built in the SAME loops as the
        float pairs — identical skip rules, zero extra graph traversal —
        feeding the per-node pole measures.
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

        return GraphInputs(
            exploitation_pairs=tuple(exploitation),
            wage_value_pairs=tuple(wage_value),
            tenancy_pairs=tuple(tenancy),
            solidarity_subgraph=extract_solidarity_subgraph(graph),
            exploitation_id_pairs=tuple(exploitation_ids),
            wage_value_id_pairs=tuple(wage_value_ids),
            tenancy_id_pairs=tuple(tenancy_ids),
        )

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
