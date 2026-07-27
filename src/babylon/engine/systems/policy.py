"""PolicySystem — LEGISLATE's resolver and the reform ceiling (P25 U9, ADR135).

Pipeline position 17.47: after AllegianceSystem (17.42, whose betrayal drift
term reads the PRIOR tick's delivery register — the one-tick lag is the
I-ORD grain) and before SovereigntySystem (17.5). Belongs to ``CONSEQUENCE``.

The system executes the agenda register through the pure pipeline of
:func:`~babylon.domain.politics.policy.resolve_legislate` at the bounded
rate ``politics.policy_agenda_rate`` (the-electoral-question.md §2.3/§2.4):

1. **Federal preemption** — a lower sovereign on the ADMINISTERS DAG
   enacting past ``preemption_envelope`` is nullified (``POLICY_PREEMPTED``).
2. **Judicial strike-down** — an RSA_JUDICIAL institution voids incidence
   past ``judicial_tolerance_scale × liberal_technocratic``
   (``POLICY_STRUCK``).
3. **The funding identity** (L-CEILING) — ``SW_deliverable = min(SW_promised,
   t_claim + φ_share·Φ_inflow − debt_service)`` plus deficit financing under
   bond discipline; the borrowed principal compounds the sovereign fiscal
   register and next tick's ``debt_service`` shrinks the ceiling.
4. **Overlay write** (``POLICY_ENACTED``) — effective NEXT tick by
   construction: the material base (positions 1–13) runs before 17.47, so a
   base consumer necessarily reads the prior tick's overlay (I-ORD).
5. **Capital strike** (``CAPITAL_STRIKE``) — incidence past
   ``capital_tolerance`` applies the SAME equalization operator the hex
   substrate carries (:func:`~babylon.domain.economics.substrate.
   equalization.equalization_deltas`) at county grain: the incidence enters
   the claimed counties' profit rates as a penalty, capital migrates out
   (``ΣΔc = 0``), and the moved ``tick_capital_stock`` is read the same
   tick by MarketScissors @17.8 and every tick after by the projections.

Fiscal facts are per-territory sums over the enacting sovereign's claimed
territories (top CLAIMS holder, the SovereigntySystem sort): ``t_claim =
Σ tick_taxes_on_surplus``; ``Φ_inflow = Σ tick_phi_hour · HOURS_PER_YEAR /
WEEKS_PER_YEAR`` (the ``flow_phi_accrued`` slicing — the tribute-pool inflow
FLOW is not published to the graph, ADR135 declares this Leontief proxy);
``debt_service = endogenous rate × sovereign debt stock`` (the rate live
since ADR089, the stock built by this unit).

Byte-safety (charter §U9(d)): the system reads ONLY register/agenda-keyed
state — an absent agenda AND absent fiscal register is a pure early return
(the DoctrineSystem idiom). None of the six qa:regression scenarios ever
carries either register, so all six are byte-unchanged with the system live.

Determinism (III.7): sorted iteration everywhere; FIFO agenda; no RNG.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Final

from babylon.domain.economics.distribution.sovereign_fiscal import (
    SovereignFiscalState,
    borrow,
    sovereign_debt_service,
)
from babylon.domain.economics.node_kinds import BoundaryEdgeKind, NodeKind
from babylon.domain.economics.substrate.equalization import equalization_deltas
from babylon.domain.politics.governance_endgame import (
    GovernanceArm,
    betrayal_crossed,
    dual_power_live,
    phi_share,
    resolve_governance_arm,
    rupture_geometry,
)
from babylon.domain.politics.policy import (
    FiscalTerrain,
    PolicyAgendaItem,
    PolicyResolution,
    PolicyResolutionKind,
    VetoGauntlet,
    resolve_legislate,
)
from babylon.formulas.constants import HOURS_PER_YEAR, WEEKS_PER_YEAR
from babylon.kernel.event_bus import Event
from babylon.kernel.system_base import SystemBase
from babylon.kernel.tick_partition import TickPartition
from babylon.models.enums import ApparatusType, EdgeType, EventType, NodeType

if TYPE_CHECKING:  # pragma: no cover
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol
    from babylon.kernel.system_protocol import ContextType
    from babylon.models.graph import GraphNode

#: FIFO agenda register: a list of ``PolicyAgendaItem.model_dump(mode="json")``
#: rows. Written by the LEGISLATE enqueue seam (OODA @14) and by scenario
#: builders; drained here at ``policy_agenda_rate`` per tick.
POLICY_AGENDA_ATTR: Final[str] = "policy_agenda"

#: Enacted overlays: ``{sovereign_id: {axis: {"magnitude", "enacted_tick",
#: "promised", "delivered"}}}``. Consumers read the PRIOR tick's value by
#: pipeline position (Survival @16 same-tick reads last tick's write since
#: 16 < 17.47; base systems 1–13 likewise) — effective next tick, I-ORD.
POLICY_OVERLAYS_ATTR: Final[str] = "policy_overlays"

#: Sovereign fiscal ledger: ``{sovereign_id:
#: SovereignFiscalState.model_dump()}`` — the debt STOCK half of
#: ``debt_service`` (the endogenous rate is NATIONAL_FINANCIAL_ATTR's).
SOVEREIGN_FISCAL_ATTR: Final[str] = "sovereign_fiscal"

#: Per-class delivery ledger: ``{class_id: {"incumbent_id", "promised",
#: "delivered", "gap", "integral", "tick"}}``. AllegianceSystem @17.42 reads
#: it NEXT tick for the betrayal drift term (θ.betrayal, ADR135); the
#: integral accumulates toward ``betrayal_threshold`` — crossing it fires
#: ``BETRAYAL_INTEGRAL_CROSSED`` once per class (U12, the SYRIZA-voter curve).
POLICY_DELIVERY_ATTR: Final[str] = "policy_delivery"

#: The governance-endgame register (U12 §3.5): ``{org_id: {"sovereign_id",
#: "opened_tick", "arm", "geometry", "contact"}}`` — ABSORBING, stamped once
#: at a governing party's FIRST ceiling contact (never re-resolved; never
#: written empty — the qa six carry no governments, TRAP-3 discipline).
#: ElectoralSystem @17.45 consumes it ONE TICK STALE (the I-ORD grain): the
#: Allende geometry falls the government via the suspension machinery; the
#: synthesis window spikes hope through the bridges.
GOVERNANCE_ENDGAME_ATTR: Final[str] = "governance_endgame"


def enqueue_agenda_item(graph: GraphProtocol, item: PolicyAgendaItem) -> None:
    """Append one drafted item to the FIFO agenda register.

    The LEGISLATE seam: the OODA dispatch calls this when the state AI
    selects the ADMINISTER/LEGISLATE sub-verb (before ADR135 that selection
    was misclassified as REPRESS at the StateAction→Action boundary).
    Scenario builders and tests seed agendas the same way.
    """
    agenda = list(graph.get_graph_attr(POLICY_AGENDA_ATTR, None) or [])
    agenda.append(item.model_dump(mode="json"))
    graph.set_graph_attr(POLICY_AGENDA_ATTR, agenda)


class PolicySystem(SystemBase):
    """Consequence-phase system executing the legislative agenda (U9)."""

    partition: ClassVar[TickPartition] = TickPartition.CONSEQUENCE
    position: ClassVar[float] = 17.47

    name: ClassVar[str] = "Policy"
    # Reform redistributes measured surplus; it never mints value. The
    # four-source license (ImperialRent, Dispossession, Decomposition,
    # Struggle) is untouched — L-CEILING (§5.5, W-A4 closure).
    creates_value: ClassVar[bool] = False

    def step(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        context: ContextType,
    ) -> None:
        wrapped = self._wrap_graph(graph)
        agenda_raw = wrapped.get_graph_attr(POLICY_AGENDA_ATTR, None)
        fiscal_raw = wrapped.get_graph_attr(SOVEREIGN_FISCAL_ATTR, None)
        if not agenda_raw and not fiscal_raw:
            # Empty-register guard (charter §U9(d), the DoctrineSystem
            # idiom): no agenda has ever been drafted and no sovereign
            # carries debt — zero reads of class/territory state, zero
            # writes, zero events. The qa six live here permanently.
            return

        defines = services.defines.politics
        agenda = [PolicyAgendaItem.model_validate(row) for row in (agenda_raw or [])]
        fiscal: dict[str, SovereignFiscalState] = {
            sovereign_id: SovereignFiscalState.model_validate(row)
            for sovereign_id, row in dict(fiscal_raw or {}).items()
        }
        overlays: dict[str, dict[str, Any]] = {
            sovereign_id: dict(axes)
            for sovereign_id, axes in dict(
                wrapped.get_graph_attr(POLICY_OVERLAYS_ATTR, None) or {}
            ).items()
        }
        delivery: dict[str, dict[str, Any]] = {
            class_id: dict(row)
            for class_id, row in dict(
                wrapped.get_graph_attr(POLICY_DELIVERY_ATTR, None) or {}
            ).items()
        }
        governance: dict[str, dict[str, Any]] = {
            org_id: dict(row)
            for org_id, row in dict(
                wrapped.get_graph_attr(GOVERNANCE_ENDGAME_ATTR, None) or {}
            ).items()
        }

        rate = max(1, int(defines.policy_agenda_rate))
        executed, remaining = agenda[:rate], agenda[rate:]
        for item in executed:
            terrain, claimed_ids = self._fiscal_terrain(wrapped, item.sovereign_id, fiscal)
            gauntlet = self._gauntlet(wrapped, item.sovereign_id)
            resolution = resolve_legislate(item, terrain, gauntlet, defines)
            self._apply(
                wrapped,
                services,
                context.tick,
                item,
                resolution,
                terrain,
                claimed_ids,
                fiscal,
                overlays,
                delivery,
                governance,
                defines,
            )

        if agenda_raw is not None or remaining:
            wrapped.set_graph_attr(
                POLICY_AGENDA_ATTR, [item.model_dump(mode="json") for item in remaining]
            )
        if fiscal:
            wrapped.set_graph_attr(
                SOVEREIGN_FISCAL_ATTR,
                {sovereign_id: state.model_dump() for sovereign_id, state in fiscal.items()},
            )
        if overlays:
            wrapped.set_graph_attr(POLICY_OVERLAYS_ATTR, overlays)
        if delivery:
            wrapped.set_graph_attr(POLICY_DELIVERY_ATTR, delivery)
        if governance:
            wrapped.set_graph_attr(GOVERNANCE_ENDGAME_ATTR, governance)

    # ------------------------------------------------------------------
    # Terrain readers
    # ------------------------------------------------------------------

    def _claimed_territories(self, graph: GraphProtocol, sovereign_id: str) -> list[GraphNode]:
        """Territories where the sovereign is the TOP claims-holder.

        The effective-controller reading (SovereigntySystem's sort:
        control desc, id asc). Sorted node iteration fixes the float
        summation order downstream (III.7).
        """
        claimed: list[GraphNode] = []
        for node in sorted(graph.query_nodes(node_type=NodeType.TERRITORY), key=lambda n: n.id):
            rows = graph.query_territory_claims(node.id)
            if rows and rows[0][0] == sovereign_id:
                claimed.append(node)
        return claimed

    def _fiscal_terrain(
        self,
        graph: GraphProtocol,
        sovereign_id: str,
        fiscal: dict[str, SovereignFiscalState],
    ) -> tuple[FiscalTerrain, list[str]]:
        """Sum the live per-territory fiscal facts over the claimed set.

        A territory missing a ``tick_`` attribute contributes nothing —
        honest absence (III.11), never a fabricated zero row.
        """
        t_claim = 0.0
        phi_inflow = 0.0
        total_surplus = 0.0
        phi_measured = False
        claimed = self._claimed_territories(graph, sovereign_id)
        for node in claimed:
            attrs = node.attributes
            t_claim += self._numeric(attrs.get("tick_taxes_on_surplus"))
            total_surplus += self._numeric(attrs.get("tick_total_surplus"))
            phi_raw = attrs.get("tick_phi_hour")
            if isinstance(phi_raw, (int, float)):
                # U12 E: presence, not just value — a 0.0 summed from ABSENT
                # attributes is unknowable, never peripheral (III.11).
                phi_measured = True
            phi_inflow += self._numeric(phi_raw) * HOURS_PER_YEAR / WEEKS_PER_YEAR
        prior = fiscal.get(sovereign_id)
        terrain = FiscalTerrain(
            t_claim=t_claim,
            phi_inflow=phi_inflow,
            interest_rate=self._interest_rate(graph),
            debt_stock=prior.debt_stock if prior is not None else 0.0,
            total_surplus=total_surplus,
            phi_measured=phi_measured,
        )
        return terrain, [node.id for node in claimed]

    @staticmethod
    def _numeric(value: object) -> float:
        return float(value) if isinstance(value, (int, float)) else 0.0

    def _interest_rate(self, graph: GraphProtocol) -> float:
        """The live endogenous rate, defensively (the market_scissors idiom).

        Absent financial layer ⟹ 0.0: no credit machinery, no debt service —
        honest absence, not a fabricated coupon.
        """
        raw = graph.get_graph_attr("national_financial", None)
        if not isinstance(raw, dict):
            return 0.0
        endogenous = raw.get("endogenous_interest")
        if not isinstance(endogenous, dict):
            return 0.0
        rate = endogenous.get("rate")
        return float(rate) if isinstance(rate, (int, float)) and rate > 0.0 else 0.0

    def _gauntlet(self, graph: GraphProtocol, sovereign_id: str) -> VetoGauntlet:
        """Assemble the veto terrain: ADMINISTERS parent + judicial benches."""
        parents = sorted(
            edge.source_id
            for edge in graph.query_edges(edge_type=EdgeType.ADMINISTERS)
            if edge.target_id == sovereign_id
        )
        benches: list[tuple[str, float]] = []
        for node in sorted(graph.query_nodes(node_type=NodeType.INSTITUTION), key=lambda n: n.id):
            if node.attributes.get("apparatus_type") != ApparatusType.RSA_JUDICIAL.value:
                continue
            balance = node.attributes.get("internal_balance")
            if not isinstance(balance, dict):
                continue
            weight = balance.get("liberal_technocratic")
            if isinstance(weight, (int, float)):
                benches.append((node.id, float(weight)))
        return VetoGauntlet(
            administers_parent=parents[0] if parents else None,
            judicial_benches=tuple(benches),
        )

    # ------------------------------------------------------------------
    # Resolution application
    # ------------------------------------------------------------------

    def _apply(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        item: PolicyAgendaItem,
        resolution: PolicyResolution,
        terrain: FiscalTerrain,
        claimed_ids: list[str],
        fiscal: dict[str, SovereignFiscalState],
        overlays: dict[str, dict[str, Any]],
        delivery: dict[str, dict[str, Any]],
        governance: dict[str, dict[str, Any]],
        defines: Any,
    ) -> None:
        if resolution.kind is PolicyResolutionKind.PREEMPTED:
            self._emit(
                services,
                tick,
                EventType.POLICY_PREEMPTED,
                {
                    "sovereign_id": item.sovereign_id,
                    "policy_axis": item.axis.value,
                    "preempting_sovereign": resolution.preempting_sovereign,
                },
            )
            self._resolve_fork(
                graph, services, tick, item, "preempted", terrain, claimed_ids, governance, defines
            )
            return
        if resolution.kind is PolicyResolutionKind.STRUCK:
            self._emit(
                services,
                tick,
                EventType.POLICY_STRUCK,
                {
                    "sovereign_id": item.sovereign_id,
                    "policy_axis": item.axis.value,
                    "striking_institution": resolution.striking_institution,
                },
            )
            self._resolve_fork(
                graph, services, tick, item, "struck", terrain, claimed_ids, governance, defines
            )
            return

        # §3.2 stance 3 / ADR137 deferral (U12): HOST DISCIPLINE. An
        # entryist's effective platform is clamped toward the host median at
        # ENACTMENT — a projection operator, never a campaign-time edit. The
        # standing overlay on the axis IS the machine's median (the duopoly
        # governs through the status quo ante); the entryist enacts only
        # ``1 - host_discipline_clamp_share`` of the distance it demanded.
        # The clamped share of funded delivery is charged to the entryist's
        # OWN delivery ledger (the scaled ``delivered`` below), and the
        # treasury floats only what the enacted fraction needs (borrowed
        # scales with it). Capital's strike response is NOT scaled: capital
        # reacts to the platform attempted, not the fraction permitted.
        enacted_magnitude = item.magnitude
        if self._is_host_disciplined(graph, item):
            standing = self._numeric(
                overlays.get(item.sovereign_id, {}).get(item.axis.value, {}).get("magnitude")
            )
            enacted_magnitude = standing + (item.magnitude - standing) * (
                1.0 - float(defines.host_discipline_clamp_share)
            )
        factor = enacted_magnitude / item.magnitude if item.magnitude > 0.0 else 1.0
        if factor != 1.0:
            delivered = resolution.delivered * factor
            resolution = resolution.model_copy(
                update={
                    "delivered": delivered,
                    "gap": resolution.promised - delivered,
                    "ratio": delivered / resolution.promised if resolution.promised > 0.0 else 1.0,
                    "borrowed": resolution.borrowed * factor,
                }
            )

        overlays.setdefault(item.sovereign_id, {})[item.axis.value] = {
            "magnitude": enacted_magnitude,
            "enacted_tick": tick,
            "promised": resolution.promised,
            "delivered": resolution.delivered,
        }
        self._emit(
            services,
            tick,
            EventType.POLICY_ENACTED,
            {
                "sovereign_id": item.sovereign_id,
                "policy_axis": item.axis.value,
                "magnitude": enacted_magnitude,
                "delivery_ratio": resolution.ratio,
            },
        )
        if resolution.borrowed > 0.0:
            prior = fiscal.get(
                item.sovereign_id, SovereignFiscalState(sovereign_id=item.sovereign_id)
            )
            fiscal[item.sovereign_id] = borrow(prior, resolution.borrowed)
        if item.promised > 0.0:
            self._record_funding_receipt(services, tick, item, resolution, terrain)
            self._split_delivery(graph, services, tick, item, resolution, delivery, defines)
        if resolution.gap > 0.0:
            # The funding identity bound (bond arm of the gauntlet): the
            # ceiling was touched even though the item enacted.
            self._resolve_fork(
                graph, services, tick, item, "fiscal", terrain, claimed_ids, governance, defines
            )
        if resolution.capital_strike:
            outflow = self._apply_capital_strike(graph, claimed_ids, resolution.incidence, defines)
            self._emit(
                services,
                tick,
                EventType.CAPITAL_STRIKE,
                {
                    "sovereign_id": item.sovereign_id,
                    "incidence": resolution.incidence,
                    "tolerance": float(defines.capital_tolerance),
                    "outflow": outflow,
                },
            )
            self._resolve_fork(
                graph,
                services,
                tick,
                item,
                "capital_strike",
                terrain,
                claimed_ids,
                governance,
                defines,
            )

    def _resolve_fork(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        item: PolicyAgendaItem,
        contact: str,
        terrain: FiscalTerrain,
        claimed_ids: list[str],
        governance: dict[str, dict[str, Any]],
        defines: Any,
    ) -> None:
        """First ceiling contact IN OFFICE resolves the SYRIZA fork (§3.5).

        The fork belongs to the GOVERNING PARTY (the ``_incumbent`` seam —
        no seated government, no fork; the qa six live there). The register
        is absorbing: one resolution per org, ever. Arm and geometry are the
        pure :mod:`~babylon.domain.politics.governance_endgame` laws over
        already-measured quantities: the org's ``institutional_pull`` (U11
        Michels accumulator), the live dual-power structure on the claimed
        terrain (the DUAL_POWER read path — the same >= 2-active-claimants
        predicate SovereigntySystem @17.5 emits for), the org's SOLIDARITY
        bridges, and the terrain's Φ share. Consequences execute in
        ElectoralSystem @17.45 NEXT tick (I-ORD).
        """
        incumbent = self._incumbent(graph, item.sovereign_id)
        if incumbent == item.sovereign_id or incumbent in governance:
            return
        org = graph.get_node(incumbent)
        if org is None:
            return
        claims = {
            territory_id: tuple(
                (row[0], row[1]) for row in graph.query_territory_claims(territory_id)
            )
            for territory_id in claimed_ids
        }
        arm = resolve_governance_arm(
            institutional_pull=self._numeric(org.attributes.get("institutional_pull")),
            capture_threshold=float(defines.governance_capture_threshold),
            organs_live=dual_power_live(claims),
        )
        geometry = ""
        if arm is GovernanceArm.RUPTURE:
            # The same measured-share predicate as E's periphery mirror
            # (III.11: an unmeasured Φ is never called starvation).
            starved = terrain.phi_measured and phi_share(
                terrain.phi_inflow, terrain.total_surplus
            ) < float(defines.periphery_phi_share_floor)
            geometry = rupture_geometry(
                bridges_present=self._org_bridges(graph, incumbent),
                phi_starved=starved,
            ).value
        governance[incumbent] = {
            "sovereign_id": item.sovereign_id,
            "opened_tick": tick,
            "arm": arm.value,
            "geometry": geometry,
            "contact": contact,
        }
        self._emit(
            services,
            tick,
            EventType.GOVERNANCE_FORK_RESOLVED,
            {
                "org_id": incumbent,
                "sovereign_id": item.sovereign_id,
                "arm": arm.value,
                "geometry": geometry,
                "contact": contact,
            },
        )

    @staticmethod
    def _org_bridges(graph: GraphProtocol, org_id: str) -> bool:
        """A live SOLIDARITY edge incident to the org — the base's bridges
        (twin of ElectoralSystem's class-side ``_has_bridges``; the org
        scale is U11's SOLIDARITY_MASS practice variable as a predicate)."""
        for edge in graph.query_edges(edge_type=EdgeType.SOLIDARITY):
            if edge.source_id == org_id or edge.target_id == org_id:
                strength = edge.attributes.get("solidarity_strength", 0.0)
                if isinstance(strength, (int, float)) and strength > 0.0:
                    return True
        return False

    @staticmethod
    def _record_funding_receipt(
        services: ServicesProtocol,
        tick: int,
        item: PolicyAgendaItem,
        resolution: PolicyResolution,
        terrain: FiscalTerrain,
    ) -> None:
        """L-RECEIPTS (§4): the Φ slice this enactment actually consumed.

        Declared decomposition convention (ADR139): the domestic tax claim
        (net of debt service) absorbs the funded delivery first; whatever
        remains came out of the tribute pool — one ``FISCAL_FUNDING`` row,
        pool → sovereign fisc, recorded only when positive. The chain's
        upstream half already has rows (``DRAIN_EDGE`` pool inflows,
        ``EXPLOITATION_FLOW`` at the source); this is the missing middle
        hop. Guarded like every register writer: no bound register (unit
        tests, the qa six) — a clean no-op.
        """
        register = getattr(services, "boundary_register", None)
        if register is None or register.session_id is None:
            return
        service = sovereign_debt_service(terrain.debt_stock, terrain.interest_rate)
        net_domestic = max(0.0, terrain.t_claim - service)
        funded = resolution.delivered - resolution.borrowed
        phi_consumed = max(0.0, funded - net_domestic)
        if phi_consumed <= 0.0:
            return
        register.record(
            session_id=register.session_id,
            tick=tick,
            source_node_id="USA",
            source_kind=NodeKind.NATIONAL,
            dest_node_id=item.sovereign_id,
            dest_kind=NodeKind.SOVEREIGN,
            flow_type=BoundaryEdgeKind.FISCAL_FUNDING,
            magnitude=phi_consumed,
        )

    def _split_delivery(
        self,
        graph: GraphProtocol,
        services: ServicesProtocol,
        tick: int,
        item: PolicyAgendaItem,
        resolution: PolicyResolution,
        delivery: dict[str, dict[str, Any]],
        defines: Any,
    ) -> None:
        """Split the promise/delivery over classes by subsistence weight.

        The delivery gap is measured PER CLASS, per incumbent (§2.4) —
        it is the single most load-bearing new quantity of the design:
        the betrayal drift term (AllegianceSystem, next tick) and U10's
        betrayal integral both read this ledger.
        """
        default_subsistence = services.defines.survival.default_subsistence
        classes = sorted(
            (
                node
                for node in graph.query_nodes(node_type=NodeType.SOCIAL_CLASS)
                if node.attributes.get("active", True)
            ),
            key=lambda n: n.id,
        )
        weights = {
            node.id: self._numeric(
                node.attributes.get("subsistence_threshold", default_subsistence)
            )
            for node in classes
        }
        total_weight = sum(weights.values())
        if total_weight <= 0.0:
            return
        incumbent = self._incumbent(graph, item.sovereign_id)
        threshold = float(defines.betrayal_threshold)
        register = getattr(services, "boundary_register", None)
        for node in classes:
            share = weights[node.id] / total_weight
            promised_c = resolution.promised * share
            delivered_c = resolution.delivered * share
            gap_c = resolution.gap * share
            if delivered_c > 0.0 and register is not None and register.session_id is not None:
                # L-RECEIPTS (§4): the delivered unit itself — sovereign →
                # class, the row the Archive walks back from.
                register.record(
                    session_id=register.session_id,
                    tick=tick,
                    source_node_id=item.sovereign_id,
                    source_kind=NodeKind.SOVEREIGN,
                    dest_node_id=node.id,
                    dest_kind=NodeKind.SOCIAL_CLASS,
                    flow_type=BoundaryEdgeKind.SOCIAL_WAGE,
                    magnitude=delivered_c,
                )
            prior_integral = self._numeric(delivery.get(node.id, {}).get("integral"))
            integral = prior_integral + gap_c
            delivery[node.id] = {
                "incumbent_id": incumbent,
                "promised": promised_c,
                "delivered": delivered_c,
                "gap": gap_c,
                "integral": integral,
                "tick": tick,
            }
            if gap_c > 0.0:
                self._emit(
                    services,
                    tick,
                    EventType.DELIVERY_GAP_CROSSED,
                    {
                        "class_id": node.id,
                        "incumbent_id": incumbent,
                        "gap": gap_c,
                        "betrayal_integral": integral,
                    },
                )
            if betrayal_crossed(integral, threshold) and not betrayal_crossed(
                prior_integral, threshold
            ):
                # The edge trigger of the SYRIZA-voter curve (U12): fires
                # exactly once per class — patience, once ruptured, stays
                # ruptured; ElectoralSystem opens the window next tick.
                self._emit(
                    services,
                    tick,
                    EventType.BETRAYAL_INTEGRAL_CROSSED,
                    {
                        "class_id": node.id,
                        "incumbent_id": incumbent,
                        "integral": integral,
                        "threshold": threshold,
                    },
                )

    @staticmethod
    def _is_host_disciplined(graph: GraphProtocol, item: PolicyAgendaItem) -> bool:
        """Whether the item's drafting org faces the host-discipline clamp.

        True iff ``item.source_org_id`` names an org holding the
        ``entryism`` doctrine stance (the U11 reformist-fork vocabulary) AND
        absent from the ``electoral_derecognized`` register (read by raw
        string — ElectoralSystem @17.45 owns the write, two positions
        earlier; the expelled face the plain gauntlet, not the clamp).
        Scenario-seeded items (empty source) are never clamped.
        """
        if not item.source_org_id:
            return False
        org = graph.get_node(item.source_org_id)
        if org is None:
            return False
        if "entryism" not in tuple(org.attributes.get("acquired_doctrine_ids") or ()):
            return False
        derecognized = frozenset(graph.get_graph_attr("electoral_derecognized", ()) or ())
        return item.source_org_id not in derecognized

    @staticmethod
    def _incumbent(graph: GraphProtocol, sovereign_id: str) -> str:
        """The delivery incumbent: the sovereign's GOVERNING PARTY when
        ElectoralSystem @17.45 seated one this tick (read from the
        ``electoral_governments`` register by raw string — the writer runs
        one position earlier), else the enacting sovereign itself.

        This is what lights U9's θ.betrayal drift term (ADR134 §5, ADR135):
        the gap accrues against a party id AllegianceSystem's incumbent
        match can find, not just the abstract sovereign.
        """
        governments = graph.get_graph_attr("electoral_governments", None)
        if isinstance(governments, dict):
            row = governments.get(sovereign_id)
            if isinstance(row, dict):
                party_id = row.get("party_id")
                if isinstance(party_id, str) and party_id:
                    return party_id
        return sovereign_id

    def _apply_capital_strike(
        self,
        graph: GraphProtocol,
        claimed_ids: list[str],
        incidence: float,
        defines: Any,
    ) -> float:
        """Arm 1: the equalization operator with the incidence as a penalty.

        The incidence depresses the CLAIMED counties' profit rates; the
        same conservation-preserving law the hex substrate carries then
        migrates capital toward the unpenalized geographies (``ΣΔc = 0``).
        With nowhere to run (every capital-bearing territory claimed), the
        gradient is uniform and nothing moves — a national policy cannot
        be fled domestically; the bond and judicial arms still bite.

        Returns the total outflow from the claimed set (the CAPITAL_STRIKE
        payload's material receipt).
        """
        claimed = set(claimed_ids)
        capitals: dict[str, float] = {}
        rates: dict[str, float] = {}
        for node in sorted(graph.query_nodes(node_type=NodeType.TERRITORY), key=lambda n: n.id):
            attrs = node.attributes
            capital = attrs.get("tick_capital_stock")
            profit_rate = attrs.get("tick_profit_rate")
            if not isinstance(capital, (int, float)) or not isinstance(profit_rate, (int, float)):
                continue
            if capital <= 0.0:
                continue
            capitals[node.id] = float(capital)
            penalty = incidence if node.id in claimed else 0.0
            rates[node.id] = float(profit_rate) - penalty
        if not capitals:
            return 0.0
        deltas = equalization_deltas(
            capitals,
            rates,
            float(defines.strike_equalization_rate),
        )
        outflow = 0.0
        for territory_id, delta in deltas.items():
            if delta != 0.0:
                graph.update_node(territory_id, tick_capital_stock=capitals[territory_id] + delta)
            if territory_id in claimed and delta < 0.0:
                outflow += -delta
        return outflow

    @staticmethod
    def _emit(
        services: ServicesProtocol,
        tick: int,
        event_type: EventType,
        payload: dict[str, Any],
    ) -> None:
        services.event_bus.publish(Event(type=event_type, tick=tick, payload=payload))


__all__ = [
    "GOVERNANCE_ENDGAME_ATTR",
    "POLICY_AGENDA_ATTR",
    "POLICY_DELIVERY_ATTR",
    "POLICY_OVERLAYS_ATTR",
    "SOVEREIGN_FISCAL_ATTR",
    "PolicySystem",
    "enqueue_agenda_item",
]
