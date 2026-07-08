"""FascistFactionSystem — the reactionary subject (spec-071).

Pipeline position ~17.4: after ConsciousnessSystem (17, which writes this
tick's agitation) and BEFORE SovereigntySystem (17.5) / ContradictionSystem
(18, which consumes the StanceIntervention this system writes). Belongs to
``CONSEQUENCE_SYSTEMS`` (spec-056 partition).

The fascism branch of the George Jackson bifurcation (Constitution I.4): when
the imperial bribe (Φ) decays, crisis agitation on the entitled strata (labor
aristocracy C_la, petty/comprador bourgeoisie C_pb) — in the ABSENCE of
solidarity — routes to fascism. Each tick:

1. For each active C_la / C_pb node: compute
   ``Fascist_Pull = Agitation × (Entitlement / (Solidarity + ε))``. Above the
   threshold, bump ``fascist_alignment`` (FASCIST_DRIFT) and push a signed
   :class:`StanceIntervention` onto ``opposition_interventions`` (the ADR051
   hook — the reactionary pull moves the live opposition registry, not a
   private counter). At ``fascist_alignment >= threshold`` with a fascist
   faction present, capture the node (FASCIST_RECRUITMENT).
2. Accumulate ``chauvinism`` on org->LA MEMBERSHIP edges and, on this tick's
   crisis events, roll defection -> ORGANIZATIONAL_FRACTURE / RED_BROWN_COUP
   (spec-071 US2).

Reads the ``dialectical_regime`` graph attribute (FR-009 — never recomputes
regime classification). NOTE the one-tick lag: ContradictionSystem @18 writes
``dialectical_regime`` AFTER this system @17.4, so on tick N this reads tick
N-1's regime (empty on tick 1). It is surfaced in the FASCIST_DRIFT event
payload as observability only — the regime NEVER gates dynamics (the crisis
gate is agitation, computed same-tick by ConsciousnessSystem @17), so the
one-tick staleness is immaterial. Determinism (III.7): sorted iteration + the
seed RNG (:func:`babylon.engine.systems.base.resolve_rng`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from babylon.dialectics.core.coupling import StanceIntervention
from babylon.engine.event_bus import Event
from babylon.engine.systems.base import SystemBase, resolve_rng
from babylon.formulas.reactionary import (
    calculate_defection_probability,
    calculate_fascist_pull,
)
from babylon.models.enums import EdgeType, EventType, SocialRole

if TYPE_CHECKING:  # pragma: no cover
    from babylon.engine.graph_protocol import GraphProtocol
    from babylon.engine.services import ServiceContainer
    from babylon.engine.systems.protocol import ContextType

#: Roles that carry an entitlement stake and can drift fascist.
_ENTITLED_ROLES: frozenset[SocialRole] = frozenset(
    {SocialRole.LABOR_ARISTOCRACY, SocialRole.COMPRADOR_BOURGEOISIE}
)

#: The opposition whose balance a reactionary pull shoves (toward capital=pole b).
_CAPITAL_LABOR_KEY = "capital_labor"

#: Crisis event types that trigger LA defection rolls this tick.
_CRISIS_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EventType.ECONOMIC_CRISIS.value,
        EventType.SUPERWAGE_CRISIS.value,
        EventType.CRISIS_PHASE_TRANSITION.value,
    }
)

#: Ideology tokens marking a BalkanizationFaction as fascist (D2 fallback).
_FASCIST_IDEOLOGY_TOKENS: tuple[str, ...] = ("fascist", "reaction", "revanch", "settler")


class FascistFactionSystem(SystemBase):
    """Consequence-phase system for the reactionary subject (spec-071)."""

    name: ClassVar[str] = "Fascist Faction"
    # Chauvinism/defection mutate org + edge state, not hex c+v+s (Spec 053 INV-001).
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        context: ContextType,
    ) -> None:
        wrapped = self._wrap_graph(graph)
        tick = _extract_tick(context)
        defines = services.defines.reactionary
        regime = self._read_regime(wrapped)

        fascist_faction_id = self._find_fascist_faction(wrapped)
        opposition_known = _CAPITAL_LABOR_KEY in (
            wrapped.get_graph_attr("opposition_states", {}) or {}
        )

        self._process_drift(
            wrapped, services, tick, defines, regime, fascist_faction_id, opposition_known
        )
        self._process_org_defections(wrapped, services, tick, defines)

    # ------------------------------------------------------------------
    # 1. Fascist pull -> drift -> capture (+ stance intervention)
    # ------------------------------------------------------------------

    def _process_drift(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        tick: int,
        defines: Any,
        regime: str | None,
        fascist_faction_id: str | None,
        opposition_known: bool,
    ) -> None:
        for node in sorted(graph.query_nodes(node_type="social_class"), key=lambda n: n.id):
            attrs = node.attributes
            if not attrs.get("active", True):
                continue
            role = _coerce_role(attrs.get("role"))
            if role not in _ENTITLED_ROLES:
                continue

            agitation = _agitation_of(attrs)
            entitlement = float(attrs.get("entitlement", 0.0))
            solidarity = self._incident_solidarity(graph, node.id)
            pull = calculate_fascist_pull(
                agitation=agitation,
                entitlement=entitlement,
                solidarity=solidarity,
                epsilon=defines.solidarity_pull_epsilon,
            )

            alignment = float(attrs.get("fascist_alignment", 0.0))
            if pull > defines.fascist_pull_threshold:
                alignment = min(1.0, alignment + defines.fascist_drift_step)
                graph.update_node(node.id, fascist_alignment=alignment)
                self._publish(
                    services,
                    Event(
                        type=EventType.FASCIST_DRIFT,
                        tick=tick,
                        payload={
                            "node_id": node.id,
                            "fascist_pull": pull,
                            "fascist_alignment": alignment,
                            "entitlement": entitlement,
                            "solidarity": solidarity,
                            "regime": regime,
                        },
                    ),
                )
                if opposition_known:
                    self._write_stance_intervention(graph, node.id, pull, defines)

            # Capture: quantity -> quality at the recruitment threshold (I.7).
            if (
                alignment >= defines.fascist_recruitment_threshold
                and fascist_faction_id is not None
                and attrs.get("aligned_faction_id") is None
            ):
                graph.update_node(node.id, aligned_faction_id=fascist_faction_id)
                self._publish(
                    services,
                    Event(
                        type=EventType.FASCIST_RECRUITMENT,
                        tick=tick,
                        payload={
                            "node_id": node.id,
                            "faction_id": fascist_faction_id,
                            "fascist_alignment": alignment,
                        },
                    ),
                )

    def _write_stance_intervention(
        self, graph: GraphProtocol, node_id: str, pull: float, defines: Any
    ) -> None:
        """Append a signed shove on the capital_labor balance (ADR051 hook)."""
        magnitude = min(pull, defines.stance_intervention_cap) * defines.stance_intervention_gain
        intervention = StanceIntervention(
            target_key=_CAPITAL_LABOR_KEY,
            delta_balance=magnitude,  # positive -> toward capital (reactionary) pole b
            source=f"system:fascist_faction:{node_id}",
        )
        existing = list(graph.get_graph_attr("opposition_interventions", []) or [])
        existing.append(intervention.model_dump())
        graph.set_graph_attr("opposition_interventions", existing)

    @staticmethod
    def _incident_solidarity(graph: GraphProtocol, node_id: str) -> float:
        """Strongest incident SOLIDARITY edge strength (the bridge that dampens reaction)."""
        best = 0.0
        for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
            if edge.target_id != node_id and edge.source_id != node_id:
                continue
            best = max(best, float(edge.attributes.get("solidarity_strength", 0.0)))
        return best

    @staticmethod
    def _read_regime(graph: GraphProtocol) -> str | None:
        """Read (never recompute) the ContradictionSystem regime classification.

        Stale-by-one-tick: @18 writes it after this @17.4 system, so this
        returns last tick's regime (None on tick 1). Observability-only — it
        annotates the FASCIST_DRIFT payload and never gates drift.
        """
        raw = graph.get_graph_attr("dialectical_regime", {}) or {}
        regime = raw.get("regime") if isinstance(raw, dict) else None
        return str(regime) if isinstance(regime, str) else None

    def _find_fascist_faction(self, graph: GraphProtocol) -> str | None:
        """Lowest-id BalkanizationFaction that is fascist (D2 predicate)."""
        candidates: list[str] = []
        for node in graph.query_nodes(node_type="balkanization_faction"):
            attrs = node.attributes
            settler_uphold = bool(attrs.get("is_settler_formation")) and (
                str(attrs.get("colonial_stance", "")).lower() == "uphold"
            )
            ideology = str(attrs.get("ideology", "")).lower()
            token_match = any(tok in ideology for tok in _FASCIST_IDEOLOGY_TOKENS)
            if settler_uphold or token_match:
                candidates.append(node.id)
        return min(candidates) if candidates else None

    # ------------------------------------------------------------------
    # 2. Chauvinism accrual + crisis defection (spec-071 US2)
    # ------------------------------------------------------------------

    def _process_org_defections(
        self,
        graph: GraphProtocol,
        services: ServiceContainer,
        tick: int,
        defines: Any,
    ) -> None:
        crisis_now = self._crisis_this_tick(services, tick)
        rng = resolve_rng(services, tick)

        # Group MEMBERSHIP edges (org -> LA class node) by org, deterministically.
        members_by_org: dict[str, list[Any]] = {}
        for edge in graph.query_edges(edge_type=EdgeType.MEMBERSHIP):
            target = graph.get_node(edge.target_id)
            if target is None:
                continue
            if _coerce_role(target.attributes.get("role")) is not SocialRole.LABOR_ARISTOCRACY:
                continue
            members_by_org.setdefault(edge.source_id, []).append(edge)

        for org_id in sorted(members_by_org):
            edges = sorted(members_by_org[org_id], key=lambda e: e.target_id)
            defections = 0
            for edge in edges:
                chauvinism = self._accrue_chauvinism(graph, edge, defines)
                if not crisis_now:
                    continue
                discipline = self._org_discipline(graph, org_id, defines)
                p_defect = calculate_defection_probability(
                    chauvinism=chauvinism, discipline=discipline
                )
                if rng.random() < p_defect:
                    defections += 1
                    self._publish(
                        services,
                        Event(
                            type=EventType.ORGANIZATIONAL_FRACTURE,
                            tick=tick,
                            payload={
                                "org_id": org_id,
                                "member_id": edge.target_id,
                                "chauvinism": chauvinism,
                                "defection_probability": p_defect,
                            },
                        ),
                    )
            if crisis_now and edges and defections > defines.red_brown_coup_fraction * len(edges):
                self._publish(
                    services,
                    Event(
                        type=EventType.RED_BROWN_COUP,
                        tick=tick,
                        payload={
                            "org_id": org_id,
                            "defections": defections,
                            "member_count": len(edges),
                        },
                    ),
                )

    def _accrue_chauvinism(self, graph: GraphProtocol, edge: Any, defines: Any) -> float:
        """Bump the MEMBERSHIP edge's chauvinism (base + super-wage bonus).

        FACADE LIMITATION: ``chauvinism`` is graph edge-state, NOT a
        Relationship model field, so ``WorldState.from_graph`` drops it. In the
        canonical BRIDGED runner the graph persists in-place across ticks, so
        chauvinism accrues correctly. But the in-memory ``Simulation`` facade
        rebuilds the graph from ``WorldState`` each tick, resetting it to 0.0 —
        so chauvinism-driven defection cannot accumulate on that path. This is
        deliberate (adding it as a Relationship field would perturb
        serialization/determinism); the org/defection layer is a bridged-runner
        (spec-072+) concern, and the base canonical world seeds no player orgs.
        """
        current = float(edge.attributes.get("chauvinism", 0.0))
        increment = float(defines.chauvinism_base_rate)
        if self._is_superwaged(graph, edge.target_id):
            increment += float(defines.chauvinism_superwage_bonus)
        new_value = min(1.0, current + increment)
        graph.update_edge(edge.source_id, edge.target_id, EdgeType.MEMBERSHIP, chauvinism=new_value)
        return new_value

    @staticmethod
    def _is_superwaged(graph: GraphProtocol, member_id: str) -> bool:
        """True if the member holds a WAGES edge carrying a positive super-wage."""
        for edge in graph.query_edges(edge_type=EdgeType.WAGES):
            if edge.target_id != member_id:
                continue
            bonus = float(edge.attributes.get("super_wage_bonus", 0.0))
            if bonus > 0.0:
                return True
        return False

    @staticmethod
    def _org_discipline(graph: GraphProtocol, org_id: str, defines: Any) -> float:
        """Organizational discipline D: cadre_level if exposed, else the default."""
        org = graph.get_node(org_id)
        if org is not None:
            cadre = org.attributes.get("cadre_level")
            if isinstance(cadre, (int, float)):
                return float(cadre)
        return float(defines.defection_default_discipline)

    @staticmethod
    def _crisis_this_tick(services: ServiceContainer, tick: int) -> bool:
        bus = services.event_bus
        history = bus.get_history() if hasattr(bus, "get_history") else []
        return any(
            getattr(e, "tick", None) == tick and str(getattr(e, "type", "")) in _CRISIS_EVENT_TYPES
            for e in history
        )


# ----------------------------------------------------------------------
# Module helpers (mirror the spec-070 system conventions)
# ----------------------------------------------------------------------


def _extract_tick(context: ContextType) -> int:
    return int(context.get("tick", 0) if isinstance(context, dict) else getattr(context, "tick", 0))


def _coerce_role(raw: object) -> SocialRole | None:
    if isinstance(raw, SocialRole):
        return raw
    if isinstance(raw, str):
        try:
            return SocialRole(raw)
        except ValueError:
            return None
    return None


def _agitation_of(attrs: dict[str, Any]) -> float:
    ideology = attrs.get("ideology")
    if isinstance(ideology, dict):
        return float(ideology.get("agitation", 0.0))
    return 0.0
