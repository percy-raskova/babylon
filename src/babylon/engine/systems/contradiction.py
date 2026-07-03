"""Contradiction system — Lawverian opposition registry (Phase C1.3).

Position 18 in the pipeline. This is the rewrite that retires the saturating,
add-only edge-``tension`` accumulator (the "Formula" + "Consumption" inertness
bugs of ``project/06-lawverian-dialectics.md`` §2). Each tick the system:

1. writes per-edge ``tension`` as the *fresh* wealth-asymmetry gap of that edge
   (EXPLOITATION / WAGES / TENANCY) — scale-free, recomputed from current
   wealth, never accumulated;
2. steps the :class:`~babylon.dialectics.core.opposition.OppositionRegistry`
   (wired by :meth:`ServiceContainer.create`) over a :class:`GraphInputs`
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

from babylon.dialectics.core.coupling import StanceIntervention, apply_interventions
from babylon.dialectics.core.opposition import OppositionState
from babylon.dialectics.instances.catalog import GraphInputs
from babylon.engine.event_bus import Event
from babylon.engine.systems.base import SystemBase
from babylon.engine.systems.protocol import ContextType
from babylon.engine.topology_monitor import extract_solidarity_subgraph
from babylon.formulas.contradiction import calculate_wealth_asymmetry_gap
from babylon.models.entities.contradiction import Contradiction, ContradictionFrame
from babylon.models.enums import ContradictionType, EdgeMode, EdgeType, EventType

if TYPE_CHECKING:
    import networkx as nx

    from babylon.dialectics.core.opposition import OppositionRegistry, OppositionSpec
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer

#: Graph attribute holding ``{key: OppositionState.model_dump()}`` for the tick.
OPPOSITION_STATES_ATTR = "opposition_states"

#: Graph attribute holding a list of ``StanceIntervention`` dumps to apply this
#: tick. Written by verb/OODA systems (spec-071), read + CLEARED here
#: (consumed-once). No producer writes it yet; unit tests set it directly.
OPPOSITION_INTERVENTIONS_ATTR = "opposition_interventions"

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
        graph: nx.DiGraph[str] | GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        """Write fresh per-edge tension, then step the opposition registry."""
        from babylon.engine.graph_protocol import GraphProtocol

        if not isinstance(graph, GraphProtocol):
            from babylon.engine.adapters.inmemory_adapter import NetworkXAdapter

            graph = NetworkXAdapter.wrap(graph)

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
        services: ServiceContainer,
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
        graph.set_graph_attr(
            OPPOSITION_STATES_ATTR, {state.key: state.model_dump() for state in states}
        )

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
        """Pre-extract the per-tick views the catalog measures read."""
        exploitation: list[tuple[float, float]] = []
        for edge in graph.query_edges(edge_type=EdgeType.EXPLOITATION):
            pair = self._edge_wealths(graph, edge.source_id, edge.target_id)
            if pair is not None:  # (labor=source=A, capital=target=B)
                exploitation.append(pair)

        tenancy: list[tuple[float, float]] = []
        for edge in graph.query_edges(edge_type=EdgeType.TENANCY):
            src = graph.get_node(edge.source_id)
            tgt = graph.get_node(edge.target_id)
            if src is None or tgt is None:
                continue
            tenancy.append(
                (
                    float(src.attributes.get("wealth", 0.0)),
                    float(tgt.attributes.get("rent_level", 0.0)),
                )
            )

        # Phase D4: one (w_paid, v_produced) pair per paid worker class node.
        # Only the wages phase writes both attrs (on classes it actually paid),
        # so presence-of-both selects exactly those nodes without a node-type
        # filter; skip inactive nodes as the edge extractors do.
        wage_value: list[tuple[float, float]] = []
        for node in graph.query_nodes():
            attrs = node.attributes
            if not attrs.get("active", True):
                continue
            if "w_paid" not in attrs or "v_produced" not in attrs:
                continue
            wage_value.append((float(attrs["w_paid"]), float(attrs["v_produced"])))

        return GraphInputs(
            exploitation_pairs=tuple(exploitation),
            wage_value_pairs=tuple(wage_value),
            tenancy_pairs=tuple(tenancy),
            solidarity_subgraph=extract_solidarity_subgraph(graph),
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

    def _write_frames(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
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
        services: ServiceContainer,
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
